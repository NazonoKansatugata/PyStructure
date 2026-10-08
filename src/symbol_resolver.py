from __future__ import annotations

from import_resolver import ImportResolver
from models import ImportInfo, ModuleInfo, module_node_id

_MAX_REEXPORT_DEPTH = 8


class SymbolResolver:
    """Resolve dotted names written in a module to graph node ids of project symbols."""

    def __init__(self, modules: list[ModuleInfo]) -> None:
        resolver = ImportResolver()
        self._modules = {module.module_name for module in modules}
        self._functions = {module.module_name: {item.name for item in module.functions} for module in modules}
        self._classes = {
            module.module_name: {item.name: {method.name for method in item.methods} for item in module.classes}
            for module in modules
        }
        self._import_maps = {module.module_name: resolver.binding_map(module.imports) for module in modules}

    def resolve(self, module_name: str, dotted: str) -> str | None:
        parts = dotted.split(".")
        local = self._resolve_in_module(module_name, parts)
        if local is not None:
            return local

        target = self._import_maps.get(module_name, {}).get(parts[0])
        if target is None:
            return None
        return self._resolve_absolute(target.split(".") + parts[1:], 0)

    def import_targets(self, import_info: ImportInfo) -> list[tuple[str, list[str]]]:
        """Return (name as written, project modules it resolves to) for each imported group."""
        if import_info.module:
            groups = [[import_info.module, *(f"{import_info.module}.{name}" for name in import_info.names)]]
        else:
            groups = [[name] for name in import_info.names]

        targets: list[tuple[str, list[str]]] = []
        for group in groups:
            internal: list[str] = []
            for candidate in group:
                module = self._longest_known_module(candidate)
                if module is not None and module not in internal:
                    internal.append(module)
            targets.append((group[0], internal))
        return targets

    def qualify(self, module_name: str, dotted: str) -> str:
        """Return the imported absolute name for a dotted name, or the name itself if not imported."""
        head, _, rest = dotted.partition(".")
        target = self._import_maps.get(module_name, {}).get(head)
        if target is None:
            return dotted
        return f"{target}.{rest}" if rest else target

    def _longest_known_module(self, dotted: str) -> str | None:
        parts = dotted.split(".")
        for length in range(len(parts), 0, -1):
            candidate = ".".join(parts[:length])
            if candidate in self._modules:
                return candidate
        return None

    def _resolve_in_module(self, module_name: str, parts: list[str]) -> str | None:
        head = parts[0]
        if head in self._functions.get(module_name, ()):
            return f"{module_name}::{head}"
        methods = self._classes.get(module_name, {}).get(head)
        if methods is not None:
            if len(parts) > 1 and parts[1] in methods:
                return f"{module_name}::{head}::{parts[1]}"
            return f"{module_name}::{head}"
        return None

    def _resolve_absolute(self, parts: list[str], depth: int) -> str | None:
        for length in range(len(parts), 0, -1):
            module_name = ".".join(parts[:length])
            if module_name not in self._modules:
                continue
            rest = parts[length:]
            if not rest:
                return module_node_id(module_name)
            symbol = self._resolve_in_module(module_name, rest)
            if symbol is not None:
                return symbol
            reexported = self._import_maps[module_name].get(rest[0])
            if reexported is not None and depth < _MAX_REEXPORT_DEPTH:
                return self._resolve_absolute(reexported.split(".") + rest[1:], depth + 1)
            return module_node_id(module_name)
        return None
