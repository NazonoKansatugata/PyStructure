from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ImportInfo:
    module: str | None
    names: tuple[str, ...]
    level: int
    lineno: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "module": self.module,
            "names": list(self.names),
            "level": self.level,
            "lineno": self.lineno,
        }


@dataclass(frozen=True)
class FunctionInfo:
    name: str
    lineno: int
    is_async: bool = False
    kind: str = "function"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "lineno": self.lineno,
            "is_async": self.is_async,
            "kind": self.kind,
        }


@dataclass(frozen=True)
class ClassInfo:
    name: str
    lineno: int
    bases: tuple[str, ...] = ()
    methods: tuple[FunctionInfo, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "lineno": self.lineno,
            "bases": list(self.bases),
            "methods": [method.to_dict() for method in self.methods],
        }


@dataclass(frozen=True)
class ModuleInfo:
    path: Path
    module_name: str
    imports: tuple[ImportInfo, ...] = ()
    classes: tuple[ClassInfo, ...] = ()
    functions: tuple[FunctionInfo, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "module_name": self.module_name,
            "imports": [item.to_dict() for item in self.imports],
            "classes": [item.to_dict() for item in self.classes],
            "functions": [item.to_dict() for item in self.functions],
        }


@dataclass(frozen=True)
class GraphNode:
    id: str
    label: str
    kind: str
    module_name: str
    path: str
    lineno: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "kind": self.kind,
            "module_name": self.module_name,
            "path": self.path,
            "lineno": self.lineno,
        }


@dataclass(frozen=True)
class GraphEdge:
    source: str
    target: str
    kind: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "kind": self.kind,
        }


@dataclass
class AnalysisResult:
    root: Path
    modules: list[ModuleInfo] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "root": str(self.root),
            "modules": [module.to_dict() for module in self.modules],
        }