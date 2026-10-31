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

# 助言ルールの閾値。小規模プロジェクトで誤検出しにくい固定値から始め、利用結果を見て調整する。
FAN_IN_THRESHOLD = 5
FAN_OUT_THRESHOLD = 8
LARGE_MODULE_LINES = 300
VERY_LARGE_MODULE_LINES = 600
# 暗黙的に読み込まれるため、到達不能の助言から除外するファイル名（拡張子なし）。
UNREACHABLE_IGNORED_NAMES: frozenset[str] = frozenset({"__init__", "__main__"})
READING_ORDER_MAX_STAGES = 3
READING_ORDER_MAX_PER_STAGE = 5

# macOS の AppleDouble ファイル (._foo.py) は Python ソースではない。
EXCLUDED_FILE_PREFIXES: tuple[str, ...] = ("._",)

# プロジェクト直下に置く設定ファイル名。
PROJECT_CONFIG_FILE_NAME = ".pystructure.json"
