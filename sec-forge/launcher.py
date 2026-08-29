"""安全的进程启动边界。"""

from __future__ import annotations

from abc import ABC, abstractmethod

from tool import Tool


class ToolLauncher(ABC):
    @abstractmethod
    def build_command_preview(self, tool: Tool) -> str:
        """返回供用户确认的命令预览，不执行工具。"""

    @abstractmethod
    def launch(self, tool: Tool) -> None:
        """启动已验证的工具；实现层应避免记录敏感参数。"""
