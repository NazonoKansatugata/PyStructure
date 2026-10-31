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


def _edges(graph, kind: str) -> set[tuple[str, str]]:
    return {(edge.source, edge.target) for edge in graph.edges if edge.kind == kind}


class SiblingImportTests(unittest.TestCase):
    def test_bare_import_resolves_to_sibling_in_script_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write(root, "app/menu.py", "from search import find\n\ndef run():\n    return find()\n")
            _write(root, "app/search.py", "def find():\n    return 1\n")
            _write(root, "search.py", "def find():\n    return 2\n")

            result, graph = ProjectAnalyzer().build_graph(root)

            self.assertEqual(_edges(graph, "imports"), {("module::app.menu", "module::app.search")})
            self.assertIn(("app.menu::run", "app.search::find"), _edges(graph, "calls"))
            metrics = {module.module_name: module.metrics for module in result.modules}
            self.assertEqual(metrics["app.menu"].fan_out, 1)
            self.assertEqual(metrics["app.search"].fan_in, 1)
            self.assertEqual(metrics["search"].fan_in, 0)

    def test_bare_import_in_real_package_stays_absolute(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write(root, "pkg/__init__.py", "")
            _write(root, "pkg/a.py", "import json\n")
            _write(root, "pkg/json.py", "X = 1\n")

            _, graph = ProjectAnalyzer().build_graph(root)

            self.assertEqual(_edges(graph, "imports"), {("module::pkg.a", "external::json")})


if __name__ == "__main__":
    unittest.main()
