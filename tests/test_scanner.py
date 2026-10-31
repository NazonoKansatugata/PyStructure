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

    def _scan_names(self, root: Path) -> list[str]:
        return [path.relative_to(root.resolve()).as_posix() for path in ProjectScanner().scan(root)]

    def _write(self, root: Path, name: str) -> None:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("X = 1\n", encoding="utf-8")

    def test_settings_exclude_by_root_relative_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for name in ("app.py", "ext/python/copy.py", "other/python/keep.py"):
                self._write(root, name)
            (root / ".pystructure.json").write_text('{"exclude": ["ext/python"]}', encoding="utf-8")

            self.assertEqual(self._scan_names(root), ["app.py", "other/python/keep.py"])

    def test_settings_exclude_by_directory_name_at_any_depth(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for name in ("app.py", "generated/a.py", "pkg/generated/b.py"):
                self._write(root, name)
            (root / ".pystructure.json").write_text('{"exclude": ["generated/"]}', encoding="utf-8")

            self.assertEqual(self._scan_names(root), ["app.py"])

    def test_invalid_settings_are_ignored(self) -> None:
        for content in ("{broken", '["x"]', '{"exclude": "pkg"}', '{"exclude": [1]}'):
            with self.subTest(content=content), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                self._write(root, "pkg/a.py")
                (root / ".pystructure.json").write_text(content, encoding="utf-8")

                with self.assertLogs("settings", level="WARNING"):
                    self.assertEqual(self._scan_names(root), ["pkg/a.py"])

    def test_missing_settings_file_uses_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "pkg/a.py")

            self.assertEqual(self._scan_names(root), ["pkg/a.py"])


if __name__ == "__main__":
    unittest.main()
