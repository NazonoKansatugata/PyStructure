from __future__ import annotations

from pathlib import Path


class ProjectScanner:
    """Find Python source files and derive module names."""

    excluded_names = {
        ".git",
        ".hg",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "build",
        "dist",
        "env",
        "venv",
        "__pycache__",
    }

    def scan(self, root: Path) -> list[Path]:
        root = root.resolve()
        files: list[Path] = []
        for path in root.rglob("*.py"):
            if self._is_excluded(path, root):
                continue
            files.append(path)
        return sorted(files)

    def module_name(self, root: Path, path: Path) -> str:
        root = root.resolve()
        path = path.resolve()
        relative = path.relative_to(root).with_suffix("")
        parts = [part for part in relative.parts if part != "__init__"]
        if not parts:
            return root.name
        return ".".join(parts)

    def _is_excluded(self, path: Path, root: Path) -> bool:
        relative_parts = path.resolve().relative_to(root).parts
        return any(part in self.excluded_names for part in relative_parts)