"""Windows 上各类工具的校验、命令构建与异步启动。"""

from __future__ import annotations

import os
import shlex
import subprocess
import webbrowser
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Mapping

from platform_base import PlatformLauncher
from tool import LaunchType, Tool


class LaunchError(RuntimeError):
    """表示可直接展示给用户的工具启动错误。"""


class LaunchMethod(StrEnum):
    PROCESS = "process"
    SHELL_OPEN = "shell_open"
    URL = "url"


@dataclass(frozen=True, slots=True)
class LaunchRequest:
    """完成校验后的启动请求，便于在执行前独立测试命令与工作目录。"""

    method: LaunchMethod
    command: tuple[str, ...] = ()
    target: str = ""
    arguments: str = ""
    working_directory: Path | None = None
    new_console: bool = False


class WindowsLauncher(PlatformLauncher):
    """按工具类型使用 Windows 原生运行时启动工具。"""

    def __init__(self, environment_paths: Mapping[str, str]) -> None:
        self._environment_paths = environment_paths

    def supports(self, tool: Tool) -> bool:
        return tool.launch_type in LaunchType

    def prepare(self, tool: Tool) -> LaunchRequest:
        """校验工具配置并生成启动请求，不创建进程。"""

        if tool.launch_type is LaunchType.WEB:
            url = tool.profile.target.strip()
            if not url:
                raise LaunchError("该网页工具未配置 URL。")
            return LaunchRequest(LaunchMethod.URL, target=url)

        target = self._existing_file(tool.profile.target)
        arguments = self._split_arguments(tool.profile.arguments)

        if tool.launch_type is LaunchType.PYTHON:
            self._require_suffix(target, ".py", "Python")
            python = self._existing_runtime("python_path", "Python 程序")
            # Python 脚本可能因执行完成或启动报错而立即退出。通过 cmd /k 调用
            # 配置的解释器可保留终端，让用户看到输出与错误信息，避免窗口闪退。
            command = (
                os.environ.get("COMSPEC", "cmd.exe"),
                "/k",
                str(python),
                str(target),
                *arguments,
            )
            return self._process_request(command, target.parent, True)

        if tool.launch_type in {LaunchType.JAVA_8, LaunchType.JAVA_11}:
            version = "Java 8" if tool.launch_type is LaunchType.JAVA_8 else "Java 11"
            setting = "java8_path" if tool.launch_type is LaunchType.JAVA_8 else "java11_path"
            self._require_suffix(target, ".jar", version)
            java = self._java_executable(setting, version)
            return self._process_request((str(java), "-jar", str(target), *arguments), target.parent)

        if tool.launch_type is LaunchType.GUI:
            if target.suffix.lower() in {".exe", ".com"}:
                # 可执行 GUI 程序直接交给 CreateProcess，不经过 ShellExecute。
                # 这样不会触发 Shell 对带来源标记文件显示的“打开文件”确认框，
                # 同时不会删除文件标记或降低 Windows 的全局安全设置。
                return self._process_request((str(target), *arguments), target.parent)
            # VBS 等依赖系统文件关联的 GUI 启动项仍使用 Windows Shell，保持兼容。
            return LaunchRequest(
                LaunchMethod.SHELL_OPEN,
                target=str(target),
                arguments=tool.profile.arguments.strip(),
                working_directory=target.parent,
            )

        if tool.launch_type is LaunchType.CLI:
            command = (os.environ.get("COMSPEC", "cmd.exe"), "/k", str(target), *arguments)
            return self._process_request(command, target.parent, True)

        if tool.launch_type is LaunchType.BATCH:
            self._require_suffix(target, ".bat", "批处理")
            return LaunchRequest(
                LaunchMethod.SHELL_OPEN,
                target=str(target),
                arguments=tool.profile.arguments.strip(),
                working_directory=target.parent,
            )

        if tool.launch_type is LaunchType.POWERSHELL:
            command = (
                "powershell.exe", "-NoLogo", "-NoExit", "-Command", "&", str(target), *arguments
            )
            return self._process_request(command, target.parent, True)

        raise LaunchError(f"不支持的工具类型：{tool.launch_type}")

    def launch(self, tool: Tool) -> None:
        """异步启动工具；系统级失败统一转换为可读提示。"""

        request = self.prepare(tool)
        try:
            if request.method is LaunchMethod.PROCESS:
                creation_flags = subprocess.CREATE_NEW_CONSOLE if request.new_console else 0
                subprocess.Popen(
                    list(request.command), cwd=request.working_directory, creationflags=creation_flags
                )
                return
            if request.method is LaunchMethod.SHELL_OPEN:
                startfile = getattr(os, "startfile", None)
                if startfile is None:
                    raise OSError("当前系统不支持 Windows Shell 启动")
                startfile(
                    request.target,
                    "open",
                    request.arguments,
                    str(request.working_directory) if request.working_directory else None,
                )
                return
            if not webbrowser.open(request.target):
                raise OSError("默认浏览器未接受该 URL")
        except OSError as error:
            raise LaunchError(f"启动工具失败：{error}") from error

    @staticmethod
    def _process_request(
        command: tuple[str, ...], working_directory: Path, new_console: bool = False
    ) -> LaunchRequest:
        return LaunchRequest(
            LaunchMethod.PROCESS,
            command=command,
            working_directory=working_directory,
            new_console=new_console,
        )

    @staticmethod
    def _existing_file(path_text: str) -> Path:
        path_text = path_text.strip()
        if not path_text:
            raise LaunchError("该工具未配置工具路径。")
        path = Path(path_text).expanduser()
        if not path.is_file():
            raise LaunchError(f"工具文件不存在：\n{path}")
        return path.resolve()

    def _existing_runtime(self, setting: str, display_name: str) -> Path:
        path_text = str(self._environment_paths.get(setting, "")).strip()
        if not path_text:
            raise LaunchError(f"settings.json 中未配置{display_name}路径。")
        path = Path(path_text).expanduser()
        if not path.is_file():
            raise LaunchError(f"settings.json 中配置的{display_name}不存在：\n{path}")
        return path.resolve()

    def _java_executable(self, setting: str, version: str) -> Path:
        path_text = str(self._environment_paths.get(setting, "")).strip()
        if not path_text:
            raise LaunchError(f"settings.json 中未配置{version}路径。")
        configured_path = Path(path_text).expanduser()
        # 设置界面约定保存 JDK/JRE 的 bin 目录；同时兼容用户直接填写 java.exe。
        java = configured_path if configured_path.name.lower() == "java.exe" else configured_path / "java.exe"
        if not java.is_file():
            raise LaunchError(f"settings.json 中配置的{version} java.exe 不存在：\n{java}")
        return java.resolve()

    @staticmethod
    def _require_suffix(path: Path, suffix: str, display_name: str) -> None:
        if path.suffix.lower() != suffix:
            raise LaunchError(f"{display_name} 工具路径必须是 {suffix} 文件：\n{path}")

    @staticmethod
    def _split_arguments(arguments: str) -> tuple[str, ...]:
        """按 Windows 命令行习惯拆分参数，同时保留带空格的成组参数。"""

        if not arguments.strip():
            return ()
        try:
            values = shlex.split(arguments, posix=False)
        except ValueError as error:
            raise LaunchError(f"启动参数格式无效：{error}") from error
        return tuple(
            value[1:-1] if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"} else value
            for value in values
        )
