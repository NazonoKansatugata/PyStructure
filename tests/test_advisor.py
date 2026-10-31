from __future__ import annotations

import tempfile
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from advisor import AdviceEngine
from api import analyze_project, analyze_project_payload as _full_payload
from config import (
    FAN_IN_THRESHOLD,
    FAN_OUT_THRESHOLD,
    LARGE_MODULE_LINES,
    READING_ORDER_MAX_PER_STAGE,
    VERY_LARGE_MODULE_LINES,
)


def analyze_project_payload(root: Path) -> dict:
    """循環・依存集中のテスト用に、他ルールの助言を除いた payload を返す。"""
    payload = _full_payload(root)
    payload["advice"] = [
        item for item in payload["advice"] if item["rule_id"] in {"circular-dependency", "dependency-concentration"}
    ]
    return payload


def _write(root: Path, name: str, text: str) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class CircularDependencyAdviceTests(unittest.TestCase):
    def test_no_advice_without_cycle(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write(root, "app.py", "import util\n")
            _write(root, "util.py", "X = 1\n")

            bundle = analyze_project(root)
            advices = AdviceEngine().advise(bundle.analysis, bundle.graph)

            self.assertEqual([advice.rule_id for advice in advices], ["reading-order"])

    def test_reports_two_module_cycle_with_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write(root, "user.py", "import service\n")
            _write(root, "service.py", "import user\n")

            advices = analyze_project_payload(root)["advice"]

            self.assertEqual(len(advices), 1)
            advice = advices[0]
            self.assertEqual(advice["rule_id"], "circular-dependency")
            self.assertEqual(advice["severity"], "high")
            self.assertEqual(advice["targets"], ["service", "user"])
            self.assertTrue(advice["reason"])
            self.assertTrue(advice["suggestions"])
            self.assertEqual(advice["evidence"]["cycle"], ["service", "user", "service"])
            self.assertEqual(sorted(advice["evidence"]["edges"]), [["service", "user"], ["user", "service"]])

    def test_reports_each_cycle_group_separately(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write(root, "a.py", "import b\n")
            _write(root, "b.py", "import a\n")
            _write(root, "x.py", "import y\n")
            _write(root, "y.py", "import z\n")
            _write(root, "z.py", "import x\n")
            _write(root, "solo.py", "import a\n")

            advices = analyze_project_payload(root)["advice"]

            self.assertEqual([advice["targets"] for advice in advices], [["a", "b"], ["x", "y", "z"]])
            self.assertEqual(advices[1]["evidence"]["cycle"], ["x", "y", "z", "x"])

    def test_ignores_external_imports(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write(root, "m.py", "import os\nimport json\n")

            self.assertEqual(analyze_project_payload(root)["advice"], [])


class DependencyConcentrationAdviceTests(unittest.TestCase):
    def _hub_project(self, root: Path, importers: int, hub_lines: int = 1) -> None:
        _write(root, "hub.py", "X = 1\n" * hub_lines)
        for index in range(importers):
            _write(root, f"user{index}.py", "import hub\n")

    def test_no_advice_below_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._hub_project(root, FAN_IN_THRESHOLD - 1)

            self.assertEqual(analyze_project_payload(root)["advice"], [])

    def test_reports_high_fan_in_as_low_severity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._hub_project(root, FAN_IN_THRESHOLD)

            advices = analyze_project_payload(root)["advice"]

            self.assertEqual(len(advices), 1)
            self.assertEqual(advices[0]["rule_id"], "dependency-concentration")
            self.assertEqual(advices[0]["severity"], "low")
            self.assertEqual(advices[0]["targets"], ["hub"])
            self.assertEqual(advices[0]["evidence"]["fan_in"], FAN_IN_THRESHOLD)

    def test_large_concentrated_module_is_medium_and_sorted_after_cycles(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._hub_project(root, FAN_IN_THRESHOLD, hub_lines=LARGE_MODULE_LINES)
            _write(root, "a.py", "import b\n")
            _write(root, "b.py", "import a\n")

            advices = analyze_project_payload(root)["advice"]

            self.assertEqual([item["severity"] for item in advices], ["high", "medium"])

    def test_entry_point_fan_out_is_not_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            names = [f"dep{index}" for index in range(FAN_OUT_THRESHOLD)]
            for name in names:
                _write(root, f"{name}.py", "X = 1\n")
            imports = "".join(f"import {name}\n" for name in names)
            _write(root, "app.py", imports + "\nif __name__ == \"__main__\":\n    pass\n")

            self.assertEqual(analyze_project_payload(root)["advice"], [])

    def test_non_entry_fan_out_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            names = [f"dep{index}" for index in range(FAN_OUT_THRESHOLD)]
            for name in names:
                _write(root, f"{name}.py", "X = 1\n")
            _write(root, "app.py", "import service\n\nif __name__ == \"__main__\":\n    pass\n")
            _write(root, "service.py", "".join(f"import {name}\n" for name in names))

            advices = analyze_project_payload(root)["advice"]

            self.assertEqual([item["targets"] for item in advices], [["service"]])
            self.assertEqual(advices[0]["evidence"]["fan_out"], FAN_OUT_THRESHOLD)


class ReadingOrderAdviceTests(unittest.TestCase):
    def _reading_order(self, root: Path) -> list[dict]:
        return [item for item in _full_payload(root)["advice"] if item["rule_id"] == "reading-order"]

    def test_stages_follow_entry_and_dependency_depth(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write(root, "app.py", "import service\n\nif __name__ == \"__main__\":\n    pass\n")
            _write(root, "service.py", "import repo\n")
            _write(root, "repo.py", "X = 1\n")

            advices = self._reading_order(root)

            self.assertEqual(len(advices), 1)
            self.assertEqual(advices[0]["severity"], "low")
            self.assertEqual(advices[0]["targets"], ["app", "service", "repo"])
            self.assertEqual([stage["depth"] for stage in advices[0]["evidence"]["stages"]], [0, 1, 2])
            self.assertIn("目安", advices[0]["reason"])

    def test_orders_stage_by_fan_in_and_caps_per_stage(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            count = READING_ORDER_MAX_PER_STAGE + 2
            names = [f"m{index}" for index in range(count)]
            _write(root, "app.py", "".join(f"import {name}\n" for name in names) + "\nif __name__ == \"__main__\":\n    pass\n")
            for name in names:
                _write(root, f"{name}.py", "X = 1\n")
            _write(root, "m6.py", "import m5\n")

            stage = self._reading_order(root)[0]["evidence"]["stages"][1]

            self.assertEqual(len(stage["modules"]), READING_ORDER_MAX_PER_STAGE)
            self.assertEqual(stage["modules"][0], "m5")

    def test_no_advice_without_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write(root, "only.py", "X = 1\n")

            self.assertEqual(self._reading_order(root), [])

    def test_unreachable_modules_are_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write(root, "app.py", "import util\n\nif __name__ == \"__main__\":\n    pass\n")
            _write(root, "util.py", "X = 1\n")
            _write(root, "orphan.py", "import util\n")

            targets = self._reading_order(root)[0]["targets"]

            self.assertNotIn("orphan", targets)


class UnreachableModuleAdviceTests(unittest.TestCase):
    def _advice(self, root: Path) -> list[dict]:
        return [item for item in _full_payload(root)["advice"] if item["rule_id"] == "unreachable-module"]

    def test_groups_unreachable_modules_into_one_advice(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write(root, "app.py", "import util\n\nif __name__ == \"__main__\":\n    pass\n")
            _write(root, "util.py", "X = 1\n")
            _write(root, "old_b.py", "X = 1\n")
            _write(root, "old_a.py", "import util\n")

            advices = self._advice(root)

            self.assertEqual(len(advices), 1)
            self.assertEqual(advices[0]["severity"], "low")
            self.assertEqual(advices[0]["targets"], ["old_a", "old_b"])
            self.assertEqual(sorted(advices[0]["evidence"]["modules"]), ["old_a", "old_b"])

    def test_no_advice_when_everything_is_reachable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write(root, "app.py", "import util\n\nif __name__ == \"__main__\":\n    pass\n")
            _write(root, "util.py", "X = 1\n")

            self.assertEqual(self._advice(root), [])

    def test_ignores_package_init_modules(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write(root, "app.py", "\nif __name__ == \"__main__\":\n    pass\n")
            _write(root, "pkg/__init__.py", "")

            self.assertEqual(self._advice(root), [])


class LargeModuleAdviceTests(unittest.TestCase):
    def _advice(self, root: Path) -> list[dict]:
        return [item for item in _full_payload(root)["advice"] if item["rule_id"] == "large-module"]

    def test_reports_large_module_with_class_and_function_counts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            body = "class A:\n    pass\n\ndef f():\n    pass\n" + "X = 1\n" * LARGE_MODULE_LINES
            _write(root, "big.py", body)

            advices = self._advice(root)

            self.assertEqual(len(advices), 1)
            self.assertEqual(advices[0]["severity"], "low")
            self.assertEqual(advices[0]["targets"], ["big"])
            self.assertEqual(advices[0]["evidence"]["class_count"], 1)
            self.assertEqual(advices[0]["evidence"]["function_count"], 1)

    def test_very_large_module_is_medium(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write(root, "huge.py", "X = 1\n" * VERY_LARGE_MODULE_LINES)

            self.assertEqual(self._advice(root)[0]["severity"], "medium")

    def test_small_module_is_not_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write(root, "small.py", "X = 1\n" * (LARGE_MODULE_LINES - 1))

            self.assertEqual(self._advice(root), [])

    def test_module_already_covered_by_concentration_is_not_duplicated(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write(root, "hub.py", "X = 1\n" * LARGE_MODULE_LINES)
            for index in range(FAN_IN_THRESHOLD):
                _write(root, f"user{index}.py", "import hub\n")

            self.assertEqual(self._advice(root), [])


if __name__ == "__main__":
    unittest.main()
