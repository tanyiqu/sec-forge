from __future__ import annotations

from pathlib import Path

import sys
from ctypes import c_void_p, wintypes

from PyQt6.QtCore import QPoint, QSize, Qt, QTimer
from PyQt6.QtGui import QCloseEvent, QCursor, QIcon, QMouseEvent, QPixmap
from PyQt6.QtWidgets import QCheckBox, QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QMainWindow, QPushButton, QScrollArea, QTabWidget, QVBoxLayout, QWidget

from config_store import ConfigStore
from resource_monitor import ProcessResourceMonitor
from resources import CLOSE_ICON_PATH, LOGO_PATH, MAXIMIZE_ICON_PATH, MINIMIZE_ICON_PATH


class TitleBar(QFrame):
    """用于移动窗口并承载窗口控制按钮的自定义标题栏。"""

    def __init__(self, window: QWidget, *, title_text: str = "SecForge", subtitle_text: str = "网安工具箱 by Tanyiqu", allow_maximize: bool = True, show_resource_usage: bool = True) -> None:
        super().__init__(window)
        self._window = window
        self._allow_maximize = allow_maximize
        self._drag_offset: QPoint | None = None
        self.setObjectName("titleBar")
        self.setFixedHeight(52)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 10, 0)
        layout.setSpacing(8)
        logo = QLabel()
        logo.setObjectName("titleLogo")
        logo.setFixedSize(24, 24)
        logo.setPixmap(QPixmap(str(LOGO_PATH)).scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        logo.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        title = QLabel(title_text)
        title.setObjectName("windowTitle")
        title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        subtitle = QLabel(subtitle_text)
        subtitle.setObjectName("windowSubtitle")
        subtitle.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(logo)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        self._resource_usage_label: QLabel | None = None
        self._resource_monitor: ProcessResourceMonitor | None = None
        self._resource_timer: QTimer | None = None
        if show_resource_usage:
            self._resource_usage_label = QLabel()
            self._resource_usage_label.setObjectName("resourceUsage")
            self._resource_usage_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._resource_usage_label.setMinimumWidth(205)
            self._resource_usage_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            layout.addWidget(self._resource_usage_label)
            self._resource_monitor = ProcessResourceMonitor()
            self._update_resource_usage()
            self._resource_timer = QTimer(self)
            self._resource_timer.setInterval(5_000)
            self._resource_timer.timeout.connect(self._update_resource_usage)
            self._resource_timer.start()
        layout.addStretch()
        self._minimize_button = self._make_button(MINIMIZE_ICON_PATH, "最小化")
        self._maximize_button: QPushButton | None = None
        self._close_button = self._make_button(CLOSE_ICON_PATH, "关闭", "closeButton")
        self._minimize_button.clicked.connect(window.showMinimized)
        self._close_button.clicked.connect(window.close)
        layout.addWidget(self._minimize_button)
        if allow_maximize:
            self._maximize_button = self._make_button(MAXIMIZE_ICON_PATH, "最大化")
            self._maximize_button.clicked.connect(self._toggle_maximized)
            layout.addWidget(self._maximize_button)
        layout.addWidget(self._close_button)

    def _update_resource_usage(self) -> None:
        """将当前进程的实时资源占用更新到标题栏，每五秒执行一次。"""

        if self._resource_usage_label is None or self._resource_monitor is None:
            return
        usage = self._resource_monitor.sample()
        memory_mb = usage.memory_bytes / (1024 * 1024)
        self._resource_usage_label.setText(
            f"CPU {usage.cpu_percent:.1f}% | 内存 {memory_mb:.0f}MB({usage.memory_percent:.1f}%)"
        )

    def _make_button(self, icon_path: Path, tooltip: str, name: str = "windowButton") -> QPushButton:
        """创建使用应用素材的标题栏控制按钮。"""

        button = QPushButton()
        button.setObjectName(name)
        button.setToolTip(tooltip)
        button.setFixedSize(34, 30)
        button.setIcon(QIcon(str(icon_path)))
        button.setIconSize(QSize(16, 16))
        return button

    def _toggle_maximized(self) -> None:
        if self._window.isMaximized():
            self._window.showNormal()
            if self._maximize_button is not None:
                self._maximize_button.setToolTip("最大化")
        else:
            self._window.showMaximized()
            if self._maximize_button is not None:
                self._maximize_button.setToolTip("还原")

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and not self._window.isMaximized():
            self._drag_offset = event.globalPosition().toPoint() - self._window.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self._window.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_offset = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if self._allow_maximize and event.button() == Qt.MouseButton.LeftButton:
            self._toggle_maximized()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class SettingsDialog(QDialog):
    """使用应用主题的模态系统设置窗口。"""

    def __init__(self, config_store: ConfigStore, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._config_store = config_store
        self.setWindowTitle("系统设置")
        self.setModal(True)
        self.setFixedSize(400, 525)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._build_ui()

    def _build_ui(self) -> None:
        surface = QFrame()
        surface.setObjectName("settingsSurface")
        surface_layout = QVBoxLayout(surface)
        surface_layout.setContentsMargins(0, 0, 0, 0)
        surface_layout.setSpacing(0)
        surface_layout.addWidget(TitleBar(self, title_text="系统设置", subtitle_text="", allow_maximize=False, show_resource_usage=False))

        body = QVBoxLayout()
        body.setContentsMargins(24, 20, 24, 20)
        body.setSpacing(18)
        tabs = QTabWidget()
        tabs.setObjectName("settingsTabs")
        general_page = QWidget()
        general_layout = QVBoxLayout(general_page)
        general_layout.setContentsMargins(22, 22, 22, 22)
        general_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._minimize_to_tray_checkbox = QCheckBox("关闭窗口时最小化到系统托盘")
        self._minimize_to_tray_checkbox.setChecked(self._config_store.minimize_to_tray_on_close())
        general_layout.addWidget(self._minimize_to_tray_checkbox)
        tabs.addTab(general_page, "常规")
        tabs.addTab(QWidget(), "环境")
        tabs.addTab(QWidget(), "关于")
        body.addWidget(tabs, 1)

        action_row = QHBoxLayout()
        action_row.setSpacing(10)
        reset_button = QPushButton("重置设置")
        reset_button.setObjectName("secondaryButton")
        reset_button.setToolTip("当前没有可重置的设置项")
        reset_button.clicked.connect(self._reset_settings)
        action_row.addWidget(reset_button)
        action_row.addStretch()
        save_button = QPushButton("保存")
        save_button.clicked.connect(self._save_settings)
        cancel_button = QPushButton("取消")
        cancel_button.setObjectName("secondaryButton")
        cancel_button.clicked.connect(self.reject)
        action_row.addWidget(save_button)
        action_row.addWidget(cancel_button)
        body.addLayout(action_row)

        body_widget = QWidget()
        body_widget.setLayout(body)
        surface_layout.addWidget(body_widget, 1)
        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(0, 0, 0, 0)
        dialog_layout.addWidget(surface)
        self.setStyleSheet("""
            #settingsSurface { background: #f5f7fb; border: 1px solid #dce2ec; border-radius: 14px; }
            #titleBar { background: #ffffff; border: none; border-top-left-radius: 14px; border-top-right-radius: 14px; border-bottom: 1px solid #e6ebf2; }
            #windowTitle { color: #182033; font-size: 16px; font-weight: 700; }
            #windowSubtitle { color: #718096; font-size: 12px; }
            #titleLogo { background: transparent; }
            #resourceUsage { color: #243047; font-size: 12px; font-weight: 600; border: none; padding: 0; background: transparent; }
            #windowButton, #closeButton { border: none; border-radius: 6px; background: transparent; color: #45536a; font-size: 18px; }
            #windowButton:hover { background: #eaf0f8; } #closeButton:hover { background: #e95353; color: white; }
            #settingsTabs::pane { background: #ffffff; border: 1px solid #d9e0ea; border-radius: 10px; top: -1px; }
            #settingsTabs::tab-bar { alignment: left; }
            #settingsTabs::tab { min-width: 74px; padding: 10px 18px; color: #6b7789; background: transparent; border: none; border-bottom: 2px solid transparent; font-weight: 600; }
            #settingsTabs::tab:hover { color: #1677e8; background: #f4f8fe; }
            #settingsTabs::tab:selected { color: #1677e8; border-bottom-color: #1677e8; }
            QCheckBox { color: #243047; font-size: 14px; spacing: 8px; }
            QCheckBox::indicator { width: 17px; height: 17px; border: 1px solid #b9c5d5; border-radius: 4px; background: #ffffff; }
            QCheckBox::indicator:checked { background: #1677e8; border-color: #1677e8; }
            QPushButton { min-height: 36px; padding: 0 15px; background: #1677e8; border: none; border-radius: 8px; color: white; font-weight: 600; }
            QPushButton:hover { background: #3689ec; }
            #secondaryButton { color: #45536a; background: #ffffff; border: 1px solid #d9e0ea; }
            #secondaryButton:hover { color: #1677e8; border-color: #9cc5f5; background: #f4f8fe; }
        """)

    def _reset_settings(self) -> None:
        """将页面中的设置项恢复为默认值，等待用户确认保存。"""

        self._minimize_to_tray_checkbox.setChecked(True)

    def _save_settings(self) -> None:
        """保存当前设置并关闭对话框。"""

        self._config_store.set_minimize_to_tray_on_close(self._minimize_to_tray_checkbox.isChecked())
        self.accept()


class MainWindow(QMainWindow):
    """SecForge 主窗口，包含固定导航栏和可缩放的工作区。"""

    _SIDEBAR_WIDTH = 220
    _RESIZE_BORDER_WIDTH = 8

    def __init__(self, config_store: ConfigStore | None = None, *, system_tray_available: bool = False) -> None:
        super().__init__()
        self._config_store = config_store or ConfigStore()
        self._config_store.ensure_config_files()
        self._system_tray_available = system_tray_available
        self.setWindowTitle("SecForge · 网安工具箱")
        self.setMinimumSize(950, 600)
        self.resize(1180, 740)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._build_ui()

    def nativeEvent(self, event_type: bytes, message: c_void_p) -> tuple[bool, int]:
        """让 Windows 无边框窗口保留系统原生的边缘与角落缩放体验。"""

        if sys.platform != "win32" or event_type != b"windows_generic_MSG":
            return False, 0

        WM_NCHITTEST = 0x0084
        HTCLIENT = 1
        HTLEFT, HTRIGHT, HTTOP, HTBOTTOM = 10, 11, 12, 15
        HTTOPLEFT, HTTOPRIGHT, HTBOTTOMLEFT, HTBOTTOMRIGHT = 13, 14, 16, 17
        # wintypes.MSG 与当前 Python/Windows 架构的指针宽度保持一致；
        # 不手工声明结构，避免 64 位环境中消息内存布局不匹配。
        native_message = wintypes.MSG.from_address(int(message))
        if native_message.message != WM_NCHITTEST or self.isMaximized():
            return False, 0

        frame = self.frameGeometry()
        cursor = QCursor.pos()
        border = self._RESIZE_BORDER_WIDTH
        on_left = cursor.x() <= frame.left() + border
        on_right = cursor.x() >= frame.right() - border
        on_top = cursor.y() <= frame.top() + border
        on_bottom = cursor.y() >= frame.bottom() - border
        if on_top and on_left:
            return True, HTTOPLEFT
        if on_top and on_right:
            return True, HTTOPRIGHT
        if on_bottom and on_left:
            return True, HTBOTTOMLEFT
        if on_bottom and on_right:
            return True, HTBOTTOMRIGHT
        if on_left:
            return True, HTLEFT
        if on_right:
            return True, HTRIGHT
        if on_top:
            return True, HTTOP
        if on_bottom:
            return True, HTBOTTOM
        return True, HTCLIENT

    def _build_ui(self) -> None:
        # 透明顶层窗口内放置圆角表面，使四角不露出系统标题栏背景。
        surface = QFrame()
        surface.setObjectName("windowSurface")
        surface_layout = QVBoxLayout(surface)
        surface_layout.setContentsMargins(0, 0, 0, 0)
        surface_layout.setSpacing(0)
        surface_layout.addWidget(TitleBar(self))
        root = QWidget()
        layout = QHBoxLayout(root)
        # 导航栏紧贴左、上、下边缘；右侧工作区随窗口剩余空间伸缩。
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        # QListWidget 的视口不会跟随父控件的圆角裁剪。使用单独的圆角容器
        # 承载透明列表，避免左下角覆盖 windowSurface 的圆角。
        sidebar_panel = QFrame()
        sidebar_panel.setObjectName("sidebarPanel")
        sidebar_panel.setFixedWidth(self._SIDEBAR_WIDTH)
        sidebar_layout = QVBoxLayout(sidebar_panel)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        sidebar = QListWidget()
        sidebar.setObjectName("sidebar")
        sidebar.viewport().setAutoFillBackground(False)
        # 分类菜单由 config/categories.json 决定，后续编辑分类时可直接复用此数据源。
        category_items = [f"▣  {name} (0)" for name in self._config_store.load_category_names()]
        sidebar.addItems(["▦  全部工具 (0)", "★  我的收藏", "◷  最近使用", "────────────", *category_items])
        sidebar.setCurrentRow(0)
        sidebar_layout.addWidget(sidebar)
        layout.addWidget(sidebar_panel)

        divider = QFrame()
        divider.setObjectName("sidebarDivider")
        divider.setFrameShape(QFrame.Shape.VLine)
        # 保持左右区域清晰分隔，同时避免分隔线额外占用工作区宽度。
        divider.setFixedWidth(1)
        layout.addWidget(divider)

        content = QVBoxLayout()
        content.setContentsMargins(24, 20, 24, 22)
        content.setSpacing(14)
        search = QLineEdit()
        search.setPlaceholderText("搜索名称 / 标签 / 描述")
        action_row = QHBoxLayout()
        action_row.addWidget(search, 1)
        add_button = QPushButton("+ 添加工具")
        add_button.setEnabled(False)
        add_button.setToolTip("工具管理功能即将提供")
        action_row.addWidget(add_button)
        settings_button = QPushButton("设置")
        settings_button.setObjectName("secondaryButton")
        settings_button.clicked.connect(self.show_settings)
        action_row.addWidget(settings_button)
        content.addLayout(action_row)
        empty = QFrame()
        empty_layout = QVBoxLayout(empty)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel("还没有添加工具")
        title.setObjectName("emptyTitle")
        hint = QLabel("通过“添加工具”建立你的本地工具库。\nSecForge 仅用于合法、已授权的安全测试与研究。")
        hint.setObjectName("emptyHint")
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(hint, alignment=Qt.AlignmentFlag.AlignCenter)
        scroll = QScrollArea()
        scroll.setObjectName("contentArea")
        scroll.setWidgetResizable(True)
        scroll.setWidget(empty)
        content.addWidget(scroll)
        layout.addLayout(content, 1)
        surface_layout.addWidget(root, 1)
        self.setCentralWidget(surface)
        self.setStyleSheet("""
            #windowSurface { background: #f5f7fb; border: 1px solid #dce2ec; border-radius: 14px; }
            #titleBar { background: #ffffff; border: none; border-top-left-radius: 14px; border-top-right-radius: 14px; border-bottom: 1px solid #e6ebf2; }
            #windowTitle { color: #182033; font-size: 16px; font-weight: 700; }
            #windowSubtitle { color: #718096; font-size: 12px; }
            #titleLogo { background: transparent; }
            #resourceUsage { color: #243047; font-size: 12px; font-weight: 600; border: none; padding: 0; background: transparent; }
            #windowButton, #closeButton { border: none; border-radius: 6px; background: transparent; color: #45536a; font-size: 18px; }
            #windowButton:hover { background: #eaf0f8; } #closeButton:hover { background: #e95353; color: white; }
            #sidebarPanel { background: #ffffff; border: none; border-bottom-left-radius: 13px; }
            #sidebar, #sidebar::viewport { background: transparent; border: none; border-radius: 0; }
            #sidebar { padding: 8px; outline: 0; color: #364153; font-size: 13px; }
            #sidebar::item { height: 34px; border-radius: 6px; padding-left: 8px; } #sidebar::item:selected { background: #e8f1ff; color: #1677e8; font-weight: 600; } #sidebar::item:hover { background: #f3f6fa; }
            #sidebarDivider { background: #cbd5e1; border: none; }
            QLineEdit { min-height: 36px; background: #ffffff; border: 1px solid #d9e0ea; border-radius: 8px; padding: 0 12px; color: #243047; } QLineEdit:focus { border-color: #1677e8; }
            QPushButton { min-height: 36px; padding: 0 15px; background: #1677e8; border: none; border-radius: 8px; color: white; font-weight: 600; } QPushButton:hover { background: #3689ec; } QPushButton:disabled { background: #9fc8f5; color: #f7fbff; }
            #secondaryButton { color: #45536a; background: #ffffff; border: 1px solid #d9e0ea; } #secondaryButton:hover { color: #1677e8; border-color: #9cc5f5; background: #f4f8fe; }
            #contentArea { border: none; background: transparent; } #contentArea > QWidget > QWidget { background: transparent; }
            #emptyState { background: #ffffff; border: 1px dashed #d5deea; border-radius: 12px; } #emptyTitle { color: #243047; font-size: 20px; font-weight: 700; } #emptyHint { color: #7c8798; font-size: 13px; }
        """)

    def show_settings(self) -> None:
        """显示独立的模态系统设置窗口。"""

        if self.isMinimized():
            self.showNormal()
        self.raise_()
        self.activateWindow()
        SettingsDialog(self._config_store, self).exec()

    def closeEvent(self, event: QCloseEvent) -> None:
        """按已保存的常规设置决定关闭主窗口时的行为。"""

        if self._system_tray_available and self._config_store.minimize_to_tray_on_close():
            self.hide()
            event.ignore()
            return
        event.accept()
