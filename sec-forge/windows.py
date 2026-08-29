"""Windows 平台启动器预留接口。"""

from platform_base import PlatformLauncher


class WindowsLauncher(PlatformLauncher):
    def supports(self, tool):  # type: ignore[no-untyped-def]
        return True

    def launch(self, tool):  # type: ignore[no-untyped-def]
        raise NotImplementedError("Windows 启动逻辑将在工具管理功能完成后实现")
