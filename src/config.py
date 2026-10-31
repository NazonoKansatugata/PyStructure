from __future__ import annotations

EXCLUDED_DIR_NAMES: frozenset[str] = frozenset(
    {
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
)

# macOS の AppleDouble ファイル (._foo.py) は Python ソースではない。
EXCLUDED_FILE_PREFIXES: tuple[str, ...] = ("._",)
