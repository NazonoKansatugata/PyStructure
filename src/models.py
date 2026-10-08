from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ImportBinding:
    name: str
    asname: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "asname": self.asname,
        }


@dataclass(frozen=True)
class ImportInfo:
    module: str | None
    names: tuple[str, ...]
    bindings: tuple[ImportBinding, ...]
    level: int
    lineno: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "module": self.module,
            "names": list(self.names),
            "bindings": [binding.to_dict() for binding in self.bindings],
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
class CallInfo:
    caller: str
    callee: str
    resolved_callee: str | None
    lineno: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "caller": self.caller,
            "callee": self.callee,
            "resolved_callee": self.resolved_callee,
            "lineno": self.lineno,
        }


@dataclass(frozen=True)
class UseInfo:
    # user はグラフのノード ID、name は未解決のドット区切り名。
    user: str
    name: str
    lineno: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "user": self.user,
            "name": self.name,
            "lineno": self.lineno,
        }


def module_node_id(module_name: str) -> str:
    return f"module::{module_name}"


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
class ModuleMetrics:
    line_count: int = 0
    size_bytes: int = 0
    fan_in: int = 0
    fan_out: int = 0
    in_cycle: bool = False
    is_entry: bool = False
    # エントリーポイントからの最短 import 距離。到達不能なら None。
    depth: int | None = None

    @property
    def unreachable(self) -> bool:
        return self.depth is None

    def to_dict(self) -> dict[str, Any]:
        return {
            "line_count": self.line_count,
            "size_bytes": self.size_bytes,
            "fan_in": self.fan_in,
            "fan_out": self.fan_out,
            "in_cycle": self.in_cycle,
            "is_entry": self.is_entry,
            "depth": self.depth,
            "unreachable": self.unreachable,
        }


@dataclass(frozen=True)
class ModuleInfo:
    path: Path
    module_name: str
    imports: tuple[ImportInfo, ...] = ()
    classes: tuple[ClassInfo, ...] = ()
    functions: tuple[FunctionInfo, ...] = ()
    calls: tuple[CallInfo, ...] = ()
    uses: tuple[UseInfo, ...] = ()
    has_main_guard: bool = False
    metrics: ModuleMetrics = field(default_factory=ModuleMetrics)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "module_name": self.module_name,
            "imports": [item.to_dict() for item in self.imports],
            "classes": [item.to_dict() for item in self.classes],
            "functions": [item.to_dict() for item in self.functions],
            "calls": [item.to_dict() for item in self.calls],
            "uses": [item.to_dict() for item in self.uses],
            "has_main_guard": self.has_main_guard,
            "metrics": self.metrics.to_dict(),
        }


@dataclass(frozen=True)
class SkippedFile:
    path: Path
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class GraphNode:
    id: str
    label: str
    kind: str
    module_name: str
    path: str
    lineno: int | None = None
    metrics: ModuleMetrics | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "label": self.label,
            "kind": self.kind,
            "module_name": self.module_name,
            "path": self.path,
            "lineno": self.lineno,
        }
        if self.metrics is not None:
            data["metrics"] = self.metrics.to_dict()
        return data


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
    skipped: list[SkippedFile] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "root": str(self.root),
            "modules": [module.to_dict() for module in self.modules],
            "skipped": [item.to_dict() for item in self.skipped],
        }