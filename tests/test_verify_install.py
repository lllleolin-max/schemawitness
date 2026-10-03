"""Archive identity remains unknown even when an enclosing checkout has Git."""
from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import schemawitness


class InstallReceiptTests(unittest.TestCase):
    @unittest.skipUnless("site-packages" in str(schemawitness.__file__), "requires normal wheel installation")
    def test_archive_does_not_borrow_parent_git_identity(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(dir=repo) as folder:
            archive = Path(folder)
            target = archive / "src" / "schemawitness"
            target.parent.mkdir(parents=True)
            shutil.copytree(repo / "src" / "schemawitness", target)
            (archive / "benchmarks").mkdir()
            script = archive / "benchmarks" / "verify_install.py"
            shutil.copyfile(repo / "benchmarks" / "verify_install.py", script)
            proc = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, timeout=10)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            result = json.loads(proc.stdout)
            self.assertIsNone(result["source_commit"])
            self.assertEqual(result["source_metadata"], "archive_without_git")
            self.assertTrue(result["installed_source_match"])
