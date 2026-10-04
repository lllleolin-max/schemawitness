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

## Round 6 — encoded pointer integration through independent evaluation

Before: `420cb44df6c1c2b6a669bffe35f44eb49939d570` (package 0.1.0).
Independent review rejected this artifact because the compiler accepted encoded
leading URI separators while jsonschema/referencing classified `%2F...` as an
anchor. Actual supported witness search raised `_WrappedReferencingError`;
the real console exited 1 with empty stdout and a traceback. No false
certificate was claimed for this defect; no Result was produced.

Archived reproduction: `git archive` of the exact before SHA was built into
a normal wheel and installed; [receipt](evidence/round6-old-archive-install.json)
confirms all eight installed modules exactly match the archive. The unchanged
reviewer SDK/actual-console probe was copied at e633cbc/f14bcda as
`benchmarks/encoded_pointer_probe.py`, historical SHA256
`010cce8342bff9c99a159486dc917c515ca60aa2724eaffeab75e1c59ddb9d0a`.
[Actual before result](evidence/round6-peer-before.json) has successful=false;
canonical URI works, encoded URI raises and console JSON is absent.

Correction: a dependency resolver adapter decodes then re-encodes the URI
fragment with literal pointer separators before delegating target lookup to
referencing. It changes the lookup argument only, never schema trees or literal
data. Lookup still uses the original document; jsonschema still evaluates
all assertions/siblings. Integral Decimal equivalence and resolver propagation
survive validator-class changes, including targets located inside annotations
or literal schema data. Compiler metadata records encountered URI spellings
only, and independent lookup checks them before any inclusion certificate.
Unresolvable backend evaluations produce UNKNOWN (`valid=None` in the helper),
never rejection evidence or a compatibility certificate.

Mathematical transport argument: for fragment f, adapter C(f) =
quote(unquote(f), safe='/~'). The dependency's pointer decode gives
unquote(C(f)) = unquote(f); a literal percent is encoded again, so `%252F`
continues to name `%2F`, not `/`. JSON Pointer `~0`/`~1` handling remains in
the independent dependency after URI decoding. Tests include literal `%`,
`%2F`, Unicode, tilde/slash names, both schema directions, siblings, nested
dialect switching, annotation targets, dual literal/schema targets and cycles.

Version bumped to 0.1.1 before public release. Separate review tooling issue:
verify_install.py now supports extracted archives without claiming a Git SHA
or borrowing a parent checkout's identity. In a checkout it requires committed
source before reporting HEAD. This tooling correction is separate from the
supported-reference semantic correction.

After core correction: `e633cbca531b196db17daac8dc31027916678cee`.
[Normal-wheel unchanged probe](evidence/round6-peer-after.json) reports
successful=true: both spellings yield wire null, BREAKING, parseable console
JSON, exit 1 and no traceback. [Wheel tests](evidence/round6-wheel-tests.txt)
cover all original sixteen tests plus the reference/receipt regressions.
[Unchanged reviewer oracle run](evidence/round6-pure-oracle.txt) completes
900 pairs against 99 independently authored member-oracle instances: 271
COMPATIBLE, 627 BREAKING, 2 UNKNOWN; all four methods/six console cases pass.
These are builder-run observations of unchanged probes, not a new reviewer score.
The pure-member probe was also copied unchanged at e633cbc/f14bcda to
`benchmarks/reviewer_membership_probe.py` for portable reproduction; membership
is independently authored and neither production helper nor compiler supplies
its acceptance oracle.
Its historical unchanged copied file SHA256 is
`076bdaf54979ad9d53495afdd885ed40f8731f3e544e509b197eb94a0a16f832`.

The first installed checkout receipt also exposed Windows locale decoding of
Git's UTF-8 Chinese path. Its actual traceback remains ignored locally. Explicit
UTF-8 Git-output decoding and a live checkout/archive receipt test fix that
separate tooling defect; no domain semantics were changed after e633cbc.
The final receipt tool now reports archive SHA as null, refuses uncommitted
source identity, and checks all nine installed module bytes.
The root-owned old FAIL report/probe remain unchanged.
No new independent scores or publication are claimed by the builder.

## Separate tooling correction — use the installed scripts scheme

Before: `f14bcda909d80a59d6fe8fbb01db344209b9c7f5`. Independent re-review found
three owned console harnesses assuming that the console lived beside
`sys.executable`; a standard Windows global interpreter uses prefix/python.exe
and prefix/Scripts/schemawitness.exe. The registered CLI works, while the
verification harnesses raise FileNotFoundError. The frozen P2 report and all
original reviewer assets are preserved by the parent outside this repository.

