from __future__ import annotations

import tempfile
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from analyzer import ProjectAnalyzer


def _write(root: Path, name: str, text: str) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class MetricsTests(unittest.TestCase):
    def test_detects_cycle_depth_unreachable_and_fan_counts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write(root, "app.py", "import a\n\nif __name__ == \"__main__\":\n    a.run()\n")
            _write(root, "a.py", "import b\n\ndef run():\n    return b\n")
            _write(root, "b.py", "import a\nimport c\n")
            _write(root, "c.py", "VALUE = 1\n")
            _write(root, "orphan.py", "import c\n")

            result = ProjectAnalyzer().analyze(root)
            metrics = {module.module_name: module.metrics for module in result.modules}

            self.assertTrue(metrics["app"].is_entry)
            self.assertEqual(metrics["app"].depth, 0)
            self.assertEqual(metrics["a"].depth, 1)
            self.assertEqual(metrics["b"].depth, 2)
            self.assertEqual(metrics["c"].depth, 3)

            self.assertTrue(metrics["a"].in_cycle)
            self.assertTrue(metrics["b"].in_cycle)
            self.assertFalse(metrics["app"].in_cycle)
            self.assertFalse(metrics["c"].in_cycle)

            self.assertTrue(metrics["orphan"].unreachable)
            self.assertFalse(metrics["c"].unreachable)

            self.assertEqual(metrics["c"].fan_in, 2)
            self.assertEqual(metrics["b"].fan_out, 2)
            self.assertEqual(metrics["app"].fan_in, 0)

    def test_resolves_from_import_of_submodule_and_ignores_external_modules(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write(root, "pkg/__init__.py", "")
            _write(root, "pkg/sub.py", "import os\n")
            _write(root, "main.py", "from pkg import sub\n\nif __name__ == \"__main__\":\n    pass\n")

            result = ProjectAnalyzer().analyze(root)
            metrics = {module.module_name: module.metrics for module in result.modules}

            self.assertEqual(metrics["pkg.sub"].depth, 1)
            self.assertEqual(metrics["pkg.sub"].fan_out, 0)
            self.assertEqual(metrics["main"].fan_out, 2)

    def test_falls_back_to_unimported_modules_when_no_main_guard(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write(root, "top.py", "import leaf\n")
            _write(root, "leaf.py", "X = 1\n")

            result = ProjectAnalyzer().analyze(root)
            metrics = {module.module_name: module.metrics for module in result.modules}

            self.assertTrue(metrics["top"].is_entry)
            self.assertEqual(metrics["leaf"].depth, 1)

    def test_records_line_count_and_size(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "m.py").write_bytes(b"a = 1\nb = 2\nc = 3\n")

            module = ProjectAnalyzer().analyze(root).modules[0]

            self.assertEqual(module.metrics.line_count, 3)
            self.assertEqual(module.metrics.size_bytes, 18)

    def test_reports_skipped_files_and_ignores_appledouble_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write(root, "good.py", "X = 1\n")
            (root / "broken.py").write_bytes(b"\x00X = 1\n")
            (root / "._good.py").write_bytes(b"\x00\x05\x16\x07")

            result = ProjectAnalyzer().analyze(root)

            self.assertEqual([module.module_name for module in result.modules], ["good"])
            self.assertEqual([item.path.name for item in result.skipped], ["broken.py"])
            self.assertEqual(result.to_dict()["skipped"][0]["path"], str(root.resolve() / "broken.py"))

    def test_module_graph_node_carries_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write(root, "m.py", "X = 1\n")

            _, graph = ProjectAnalyzer().build_graph(root)

            node = graph.nodes["module::m"].to_dict()
            self.assertIn("metrics", node)
            self.assertEqual(node["metrics"]["line_count"], 1)


if __name__ == "__main__":
    unittest.main()
