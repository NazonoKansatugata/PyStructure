from __future__ import annotations

import ast
from collections.abc import Collection

from models import UseInfo, module_node_id


def _dotted_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _dotted_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else None
    return None


class _UseVisitor(ast.NodeVisitor):
    """Collect non-call references to known names, attributed to the enclosing top-level symbol."""

    def __init__(self, module_name: str, known_heads: Collection[str]) -> None:
        self.module_name = module_name
        self.known_heads = known_heads
        self.uses: dict[tuple[str, str], int] = {}
        self.class_name: str | None = None
        self.function_name: str | None = None

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        if self.class_name is not None or self.function_name is not None:
            self.generic_visit(node)
            return
        # 基底クラスは inherits 辺で扱うため、ここでは参照として数えない。
        for decorator in node.decorator_list:
            self.visit(decorator)
        for keyword in node.keywords:
            self.visit(keyword.value)
        self.class_name = node.name
        for child in node.body:
            self.visit(child)
        self.class_name = None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def visit_Call(self, node: ast.Call) -> None:
        # 呼び出し先そのものは calls 辺で扱う。
        if _dotted_name(node.func) is None:
            self.visit(node.func)
        for argument in node.args:
            self.visit(argument)
        for keyword in node.keywords:
            self.visit(keyword.value)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        dotted = _dotted_name(node)
        if dotted is None:
            self.generic_visit(node)
            return
        self._record(dotted, node.lineno)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self._record(node.id, node.lineno)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        if self.function_name is not None:
            self.generic_visit(node)
            return
        self.function_name = node.name
        self.generic_visit(node)
        self.function_name = None

    def _record(self, name: str, lineno: int) -> None:
        if name.split(".")[0] in self.known_heads:
            self.uses.setdefault((self._user_id(), name), lineno)

    def _user_id(self) -> str:
        if self.class_name and self.function_name:
            return f"{self.module_name}::{self.class_name}::{self.function_name}"
        if self.function_name:
            return f"{self.module_name}::{self.function_name}"
        if self.class_name:
            return f"{self.module_name}::{self.class_name}"
        return module_node_id(self.module_name)


class UseAnalyzer:
    def analyze(self, module_name: str, tree: ast.AST, known_heads: Collection[str]) -> tuple[UseInfo, ...]:
        visitor = _UseVisitor(module_name, known_heads)
        visitor.visit(tree)
        return tuple(UseInfo(user=user, name=name, lineno=lineno) for (user, name), lineno in visitor.uses.items())
