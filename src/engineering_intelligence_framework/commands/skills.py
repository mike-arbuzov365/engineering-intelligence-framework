"""Model-free validation для canonical EIF skills і starter profiles."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from ..resources import framework_root
from ..workspace_contract import schema_data

CONTRACT_PATH = Path("tests/contract.yaml")
MAX_CONTRACT_BYTES = 16_384


class SkillContractError(RuntimeError):
    """Skill contract не можна безпечно прочитати або перевірити."""


@dataclass(frozen=True)
class SkillRecord:
    name: str
    profile: str
    directory: Path
    manifest: Path
    contract: Path


def discover_skill_records(root: Path) -> list[SkillRecord]:
    """Повертає deterministic inventory core і starter-profile skills."""
    root = root.resolve()
    records: list[SkillRecord] = []

    core_root = root / "skills"
    if core_root.is_dir():
        for directory in sorted(core_root.iterdir()):
            manifest = directory / "SKILL.md"
            if directory.is_dir() and manifest.is_file():
                records.append(
                    SkillRecord(
                        name=directory.name,
                        profile="core",
                        directory=directory,
                        manifest=manifest,
                        contract=directory / CONTRACT_PATH,
                    )
                )

    profiles_root = root / "professional-profiles"
    if profiles_root.is_dir():
        for profile_dir in sorted(profiles_root.iterdir()):
            skills_root = profile_dir / "skills"
            if not profile_dir.is_dir() or not skills_root.is_dir():
                continue
            for directory in sorted(skills_root.iterdir()):
                manifest = directory / "SKILL.md"
                if directory.is_dir() and manifest.is_file():
                    records.append(
                        SkillRecord(
                            name=directory.name,
                            profile=profile_dir.name,
                            directory=directory,
                            manifest=manifest,
                            contract=directory / CONTRACT_PATH,
                        )
                    )

    return sorted(records, key=lambda item: (item.profile, item.name))


def _load_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise SkillContractError(f"cannot parse {path}: {error}") from error


def _frontmatter(manifest: Path) -> dict[str, Any]:
    text = manifest.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise SkillContractError(f"{manifest}: missing YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise SkillContractError(f"{manifest}: unclosed YAML frontmatter")
    try:
        data = yaml.safe_load(text[4:end])
    except yaml.YAMLError as error:
        raise SkillContractError(f"{manifest}: invalid YAML frontmatter: {error}") from error
    if not isinstance(data, dict):
        raise SkillContractError(f"{manifest}: frontmatter must be a mapping")
    return data


def _schema_errors(data: Any) -> list[str]:
    validator = Draft202012Validator(schema_data("skill-contract.schema.json"))
    errors = sorted(validator.iter_errors(data), key=lambda error: list(error.path))
    return [
        f"{'.'.join(str(item) for item in error.path) or '(root)'}: {error.message}"
        for error in errors
    ]


def _contained(root: Path, relative: str, label: str) -> tuple[Path | None, str | None]:
    root = root.resolve()
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        return None, f"{label} escapes framework root: {relative}"
    candidate = (root / path).resolve()
    if not candidate.is_relative_to(root):
        return None, f"{label} escapes framework root: {relative}"
    return candidate, None


def _support_files(directory: Path, subdir: str) -> set[str]:
    root = directory / subdir
    if not root.is_dir():
        return set()
    return {
        path.relative_to(directory).as_posix()
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }


def _paragraphs(text: str) -> set[str]:
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            text = text[end + 5 :]
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    paragraphs: set[str] = set()
    for block in re.split(r"\n\s*\n", text):
        lines = [line.strip() for line in block.splitlines()]
        if not lines or any(line.startswith(("#", "- ", "* ", "1.")) for line in lines):
            continue
        normalized = " ".join(" ".join(lines).split())
        if len(normalized) >= 120:
            paragraphs.add(normalized.casefold())
    return paragraphs


def validate_record(root: Path, record: SkillRecord) -> list[str]:
    """Перевіряє один manifest і local contract без виконання scripts."""
    errors: list[str] = []
    label = record.contract.relative_to(root).as_posix()
    if not record.contract.is_file():
        return [f"{label}: missing local contract fixture"]
    if record.contract.stat().st_size > MAX_CONTRACT_BYTES:
        errors.append(f"{label}: fixture exceeds {MAX_CONTRACT_BYTES} bytes")

    try:
        data = _load_yaml(record.contract)
    except SkillContractError as error:
        return [str(error)]
    if not isinstance(data, dict):
        return [f"{label}: fixture must be a mapping"]
    errors.extend(f"{label}: {error}" for error in _schema_errors(data))
    if errors:
        return errors

    try:
        manifest_data = _frontmatter(record.manifest)
        manifest_text = record.manifest.read_text(encoding="utf-8")
    except (OSError, UnicodeError, SkillContractError) as error:
        return [str(error)]

    skill = data["skill"]
    if skill["name"] != record.name:
        errors.append(f"{label}: skill.name differs from directory {record.name!r}")
    if skill["profile"] != record.profile:
        errors.append(f"{label}: skill.profile differs from {record.profile!r}")
    if manifest_data.get("name") != record.name:
        errors.append(f"{record.manifest}: frontmatter name differs from directory")
    description = manifest_data.get("description")
    if not isinstance(description, str) or not description.strip():
        errors.append(f"{record.manifest}: frontmatter description is required")

    reference_texts: dict[str, str] = {}
    for relative in data["references"]["required"]:
        path, containment_error = _contained(root, relative, "required reference")
        if containment_error:
            errors.append(f"{label}: {containment_error}")
            continue
        assert path is not None
        if not path.is_file():
            errors.append(f"{label}: required reference is missing: {relative}")
            continue
        try:
            reference_texts[relative] = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            errors.append(f"{label}: cannot read reference {relative}: {error}")

    canonical_relative = skill["canonical_workflow"]
    canonical_path, containment_error = _contained(
        root, canonical_relative, "canonical workflow"
    )
    canonical_text = ""
    if containment_error:
        errors.append(f"{label}: {containment_error}")
    elif canonical_path is None or not canonical_path.is_file():
        errors.append(f"{label}: canonical workflow is missing: {canonical_relative}")
    else:
        canonical_text = canonical_path.read_text(encoding="utf-8")
        # A self-contained skill is its own canonical workflow. Requiring it to
        # list itself as a reference, and to name its own filename in its own
        # body, would be bookkeeping that proves nothing.
        points_at_itself = canonical_path.resolve() == record.manifest.resolve()
        if not points_at_itself:
            if canonical_relative not in data["references"]["required"]:
                errors.append(
                    f"{label}: canonical workflow must be a required reference"
                )
            if canonical_path.name not in manifest_text:
                errors.append(
                    f"{record.manifest}: does not point to canonical workflow"
                )

    combined = "\n".join([manifest_text, *reference_texts.values()])
    # Grounding is a raw substring match, so a token that is present in the
    # prose but split by a line wrap reads as absent. That failure looks like
    # a missing rule and is actually a hard wrap, so say which one it is.
    unwrapped = " ".join(combined.split())
    for section in ("evidence", "commands", "stop_conditions", "forbidden_behavior"):
        for token in data[section]["required"]:
            if token in combined:
                continue
            if " ".join(token.split()) in unwrapped:
                errors.append(
                    f"{label}: {section} token {token!r} is split across a line "
                    "break in the prose; keep the phrase on one line"
                )
            else:
                errors.append(f"{label}: {section} token is not grounded: {token!r}")
    for token in data["assertions"]["manifest_contains"]:
        if token not in manifest_text:
            errors.append(f"{label}: manifest missing asserted token: {token!r}")
    for token in data["assertions"]["canonical_contains"]:
        if token not in canonical_text:
            errors.append(f"{label}: canonical workflow missing token: {token!r}")
    for token in data["assertions"]["manifest_not_contains"]:
        if token in manifest_text:
            errors.append(f"{label}: forbidden manifest token found: {token!r}")

    trigger_ids: set[str] = set()
    positive_prompts: set[str] = set()
    negative_prompts: set[str] = set()
    for category, target in (
        ("positive", positive_prompts),
        ("negative", negative_prompts),
    ):
        for scenario in data["triggers"][category]:
            scenario_id = scenario["id"]
            if scenario_id in trigger_ids:
                errors.append(f"{label}: duplicate trigger id: {scenario_id}")
            trigger_ids.add(scenario_id)
            target.add(" ".join(scenario["prompt"].casefold().split()))
    overlap = sorted(positive_prompts & negative_prompts)
    if overlap:
        errors.append(f"{label}: positive and negative trigger prompts overlap")

    declared_scripts = {item["path"] for item in data["supporting_files"]["scripts"]}
    declared_references = {
        item["path"] for item in data["supporting_files"]["references"]
    }
    actual_scripts = _support_files(record.directory, "scripts")
    actual_references = _support_files(record.directory, "references")
    if declared_scripts != actual_scripts:
        errors.append(
            f"{label}: scripts declaration mismatch: "
            f"declared={sorted(declared_scripts)} actual={sorted(actual_scripts)}"
        )
    if declared_references != actual_references:
        errors.append(
            f"{label}: references declaration mismatch: "
            f"declared={sorted(declared_references)} actual={sorted(actual_references)}"
        )
    for declaration in data["supporting_files"]["scripts"]:
        path = record.directory / declaration["path"]
        if path.is_file():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != declaration["sha256"]:
                errors.append(
                    f"{label}: script digest mismatch for {declaration['path']}"
                )

    # The thin-pointer rule assumes two files: a manifest that points, and a
    # canonical workflow that carries the prose. A self-contained skill
    # declares itself as its own canonical workflow, and then every paragraph
    # trivially "duplicates" - the same file compared against itself. Skip the
    # check there rather than report a defect the author cannot fix without
    # splitting a one-file skill in two for no reader's benefit.
    self_canonical = (
        canonical_path is not None
        and canonical_path.resolve() == record.manifest.resolve()
    )
    if not self_canonical:
        duplicated = _paragraphs(manifest_text) & _paragraphs(canonical_text)
        if duplicated:
            errors.append(
                f"{record.manifest}: duplicates canonical workflow prose; keep a thin pointer"
            )
    return errors


def check_framework(root: Path) -> tuple[list[SkillRecord], list[str]]:
    records = discover_skill_records(root)
    errors: list[str] = []
    if not records:
        errors.append(f"{root}: no canonical skills found")
    for record in records:
        errors.extend(validate_record(root.resolve(), record))
    return records, errors


# A project instance keeps its own canonical skills in one of these, relative
# to the project root. `skills/` is the override location the generated
# loaders already point at; `docs/skills/` is the location an adopting
# project uses when it files skills with the rest of its documentation.
PROJECT_SKILL_ROOTS = ("skills", "docs/skills")

GENERATED_LOADER_MARKER = "<!-- eif:generated-skill-loader -->"


def discover_project_skill_records(project_root: Path) -> list[SkillRecord]:
    """Повертає canonical project-owned skills, без generated loaders.

    An agent-discovery directory such as `.claude/skills/` or `.agents/skills/`
    holds generated pointers, not canonical workflows. Validating those as
    skills would report a contract failure for every one of them, so the
    marker is what separates a real skill from a loader.
    """
    project_root = project_root.resolve()
    records: list[SkillRecord] = []
    seen: set[str] = set()
    for relative in PROJECT_SKILL_ROOTS:
        skills_root = project_root / relative
        if not skills_root.is_dir():
            continue
        for directory in sorted(skills_root.iterdir()):
            manifest = directory / "SKILL.md"
            if not directory.is_dir() or not manifest.is_file():
                continue
            if directory.name in seen:
                continue
            try:
                if GENERATED_LOADER_MARKER in manifest.read_text(encoding="utf-8"):
                    continue
            except (OSError, UnicodeError):
                continue
            seen.add(directory.name)
            contract = directory / CONTRACT_PATH
            # A project names its own profile. The framework's own records get
            # their profile from the directory they sit in; a project has no
            # such directory, so forcing a literal "project" here would report
            # a mismatch against every contract that declares anything else.
            declared = "project"
            if contract.is_file():
                loaded = _load_yaml(contract)
                if isinstance(loaded, dict):
                    skill_block = loaded.get("skill")
                    if isinstance(skill_block, dict):
                        value = skill_block.get("profile")
                        if isinstance(value, str) and value.strip():
                            declared = value.strip()
            records.append(
                SkillRecord(
                    name=directory.name,
                    profile=declared,
                    directory=directory,
                    manifest=manifest,
                    contract=contract,
                )
            )
    return sorted(records, key=lambda item: item.name)


EVAL_FIXTURES_PATH = Path("evals") / "evals.json"


def validate_eval_fixtures(root: Path, record: SkillRecord) -> list[str]:
    """Перевіряє model-free eval fixtures скіла, якщо вони існують.

    This is deliberately not the behavioral eval manifest in
    `core/schemas/skill-eval-manifest.schema.json`. That one describes a
    comparative run with a model, a budget and an owner gate, and it is
    admission gate 7. Fixtures are the cheap tier below it: a set of prompts
    with outcomes that must or must not appear, checkable without calling
    anything. Absent fixtures are not an error; a malformed set is.
    """
    path = record.directory / EVAL_FIXTURES_PATH
    if not path.is_file():
        return []
    label = path.relative_to(root).as_posix()
    errors: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return [f"{label}: cannot parse eval fixtures: {error}"]

    if not isinstance(data, dict):
        return [f"{label}: eval fixtures must be an object"]
    if data.get("schema_version") != 1:
        errors.append(f"{label}: schema_version must be 1")
    if data.get("skill") != record.name:
        errors.append(
            f"{label}: skill must be {record.name!r}, got {data.get('skill')!r}"
        )

    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        errors.append(f"{label}: cases must be a non-empty array")
        return errors

    seen_ids: set[str] = set()
    for index, case in enumerate(cases):
        where = f"{label}: cases[{index}]"
        if not isinstance(case, dict):
            errors.append(f"{where}: must be an object")
            continue
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id.strip():
            errors.append(f"{where}: id must be a non-empty string")
        elif case_id in seen_ids:
            errors.append(f"{where}: duplicate case id: {case_id!r}")
        else:
            seen_ids.add(case_id)
        prompt = case.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            errors.append(f"{where}: prompt must be a non-empty string")
        required = case.get("required_outcomes") or []
        forbidden = case.get("forbidden_outcomes") or []
        for key, value in (("required_outcomes", required), ("forbidden_outcomes", forbidden)):
            if not isinstance(value, list) or any(
                not isinstance(item, str) or not item.strip() for item in value
            ):
                errors.append(f"{where}: {key} must be an array of non-empty strings")
        # A case that asserts nothing passes trivially and is worse than no
        # case at all, because it inflates the fixture count.
        if not required and not forbidden:
            errors.append(
                f"{where}: needs at least one required_outcomes or "
                "forbidden_outcomes entry"
            )
    return errors


def check_project(project_root: Path) -> tuple[list[SkillRecord], list[str]]:
    """Валідує project-owned skills тим самим контрактом, що й framework ones.

    A project with no skills of its own is not an error: most projects have
    none, and failing there would make the flag unusable as a default.
    """
    records = discover_project_skill_records(project_root)
    errors: list[str] = []
    root = project_root.resolve()
    for record in records:
        errors.extend(validate_record(root, record))
        errors.extend(validate_eval_fixtures(root, record))
    return records, errors


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="eifctl skills", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="Validate local skill contracts without model calls.")
    check.add_argument(
        "--framework-root",
        type=Path,
        default=None,
        help="Framework source/resource root; defaults to the installed package.",
    )
    check.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help=(
            "Also validate project-owned skills under <root>/skills or "
            "<root>/docs/skills. Generated loader directories are skipped."
        ),
    )
    check.add_argument(
        "--project-only",
        action="store_true",
        help="Validate only project-owned skills; requires --project-root.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command != "check":
        raise AssertionError(f"unhandled command: {args.command}")

    if args.project_only and args.project_root is None:
        print("FAIL --project-only requires --project-root", file=sys.stderr)
        return 2

    records: list[SkillRecord] = []
    errors: list[str] = []

    if not args.project_only:
        if args.framework_root is not None:
            root = args.framework_root.expanduser().resolve()
            records, errors = check_framework(root)
        else:
            with framework_root() as packaged_root:
                root = packaged_root.resolve()
                records, errors = check_framework(root)

    if args.project_root is not None:
        project_root = args.project_root.expanduser().resolve()
        project_records, project_errors = check_project(project_root)
        records = records + project_records
        errors = errors + project_errors

    if errors:
        for error in errors:
            print(f"FAIL {error}", file=sys.stderr)
        print(
            f"EIF-RESULT: passed=0 total={len(records)} errors={len(errors)}",
            file=sys.stderr,
        )
        return 1

    for record in records:
        print(f"PASS skill contract: {record.name} profile={record.profile}")
    print(f"EIF-RESULT: passed={len(records)} total={len(records)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
