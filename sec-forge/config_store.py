"""JSON 配置读写。"""

from __future__ import annotations

import json
from pathlib import Path

from tool import Tool


class ConfigStore:
    SCHEMA_VERSION = 1

    def __init__(self, path: Path) -> None:
        self.path = path

    def load_tools(self) -> list[Tool]:
        if not self.path.exists():
            return []
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if raw.get("schema_version") != self.SCHEMA_VERSION:
            raise ValueError("不支持的配置文件版本")
        return [Tool.from_dict(item) for item in raw.get("tools", [])]

    def save_tools(self, tools: list[Tool]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({"schema_version": self.SCHEMA_VERSION, "tools": [tool.to_dict() for tool in tools]}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
