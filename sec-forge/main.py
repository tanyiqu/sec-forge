"""应用启动逻辑。"""

from __future__ import annotations

import sys


def main() -> int:
    try:
        from PyQt6.QtWidgets import QApplication
    except ImportError:
        print("SecForge 需要 PyQt6。请先安装项目声明的依赖后再启动。", file=sys.stderr)
        return 1

    from main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("SecForge")
    app.setOrganizationName("SecForge")
    window = MainWindow()
    window.show()
    return app.exec()
