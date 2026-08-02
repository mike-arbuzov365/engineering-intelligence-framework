---
type: failure_pattern
status: validated
evidence: OBSERVED
source: retro
confidence: high
created: 2026-08-02
review_after: 2026-11-02
scope: framework
---

# Failure patterns

<!-- Knowledge source: RETRO-001 of the preo-web project instance, 2026-08-02,
covering 2026-07-22..2026-08-02 across three repositories. Each pattern below
is listed only because it repeated; single occurrences stayed in that
instance's retro inbox as notes. -->

A recurring error pattern, not a single incident. A lesson that shows up once
is a note; the same lesson three times is a rule the framework was missing.

Each entry states the shape, the evidence that it repeats, and the cheapest
check that catches it. The check matters more than the description: a pattern
you can only recognise in hindsight is not yet actionable.

## FP-001: shipped but never wired

Something is built correctly and nothing carries it the last step to where it
would actually run. The artifact exists, the code compiles, the tests pass,
and the capability does not exist for whoever was supposed to use it.

**Evidence of repetition** - four occurrences, three codebases, one of them
this framework, twice:

| Occurrence | Built | Missing last step |
|---|---|---|
| Test suites, EIF 0.2.0 | suites in the repository | not registered in the run inventory, so no workflow ran them |
| Skills, EIF through 0.2.4 | 11 skills copied into every instance's runtime | nothing wrote to the directory each adapter actually reads |
| Knowledge corpus, project instance | a provisioning method | called only from tests |
| Intake channel, project instance | column and migration | no production code ever assigned it |

**Why it survives.** The failure is silent by construction. Nothing throws,
nothing turns red, and the result is indistinguishable from a deliberate
decision not to use the thing. The skills case cost the most: three separate
retro signals about "this project has no discipline" - no retro ever run, the
knowledge base never fed, packets executed without their playbook - were one
defect in which `run-retro`, `knowledge-ingest` and `run-execution-packet`
were invisible. Someone who does not know a capability exists looks exactly
like someone who chose not to use it.

**Cheapest check.** For anything newly built, ask who calls it and answer
with a reference, not an intention. A repository search that returns only the
definition and its tests *is* the answer: nobody. Run it before claiming the
work done, not after.

**Corollary for reviews.** "Merged" is not "wired". A plan-vs-done matrix
should ask, per row, what evidence exists that the thing runs - not whether
the code is present.

## FP-002: the specification was met and the result was wrong

A rule prescribes a mechanism - a value, a step, a procedure - and says
nothing about the outcome. The mechanism is implemented exactly and the
outcome is still bad. This is a defect in the rule, not in whoever followed
it.

**Evidence of repetition** - three occurrences:

- A design language prescribed section padding as a clamp expression. The
  implementation matched it exactly. Nothing prescribed what the section
  should come out as, and eight sections ranged over 2.2x with four of them
  shorter than the viewport.
- A packet's own start file required a separate branch for the second
  repository. The agent that wrote the rule then worked directly on the
  default branch for three sessions.
- A readiness check required every model route to name a *different* fallback
  provider. Correct as a default for internal work; wrong as an invariant for
  a route whose provider choice is a data boundary rather than a resilience
  detail.

**Cheapest check.** Where it is possible, state the observable property
("a section occupies at least one screen") rather than the quantity that is
supposed to produce it. The quantity is then derivable and checkable; the
reverse is not. Where only a procedure can be stated, put the check at the
moment of use, not in the document.

## FP-003: verification that does not reproduce the consumer

A test passes because it exercises the code the way the test author found
convenient, not the way the actual consumer does. The suite is green and the
behaviour is broken.

**Evidence of repetition** - three occurrences:

- A streaming test rejoined chunks with a space; the browser client
  concatenates them with nothing. The test passed while users saw two words
  run together.
- A definition-of-done row cited tests that covered role constants and a
  configuration flag, while the code path they were said to prove had no test
  at all.
- A full suite of 929 tests and a clean build, followed immediately by a 500
  on the first end-to-end request.

**Cheapest check.** Ask what the consumer literally does with the output, and
make the test do that. Where the consumer is another process, only a live
call answers it: a build proves the code compiles, a test proves it does what
the author expected, and neither proves the author expected the right thing.
