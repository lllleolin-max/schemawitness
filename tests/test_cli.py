from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from schemawitness import loads, dumps


class InstalledCLI(unittest.TestCase):
    def test_status_codes_and_batch(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            old, new = root / "old.json", root / "new.json"
            for schema, expected, status in (({"type": "number"}, 0, "COMPATIBLE"),
                                             ({"type": "integer", "minimum": 1}, 1, "BREAKING"),
                                             ({"type": "integer", "multipleOf": 2}, 2, "UNKNOWN"),
                                             ({"type": "potato"}, 3, "INVALID")):
                old.write_text('{"type":"integer"}', encoding="utf-8")
                new.write_text(dumps(schema), encoding="utf-8")
                proc = subprocess.run([sys.executable, "-m", "schemawitness", str(old), str(new)],
                                      capture_output=True, text=True, timeout=10)
                self.assertEqual(proc.returncode, expected, proc.stderr)
                self.assertEqual(loads(proc.stdout)["status"], status)
            new.write_text('{"x":1,"x":2}', encoding="utf-8")
            proc = subprocess.run([sys.executable, "-m", "schemawitness", str(old), str(new)],
                                  capture_output=True, text=True, timeout=10)
            self.assertEqual(proc.returncode, 3)
            manifest = root / "release.json"
            manifest.write_text(dumps({"operations": [{"id": "GET /x", "request": {"old": False, "new": False},
                                                        "response": {"old": {"type": "number"}, "new": {"type": "integer"}}}]}), encoding="utf-8")
            proc = subprocess.run([sys.executable, "-m", "schemawitness", "review", str(manifest)],
                                  capture_output=True, text=True, timeout=10)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(loads(proc.stdout)["decision"], "ALLOW")
