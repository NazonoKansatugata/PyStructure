from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from graph import DependencyGraph
from models import AnalysisResult


@dataclass(frozen=True)
class JsonExporter:
    def payload(self, analysis: AnalysisResult, graph: DependencyGraph) -> dict[str, Any]:
        return {
            "analysis": analysis.to_dict(),
            "graph": graph.to_dict(),
        }

    def export(self, analysis: AnalysisResult, graph: DependencyGraph) -> str:
        return json.dumps(self.payload(analysis, graph), ensure_ascii=False, indent=2)


@dataclass(frozen=True)
class GraphvizExporter:
    def export(self, analysis: AnalysisResult, graph: DependencyGraph) -> str:
        lines = ["digraph PyStructure {"]

        for node in graph.nodes.values():
            label = node.label.replace('"', '\\"')
            lines.append(f'  "{node.id}" [label="{label}", kind="{node.kind}"];')

        for edge in graph.edges:
            lines.append(f'  "{edge.source}" -> "{edge.target}" [label="{edge.kind}"];')

        lines.append("}")
        return "\n".join(lines)


@dataclass(frozen=True)
class TextExporter:
    def export(self, analysis: AnalysisResult, graph: DependencyGraph) -> str:
        lines: list[str] = [
            f"Root: {analysis.root}",
            f"Modules: {len(analysis.modules)}",
            f"Nodes: {len(graph.nodes)}",
            f"Edges: {len(graph.edges)}",
            f"Circular modules: {sum(1 for module in analysis.modules if module.metrics.in_cycle)}",
            f"Unreachable modules: {sum(1 for module in analysis.modules if module.metrics.unreachable)}",
            f"Skipped files: {len(analysis.skipped)}",
            "",
            "Modules:",
        ]

        for module in analysis.modules:
            metrics = module.metrics
            flags = [flag for flag, active in (("entry", metrics.is_entry), ("cycle", metrics.in_cycle), ("unreachable", metrics.unreachable)) if active]
            suffix = f" [{', '.join(flags)}]" if flags else ""
            lines.append(f"- {module.module_name}{suffix}")
            lines.append(
                f"  Metrics: lines={metrics.line_count}, fan_in={metrics.fan_in}, fan_out={metrics.fan_out}, depth={metrics.depth}"
            )
            lines.append(f"  Imports: {len(module.imports)}")
            for import_info in module.imports:
                bindings = ", ".join(
                    f"{binding.name} as {binding.asname}" if binding.asname else binding.name
                    for binding in import_info.bindings
                )
                source = import_info.module or "(absolute)"
                lines.append(f"    - import {source}: {bindings}")
            lines.append(f"  Classes: {len(module.classes)}")
            for class_info in module.classes:
                bases = f" ({', '.join(class_info.bases)})" if class_info.bases else ""
                lines.append(f"    - class {class_info.name}{bases}")
                for method in class_info.methods:
                    kind = "async method" if method.is_async else "method"
                    lines.append(f"      - {kind} {method.name}")
            lines.append(f"  Functions: {len(module.functions)}")
            for function_info in module.functions:
                kind = "async function" if function_info.is_async else "function"
                lines.append(f"    - {kind} {function_info.name}")
            lines.append(f"  Calls: {len(module.calls)}")
            for call in module.calls:
                target = call.resolved_callee or call.callee
                lines.append(f"    - {call.caller} -> {target} (line {call.lineno})")

        return "\n".join(lines)