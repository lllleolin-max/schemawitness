# Release verification receipt

Observed locally on 2026-10-03, Windows, Python 3.14.3, schemawitness 0.1.1,
jsonschema 4.26.0 / referencing 0.37.0. Python 3.11 and Linux are declared/covered
by the CI matrix but have not been executed locally. The previous exact 420cb44
artifact was independently rejected; f14bcda passed local semantic re-review
but was held for its Windows console harness layout defect. The current tooling
correction awaits a new exact-SHA independent review and remote CI. Both old
reports and all original reviewer probes have been preserved by the parent.

Normal wheel workflow (PowerShell; equivalent venv `bin/python` on POSIX):

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e . build
.\.venv\Scripts\python.exe -m build --wheel
py -3 -m venv .wheel-venv
.\.wheel-venv\Scripts\python.exe -m pip install .\dist\schemawitness-0.1.1-py3-none-any.whl
.\.wheel-venv\Scripts\python.exe benchmarks\verify_install.py
.\.wheel-venv\Scripts\python.exe -m unittest discover -s tests -v
.\.wheel-venv\Scripts\python.exe examples\workflow.py
.\.wheel-venv\Scripts\python.exe benchmarks\compare.py
.\.wheel-venv\Scripts\python.exe benchmarks\adverse.py
.\.wheel-venv\Scripts\python.exe benchmarks\encoded_pointer_probe.py
.\.wheel-venv\Scripts\python.exe benchmarks\reviewer_membership_probe.py
```

The first venv is a build/development environment. Verification uses the second
environment's normal archive-installed wheel. [Machine-readable receipt](evidence/round6-installed-wheel.json)
asserts site-packages import, noneditable install and byte-for-byte equality
of all nine installed Python modules with repository source. Its source-code
commit is `e633cbca531b196db17daac8dc31027916678cee`; the following verification
freeze preserves those source bytes. Run `verify_install.py` at the final SHA
to bind the same module hashes to that SHA.

The receipt also supports extracted source archives: without a `.git` entry at
the actual source root it reports `source_commit:null`, `archive_without_git`
and the installed/source hashes. It never borrows an enclosing checkout's SHA.
With Git metadata, it rejects uncommitted library source and uses explicit UTF-8
for Git's path output so Windows Chinese workspace names work.

Historical sixth-correction results:

- [Wheel tests](evidence/round6-wheel-tests.txt): 24 unittest methods pass in 5.794 s;
  includes subprocess CLI codes 0/1/2/3, batch release, 625 independently
  evaluated schema pairs, exact numeric/reference/literal/resource regressions,
  six new encoded-reference methods and two normal-install receipt methods.
- [Unchanged encoded-pointer probe](evidence/round6-peer-after.json): both
  spellings BREAKING, wire null, actual console exit 1 with valid JSON/no trace.
  [Old archive](evidence/round6-old-archive-install.json) matches all eight
  archived/installed modules; [before result](evidence/round6-peer-before.json)
  has successful=false. The original probe SHA remains unchanged, recorded in
  ITERATIONS; the current owned copy adapts console discovery only.
- [Unchanged pure-membership probe](evidence/round6-pure-oracle.txt): all four
  methods pass, 900 schema pairs / 99 authored instances; 271 COMPATIBLE,
  627 BREAKING, 2 UNKNOWN; six extra actual-console cases. Its membership oracle
  does not call the library's compiler, accepts, wire parser or validator helper.
  This is a builder-run reproducibility observation, not a new review score.
- [Workflow](evidence/round6-workflow.txt): two BREAKING + two COMPATIBLE; BLOCK, with
  request `{"quantity":1}` and response `{}` independently checked wire fixtures.
- [Comparison](evidence/round6-benchmark.json): full 12/12, disclosed shallow baseline
  5/12, search-only 9/12, proof-only 4/12; observed runtime 0.019986 s. Synthetic
  cases, not incumbent performance or real traffic estimates.
- [Adverse cases](evidence/round6-adverse.jsonl): UNKNOWN for equivalent empty-array
  shape beyond the sufficient calculus, candidate length limit, unsupported
  numeric range and unsupported combinator. No witness/compatibility invented.

Required correction commits: `de79af5f4fa70b741a5525f8eb884c5cc7a04361`,
`24486f7e893fefdaca8614ec4fd0f309e41caf30`,
`ea4ae96cc57399c6d4fbf247c08a56635ed03c34`.
Additional corrections: `7e08d1d72856ee360559953c87fe97569d6280bf`,
`d03e2213f9ca42df4c9fdeb4e83fd89bee995394`.
Sixth actual correction: `e633cbca531b196db17daac8dc31027916678cee`, directly
after rejected 420cb44. No library source changed after this correction;
the following verification freeze includes the separate UTF-8 receipt fix.
Each actual before/after probe and scope is in [ITERATIONS](ITERATIONS.md).

Current tooling verification uses a freshly built ordinary 0.1.1 wheel in a
fresh `.wheel-venv`, imported from site-packages. No library source or package
metadata changed after e633cbc. The current owned console discovery uses the
interpreter's sysconfig scripts installation directory; all actual-console
assertions remain intact.

[Current normal-wheel receipt](evidence/tooling-installed-wheel.json) records
correction commit `78e1050113974eb5afa064acb1aba3eff2de6cc9`, site-packages
import, editable=false, package 0.1.1 and equality of all nine module hashes.
The following documentation/receipt freeze preserves the same tested library
and harness source; run verify_install.py at frozen HEAD to bind that identity.

- [Full wheel suite](evidence/tooling-wheel-tests.txt): all 24 methods pass,
  no skips, in 6.867 s, including the 625-pair finite independent-validator oracle.
- [Owned encoded-pointer probe](evidence/tooling-owned-encoded.json) and
  [owned membership probe](evidence/tooling-owned-oracle.txt) pass with new
  scripts discovery; the independent member function and assertions are unchanged.
  Their current SHA256 values are respectively
  `e7096c6ca8ac5b1247f33796e9174ab8b13f42d54eeae8f37f8c80ba0fc11b6f` and
  `398552a9417fa23f4db25db2c9c721f5b4664f51f0c4e963a5a62b2bc1a7c1d0`.
- [Unchanged original encoded probe](evidence/tooling-original-encoded.json)
  passes in the normal venv layout. [Unchanged original member probe](evidence/tooling-original-oracle.txt)
  passes 900 pairs / 99 instances, with 271 COMPATIBLE, 627 BREAKING and 2 UNKNOWN,
  plus six registered-console cases. Original SHA values remain 010cce... and
  076bda... in ITERATIONS; these originals are parent-owned review assets.
- [Additional unchanged reference review suite](evidence/tooling-original-references.txt)
  passes five methods with its preserved original membership companion: 60
  reference schemas, 840 membership checks, 240 directional comparisons, 27
  exact class-switch checks and eight actual compare/batch console cases.
- [Workflow](evidence/tooling-workflow.txt) returns BLOCK with two BREAKING and
  two COMPATIBLE checks, with the same independently validated wire fixtures.
  [Twelve contrasts](evidence/tooling-benchmark.json) retain full/shallow/search-only/proof-only
  counts 12/5/9/4; local runtime 0.021248 s. [Four adverse cases](evidence/tooling-adverse.jsonl)
  all remain UNKNOWN. Synthetic timings are not production or incumbent evidence.
- [Controlled Windows prefix before/after](CONSOLE_LAYOUT.md) reproduces all
  three old FileNotFoundError failures and all fourteen corrected real console
  calls using the real global interpreter plus a genuine isolated installation.
  PYTHONPATH and the alternate-prefix scripts lookup are explicitly overridden.
  This does not claim default global installation or remote Windows CI success.

No independent scores or public publication are claimed here. Adoption,
customers, actual revenue and willingness to pay remain unknown. Principal
limitations: explicit subset, sufficient/incomplete calculus, bounded search,
schema export required, no provider execution or hostile-process sandbox.
