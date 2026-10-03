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
After: `de79af5f4fa70b741a5525f8eb884c5cc7a04361`.
[Actual after output](evidence/round1-after.txt): regression plus full suite pass.
Limitation: the independent validator is still a separate dependency whose
type checker needs the documented Decimal integer extension.

## Round 2 — JSON Pointer is not Python indexing

Before: `de79af5f4fa70b741a5525f8eb884c5cc7a04361`.
Self-review tested `#/allOf/-1`, a negative Python list index but an invalid
RFC 6901 array-index token. The compiler incorrectly resolved the last array
member and certified COMPATIBLE for an invalid reference. Leading-zero and
signed tokens had the same risk.

Command: `python -m unittest discover -s tests -p test_regressions.py -v`.
[Actual before output](evidence/round2-before.txt): FAIL, expected INVALID but
got COMPATIBLE. Correction validates canonical nonnegative array-index syntax,
tilde escapes and URI percent/UTF-8 escapes before resolution. It handles
percent-encoded pointer separators and detects reference cycles by target
identity, including differently encoded aliases.

After: `24486f7e893fefdaca8614ec4fd0f309e41caf30`.
[Actual after output](evidence/round2-after.txt): full suite and expanded
malformed/escaped/alias-reference regressions pass. External references and
anchors remain UNKNOWN; no network retrieval is added.

## Round 3 — enforce wire resources before full expansion

Before: `24486f7e893fefdaca8614ec4fd0f309e41caf30`.
Self-review nested five fixed-length arrays (4 items each) and instrumented
actual successful serializations with a 1,000-byte document budget. The old
encoder allocated full wires before the parser rejected their size; the
largest completed encoding was 3,753 bytes. Repeated nesting could amplify
this discrepancy well beyond a per-container length cap.

Command: `python -m unittest discover -s tests -p test_regressions.py -v`.
[Actual before output](evidence/round3-before.txt): FAIL, 3753 > 1000.
Correction: incremental byte/depth-budgeted wire emission, bounded string
escaping, cycle rejection, capped diagnostics and memoized source-validation
of shared filler containers. Oversized schema transport returns UNKNOWN;
oversized candidates cannot become evidence and remain UNKNOWN if no other
certified witness exists.

After: `ea4ae96cc57399c6d4fbf247c08a56635ed03c34`.
[Actual after output](evidence/round3-after.txt): full suite passes; the probe
never completes an encoding above 1,000 bytes. A 16-way, 12-level shared value
is rejected during 64-byte emission without expanding its full wire.
Limitations: no wall-clock or OS sandbox; callers need a limited worker for
hostile workloads. Per-operation budgets remain separate in batch review.

## Additional pre-release review — preserve integer semantics through ref switching

Before: `ea4ae96cc57399c6d4fbf247c08a56635ed03c34`.
After the required three cycles, a broader reference probe found a further
edge: a reference into an annotation containing a schema object could make
jsonschema switch back to its stock integer predicate. A `1.0` wire value was
rejected as a noninteger, and the search-only ablation could emit false evidence.
[Before output](evidence/round4-before.txt): regression FAIL.

Correction: independently validate the untouched original schema; represent
transported integral Decimals by equivalent mathematical ints inside the
independent validator. This preserves JSON Schema equality while surviving
validator-class switching without any schema rewriting. Input preflight also
runs before SDK serialization to catch oversized numeric literals precisely.
[After output](evidence/round4-after.txt): full suite passes, including the
arbitrary-location reference and search-only regression.
After: `7e08d1d72856ee360559953c87fe97569d6280bf`.

The evidence text preserves observed failures/results while redacting local
machine prefixes as `<repo>/`; raw logs remain ignored locally. The release
verification expands the finite oracle to 625 schema pairs, including exact
decimals, type unions, intersections and reference siblings.

## Additional resource review — budget preprocessing before deduplication

Before-code: `7e08d1d72856ee360559953c87fe97569d6280bf`; probe run after additional
diagnostic/CLI tests were prepared but before this correction. Instrumenting
the structural de-duplication key showed oversized shared candidates reached
key expansion before bounded serialization. The wire guard raised an ERROR
on the five-level array: [actual before output](evidence/round5-before.txt).

Correction: capped exact wire-size estimation with memoized shared containers
before keys, an 8 MB cumulative candidate encoding budget and explicit search
limit reasons. The original wire estimator regression remains; no oversized
candidate now reaches the key guard. New tests compare estimated bytes against
actual serialization and check the cumulative budget.
[After output](evidence/round5-after.txt) records the full pass. The correction
commit is `d03e2213f9ca42df4c9fdeb4e83fd89bee995394`. This further correction is substantive code,
not one of the three required cycles or a documentation-only change.
