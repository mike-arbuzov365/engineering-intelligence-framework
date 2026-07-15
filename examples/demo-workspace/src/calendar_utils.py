"""Small date-utility module for the EIF vertical-slice demo.

Task for this demo: implement is_leap_year(year). See task-scope.md in
this directory for the scoped task and the seeded knowledge artifact this
task is expected to retrieve before implementing.
"""


def is_leap_year(year: int) -> bool:
    # Gregorian calendar rule (see knowledge/facts/FACT-0001-gregorian-leap-year-rule.md):
    # divisible by 4, except century years, unless also divisible by 400.
    # A naive "year % 4 == 0" check is wrong here - see
    # knowledge/failure-patterns/PATTERN-0001-naive-leap-year-check.md,
    # retrieved during this task's experience-retrieval preflight (see
    # task-scope.md) before this was written.
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