Correction: only these three harnesses use the interpreter's sysconfig scripts
installation path. Actual registered-console subprocess calls and all existing
protocol/wire assertions remain. A focused controlled-prefix driver exercises
the old archived files versus corrected runners with fourteen actual console
cases. [Before](evidence/tooling-layout-before.json) records three actual
FileNotFoundError results; [after](evidence/tooling-layout-after.json) records
6 + 2 + 6 successful actual console calls. The real global interpreter and
launcher are used; PYTHONPATH and the alternate-prefix scripts lookup are
explicitly scoped, not represented as default global installation.
[Reproduction and limits](CONSOLE_LAYOUT.md) give the exact override mechanism.

This does not add an algorithm review cycle. All nine library modules remain
identical to `e633cbca531b196db17daac8dc31027916678cee`, and version remains
0.1.1. The copied owned encoded-pointer/pure-membership probes now have changed
discovery bytes; the historical SHA values above identify the preserved
originals, not the current copies. Current normal-wheel verification and
unchanged-original probe results are recorded in [RELEASE_VERIFICATION](RELEASE_VERIFICATION.md).
Remote default-global Windows CI remains a parent-run gate.

After tooling correction: `78e1050113974eb5afa064acb1aba3eff2de6cc9`.
The [committed ordinary-wheel receipt](evidence/tooling-installed-wheel.json)
binds all nine installed module hashes to this correction SHA. The subsequent
verification freeze adds this receipt/provenance only; library and runner
source remain unchanged. A receipt generated at the final frozen HEAD is
available from `python benchmarks/verify_install.py` without any source edits.

## 0.2.0 round 1 — bounded sharing, measured baseline

Baseline: `63eb34a67574e23c46f798008826b825d411567a`, ordinary canonical LF
archive/wheel/site association of nine modules, 24/24 installed tests in
6.445 s. The remote README-only `a46a4a57a12e80d8be960ddffa6d4e1cec29e1fb`
was fast-forwarded and preserved. Baseline 100 repeated/distinct operations
each made 200 core comparisons, 400 compiler expansions, 200 proof entries and
200 search entries. This is the disclosed original per-direction contract,
not a retrospective aggregate-budget defect.

Implementation: `aab4ec0`. New opt-in BatchLimits shares explicit application
work and bounds input/cache/result payloads. Full shape validation precedes
core work, and per-call typed full-document/direction cache identities precede
normalization. Original compare/default review semantics and independent wire
validation remain. Ordinary installation matched all ten package modules and
passed 33/33 tests in 6.980 s. Repeated comparisons fell to two; distinct stayed
200 and was slower/more memory-intensive. [BATCH](BATCH.md) retains both costs.

## 0.2.0 round 2 — resources, precision and composition

Before `aab4ec0`: a malformed operation with 100,003 keys allocated 4,195,768 B
for `set(operation)` before rejection. The focused actual probe and regression
failed its additional-allocation bound. Correction `dfe86cb` tests dictionary
field count before constructing only the expected 1/2/3-key sets. The same
ordinary-wheel probe then allocated 1,176 B and remained INVALID/core zero.
This is a resource correction, not a new compatibility rule.

The corrected ordinary install passed 34/34 tests in 8.740 s, the unchanged
900-pair/99-instance pure-membership probe, and the 80-unit aggregate case.
Tests cover detached cached results, changed shared documents, bool/int/
Decimal/float identities, original Decimal precision, encoded pointers and
full local targets, unsupported external references, backend failure, 120 new
schema pairs/240 directions against single comparisons and independent standard
membership on every emitted witness, plus exact work/input/cache/result bounds.
The standard-membership family uses integer-only numeric constraints; retained
precision regressions and the separate exact pure oracle cover Decimal behavior.

The first ordinary-install integration driver incorrectly expected only three
BREAKING checks for a precise const-versus-maximum pair. Both request and
response inclusions actually break, giving six. Original driver/failure and
its corrected copy remain separate in local build evidence; no product fix is
claimed for that harness error. The corrected driver made 35 real sysconfig
console calls across native/PYTHONUTF8=0/1/cp936/cp1252, with ASCII machine JSON,
expected exits, exact wire values and protected inputs. Both SDK examples pass.

## 0.2.0 round 3 — final install and accounting review

Added multibyte exact-wire payload/storage boundaries and a sweep checking each
backend invocation against the charged ledger before exhaustion. No additional
semantic defect was found; this round does not manufacture a third new bug.
README, architecture, security, changelog and the offline benchmark describe
work units, separate precheck cost, serialized storage versus Python/RSS,
UNKNOWN/provenance envelope overhead and distinct/small-input counterexamples.
Caller concurrent mutation and cross-call cache persistence remain unsupported.

The final ordinary source/wheel/site and console verification is generated at
the clean exact final SHA by the builder; it is separate from the later peer
review, scores and remote publication/CI. Historical correction rounds and
failure records above remain unchanged. No independent score, adoption,
production performance or revenue result is inferred from these self-reviews.
