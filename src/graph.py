from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from models import GraphEdge, GraphNode, ModuleInfo, module_node_id
from symbol_resolver import SymbolResolver


@dataclass
class DependencyGraph:
    nodes: dict[str, GraphNode] = field(default_factory=dict)
    edges: list[GraphEdge] = field(default_factory=list)
    _edge_keys: set[tuple[str, str, str]] = field(default_factory=set, repr=False)

    def add_node(self, node: GraphNode) -> None:
        self.nodes[node.id] = node

    def add_edge(self, edge: GraphEdge) -> None:
        key = (edge.source, edge.target, edge.kind)
        if key not in self._edge_keys:
            self._edge_keys.add(key)
            self.edges.append(edge)

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "edges": [edge.to_dict() for edge in self.edges],
        }


class GraphBuilder:
    def build(self, modules: list[ModuleInfo]) -> DependencyGraph:
        graph = DependencyGraph()
        for module in modules:
            module_id = module_node_id(module.module_name)
            graph.add_node(
                GraphNode(
                    id=module_id,
                    label=module.module_name,
                    kind="module",
                    module_name=module.module_name,
                    path=str(module.path),
                    metrics=module.metrics,
                )
            )
            for class_info in module.classes:
                class_id = f"{module.module_name}::{class_info.name}"
                graph.add_node(
                    GraphNode(
                        id=class_id,
                        label=class_info.name,
                        kind="class",
                        module_name=module.module_name,
                        path=str(module.path),
                        lineno=class_info.lineno,
                    )
                )
                graph.add_edge(GraphEdge(source=class_id, target=module_id, kind="defined_in"))
                for method in class_info.methods:
                    method_id = f"{class_id}::{method.name}"
                    graph.add_node(
                        GraphNode(
                            id=method_id,
                            label=method.name,
                            kind="method",
                            module_name=module.module_name,
                            path=str(module.path),
                            lineno=method.lineno,
                        )
                    )
                    graph.add_edge(GraphEdge(source=method_id, target=class_id, kind="defined_in"))
            for function_info in module.functions:
                function_id = f"{module.module_name}::{function_info.name}"
                graph.add_node(
                    GraphNode(
                        id=function_id,
                        label=function_info.name,
                        kind="function",
                        module_name=module.module_name,
                        path=str(module.path),
                        lineno=function_info.lineno,
                    )
                )
                graph.add_edge(GraphEdge(source=function_id, target=module_id, kind="defined_in"))
        resolver = SymbolResolver(modules)
        self._add_import_edges(graph, modules, resolver)
        self._add_call_edges(graph, modules, resolver)
        self._add_symbol_edges(graph, modules, resolver)
        return graph

    def _add_import_edges(self, graph: DependencyGraph, modules: list[ModuleInfo], resolver: SymbolResolver) -> None:
        for module in modules:
            module_id = module_node_id(module.module_name)
            for import_info in module.imports:
                for written, internal in resolver.import_targets(import_info):
                    if not internal:
                        external_id = self._add_external(graph, written)
                        graph.add_edge(GraphEdge(source=module_id, target=external_id, kind="imports"))
                        continue
                    for target in internal:
                        if target != module.module_name:
                            graph.add_edge(
                                GraphEdge(source=module_id, target=module_node_id(target), kind="imports")
                            )

    def _add_call_edges(self, graph: DependencyGraph, modules: list[ModuleInfo], resolver: SymbolResolver) -> None:
        # 解決できない呼び出し (組込み・外部ライブラリ) は辺にせず、module.calls のみに残す。
        for module in modules:
            for call_info in module.calls:
                if call_info.caller not in graph.nodes:
                    continue
                target = call_info.resolved_callee
                if target not in graph.nodes:
                    target = resolver.resolve(module.module_name, call_info.callee)
                if target in graph.nodes and graph.nodes[target].kind in {"class", "function", "method"}:
                    graph.add_edge(GraphEdge(source=call_info.caller, target=target, kind="calls"))

    def _add_external(self, graph: DependencyGraph, name: str) -> str:
        external_id = f"external::{name}"
        graph.add_node(GraphNode(id=external_id, label=name, kind="external", module_name="", path=""))
        return external_id

    def _add_symbol_edges(self, graph: DependencyGraph, modules: list[ModuleInfo], resolver: SymbolResolver) -> None:
        for module in modules:
            for class_info in module.classes:
                class_id = f"{module.module_name}::{class_info.name}"
                for base in class_info.bases:
                    name = base.split("[", 1)[0]
                    if not self._is_dotted_name(name) or name == "object":
                        continue
                    resolved = resolver.resolve(module.module_name, name)
                    if resolved is None:
                        resolved = self._add_external(graph, resolver.qualify(module.module_name, name))
                    elif graph.nodes[resolved].kind != "class":
                        continue
                    if resolved != class_id:
                        graph.add_edge(GraphEdge(source=class_id, target=resolved, kind="inherits"))
            for use_info in module.uses:
                resolved = resolver.resolve(module.module_name, use_info.name)
                if resolved is not None and resolved != use_info.user and use_info.user in graph.nodes:
                    graph.add_edge(GraphEdge(source=use_info.user, target=resolved, kind="uses"))

    def _is_dotted_name(self, name: str) -> bool:
        return bool(name) and all(part.isidentifier() for part in name.split("."))
