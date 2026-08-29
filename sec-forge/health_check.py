"""仅检查配置与文件存在性；不会运行任何受管工具。"""

from __future__ import annotations

from pathlib import Path

from tool import LaunchType, Tool, ToolHealth


def check_tool(tool: Tool) -> ToolHealth:
    profile = tool.profile
    if not tool.name or not profile.target:
        return ToolHealth.INCOMPLETE
    if tool.launch_type is LaunchType.WEB:
        return ToolHealth.NORMAL if profile.target.startswith(("http://", "https://")) else ToolHealth.INVALID_PATH
    if not Path(profile.target).is_file():
        return ToolHealth.INVALID_PATH
    if profile.working_directory and not Path(profile.working_directory).is_dir():
        return ToolHealth.INVALID_PATH
    return ToolHealth.NORMAL
