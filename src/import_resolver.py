from __future__ import annotations

from pathlib import Path

from models import ImportInfo


class ImportResolver:
    """Normalize import statements into module targets."""

    def binding_map(self, imports: tuple[ImportInfo, ...]) -> dict[str, str]:
        """Map each locally bound name to the absolute dotted name it refers to."""
        bindings: dict[str, str] = {}
        for item in imports:
            for binding in item.bindings:
                if binding.name == "*":
                    continue
                if item.module:
                    bindings[binding.asname or binding.name] = f"{item.module}.{binding.name}"
                elif item.level == 0:
                    head = binding.name.split(".")[0]
                    if binding.asname:
                        bindings[binding.asname] = binding.name
                    else:
                        bindings[head] = head
        return bindings

    def resolve_package_name(self, root: Path, path: Path) -> str:
        root = root.resolve()
        path = path.resolve()
        relative = path.relative_to(root).with_suffix("")
        parts = [part for part in relative.parts if part != "__init__"]
        if not parts:
            return root.name
        return ".".join(parts)

    def resolve_relative_module(
        self,
        current_module: str,
        level: int,
        module: str | None,
        *,
        current_is_package: bool = False,
    ) -> str | None:
        if level <= 0:
            return module

        current_parts = current_module.split(".")
        if current_is_package:
            parent_hops = max(level - 1, 0)
            if parent_hops == 0:
                base_parts = current_parts[:]
            else:
                base_parts = current_parts[:-parent_hops] if parent_hops <= len(current_parts) else []
        else:
            base_parts = current_parts[:-level] if level <= len(current_parts) else []

        if module:
            base_parts.extend(module.split("."))

        if not base_parts:
            return None
        return ".".join(base_parts)