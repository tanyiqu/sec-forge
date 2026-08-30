"""工具配置领域模型。所有配置数据仅表示启动信息，不可作为代码执行。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any
from uuid import uuid4


class LaunchType(StrEnum):
    PYTHON = "python"
    JAVA_8 = "java8"
    JAVA_11 = "java11"
    GUI = "gui"
    CLI = "cli"
    BATCH = "batch"
    POWERSHELL = "powershell"
    WEB = "web"


class ToolHealth(StrEnum):
    NORMAL = "normal"
    INVALID_PATH = "invalid_path"
    INVALID_ENVIRONMENT = "invalid_environment"
    INCOMPLETE = "incomplete"
    UNCHECKED = "unchecked"


@dataclass(slots=True)
class ToolProfile:
    target: str = ""
    working_directory: str = ""
    environment_id: str | None = None
    pre_arguments: str = ""
    arguments: str = ""
    show_terminal: bool = False
    run_as_administrator: bool = False


@dataclass(slots=True)
class Tool:
    name: str
    category_id: str
    launch_type: LaunchType
    profile: ToolProfile
    id: str = field(default_factory=lambda: str(uuid4()))
    description: str = ""
    tags: list[str] = field(default_factory=list)
    icon_path: str = ""
    favorite: bool = False
    weight: int = 0
    health: ToolHealth = ToolHealth.UNCHECKED

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["launch_type"] = self.launch_type.value
        data["health"] = self.health.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Tool":
        return cls(
            id=str(data.get("id") or uuid4()),
            name=str(data.get("name", "")),
            category_id=str(data.get("category_id", "")),
            launch_type=LaunchType(data.get("launch_type", LaunchType.GUI)),
            profile=ToolProfile(**data.get("profile", {})),
            description=str(data.get("description", "")),
            tags=[str(tag) for tag in data.get("tags", [])],
            icon_path=str(data.get("icon_path", "")),
            favorite=bool(data.get("favorite", False)),
            weight=cls._normalized_weight(data.get("weight", 0)),
            health=ToolHealth(data.get("health", ToolHealth.UNCHECKED)),
        )

    @staticmethod
    def _normalized_weight(value: Any) -> int:
        """将配置中的权重限制在工具配置支持的 0 至 10 范围内。"""

        if isinstance(value, bool):
            return 0
        try:
            weight = int(value)
        except (TypeError, ValueError):
            return 0
        return weight if 0 <= weight <= 10 else 0
