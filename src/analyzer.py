from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from graph import GraphBuilder, DependencyGraph
from import_resolver import ImportResolver
from models import AnalysisResult, ClassInfo, FunctionInfo, ImportInfo, ModuleInfo
from scanner import ProjectScanner


@dataclass
class _ModuleVisitor(ast.NodeVisitor):
    imports: list[ImportInfo]
    classes: list[ClassInfo]
    functions: list[FunctionInfo]

    def visit_Import(self, node: ast.Import) -> None:
        self.imports.append(
            ImportInfo(
                module=None,
                names=tuple(alias.name for alias in node.names),
                level=0,
                lineno=node.lineno,
            )
        )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        self.imports.append(
            ImportInfo(
                module=node.module,
                names=tuple(alias.name for alias in node.names),
                level=node.level,
                lineno=node.lineno,
            )
        )

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        methods: list[FunctionInfo] = []
        for child in node.body:
            if isinstance(child, ast.FunctionDef):
                methods.append(
                    FunctionInfo(name=child.name, lineno=child.lineno, is_async=False, kind="method")
                )
            elif isinstance(child, ast.AsyncFunctionDef):
                methods.append(
                    FunctionInfo(name=child.name, lineno=child.lineno, is_async=True, kind="method")
                )

        bases = tuple(self._name_from_expr(base) for base in node.bases)
        self.classes.append(ClassInfo(name=node.name, lineno=node.lineno, bases=bases, methods=tuple(methods)))

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.functions.append(FunctionInfo(name=node.name, lineno=node.lineno, is_async=False))

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.functions.append(FunctionInfo(name=node.name, lineno=node.lineno, is_async=True))

    def _name_from_expr(self, expr: ast.AST) -> str:
        if isinstance(expr, ast.Name):
            return expr.id
        if isinstance(expr, ast.Attribute):
            prefix = self._name_from_expr(expr.value)
            return f"{prefix}.{expr.attr}" if prefix else expr.attr
        return ast.unparse(expr) if hasattr(ast, "unparse") else expr.__class__.__name__


class ProjectAnalyzer:
    def __init__(self) -> None:
        self.scanner = ProjectScanner()
        self.import_resolver = ImportResolver()
        self.graph_builder = GraphBuilder()

    def analyze(self, root: Path) -> AnalysisResult:
        root = root.resolve()
        modules = [self._analyze_file(root, path) for path in self.scanner.scan(root)]
        return AnalysisResult(root=root, modules=modules)

    def build_graph(self, root: Path) -> tuple[AnalysisResult, DependencyGraph]:
        result = self.analyze(root)
        return result, self.graph_builder.build(result.modules)

    def _analyze_file(self, root: Path, path: Path) -> ModuleInfo:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        visitor = _ModuleVisitor(imports=[], classes=[], functions=[])
        visitor.visit(tree)

        module_name = self.import_resolver.resolve_package_name(root, path)
        imports = tuple(
            ImportInfo(
                module=self.import_resolver.resolve_relative_module(
                    module_name,
                    item.level,
                    item.module,
                    current_is_package=path.name == "__init__.py",
                ),
                names=item.names,
                level=item.level,
                lineno=item.lineno,
            )
            for item in visitor.imports
        )
        return ModuleInfo(
            path=path,
            module_name=module_name,
            imports=imports,
            classes=tuple(visitor.classes),
            functions=tuple(visitor.functions),
        )