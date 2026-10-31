from __future__ import annotations

from collections import deque
from typing import Protocol

from config import (
    FAN_IN_THRESHOLD,
    FAN_OUT_THRESHOLD,
    LARGE_MODULE_LINES,
    READING_ORDER_MAX_PER_STAGE,
    READING_ORDER_MAX_STAGES,
    UNREACHABLE_IGNORED_NAMES,
    VERY_LARGE_MODULE_LINES,
)
from metrics import MetricsAnalyzer
from models import Advice, AnalysisResult, ModuleMetrics
from graph import DependencyGraph

SEVERITY_HIGH = "high"
SEVERITY_MEDIUM = "medium"
SEVERITY_LOW = "low"


class AdviceRule(Protocol):
    """解析結果から 0 個以上の助言を生成するルール。1 ルール 1 クラスで実装する。"""

    rule_id: str

    def evaluate(self, analysis: AnalysisResult, graph: DependencyGraph) -> list[Advice]: ...


def internal_import_graph(analysis: AnalysisResult, graph: DependencyGraph) -> dict[str, set[str]]:
    """モジュール名をキーにした、プロジェクト内 import の隣接表を返す。"""
    prefix = "module::"
    names = {module.module_name for module in analysis.modules}
    outgoing: dict[str, set[str]] = {name: set() for name in names}
    for edge in graph.edges:
        if edge.kind != "imports" or not edge.source.startswith(prefix) or not edge.target.startswith(prefix):
            continue
        source, target = edge.source[len(prefix):], edge.target[len(prefix):]
        if source in names and target in names:
            outgoing[source].add(target)
    return outgoing


class CircularDependencyRule:
    rule_id = "circular-dependency"

    def evaluate(self, analysis: AnalysisResult, graph: DependencyGraph) -> list[Advice]:
        outgoing = internal_import_graph(analysis, graph)
        paths = {module.module_name: str(module.path) for module in analysis.modules}
        advices: list[Advice] = []

        for component in MetricsAnalyzer().cyclic_components(outgoing):
            members = set(component)
            cycle = self._shortest_cycle(component[0], outgoing, members)
            edges = [[source, target] for source in component for target in sorted(outgoing[source] & members)]
            names = "、".join(component)
            advices.append(
                Advice(
                    rule_id=self.rule_id,
                    severity=SEVERITY_HIGH,
                    title=f"循環参照を検出しました: {names}",
                    reason=(
                        f"{len(component)} 個のモジュールが互いに import し合っています。"
                        "変更時の影響範囲が広がったり、単体でのテストや再利用が難しくなったりする可能性があります。"
                    ),
                    suggestions=(
                        "循環しているモジュールが共通で必要としている処理やデータを確認してください。",
                        "共通部分を別のモジュールに切り出すことを検討してください。",
                        "依存の向きが一方向になるよう、責務の分け方を見直すことを検討してください。",
                    ),
                    targets=tuple(component),
                    evidence={
                        "cycle": cycle,
                        "edges": edges,
                        "paths": {name: paths[name] for name in component},
                    },
                )
            )
        return advices

    def _shortest_cycle(self, start: str, outgoing: dict[str, set[str]], members: set[str]) -> list[str]:
        """start から start に戻る最短経路を [start, ..., start] の形で返す。"""
        parents: dict[str, str | None] = {start: None}
        queue = deque([start])
        while queue:
            current = queue.popleft()
            for target in sorted(outgoing[current] & members):
                if target == start:
                    path = [current]
                    while parents[path[-1]] is not None:
                        path.append(parents[path[-1]])  # type: ignore[arg-type]
                    path.reverse()
                    return path + [start]
                if target not in parents:
                    parents[target] = current
                    queue.append(target)
        return [start]


def is_concentrated(metrics: ModuleMetrics) -> bool:
    """依存集中ルールの対象かどうか。巨大モジュールのルールとの重複判定にも使う。"""
    return metrics.fan_in >= FAN_IN_THRESHOLD or (
        metrics.fan_out >= FAN_OUT_THRESHOLD and not metrics.is_entry
    )


