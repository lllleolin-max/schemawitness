# Release verification receipt

Observed locally on 2026-10-03, Windows, Python 3.14.3, schemawitness 0.1.1,
jsonschema 4.26.0 / referencing 0.37.0. Python 3.11 and Linux are declared/covered
by the CI matrix but have not been executed locally. The previous exact 420cb44
artifact was independently rejected; this corrected artifact awaits re-review
and remote CI. The old failure/report has been preserved.

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

Observed results:

- [Wheel tests](evidence/round6-wheel-tests.txt): 24 unittest methods pass in 5.794 s;
  includes subprocess CLI codes 0/1/2/3, batch release, 625 independently
  evaluated schema pairs, exact numeric/reference/literal/resource regressions,
  six new encoded-reference methods and two normal-install receipt methods.
- [Unchanged encoded-pointer probe](evidence/round6-peer-after.json): both
  spellings BREAKING, wire null, actual console exit 1 with valid JSON/no trace.
  [Old archive](evidence/round6-old-archive-install.json) matches all eight
  archived/installed modules; [before result](evidence/round6-peer-before.json)
  has successful=false. The copied probe SHA is unchanged, recorded in ITERATIONS.
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

No independent scores or public publication are claimed here. Adoption,
customers, actual revenue and willingness to pay remain unknown. Principal
limitations: explicit subset, sufficient/incomplete calculus, bounded search,
schema export required, no provider execution or hostile-process sandbox.
