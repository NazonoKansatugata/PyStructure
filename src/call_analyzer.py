from __future__ import annotations

import ast

from models import CallInfo, ImportInfo


class _CallVisitor(ast.NodeVisitor):
    def __init__(self, module_name: str, imports: tuple[ImportInfo, ...]) -> None:
        self.module_name = module_name
        self.calls: list[CallInfo] = []
        self.class_stack: list[str] = []
        self.function_stack: list[str] = []
        self.import_map = self._build_import_map(imports)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.class_stack.append(node.name)
        for child in node.body:
            if isinstance(child, ast.FunctionDef):
                self.visit(child)
            elif isinstance(child, ast.AsyncFunctionDef):
                self.visit(child)
        self.class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.function_stack.append(node.name)
        for child in node.body:
            self.visit(child)
        self.function_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.function_stack.append(node.name)
        for child in node.body:
            self.visit(child)
        self.function_stack.pop()

    def visit_Call(self, node: ast.Call) -> None:
        if self.function_stack:
            caller = self._current_caller()
            callee = self._call_name(node.func)
            resolved_callee = self._resolve_callee(node.func)
            self.calls.append(
                CallInfo(caller=caller, callee=callee, resolved_callee=resolved_callee, lineno=node.lineno)
            )
        self.generic_visit(node)

    def _current_caller(self) -> str:
        function_name = self.function_stack[-1]
        if self.class_stack:
            return f"{self.module_name}::{self.class_stack[-1]}::{function_name}"
        return f"{self.module_name}::{function_name}"

    def _call_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            prefix = self._call_name(node.value)
            return f"{prefix}.{node.attr}" if prefix else node.attr
        return ast.unparse(node) if hasattr(ast, "unparse") else node.__class__.__name__

    def _resolve_callee(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Name):
            return self.import_map.get(node.id)
        if isinstance(node, ast.Attribute):
            prefix = self._resolve_callee(node.value)
            if prefix:
                return f"{prefix}.{node.attr}"
        return None

    def _build_import_map(self, imports: tuple[ImportInfo, ...]) -> dict[str, str]:
        import_map: dict[str, str] = {}
        for item in imports:
            if item.module:
                for binding in item.bindings:
                    exported_name = binding.asname or binding.name
                    import_map[exported_name] = f"{item.module}.{binding.name}"
            else:
                for binding in item.bindings:
                    exported_name = binding.asname or binding.name
                    import_map[exported_name] = binding.name
        return import_map


class CallAnalyzer:
    def analyze(self, module_name: str, tree: ast.AST, imports: tuple[ImportInfo, ...]) -> tuple[CallInfo, ...]:
        visitor = _CallVisitor(module_name, imports)
        visitor.visit(tree)
        return tuple(visitor.calls)