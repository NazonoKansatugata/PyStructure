from __future__ import annotations

import tempfile
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from api import analyze_project
from exporter import MarkdownExporter


class MarkdownExporterTests(unittest.TestCase):
    def _export(self, files: dict[str, str]) -> str:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for name, text in files.items():
                (root / name).write_text(text, encoding="utf-8")
            bundle = analyze_project(root)
            return MarkdownExporter().export(bundle.analysis, bundle.graph)

    def test_cycle_advice_has_reason_targets_suggestions_and_evidence(self) -> None:
        text = self._export({"a.py": "import b\n", "b.py": "import a\n"})

        self.assertIn("# PyStructure", text)
        self.assertIn("### 理由", text)
        self.assertIn("### 対象", text)
        self.assertIn("### 改善案", text)
        self.assertIn("### 根拠", text)
        self.assertIn("`a`", text)
        self.assertTrue(text.endswith("\n"))

    def test_empty_project_reports_no_advice_section_errors(self) -> None:
        text = self._export({})

        self.assertIn("アドバイス数: 0", text)
        self.assertIn("アドバイスはありません", text)


if __name__ == "__main__":
    unittest.main()
