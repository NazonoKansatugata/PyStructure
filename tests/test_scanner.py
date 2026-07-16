from __future__ import annotations

import tempfile
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from scanner import ProjectScanner


class ScannerTests(unittest.TestCase):
    def test_ignores_virtual_environment_like_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "app.py").write_text("print('ok')\n", encoding="utf-8")
            (root / "venv").mkdir()
            (root / "venv" / "ignored.py").write_text("print('skip')\n", encoding="utf-8")

            files = ProjectScanner().scan(root)

            self.assertEqual([path.name for path in files], ["app.py"])


if __name__ == "__main__":
    unittest.main()
