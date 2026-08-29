"""应用启动逻辑。"""

from __future__ import annotations

import sys


def main() -> int:
    try:
        from PyQt6.QtGui import QAction, QIcon
        from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon
    except ImportError:
        print("SecForge 需要 PyQt6。请先安装项目声明的依赖后再启动。", file=sys.stderr)
        return 1

    from config_store import ConfigStore
    from main_window import MainWindow
    from resources import LOGO_PATH

    app = QApplication(sys.argv)
    app.setApplicationName("SecForge")
    app.setOrganizationName("SecForge")
    # 主窗口真正关闭时应结束应用；最小化到托盘会在 closeEvent 中忽略关闭事件。
    app.setQuitOnLastWindowClosed(True)
    config_store = ConfigStore()
    config_store.ensure_config_files()
    # 任务栏和系统托盘共用应用资源目录内的品牌图标。
    app_icon = QIcon(str(LOGO_PATH))
    app.setWindowIcon(app_icon)
    tray_available = QSystemTrayIcon.isSystemTrayAvailable()
    window = MainWindow(config_store, system_tray_available=tray_available)
    window.setWindowIcon(app_icon)

    if tray_available:
        tray_icon = QSystemTrayIcon(app_icon, app)
        tray_icon.setToolTip("SecForge · 网安工具箱")
        tray_menu = QMenu()
        show_action = QAction("显示主窗口", tray_menu)
        setting_action = QAction("设置", tray_menu)
        exit_action = QAction("退出程序", tray_menu)
        show_action.triggered.connect(window.showNormal)
        show_action.triggered.connect(window.raise_)
        show_action.triggered.connect(window.activateWindow)
        setting_action.triggered.connect(window.show_settings)
        exit_action.triggered.connect(app.quit)
        tray_menu.addAction(show_action)
        tray_menu.addSeparator()
        tray_menu.addAction(setting_action)
        tray_menu.addSeparator()
        tray_menu.addAction(exit_action)
        tray_icon.setContextMenu(tray_menu)

        def show_from_tray(reason: QSystemTrayIcon.ActivationReason) -> None:
            if reason in {QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick}:
                window.showNormal()
                window.raise_()
                window.activateWindow()

        tray_icon.activated.connect(show_from_tray)
        tray_icon.show()
        app.tray_icon = tray_icon  # type: ignore[attr-defined]
    window.show()
    return app.exec()
