"""应用内静态资源的统一路径定义。"""

from __future__ import annotations

from pathlib import Path


IMAGE_ASSETS_DIR = Path(__file__).resolve().parent / "assets" / "images"

# 所有运行时图标均通过这里定位，避免界面模块依赖当前工作目录。
LOGO_PATH = IMAGE_ASSETS_DIR / "logo.png"
CLOSE_ICON_PATH = IMAGE_ASSETS_DIR / "close_normal.png"
MAXIMIZE_ICON_PATH = IMAGE_ASSETS_DIR / "max_normal.png"
MINIMIZE_ICON_PATH = IMAGE_ASSETS_DIR / "min_normal.png"
