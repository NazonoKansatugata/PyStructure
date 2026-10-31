from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from config import PROJECT_CONFIG_FILE_NAME

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProjectSettings:
    """プロジェクト直下の .pystructure.json から読み込むユーザー設定。

    exclude: 解析から除外するディレクトリ名、またはルートからの相対パス（"/" 区切り）。
    ディレクトリ名のみ（"build"）は階層を問わず一致し、"a/b" のようなパスはルート相対で一致する。
    """

    exclude: tuple[str, ...] = ()

    def is_excluded(self, relative_parts: tuple[str, ...]) -> bool:
        for pattern in self.exclude:
            pattern_parts = PurePosixPath(pattern).parts
            if not pattern_parts:
                continue
            if len(pattern_parts) == 1:
                if pattern_parts[0] in relative_parts:
                    return True
            elif relative_parts[: len(pattern_parts)] == pattern_parts:
                return True
        return False

    @classmethod
    def load(cls, root: Path) -> ProjectSettings:
        """設定ファイルを読む。無い場合や不正な場合は既定値を返し、警告のみ記録する。"""
        path = root / PROJECT_CONFIG_FILE_NAME
        if not path.is_file():
            return cls()
        try:
            data: Any = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as error:
            logger.warning("Ignoring unreadable settings file %s: %s", path, error)
            return cls()
        return cls._from_dict(data, path)

    @classmethod
    def _from_dict(cls, data: Any, path: Path) -> ProjectSettings:
        if not isinstance(data, dict):
            logger.warning("Ignoring settings file %s: top level must be an object", path)
            return cls()
        exclude = data.get("exclude", [])
        if not isinstance(exclude, list) or not all(isinstance(item, str) for item in exclude):
            logger.warning("Ignoring 'exclude' in %s: must be a list of strings", path)
            return cls()
        return cls(exclude=tuple(item.strip().strip("/\\") for item in exclude if item.strip().strip("/\\")))
