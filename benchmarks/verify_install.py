"""Fail if tests accidentally use editable src or a stale installed wheel."""
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
print(json.dumps({"python": platform.python_version(), "schemawitness": metadata.version("schemawitness"),
                  "jsonschema": metadata.version("jsonschema"), "site_packages_import": True,
                  "editable": False, "installed_source_match": True, "module_sha256": modules,
                  "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()}, sort_keys=True))
