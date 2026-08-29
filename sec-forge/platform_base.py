from __future__ import annotations

from abc import ABC, abstractmethod

from tool import Tool


class PlatformLauncher(ABC):
    @abstractmethod
    def supports(self, tool: Tool) -> bool: ...

    @abstractmethod
    def launch(self, tool: Tool) -> None: ...
