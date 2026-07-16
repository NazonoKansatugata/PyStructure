from __future__ import annotations

import tempfile
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from analyzer import ProjectAnalyzer


class AnalyzerTests(unittest.TestCase):
    def test_extracts_modules_classes_functions_and_imports(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "package").mkdir()
            (root / "package" / "__init__.py").write_text("from .module import Example\n", encoding="utf-8")
            (root / "package" / "module.py").write_text(
                "import os\nfrom .submodule import helper\n\nclass Example:\n    def run(self):\n        return helper()\n\ndef top_level():\n    return os.name\n",
                encoding="utf-8",
            )
            (root / "package" / "submodule.py").write_text(
                "def helper():\n    return 1\n",
                encoding="utf-8",
            )

            result, graph = ProjectAnalyzer().build_graph(root)

            self.assertEqual(len(result.modules), 3)
            self.assertGreaterEqual(len(graph.nodes), 3)
            module_names = {module.module_name for module in result.modules}
            self.assertIn("package.module", module_names)

            module = next(item for item in result.modules if item.module_name == "package.module")
            self.assertEqual([item.name for item in module.classes], ["Example"])
            self.assertEqual([item.name for item in module.functions], ["top_level"])
            self.assertEqual(module.imports[0].module, None)
            self.assertEqual(module.imports[1].module, "package.submodule")

            package_init = next(item for item in result.modules if item.module_name == "package")
            self.assertEqual(package_init.imports[0].module, "package.module")


if __name__ == "__main__":
    unittest.main()
