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


class SymbolEdgeTests(unittest.TestCase):
    def test_inherits_resolves_local_imported_reexported_and_external_bases(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write(root, "pkg/__init__.py", "from .base import Base\n")
            _write(root, "pkg/base.py", "class Base:\n    pass\n")
            _write(
                root,
                "pkg/child.py",
                "import abc\nimport pkg\nfrom pkg import Base\nfrom typing import Generic\n\n"
                "class Local(Base):\n    pass\n\n"
                "class Dotted(pkg.Base):\n    pass\n\n"
                "class Chained(Local, abc.ABC, Generic[int], Exception, object):\n    pass\n",
            )

            _, graph = ProjectAnalyzer().build_graph(root)
            inherits = _edges(graph, "inherits")

            self.assertIn(("pkg.child::Local", "pkg.base::Base"), inherits)
            self.assertIn(("pkg.child::Dotted", "pkg.base::Base"), inherits)
            self.assertIn(("pkg.child::Chained", "pkg.child::Local"), inherits)
            self.assertIn(("pkg.child::Chained", "external::abc.ABC"), inherits)
            self.assertIn(("pkg.child::Chained", "external::typing.Generic"), inherits)
            self.assertIn(("pkg.child::Chained", "external::Exception"), inherits)
            self.assertNotIn("external::object", graph.nodes)
            self.assertEqual(graph.nodes["external::abc.ABC"].kind, "external")

    def test_uses_covers_references_but_not_calls_or_bases(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write(root, "types.py", "class Item:\n    pass\n\nclass Base:\n    pass\n\nLIMIT = 3\n")
            _write(root, "helpers.py", "def helper():\n    return 1\n\ndef callback():\n    return 2\n")
            _write(
                root,
                "app.py",
                "import types as t\nfrom helpers import helper, callback\nfrom types import Item, Base\n\n"
                "class Holder(Base):\n    registry = {}\n\n"
                "    def make(self, item: Item) -> t.Item:\n"
                "        helper()\n"
                "        return isinstance(item, Item)\n\n"
                "def register(handlers=None):\n    handlers = [callback]\n    return t.LIMIT\n",
            )

            _, graph = ProjectAnalyzer().build_graph(root)
            uses = _edges(graph, "uses")

            self.assertIn(("app::Holder::make", "types::Item"), uses)
            self.assertIn(("app::register", "helpers::callback"), uses)
            self.assertIn(("app::register", "module::types"), uses)
            self.assertNotIn(("app::Holder::make", "helpers::helper"), uses)
            self.assertNotIn(("app::Holder", "types::Base"), uses)
            self.assertEqual(len([edge for edge in graph.edges if edge.kind == "uses" and edge.source == "app::Holder::make"]), 1)

    def test_resolves_method_reference_and_skips_unknown_names(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write(root, "svc.py", "class Service:\n    def run(self):\n        pass\n")
            _write(root, "main.py", "import os\nfrom svc import Service\n\ndef go():\n    handler = Service.run\n    return os.sep, handler\n")

            result, graph = ProjectAnalyzer().build_graph(root)

            self.assertIn(("main::go", "svc::Service::run"), _edges(graph, "uses"))
            main = next(module for module in result.modules if module.module_name == "main")
            self.assertTrue(all(use.name.split(".")[0] in {"Service", "os"} for use in main.uses))
            self.assertEqual(
                {target for source, target in _edges(graph, "uses") if source == "main::go"},
                {"svc::Service::run"},
            )


if __name__ == "__main__":
    unittest.main()
