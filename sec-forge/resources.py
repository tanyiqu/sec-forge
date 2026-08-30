"""应用内静态资源的统一路径定义。"""

from __future__ import annotations

from pathlib import Path


IMAGE_ASSETS_DIR = Path(__file__).resolve().parent / "assets" / "images"

# 所有运行时图标均通过这里定位，避免界面模块依赖当前工作目录。
LOGO_PATH = IMAGE_ASSETS_DIR / "logo.png"
CLOSE_ICON_PATH = IMAGE_ASSETS_DIR / "close_normal.png"
MAXIMIZE_ICON_PATH = IMAGE_ASSETS_DIR / "max_normal.png"
MINIMIZE_ICON_PATH = IMAGE_ASSETS_DIR / "min_normal.png"

# 左侧菜单入口图标。分类菜单共用工具图标，保持菜单视觉一致。
ALL_TOOLS_ICON_PATH = IMAGE_ASSETS_DIR / "all.png"
FAVORITES_ICON_PATH = IMAGE_ASSETS_DIR / "star.png"
RECENT_TOOLS_ICON_PATH = IMAGE_ASSETS_DIR / "recent.png"
TOOLS_MENU_ICON_PATH = IMAGE_ASSETS_DIR / "tools.png"
