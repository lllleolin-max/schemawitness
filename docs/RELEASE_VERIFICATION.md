# Release verification receipt

Observed locally on 2026-10-03, Windows, Python 3.14.3, schemawitness 0.1.0,
jsonschema 4.26.0. Python 3.11 and Linux are declared/covered by the CI matrix
but have not been executed locally. Remote CI and independent review are pending.

Normal wheel workflow (PowerShell; equivalent venv `bin/python` on POSIX):

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e . build
.\.venv\Scripts\python.exe -m build --wheel
py -3 -m venv .wheel-venv
.\.wheel-venv\Scripts\python.exe -m pip install .\dist\schemawitness-0.1.0-py3-none-any.whl
.\.wheel-venv\Scripts\python.exe benchmarks\verify_install.py
.\.wheel-venv\Scripts\python.exe -m unittest discover -s tests -v
.\.wheel-venv\Scripts\python.exe examples\workflow.py
.\.wheel-venv\Scripts\python.exe benchmarks\compare.py
.\.wheel-venv\Scripts\python.exe benchmarks\adverse.py
```

The first venv is a build/development environment. Verification uses the second
environment's normal archive-installed wheel. [Machine-readable receipt](evidence/installed-wheel.json)
asserts site-packages import, noneditable install and byte-for-byte equality
of all eight installed Python modules with repository source. Its source-code
commit is `d03e2213f9ca42df4c9fdeb4e83fd89bee995394`; the following documentation
freeze preserves those source bytes. Run `verify_install.py` at the final SHA
to bind the same module hashes to that SHA.

Observed results:

- [Wheel tests](evidence/wheel-tests.txt): 16 unittest methods pass in 2.778 s;
  includes subprocess CLI codes 0/1/2/3, batch release, 625 independently
  evaluated schema pairs, exact numeric/reference/literal/resource regressions.
- [Workflow](evidence/workflow.txt): two BREAKING + two COMPATIBLE; BLOCK, with
  request `{"quantity":1}` and response `{}` independently checked wire fixtures.
- [Comparison](evidence/benchmark.json): full 12/12, disclosed shallow baseline
  5/12, search-only 9/12, proof-only 4/12; observed runtime 0.019788 s. Synthetic
  cases, not incumbent performance or real traffic estimates.
- [Adverse cases](evidence/adverse.jsonl): UNKNOWN for equivalent empty-array
  shape beyond the sufficient calculus, candidate length limit, unsupported
  numeric range and unsupported combinator. No witness/compatibility invented.

Required correction commits: `de79af5f4fa70b741a5525f8eb884c5cc7a04361`,
`24486f7e893fefdaca8614ec4fd0f309e41caf30`,
`ea4ae96cc57399c6d4fbf247c08a56635ed03c34`.
Additional corrections: `7e08d1d72856ee360559953c87fe97569d6280bf`,
`d03e2213f9ca42df4c9fdeb4e83fd89bee995394`.
Each actual before/after probe and scope is in [ITERATIONS](ITERATIONS.md).

No independent scores or public publication are claimed here. Adoption,
customers, actual revenue and willingness to pay remain unknown. Principal
limitations: explicit subset, sufficient/incomplete calculus, bounded search,
schema export required, no provider execution or hostile-process sandbox.