class DependencyConcentrationRule:
    """多くのモジュールから参照される、または多くのモジュールを参照するモジュールへの注意喚起。

    共通ユーティリティなど自然な設計の場合もあるため、断定せず確認を促す。
    行数が大きいものだけを重要度 medium とする。エントリーポイントの fan_out は自然なので対象外。
    """

    rule_id = "dependency-concentration"

    def evaluate(self, analysis: AnalysisResult, graph: DependencyGraph) -> list[Advice]:
        advices: list[Advice] = []
        for module in analysis.modules:
            metrics = module.metrics
            heavy_in = metrics.fan_in >= FAN_IN_THRESHOLD
            heavy_out = metrics.fan_out >= FAN_OUT_THRESHOLD and not metrics.is_entry
            if not (heavy_in or heavy_out):
                continue

            large = metrics.line_count >= LARGE_MODULE_LINES
            facts: list[str] = []
            if heavy_in:
                facts.append(f"{metrics.fan_in} 個のモジュールから参照されています")
            if heavy_out:
                facts.append(f"{metrics.fan_out} 個のモジュールを参照しています")
            if large:
                facts.append(f"{metrics.line_count} 行あり、複数の責務を持っている可能性があります")

            suggestions = [
                "このモジュールが共通基盤として意図されたものか確認してください。",
            ]
            if heavy_in:
                suggestions.append("変更すると多くのモジュールに影響するため、変更時はテストや影響範囲の確認を重点的に行うことを検討してください。")
            if heavy_out:
                suggestions.append("参照先が多いため、処理を役割ごとに分けて参照数を減らせないか検討してください。")
            if large:
                suggestions.append("責務ごとにモジュールを分割できないか検討してください。")

            advices.append(
                Advice(
                    rule_id=self.rule_id,
                    severity=SEVERITY_MEDIUM if large else SEVERITY_LOW,
                    title=f"依存が集中しているモジュール: {module.module_name}",
                    reason="、".join(facts) + "。依存が集中していても問題とは限りませんが、変更の影響が広がりやすい箇所です。",
                    suggestions=tuple(suggestions),
                    targets=(module.module_name,),
                    evidence={
                        "fan_in": metrics.fan_in,
                        "fan_out": metrics.fan_out,
                        "line_count": metrics.line_count,
                        "thresholds": {
                            "fan_in": FAN_IN_THRESHOLD,
                            "fan_out": FAN_OUT_THRESHOLD,
                            "large_module_lines": LARGE_MODULE_LINES,
                        },
                        "path": str(module.path),
                    },
                )
            )
        return advices


class ReadingOrderRule:
    """プロジェクトを読み進める際の推奨順序を段階的に示す学習支援。

    依存の深さは実行順序を表すとは限らないため、あくまで構造を把握するための目安として提示する。
    """

    rule_id = "reading-order"

    def evaluate(self, analysis: AnalysisResult, graph: DependencyGraph) -> list[Advice]:
        stages: dict[int, list] = {}
        for module in analysis.modules:
            depth = module.metrics.depth
            if depth is not None and depth <= READING_ORDER_MAX_STAGES:
                stages.setdefault(depth, []).append(module)
        if 0 not in stages or len(stages) < 2:
            return []

        labels = {0: "エントリーポイントを確認する"}
        suggestions: list[str] = []
        stage_names: list[list[str]] = []
        for depth in sorted(stages):
            # 多くのモジュールから参照されるものを先に読むと全体像をつかみやすい
            ordered = sorted(stages[depth], key=lambda item: (-item.metrics.fan_in, item.module_name))
            names = [item.module_name for item in ordered[:READING_ORDER_MAX_PER_STAGE]]
            stage_names.append(names)
            label = labels.get(depth, f"エントリーポイントから {depth} 段階先のモジュールを確認する")
            if depth == 1:
                label = "エントリーポイントが直接参照しているモジュールを確認する"
            more = len(ordered) - len(names)
            suffix = f"（ほか {more} 件）" if more > 0 else ""
            suggestions.append(f"{depth + 1}. {label}: {', '.join(names)}{suffix}")

        flat = tuple(name for names in stage_names for name in names)
        return [
            Advice(
                rule_id=self.rule_id,
                severity=SEVERITY_LOW,
                title="推奨する読み進め方",
                reason=(
                    "エントリーポイントから依存をたどる順に読むと、プロジェクトの構造を把握しやすくなります。"
                    "依存の深さは実際の実行順序とは一致しない場合があるため、目安として利用してください。"
                ),
                suggestions=tuple(suggestions) + ("必要に応じて、各モジュールのクラスや関数を確認してください。",),
                targets=flat,
                evidence={
                    "stages": [{"depth": depth, "modules": names} for depth, names in zip(sorted(stages), stage_names)],
                    "max_stages": READING_ORDER_MAX_STAGES,
                    "max_per_stage": READING_ORDER_MAX_PER_STAGE,
                },
            )
        ]


