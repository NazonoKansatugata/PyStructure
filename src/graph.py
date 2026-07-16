from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from models import GraphEdge, GraphNode, ModuleInfo


@dataclass
class DependencyGraph:
    nodes: dict[str, GraphNode] = field(default_factory=dict)
    edges: list[GraphEdge] = field(default_factory=list)

    def add_node(self, node: GraphNode) -> None:
        self.nodes[node.id] = node

    def add_edge(self, edge: GraphEdge) -> None:
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
            module_id = self._module_node_id(module.module_name)
            graph.add_node(
                GraphNode(
                    id=module_id,
                    label=module.module_name,
                    kind="module",
                    module_name=module.module_name,
                    path=str(module.path),
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
            for import_info in module.imports:
                targets = [import_info.module] if import_info.module else list(import_info.names)
                for target in targets:
                    if not target:
                        continue
                    graph.add_edge(GraphEdge(source=module_id, target=target, kind="imports"))
        return graph

    def _module_node_id(self, module_name: str) -> str:
        return f"module::{module_name}"