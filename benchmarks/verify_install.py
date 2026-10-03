"""Verify installed bytes in a checkout OR extracted source archive.

Git SHA is reported only for an actual repository root; an archive explicitly
reports source_commit=null. Parent checkout metadata is never borrowed.
"""
from pathlib import Path
from hashlib import sha256
import importlib.metadata as metadata
import json
import platform
import subprocess
import schemawitness

repo = Path(__file__).resolve().parents[1]
package = Path(schemawitness.__file__).resolve().parent
assert "site-packages" in str(package), "normal installed wheel required"
direct = json.loads(metadata.distribution("schemawitness").read_text("direct_url.json") or "{}")
assert not direct.get("dir_info", {}).get("editable", False), "editable install rejected"
modules = {}
for source in sorted((repo / "src" / "schemawitness").glob("*.py")):
    installed = package / source.name
    assert source.read_bytes() == installed.read_bytes(), "installed module differs: " + source.name
    modules[source.name] = sha256(installed.read_bytes()).hexdigest()
assert modules
identity = {"source_commit": None, "source_metadata": "archive_without_git"}
if (repo / ".git").exists():
    top = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=repo,
                                      text=True, encoding="utf-8").strip()).resolve()
    assert top == repo, "Git metadata does not belong to this source root"
    dirty = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", "src/schemawitness"], cwd=repo).returncode
    assert dirty == 0, "source changes are not committed; cannot bind installed bytes to HEAD"
    identity = {"source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo,
                                                         text=True, encoding="utf-8").strip(),
                "source_metadata": "git_checkout"}
print(json.dumps({"python": platform.python_version(), "schemawitness": metadata.version("schemawitness"),
                  "jsonschema": metadata.version("jsonschema"), "site_packages_import": True,
                  "referencing": metadata.version("referencing"),
                  "editable": False, "installed_source_match": True, "module_sha256": modules,
                  **identity}, sort_keys=True))
