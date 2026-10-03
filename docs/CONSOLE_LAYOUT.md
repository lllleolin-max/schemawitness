# Windows console discovery correction

The registered console works in the rejected f14bcda tooling freeze. Its three
owned runners nevertheless looked next to `sys.executable`, which is wrong for
a standard Windows global installation: `python.exe` is under the interpreter
prefix and the registered console is under its `Scripts` directory. Venvs put
both in `Scripts`, so the ordinary venv tests missed this layout defect.

The owned runners now use `Path(sysconfig.get_path('scripts'))` and still invoke
the actual registered console. They retain their source/target, wire membership,
exit-code, JSON and source-file-preservation assertions. The library's nine
modules and package metadata are unchanged. This is a tooling correction, not
another algorithm correction or a claim that remote Windows CI has passed.

## Executed controlled installation

The local before/after experiment uses a **real global Python 3.14.3** and a
genuine ordinary-wheel `pip --prefix` installation, including dependencies and
a registered launcher that embeds this real interpreter. No user-global
package is installed, and `sys.executable` is never replaced by a layout marker.

An alternate pip prefix does **not** change the interpreter's default sysconfig
paths. This experiment makes two explicit overrides: `PYTHONPATH` supplies the
prefix's `Lib/site-packages`; the driver scopes only `sysconfig.get_path('scripts')`
to the path computed with the real `nt` scheme and `base`/`platbase` set to the
alternate prefix. The actual console subprocess inherits that PYTHONPATH.
These are controlled prefix observations; default global installation and
remote GitHub Windows CI remain untested locally. Product runners use unpatched
sysconfig normally, including in CI and venvs.

[Before](evidence/tooling-layout-before.json): all three archived f14bcda
runners raise FileNotFoundError on their first actual console attempt, although
the independently invoked registered `Scripts` console returns BREAKING/null.
[After](evidence/tooling-layout-after.json): the same real prefix installation
runs all fourteen owned console calls (6 + 2 + 6) successfully, preserving their
protocol and membership assertions. The driver records both overrides explicitly.
The library bytes are identical between the two harness runs.

Portable PowerShell reproduction from the repository, with a real global
interpreter (not the venv interpreter):

```powershell
py -3 -m pip wheel --no-deps --wheel-dir dist .
py -3 -m pip install --ignore-installed --prefix docs/evidence/local/layout-prefix dist/schemawitness-0.1.1-py3-none-any.whl
New-Item -ItemType Directory -Force docs/evidence/local/layout-before | Out-Null
git -c core.autocrlf=false archive f14bcda909d80a59d6fe8fbb01db344209b9c7f5 --format=tar --output docs/evidence/local/layout-before.tar tests/test_encoded_refs.py benchmarks/encoded_pointer_probe.py benchmarks/reviewer_membership_probe.py
tar -xf docs/evidence/local/layout-before.tar -C docs/evidence/local/layout-before
$taskPreviousPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = (Resolve-Path docs/evidence/local/layout-prefix/Lib/site-packages).Path
    py -3 benchmarks/console_layout_probe.py --prefix docs/evidence/local/layout-prefix --harness-root docs/evidence/local/layout-before --expect-fail
    py -3 benchmarks/console_layout_probe.py --prefix docs/evidence/local/layout-prefix --harness-root .
} finally {
    $env:PYTHONPATH = $taskPreviousPythonPath
}
```

The archived harness-only reproduction uses the current identical core; the
sixth semantic correction's independently preserved old/new wheel evidence
remains separate in [ITERATIONS](ITERATIONS.md). The root-owned original
reviewer probes and reports are unchanged. The owned copied probe bytes now
differ solely in console discovery/imports and provenance wording; their
independent membership and validation conditions are unchanged.
