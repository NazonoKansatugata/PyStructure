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


class GraphEdgeNormalizationTests(unittest.TestCase):
    def test_imports_point_to_module_nodes_and_external_nodes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write(root, "pkg/__init__.py", "")
            _write(root, "pkg/sub.py", "X = 1\n")
            _write(root, "main.py", "import os\nimport pkg.sub\nfrom pkg import sub\nfrom rich.console import Console\n")

            _, graph = ProjectAnalyzer().build_graph(root)
            imports = {target for source, target in _edges(graph, "imports") if source == "module::main"}

            self.assertEqual(imports, {"external::os", "module::pkg.sub", "module::pkg", "external::rich.console"})
            self.assertEqual(graph.nodes["external::os"].kind, "external")

    def test_calls_resolve_to_symbol_nodes_and_drop_unresolved_targets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write(root, "helpers.py", "def helper():\n    return 1\n\nclass Tool:\n    def run(self):\n        return self.stop()\n\n    def stop(self):\n        return 0\n")
            _write(
                root,
                "main.py",
                "import os\nfrom helpers import helper, Tool\n\ndef go():\n    helper()\n    helper()\n    os.getcwd()\n    len([])\n    return Tool()\n",
            )

            _, graph = ProjectAnalyzer().build_graph(root)
            calls = _edges(graph, "calls")

            self.assertIn(("main::go", "helpers::helper"), calls)
            self.assertIn(("main::go", "helpers::Tool"), calls)
            self.assertIn(("helpers::Tool::run", "helpers::Tool::stop"), calls)
            self.assertEqual({target for source, target in calls if source == "main::go"}, {"helpers::helper", "helpers::Tool"})
            self.assertEqual(len([edge for edge in graph.edges if edge.kind == "calls" and edge.source == "main::go"]), 2)

    def test_every_edge_endpoint_is_a_node_in_this_repository(self) -> None:
        graph = ProjectAnalyzer().build_graph(Path(__file__).resolve().parents[1] / "src")[1]

        dangling = [edge for edge in graph.edges if edge.source not in graph.nodes or edge.target not in graph.nodes]

        self.assertEqual(dangling, [])


if __name__ == "__main__":
    unittest.main()
