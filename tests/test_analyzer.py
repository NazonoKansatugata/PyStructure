from __future__ import annotations

import tempfile
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from analyzer import ProjectAnalyzer


class AnalyzerTests(unittest.TestCase):
    def test_extracts_modules_classes_functions_imports_and_calls(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "package").mkdir()
            (root / "package" / "__init__.py").write_text("from .module import Example\n", encoding="utf-8")
            (root / "package" / "module.py").write_text(
                "import os\nfrom .submodule import helper\nfrom .submodule import helper as helper_alias\n\nclass Example:\n    def run(self):\n        return helper()\n\n    def via_self(self):\n        return self.run()\n\n    @classmethod\n    def via_cls(cls):\n        return cls.run()\n\ndef top_level():\n    return os.name\n\ndef aliased():\n    return helper_alias()\n",
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
            self.assertEqual([item.name for item in module.functions], ["top_level", "aliased"])
            self.assertEqual(module.imports[0].module, None)
            self.assertEqual(module.imports[1].module, "package.submodule")
            self.assertEqual(
                [call.caller for call in module.calls],
                ["package.module::Example::run", "package.module::Example::via_self", "package.module::Example::via_cls", "package.module::aliased"],
            )
            self.assertEqual([call.callee for call in module.calls], ["helper", "self.run", "cls.run", "helper_alias"])
            self.assertEqual(
                [call.resolved_callee for call in module.calls],
                [
                    "package.submodule.helper",
                    "package.module::Example::run",
                    "package.module::Example::run",
                    "package.submodule.helper",
                ],
            )
            self.assertEqual(module.imports[2].bindings[0].asname, "helper_alias")

            package_init = next(item for item in result.modules if item.module_name == "package")
            self.assertEqual(package_init.imports[0].module, "package.module")

    def test_reads_python_source_using_declared_encoding(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            legacy_source = "# -*- coding: cp932 -*-\n\nMESSAGE = \"表\"\n"
            (root / "legacy.py").write_bytes(legacy_source.encode("cp932"))

            result = ProjectAnalyzer().analyze(root)

            self.assertEqual(len(result.modules), 1)
            self.assertEqual(result.modules[0].module_name, "legacy")
            self.assertEqual(result.modules[0].functions, ())

    def test_skips_python_file_with_null_bytes_and_continues(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "good.py").write_text("def ok():\n    return 1\n", encoding="utf-8")
            (root / "broken.py").write_bytes(b"\x00def nope():\n    return 0\n")

            result = ProjectAnalyzer().analyze(root)

            self.assertEqual([module.module_name for module in result.modules], ["good"])


if __name__ == "__main__":
    unittest.main()
