from __future__ import annotations

from pathlib import Path

from config import EXCLUDED_DIR_NAMES, EXCLUDED_FILE_PREFIXES
from settings import ProjectSettings


class ProjectScanner:
    """Find Python source files and derive module names."""

    excluded_names = EXCLUDED_DIR_NAMES

    def scan(self, root: Path) -> list[Path]:
        root = root.resolve()
        settings = ProjectSettings.load(root)
        files: list[Path] = []
        for path in root.rglob("*.py"):
            if self._is_excluded(path, root, settings):
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

    def _is_excluded(self, path: Path, root: Path, settings: ProjectSettings) -> bool:
        if path.name.startswith(EXCLUDED_FILE_PREFIXES):
            return True
        relative_parts = path.resolve().relative_to(root).parts
        if any(part in self.excluded_names for part in relative_parts):
            return True
        return settings.is_excluded(relative_parts)