# Traceable implementation reviews

Initial implementation is committed before the three substantive self-review
cycles. Each subsequent cycle records an actual probe failure, a code correction
and verification. No independent score is assigned by the builder.

Initial build: exact transport, product normalization, sufficient inclusion
calculus, separate witness search/validator, batch release review, nine unittest
methods including the 289-pair finite oracle. `examples/workflow.py` and the
12-case benchmark exercise installed-package workflows.

## Round 1 — preserve literal data in independent validation

Before: `2910435d5924433738437480899bc7012804c189` (working initial build).
Self-review probed a literal object containing `$schema`, independently using
the unmodified Draft202012Validator. The initial dialect-stripping traversal
incorrectly altered enum/const instance data and emitted a wire value accepted
by both schemas. This falsified the witness guarantee.

Command: `python -m unittest discover -s tests -p test_regressions.py -v`.
[Actual before output](evidence/round1-before.txt): one FAIL; the allegedly
target-invalid witness was target-valid under the original schema.

Correction: walk only schema-bearing keyword positions; preserve all literal
enum/const/default/example data. Added nested-literal and source-const cases.
After: correction commit recorded below following commit creation.
[Actual after output](evidence/round1-after.txt): regression plus full suite pass.
Limitation: the independent validator is still a separate dependency whose
type checker needs the documented Decimal integer extension.
