# Task: implement `is_leap_year`

<!-- Written from templates/task-scope.md, filled in for this demo task. -->

## Goal

Implement `is_leap_year(year)` in `src/calendar_utils.py` so that
`tests/test_calendar_utils.py` passes.

## Experience retrieval preflight

- Searched for: `leap year`
  (`python scripts/eif_search_knowledge.py --knowledge-root examples/demo-workspace/knowledge "leap year"`,
  run from the framework root)
- Found:
  - `failure-patterns/PATTERN-0001-naive-leap-year-check.md` (score 44) -
    warns that the obvious `year % 4 == 0` implementation is wrong for
    century years not divisible by 400, and that a test suite covering
    only 2000 (or only "recent" years) will not catch the bug.
  - `facts/FACT-0001-gregorian-leap-year-rule.md` (score 21) - states the
    actual rule: divisible by 4, except centuries, unless divisible by 400.
- How it changes the plan: implement the rule from `FACT-0001` directly -
  `year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)` - instead of
  the naive `year % 4 == 0` a first pass would plausibly reach for. This
  is not a hypothetical: `tests/test_calendar_utils.py` already contains
  `test_century_year_not_divisible_by_400_is_not_leap`, which the naive
  version would fail.

## In scope

- `src/calendar_utils.py`: implement `is_leap_year`.

## Out of scope / do not touch

- `tests/test_calendar_utils.py` - the test defines the required
  behavior; it is not to be edited to make an incorrect implementation
  pass.
- Anything outside `examples/demo-workspace/`.

## Verification

```
python examples/demo-workspace/tests/test_calendar_utils.py -v
```

## Exit criteria

- [ ] `is_leap_year` no longer raises `NotImplementedError`.
- [ ] `python examples/demo-workspace/tests/test_calendar_utils.py -v`
      exits 0 with all 4 tests passing, including the century-year cases.
- [ ] Implementation matches `FACT-0001`'s rule, not the naive check
      `PATTERN-0001` warns against.

## Stop conditions

None encountered - the retrieved fact fully specifies the required
behavior.