class UnreachableModuleRule:
    """エントリーポイントから import をたどっても到達できないモジュールの確認を促す。

    動的 import やプラグイン機構、単体スクリプトなど意図的な場合もあるため、断定しない。
    """

    rule_id = "unreachable-module"

    def evaluate(self, analysis: AnalysisResult, graph: DependencyGraph) -> list[Advice]:
        modules = [
            module
            for module in analysis.modules
            if module.metrics.unreachable and module.path.stem not in UNREACHABLE_IGNORED_NAMES
        ]
        if not modules:
            return []

        names = sorted(module.module_name for module in modules)
        return [
            Advice(
                rule_id=self.rule_id,
                severity=SEVERITY_LOW,
                title=f"エントリーポイントから到達できないモジュール: {len(names)} 件",
                reason=(
                    "エントリーポイントから import をたどっても到達できないモジュールです。"
                    "不要になったコードの可能性がありますが、動的な import や単体で実行するスクリプト、"
                    "テストなど、意図的に独立している場合もあります。"
                ),
                suggestions=(
                    "動的 import や外部から直接実行されるなど、意図的に独立しているモジュールか確認してください。",
                    "使われていない場合は、削除や整理を検討してください。",
                    "必要なモジュールであれば、利用元から import されているか確認してください。",
                ),
                targets=tuple(names),
                evidence={"modules": {module.module_name: str(module.path) for module in modules}},
            )
        ]


class LargeModuleRule:
    """行数が大きく、複数の責務を持っている可能性があるモジュールの分割を検討させる。

    行数だけでは責務の大きさは判断できないため、クラス・関数の数を併記して判断材料にする。
    依存集中ルールで既に扱われるモジュールは重複を避けて除外する。
    """

    rule_id = "large-module"

    def evaluate(self, analysis: AnalysisResult, graph: DependencyGraph) -> list[Advice]:
        advices: list[Advice] = []
        for module in analysis.modules:
            metrics = module.metrics
            if metrics.line_count < LARGE_MODULE_LINES or is_concentrated(metrics):
                continue

            class_count = len(module.classes)
            function_count = len(module.functions)
            very_large = metrics.line_count >= VERY_LARGE_MODULE_LINES
            advices.append(
                Advice(
                    rule_id=self.rule_id,
                    severity=SEVERITY_MEDIUM if very_large else SEVERITY_LOW,
                    title=f"規模の大きいモジュール: {module.module_name}",
                    reason=(
                        f"{metrics.line_count} 行あり、クラス {class_count} 個、関数 {function_count} 個を含みます。"
                        "規模が大きいと、読み解きや変更が難しくなり、複数の責務を持っている可能性があります。"
                    ),
                    suggestions=(
                        "モジュール内の処理を役割ごとに整理し、分けられるまとまりがないか確認してください。",
                        "関連するクラスや関数を別モジュールに切り出すことを検討してください。",
                        "規模が大きくても単一の責務であれば、そのままで問題ない場合もあります。",
                    ),
                    targets=(module.module_name,),
                    evidence={
                        "line_count": metrics.line_count,
                        "class_count": class_count,
                        "function_count": function_count,
                        "thresholds": {
                            "large_module_lines": LARGE_MODULE_LINES,
                            "very_large_module_lines": VERY_LARGE_MODULE_LINES,
                        },
                        "path": str(module.path),
                    },
                )
            )
        return advices


class AdviceEngine:
    def __init__(self, rules: list[AdviceRule] | None = None) -> None:
        self._rules: list[AdviceRule] = (
            rules
            if rules is not None
            else [
                CircularDependencyRule(),
                DependencyConcentrationRule(),
                LargeModuleRule(),
                UnreachableModuleRule(),
                ReadingOrderRule(),
            ]
        )

    def advise(self, analysis: AnalysisResult, graph: DependencyGraph) -> list[Advice]:
        advices = [advice for rule in self._rules for advice in rule.evaluate(analysis, graph)]
        order = {SEVERITY_HIGH: 0, SEVERITY_MEDIUM: 1, SEVERITY_LOW: 2}
        return sorted(advices, key=lambda advice: order.get(advice.severity, len(order)))
