"""程序目录下 JSON 配置文件的创建与读写。"""

from __future__ import annotations

import json
from pathlib import Path

from tool import Tool


class ConfigStore:
    """集中管理系统设置、分类和工具列表的本地 JSON 配置。"""

    SCHEMA_VERSION = 1
    CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
    SETTINGS_PATH = CONFIG_DIR / "settings.json"
    CATEGORIES_PATH = CONFIG_DIR / "categories.json"
    TOOLS_PATH = CONFIG_DIR / "tools.json"

    # sec-forge.py 位于项目根目录，运行时环境目录与它同级。
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    _DEFAULT_ENVIRONMENT_PATHS = {
        "python_path": str(PROJECT_ROOT / "env" / "python3" / "python.exe"),
        "java8_path": str(PROJECT_ROOT / "env" / "Java_path" / "Java_8_win" / "bin"),
        "java11_path": str(PROJECT_ROOT / "env" / "Java_path" / "Java_11_win" / "bin"),
    }
    _DEFAULT_SETTINGS = {
        "schema_version": SCHEMA_VERSION,
        "general": {"minimize_to_tray_on_close": True},
        **_DEFAULT_ENVIRONMENT_PATHS,
    }
    _DEFAULT_CATEGORIES = {
        "schema_version": SCHEMA_VERSION,
        "categories": [
            {"id": "information_collection", "name": "信息收集", "order": 0},
            {"id": "vulnerability_scanning", "name": "漏洞扫描", "order": 1},
            {"id": "web_tools", "name": "Web 工具", "order": 2},
            {"id": "password_tools", "name": "密码工具", "order": 3},
            {"id": "other", "name": "其他工具", "order": 4},
        ],
    }
    _DEFAULT_TOOLS = {"schema_version": SCHEMA_VERSION, "tools": []}

    def __init__(self, path: Path | None = None) -> None:
        # 保留可传入路径的能力，以兼容已有的工具列表存储调用方式。
        self.path = path or self.TOOLS_PATH

    def ensure_config_files(self) -> None:
        """创建缺失的配置目录和默认配置文件，不覆盖用户已有数据。"""

        self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        default_files = {
            self.SETTINGS_PATH: self._DEFAULT_SETTINGS,
            self.CATEGORIES_PATH: self._DEFAULT_CATEGORIES,
            self.TOOLS_PATH: self._DEFAULT_TOOLS,
        }
        for path, content in default_files.items():
            if not path.exists():
                self._write_json(path, content)
        self._ensure_environment_defaults()

    def load_settings(self) -> dict[str, object]:
        """读取系统设置；缺失的设置文件会先按默认值创建。"""

        self.ensure_config_files()
        raw = self._read_json(self.SETTINGS_PATH)
        self._validate_schema(raw)
        return raw

    def minimize_to_tray_on_close(self) -> bool:
        """返回关闭主窗口时是否最小化到系统托盘，默认启用。"""

        general = self.load_settings().get("general", {})
        if not isinstance(general, dict):
            return True
        value = general.get("minimize_to_tray_on_close", True)
        return value if isinstance(value, bool) else True

    def set_minimize_to_tray_on_close(self, enabled: bool) -> None:
        """保存关闭主窗口时最小化到系统托盘的设置。"""

        settings = self.load_settings()
        general = settings.get("general")
        if not isinstance(general, dict):
            general = {}
            settings["general"] = general
        general["minimize_to_tray_on_close"] = enabled
        self._write_json(self.SETTINGS_PATH, settings)

    def environment_paths(self) -> dict[str, str]:
        """返回环境页展示的路径；无效值回退为项目内的默认路径。"""

        settings = self.load_settings()
        return {
            key: value if isinstance(value := settings.get(key), str) else default
            for key, default in self.default_environment_paths().items()
        }

    def default_environment_paths(self) -> dict[str, str]:
        """返回项目根目录下预置运行时环境的默认绝对路径。"""

        return self._DEFAULT_ENVIRONMENT_PATHS.copy()

    def set_environment_paths(self, *, python_path: str, java8_path: str, java11_path: str) -> None:
        """保存用户在环境页选择的 Python 和 Java 路径。"""

        settings = self.load_settings()
        settings.update(
            {
                "python_path": python_path,
                "java8_path": java8_path,
                "java11_path": java11_path,
            }
        )
        self._write_json(self.SETTINGS_PATH, settings)

    def window_geometry(self) -> tuple[int, int, int, int] | None:
        """返回已保存的窗口宽、高及左上角坐标，无效或缺失时返回 ``None``。"""

        settings = self.load_settings()
        keys = ("width", "height", "x", "y")
        values = tuple(settings.get(key) for key in keys)
        # bool 是 int 的子类，但不应作为窗口坐标或尺寸使用。
        if not all(isinstance(value, int) and not isinstance(value, bool) for value in values):
            return None
        width, height, x, y = values
        if width <= 0 or height <= 0:
            return None
        return width, height, x, y

    def set_window_geometry(self, *, width: int, height: int, x: int, y: int) -> None:
        """保存主窗口的普通状态尺寸与左上角坐标。"""

        settings = self.load_settings()
        settings.update({"width": width, "height": height, "x": x, "y": y})
        self._write_json(self.SETTINGS_PATH, settings)

    def load_category_names(self) -> list[str]:
        """按配置顺序读取左侧菜单中展示的分类名称。"""

        self.ensure_config_files()
        raw = self._read_json(self.CATEGORIES_PATH)
        self._validate_schema(raw)
        categories = raw.get("categories", [])
        if not isinstance(categories, list):
            raise ValueError("分类配置格式无效")

        category_items: list[tuple[int, str]] = []
        for category in categories:
            if not isinstance(category, dict):
                raise ValueError("分类配置格式无效")
            name = category.get("name")
            order = category.get("order", 0)
            if not isinstance(name, str) or not isinstance(order, int):
                raise ValueError("分类配置格式无效")
            category_items.append((order, name))
        return [name for _, name in sorted(category_items)]

    def load_tools(self) -> list[Tool]:
        self.ensure_config_files()
        if not self.path.exists():
            return []
        raw = self._read_json(self.path)
        self._validate_schema(raw)
        return [Tool.from_dict(item) for item in raw.get("tools", [])]

    def save_tools(self, tools: list[Tool]) -> None:
        self._write_json(
            self.path,
            {"schema_version": self.SCHEMA_VERSION, "tools": [tool.to_dict() for tool in tools]},
        )

    def _validate_schema(self, raw: dict[str, object]) -> None:
        if raw.get("schema_version") != self.SCHEMA_VERSION:
            raise ValueError("不支持的配置文件版本")

    def _ensure_environment_defaults(self) -> None:
        """为旧版 settings.json 补充环境路径，保留用户已经保存的值。"""

        settings = self._read_json(self.SETTINGS_PATH)
        self._validate_schema(settings)
        changed = False
        for key, default in self._DEFAULT_ENVIRONMENT_PATHS.items():
            if key not in settings:
                settings[key] = default
                changed = True
        if changed:
            self._write_json(self.SETTINGS_PATH, settings)

    @staticmethod
    def _read_json(path: Path) -> dict[str, object]:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"配置文件格式无效：{path.name}")
        return raw

    @staticmethod
    def _write_json(path: Path, content: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
