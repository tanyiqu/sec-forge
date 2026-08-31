"""程序目录下 JSON 配置文件的创建与读写。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tool import LaunchType, Tool, ToolProfile


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
    # 分类使用字符串数组保存，数组顺序即左侧菜单的展示顺序。
    _DEFAULT_CATEGORIES = {
        "categories": [
            "信息收集工具",
            "框架漏洞利用工具",
            "漏洞扫描与利用工具",
            "抓包与代理工具",
            "后渗透工具",
            "爆破工具",
        ],
    }
    # tools.json 是用户直接维护的工具清单，使用扁平数组格式，方便导入、导出和查看。
    _DEFAULT_TOOLS: list[dict[str, object]] = []

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
        self._migrate_legacy_categories()
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
        """按配置数组顺序读取左侧菜单中展示的分类名称。

        当前 ``categories.json`` 使用 ``{"categories": ["分类名称", ...]}``
        格式。为避免旧版本地配置失效，也支持读取原有的分类对象数组。
        """

        self.ensure_config_files()
        raw = self._read_json(self.CATEGORIES_PATH)
        return self._category_names_from_raw(raw)

    def load_tool_configurations(self) -> list[dict[str, object]]:
        """读取 ``tools.json`` 中面向用户的工具配置记录。

        新格式为记录数组；同时兼容项目骨架阶段可能生成的
        ``{\"schema_version\": 1, \"tools\": [...]}`` 格式，避免已有配置失效。
        """

        self.ensure_config_files()
        if not self.path.exists():
            return []

        text = self.path.read_text(encoding="utf-8").strip()
        if not text:
            return []
        raw: Any = json.loads(text)
        if isinstance(raw, dict):
            self._validate_schema(raw)
            raw = raw.get("tools", [])
        if not isinstance(raw, list):
            raise ValueError("工具配置格式无效")

        records: list[dict[str, object]] = []
        needs_star_migration = False
        for item in raw:
            if not isinstance(item, dict):
                raise ValueError("工具配置格式无效")
            profile = item.get("profile", {})
            profile = profile if isinstance(profile, dict) else {}
            star = item.get("star", False)
            if not isinstance(star, bool):
                star = False
                needs_star_migration = True
            if "star" not in item:
                needs_star_migration = True
            records.append({
                "name": str(item.get("name", "")),
                "category": str(item.get("category", item.get("category_id", ""))),
                "type": str(item.get("type", item.get("launch_type", "GUI应用"))),
                "description": str(item.get("description", "")),
                "path": str(item.get("path", profile.get("target", ""))),
                "params": str(item.get("params", profile.get("arguments", ""))),
                "url": str(item.get("url", "")),
                # 旧配置没有 weight 时保持默认优先级；非法值也安全回退为 0。
                "weight": self._normalize_weight(item.get("weight", 0)),
                # 收藏状态以 bool 保存；旧记录在首次读取时自动补齐为 false。
                "star": star,
            })
        if needs_star_migration:
            self.save_tool_configurations(records)
        return records

    def add_tool_configuration(self, configuration: dict[str, object]) -> None:
        """将一条已校验的工具配置追加写入 ``tools.json``。"""

        records = self.load_tool_configurations()
        records.append(configuration)
        self.save_tool_configurations(records)

    def save_tool_configurations(self, configurations: list[dict[str, object]]) -> None:
        """使用稳定的字段顺序保存用户可读的工具配置数组。"""

        fields = ("name", "category", "type", "description", "path", "params", "url")
        normalized = [
            {
                **{field: str(item.get(field, "")) for field in fields},
                # JSON 中保持数值类型，方便用户直接编辑和按权重理解排序。
                "weight": self._normalize_weight(item.get("weight", 0)),
                "star": item.get("star", False) if isinstance(item.get("star", False), bool) else False,
            }
            for item in configurations
        ]
        self._write_json_value(self.path, normalized)

    def set_tool_configuration_star(self, configuration: dict[str, object], starred: bool) -> None:
        """更新一条工具配置的收藏状态并立即保存到 ``tools.json``。

        工具清单当前没有独立 ID，故以完整规范化配置定位记录；完全重复的
        配置在界面上没有可区分信息，更新其中第一条即可保持行为确定。
        """

        records = self.load_tool_configurations()
        for record in records:
            if record == configuration:
                record["star"] = starred
                self.save_tool_configurations(records)
                return
        raise ValueError("未找到要更新收藏状态的工具配置")

    def update_tool_configuration(
        self, original: dict[str, object], updated: dict[str, object]
    ) -> None:
        """用 ``updated`` 替换一条已有工具配置并立即保存。

        工具清单暂未使用独立 ID，因此沿用收藏功能的完整配置匹配规则：
        当存在完全重复的记录时，始终更新列表中的第一条记录。
        """

        records = self.load_tool_configurations()
        for index, record in enumerate(records):
            if record == original:
                records[index] = updated
                self.save_tool_configurations(records)
                return
        raise ValueError("未找到要编辑的工具配置")

    def delete_tool_configuration(self, configuration: dict[str, object]) -> None:
        """删除一条已有工具配置并立即同步到 ``tools.json``。

        完全重复的记录按列表顺序只删除第一条，以保持操作结果可预测。
        """

        records = self.load_tool_configurations()
        for index, record in enumerate(records):
            if record == configuration:
                del records[index]
                self.save_tool_configurations(records)
                return
        raise ValueError("未找到要删除的工具配置")

    def load_tools(self) -> list[Tool]:
        """将用户配置转换为既有领域模型，保持旧调用方兼容。"""

        launch_types = {
            "Python": LaunchType.PYTHON,
            "Java8": LaunchType.JAVA_8,
            "Java11": LaunchType.JAVA_11,
            "GUI应用": LaunchType.GUI,
            "命令行": LaunchType.CLI,
            "批处理": LaunchType.BATCH,
            "Powershell": LaunchType.POWERSHELL,
            "网页": LaunchType.WEB,
        }
        return [
            Tool(
                name=item["name"],
                category_id=item["category"],
                launch_type=launch_types.get(item["type"], LaunchType.GUI),
                profile=ToolProfile(target=item["url"] or item["path"], arguments=item["params"]),
                description=item["description"],
                weight=self._normalize_weight(item["weight"]),
            )
            for item in self.load_tool_configurations()
        ]

    def save_tools(self, tools: list[Tool]) -> None:
        type_names = {
            LaunchType.PYTHON: "Python",
            LaunchType.JAVA_8: "Java8",
            LaunchType.JAVA_11: "Java11",
            LaunchType.GUI: "GUI应用",
            LaunchType.CLI: "命令行",
            LaunchType.BATCH: "批处理",
            LaunchType.POWERSHELL: "Powershell",
            LaunchType.WEB: "网页",
        }
        self.save_tool_configurations([
            {
                "name": tool.name,
                "category": tool.category_id,
                "type": type_names[tool.launch_type],
                "description": tool.description,
                "path": "" if tool.launch_type is LaunchType.WEB else tool.profile.target,
                "params": tool.profile.arguments,
                "url": tool.profile.target if tool.launch_type is LaunchType.WEB else "",
                "weight": self._normalize_weight(tool.weight),
                "star": tool.favorite,
            }
            for tool in tools
        ])

    @staticmethod
    def _normalize_weight(value: object) -> int:
        """返回 ``tools.json`` 支持的整数权重；无效值回退为默认值 0。"""

        # bool 是 int 的子类，不能作为用户可见的权重配置。
        if isinstance(value, bool):
            return 0
        try:
            weight = int(value)
        except (TypeError, ValueError):
            return 0
        return weight if 0 <= weight <= 10 else 0

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

    def _migrate_legacy_categories(self) -> None:
        """将旧版分类对象数组迁移为按名称排列的字符串数组。"""

        raw = self._read_json(self.CATEGORIES_PATH)
        categories = raw.get("categories")
        if not isinstance(categories, list) or not categories:
            return
        if all(isinstance(category, str) for category in categories):
            return

        self._write_json(
            self.CATEGORIES_PATH,
            {"categories": self._category_names_from_raw(raw)},
        )

    @staticmethod
    def _category_names_from_raw(raw: dict[str, object]) -> list[str]:
        """解析新旧两种分类格式，并保留对应的展示顺序。"""

        categories = raw.get("categories", [])
        if not isinstance(categories, list):
            raise ValueError("分类配置格式无效")
        if all(isinstance(category, str) for category in categories):
            return categories.copy()

        # 兼容旧版 ``name`` / ``order`` 对象数组；相同 order 时维持文件顺序。
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

    @staticmethod
    def _read_json(path: Path) -> dict[str, object]:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"配置文件格式无效：{path.name}")
        return raw

    @staticmethod
    def _write_json(path: Path, content: dict[str, object]) -> None:
        ConfigStore._write_json_value(path, content)

    @staticmethod
    def _write_json_value(path: Path, content: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
