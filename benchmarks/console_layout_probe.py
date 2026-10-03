"""Check owned runners with a real Windows global Python and isolated --prefix.

Install a normal wheel and its dependencies under --prefix first, then launch
this script with that installation's Lib/site-packages on PYTHONPATH. The real
interpreter is never replaced. Only sysconfig's scripts lookup is scoped to the
explicit pip prefix, using the real interpreter's installation scheme. This is
a controlled prefix installation, not a user-global install or remote CI run.
"""
import argparse
from contextlib import redirect_stderr, redirect_stdout
import importlib.metadata as metadata
import importlib.util
from io import StringIO
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import sysconfig
import tempfile
from unittest.mock import patch


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", type=Path, required=True)
    parser.add_argument("--harness-root", type=Path, required=True)
    parser.add_argument("--expect-fail", action="store_true")
    args = parser.parse_args()
    if os.name != "nt":
        print(json.dumps({"skipped": True, "reason": "Windows global Python layout"}))
        return 0
    prefix = args.prefix.resolve()
    root = args.harness_root.resolve()
    interpreter = sys.executable
    real_get_path = sysconfig.get_path
    scheme = sysconfig.get_default_scheme()
    variables = {"base": str(prefix), "platbase": str(prefix)}
    scripts = Path(real_get_path("scripts", scheme=scheme, vars=variables))
    assert scripts == prefix / "Scripts"
    assert Path(real_get_path("scripts")) != Path(interpreter).parent
    assert not (Path(interpreter).parent / "schemawitness.exe").exists()
    executable = scripts / "schemawitness.exe"
    assert executable.is_file(), "isolated prefix must contain a registered console"
    # pip's real launcher binds to this real global interpreter, not a marker.
    assert interpreter.encode("utf-8") in executable.read_bytes()
    import schemawitness
    assert Path(schemawitness.__file__).resolve().is_relative_to(prefix / "Lib" / "site-packages")
    direct = json.loads(metadata.distribution("schemawitness").read_text("direct_url.json") or "{}")
    assert not direct.get("dir_info", {}).get("editable", False)
    with tempfile.TemporaryDirectory() as name:
        old, new = Path(name) / "old.json", Path(name) / "new.json"
        old.write_text("true", encoding="utf-8")
        new.write_text('{"$defs":{"N":{"type":"integer"}},"$ref":"#%2F$defs%2FN"}', encoding="utf-8")
        console = subprocess.run([str(executable), str(old), str(new)], capture_output=True, text=True, timeout=10)
    report = json.loads(console.stdout)
    assert console.returncode == 1 and report["status"] == "BREAKING" and report["wire"] == "null"
    assert "Traceback" not in console.stderr
    assert report["validation"]["source"]["valid"] and not report["validation"]["target"]["valid"]

    def scoped_path(name, *positional, **keywords):
        return str(scripts) if name == "scripts" else real_get_path(name, *positional, **keywords)

    checks = [
        ("tests/test_encoded_refs.py", 6, lambda: load(root / "tests/test_encoded_refs.py", "owned_encoded_tests")
         .EncodedReferenceTests("test_actual_console_source_target_and_direction").test_actual_console_source_target_and_direction()),
        ("benchmarks/encoded_pointer_probe.py", 2, lambda: runpy.run_path(str(root / "benchmarks/encoded_pointer_probe.py"), run_name="__main__")),
        ("benchmarks/reviewer_membership_probe.py", 6, lambda: load(root / "benchmarks/reviewer_membership_probe.py", "owned_member_tests")
         .ReviewerTests("test_real_console_roundtrip_exit_codes_source_preservation").test_real_console_roundtrip_exit_codes_source_preservation()),
    ]
    results = []
    for relative, count, function in checks:
        with patch("sysconfig.get_path", side_effect=scoped_path), patch("subprocess.run", wraps=subprocess.run) as called, redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            failure = None
            try:
                function()
            except SystemExit as exc:
                assert exc.code == 0, relative
            except FileNotFoundError:
                failure = "FileNotFoundError"
            if args.expect_fail:
                assert failure == "FileNotFoundError", relative
                assert called.call_count == 1
                assert Path(called.call_args.args[0][0]) == Path(interpreter).parent / "schemawitness.exe"
            else:
                assert failure is None and called.call_count == count, relative
                assert all(Path(call.args[0][0]) == executable for call in called.call_args_list)
            results.append({"file": relative, "exception": failure, "actual_console_attempts": called.call_count})
        assert sys.executable == interpreter
    print(json.dumps({"successful": True, "expected_owned_failure": args.expect_fail,
                      "scope": "controlled pip --prefix installation; user global installation untouched",
                      "scheme": scheme, "real_global_interpreter_unchanged": True,
                      "module_import_override": "PYTHONPATH=<prefix>/Lib/site-packages",
                      "scripts_lookup_override": "sysconfig.get_path('scripts') scoped with scheme=nt and base/platbase=<prefix>",
                      "default_global_install_tested": False, "remote_ci_tested": False,
                      "normal_prefix_package_import": True, "registered_launcher_matches_interpreter": True,
                      "scripts_directory": "Scripts", "actual_scripts_console_exit": console.returncode,
                      "actual_scripts_console_status": report["status"], "results": results}, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
