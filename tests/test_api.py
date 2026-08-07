from __future__ import annotations

import tempfile
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from api import AnalysisBundle, analyze_project, analyze_project_payload


class ApiTests(unittest.TestCase):
    def test_returns_shared_json_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "module.py").write_text("def hello():\n    return 1\n", encoding="utf-8")

            bundle = analyze_project(root)
            payload = analyze_project_payload(root)

            self.assertIsInstance(bundle, AnalysisBundle)
            self.assertEqual(set(payload.keys()), {"analysis", "graph"})
            self.assertEqual(payload["analysis"]["root"], str(root.resolve()))
            self.assertEqual(payload["analysis"]["modules"][0]["module_name"], "module")
            self.assertTrue(payload["graph"]["nodes"])
