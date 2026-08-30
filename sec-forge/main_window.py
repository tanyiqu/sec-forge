from __future__ import annotations

from pathlib import Path
from typing import Callable

import sys
from ctypes import c_void_p, wintypes

from PyQt6.QtCore import QPoint, QRect, QSize, Qt, QTimer
from PyQt6.QtGui import QCloseEvent, QCursor, QIcon, QMouseEvent, QPixmap
from PyQt6.QtWidgets import QApplication, QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPushButton, QScrollArea, QTabWidget, QToolButton, QVBoxLayout, QWidget

from config_store import ConfigStore
from resource_monitor import ProcessResourceMonitor
from resources import (
    ALL_TOOLS_ICON_PATH,
    CLOSE_ICON_PATH,
    FAVORITES_ICON_PATH,
    LOGO_PATH,
    MAXIMIZE_ICON_PATH,
    MINIMIZE_ICON_PATH,
    RECENT_TOOLS_ICON_PATH,
    TOOL_STARRED_ICON_PATH,
    TOOL_STATUS_ERROR_ICON_PATH,
    TOOL_STATUS_OK_ICON_PATH,
    TOOL_UNSTARRED_ICON_PATH,
    TOOLS_MENU_ICON_PATH,
)


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
        environment_page = QWidget()
        environment_layout = QVBoxLayout(environment_page)
        environment_layout.setContentsMargins(22, 22, 22, 22)
        environment_layout.setSpacing(10)
        environment_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        environment_paths = self._config_store.environment_paths()
        self._python_path_input = self._add_environment_path_setting(
            environment_layout, "自定义Python路径", environment_paths["python_path"], select_directory=False
        )
        self._java8_path_input = self._add_environment_path_setting(
            environment_layout, "Java 8路径", environment_paths["java8_path"], select_directory=True
        )
        self._java11_path_input = self._add_environment_path_setting(
            environment_layout, "Java 11路径", environment_paths["java11_path"], select_directory=True
        )
        tabs.addTab(environment_page, "环境")
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
            #environmentLabel { color: #243047; font-size: 14px; font-weight: 600; }
            QPushButton { min-height: 36px; padding: 0 15px; background: #1677e8; border: none; border-radius: 8px; color: white; font-weight: 600; }
            QPushButton:hover { background: #3689ec; }
            #secondaryButton { color: #45536a; background: #ffffff; border: 1px solid #d9e0ea; }
            #secondaryButton:hover { color: #1677e8; border-color: #9cc5f5; background: #f4f8fe; }
        """)

    def _add_environment_path_setting(
        self, layout: QVBoxLayout, label_text: str, path: str, *, select_directory: bool
    ) -> QLineEdit:
        """在环境页添加标签单行、输入框与浏览按钮单行的路径设置。"""

        label = QLabel(label_text)
        label.setObjectName("environmentLabel")
        layout.addWidget(label)
        row = QHBoxLayout()
        row.setSpacing(10)
        path_input = QLineEdit(path)
        path_input.setPlaceholderText("请选择路径")
        browse_button = QPushButton("浏览")
        browse_button.setObjectName("secondaryButton")
        browse_button.clicked.connect(
            lambda: self._browse_environment_path(path_input, label_text, select_directory)
        )
        row.addWidget(path_input, 1)
        row.addWidget(browse_button)
        layout.addLayout(row)
        return path_input

    def _browse_environment_path(
        self, path_input: QLineEdit, label_text: str, select_directory: bool
    ) -> None:
        """按设置项选择文件或文件夹，并把绝对路径显示到对应输入框。"""

        if select_directory:
            selected_path = QFileDialog.getExistingDirectory(self, f"选择{label_text}", path_input.text())
        else:
            selected_path, _ = QFileDialog.getOpenFileName(
                self, f"选择{label_text}", path_input.text(), "所有文件 (*)"
            )
        if selected_path:
            path_input.setText(str(Path(selected_path).resolve()))

    def _reset_settings(self) -> None:
        """将页面中的设置项恢复为默认值，等待用户确认保存。"""

        self._minimize_to_tray_checkbox.setChecked(True)
        environment_paths = self._config_store.default_environment_paths()
        self._python_path_input.setText(environment_paths["python_path"])
        self._java8_path_input.setText(environment_paths["java8_path"])
        self._java11_path_input.setText(environment_paths["java11_path"])

    def _save_settings(self) -> None:
        """保存当前设置并关闭对话框。"""

        self._config_store.set_minimize_to_tray_on_close(self._minimize_to_tray_checkbox.isChecked())
        self._config_store.set_environment_paths(
            python_path=self._python_path_input.text(),
            java8_path=self._java8_path_input.text(),
            java11_path=self._java11_path_input.text(),
        )
        self.accept()


class AddToolDialog(QDialog):
    """收集并校验本地工具启动信息的模态窗口。"""

    _TOOL_TYPES = ("Python", "Java8", "Java11", "GUI应用", "命令行", "批处理", "Powershell", "网页")

    def __init__(self, config_store: ConfigStore, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._config_store = config_store
        self.setWindowTitle("添加工具")
        self.setModal(True)
        self.setFixedWidth(510)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)
        title = QLabel("添加工具")
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(13)
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("例如：DirSearch目录探测工具")
        self._description_input = QLineEdit()
        self._description_input.setPlaceholderText("简要说明工具用途")
        self._type_selector = QComboBox()
        self._type_selector.addItems(self._TOOL_TYPES)
        self._path_input = QLineEdit()
        self._path_input.setPlaceholderText("选择本地工具文件")
        browse_button = QPushButton("浏览")
        browse_button.setObjectName("secondaryButton")
        browse_button.clicked.connect(self._browse_path)
        path_row = QHBoxLayout()
        path_row.setContentsMargins(0, 0, 0, 0)
        path_row.addWidget(self._path_input, 1)
        path_row.addWidget(browse_button)
        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("网页工具的 URL（可选）")
        self._category_selector = QComboBox()
        self._category_selector.addItems(self._config_store.load_category_names())
        self._params_input = QLineEdit()
        self._params_input.setPlaceholderText("可选，例如：-h")
        self._weight_selector = QComboBox()
        self._weight_selector.addItems([str(weight) for weight in range(11)])
        self._weight_selector.setCurrentText("0")
        form.addRow("工具名称：", self._name_input)
        form.addRow("工具描述：", self._description_input)
        form.addRow("工具类型：", self._type_selector)
        form.addRow("工具路径：", path_row)
        form.addRow("网页：", self._url_input)
        form.addRow("工具分类：", self._category_selector)
        form.addRow("启动参数：", self._params_input)
        form.addRow("权重：", self._weight_selector)
        layout.addLayout(form)
        layout.addStretch()

        actions = QHBoxLayout()
        actions.addStretch()
        cancel_button = QPushButton("取消")
        cancel_button.setObjectName("secondaryButton")
        cancel_button.clicked.connect(self.reject)
        save_button = QPushButton("保存")
        save_button.clicked.connect(self._save_tool)
        actions.addWidget(cancel_button)
        actions.addWidget(save_button)
        layout.addLayout(actions)
        self.setStyleSheet("""
            QDialog { background: #f5f7fb; color: #243047; }
            #dialogTitle { color: #182033; font-size: 19px; font-weight: 700; }
            QLabel { font-size: 14px; font-weight: 600; }
            QLineEdit, QComboBox { min-height: 36px; background: #ffffff; border: 1px solid #d9e0ea; border-radius: 8px; padding: 0 10px; color: #243047; }
            QLineEdit:focus, QComboBox:focus { border-color: #1677e8; }
            QComboBox { padding-right: 32px; }
            QComboBox:hover { border-color: #9cc5f5; background: #f9fbff; }
            QComboBox::drop-down { width: 30px; border: none; border-left: 1px solid #e4eaf2; border-top-right-radius: 8px; border-bottom-right-radius: 8px; background: #f7f9fc; }
            QComboBox::down-arrow { width: 7px; height: 7px; border-right: 2px solid #64748b; border-bottom: 2px solid #64748b; margin: 0 10px 4px 0; }
            QComboBox QAbstractItemView { background: #ffffff; border: 1px solid #cdd8e7; border-radius: 8px; padding: 5px; outline: none; color: #243047; selection-background-color: #e8f1ff; selection-color: #1677e8; }
            QComboBox QAbstractItemView::item { min-height: 32px; padding: 0 10px; border-radius: 5px; }
            QComboBox QAbstractItemView::item:hover { background: #f3f7fd; color: #1677e8; }
            QPushButton { min-height: 36px; padding: 0 15px; background: #1677e8; border: none; border-radius: 8px; color: white; font-weight: 600; }
            QPushButton:hover { background: #3689ec; }
            #secondaryButton { color: #45536a; background: #ffffff; border: 1px solid #d9e0ea; }
            #secondaryButton:hover { color: #1677e8; border-color: #9cc5f5; background: #f4f8fe; }
        """)
        # 样式中的控件最小高度会影响布局，需在应用 QSS 后计算最终高度。
        # 新增字段时会随布局自动增高，不会在对话框右侧产生滚动条。
        self.adjustSize()
        self.setFixedHeight(self.sizeHint().height())

    def _browse_path(self) -> None:
        """用不限文件类型的选择器填充工具路径。"""

        path, _ = QFileDialog.getOpenFileName(self, "选择工具文件", self._path_input.text(), "所有文件 (*)")
        if path:
            self._path_input.setText(path)

    def _save_tool(self) -> None:
        """校验输入后，以用户约定的字段写入 tools.json。"""

        name = self._name_input.text().strip()
        path = self._path_input.text().strip()
        url = self._url_input.text().strip()
        category = self._category_selector.currentText()
        tool_type = self._type_selector.currentText()
        is_web_tool = tool_type == "网页"
        if not name or not category or (not url if is_web_tool else not path):
            target_name = "网页 URL" if is_web_tool else "工具路径"
            QMessageBox.warning(self, "信息不完整", f"请填写工具名称、{target_name}和工具分类。")
            return
        self._config_store.add_tool_configuration({
            "name": name,
            "category": category,
            "type": tool_type,
            "description": self._description_input.text().strip(),
            "path": "" if is_web_tool else path,
            "params": self._params_input.text().strip(),
            "url": url if is_web_tool else "",
            "weight": int(self._weight_selector.currentText()),
        })
        self.accept()


class ToolCard(QFrame):
    """以固定尺寸显示工具信息的卡片；样式由对象名对应的 QSS 统一控制。"""

    WIDTH = 200
    HEIGHT = 140

    def __init__(
        self,
        configuration: dict[str, object],
        on_star_changed: Callable[[dict[str, object], bool], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("toolCard")
        self.setFixedSize(self.WIDTH, self.HEIGHT)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        title_row = QHBoxLayout()
        title_row.setSpacing(6)
        path_exists = bool(str(configuration["path"])) and Path(str(configuration["path"])).exists()
        status = QLabel()
        status.setObjectName("toolCardStatus")
        status.setPixmap(QPixmap(str(TOOL_STATUS_OK_ICON_PATH if path_exists else TOOL_STATUS_ERROR_ICON_PATH)).scaled(
            16, 16, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        ))
        status.setToolTip("工具文件存在" if path_exists else "工具文件不存在或未配置")
        title_row.addWidget(status)

        title = QLabel(str(configuration["name"]))
        title.setObjectName("toolCardTitle")
        title.setToolTip(str(configuration["name"]))
        title.setWordWrap(False)
        title.setTextFormat(Qt.TextFormat.PlainText)
        title_row.addWidget(title, 1)

        star_button = QToolButton()
        star_button.setObjectName("toolCardStar")
        starred = bool(configuration["star"])
        star_button.setIcon(QIcon(str(TOOL_STARRED_ICON_PATH if starred else TOOL_UNSTARRED_ICON_PATH)))
        star_button.setIconSize(QSize(18, 18))
        star_button.setToolTip("取消收藏" if starred else "收藏工具")
        star_button.clicked.connect(lambda: on_star_changed(configuration, not starred))
        title_row.addWidget(star_button)
        layout.addLayout(title_row)

        description = QLabel(str(configuration["description"]))
        description.setObjectName("toolCardDescription")
        description.setWordWrap(True)
        description.setTextFormat(Qt.TextFormat.PlainText)
        description.setToolTip(str(configuration["description"]))
        layout.addWidget(description, 1)

        footer = QHBoxLayout()
        footer.setSpacing(6)
        tool_type = QLabel(str(configuration["type"]))
        tool_type.setObjectName("toolCardType")
        category = QLabel(str(configuration["category"]))
        category.setObjectName("toolCardCategory")
        category.setToolTip(str(configuration["category"]))
        footer.addWidget(tool_type)
        footer.addWidget(category, 1)
        run_button = QPushButton("运行")
        run_button.setObjectName("toolCardRun")
        run_button.setToolTip("运行功能尚未实现")
        footer.addWidget(run_button)
        layout.addLayout(footer)


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
        self._restore_window_geometry()

    def _restore_window_geometry(self) -> None:
        """恢复任一已连接显示器内的窗口状态，无法恢复时置于主屏幕中央。"""

        screen = QApplication.primaryScreen()
        if screen is None:
            return
        available_area = screen.availableGeometry()
        saved_geometry = self._config_store.window_geometry()
        if saved_geometry is not None:
            width, height, x, y = saved_geometry
            self.resize(width, height)
            requested_area = QRect(x, y, self.width(), self.height())
            # 坐标是虚拟桌面坐标：副显示器在主显示器左侧或上方时会出现负值。
            # 只要窗口完整落在任一当前已连接显示器的可用区域，就应原位恢复。
            if any(screen.availableGeometry().contains(requested_area) for screen in QApplication.screens()):
                self.move(x, y)
                return

        # 保存的坐标缺失、无效，或原显示器已断开导致窗口位于所有屏幕外时，
        # 保留当前尺寸并回退至主显示器中央。
        self.move(
            available_area.x() + (available_area.width() - self.width()) // 2,
            available_area.y() + (available_area.height() - self.height()) // 2,
        )
        self.save_window_geometry()

    def save_window_geometry(self) -> None:
        """将当前普通窗口的尺寸和位置写入本地设置文件。"""

        if self.isMaximized() or self.isMinimized():
            return
        geometry = self.geometry()
        self._config_store.set_window_geometry(
            width=geometry.width(), height=geometry.height(), x=geometry.x(), y=geometry.y()
        )

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
        # 固定入口及分类使用应用素材图标，避免依赖不同系统的字符字形。
        # tools.json 中的 category 保存分类展示名，因此可直接与左侧菜单名称匹配。
        # 未知或已删除分类中的工具仍计入“全部工具”，不会被错误地归入其他分类。
        tool_configurations = self._config_store.load_tool_configurations()
        category_names = self._config_store.load_category_names()
        category_counts = {name: 0 for name in category_names}
        for configuration in tool_configurations:
            category = configuration["category"]
            if category in category_counts:
                category_counts[category] += 1
        sidebar_items = [
            (ALL_TOOLS_ICON_PATH, f"全部工具 ({len(tool_configurations)})", "all"),
            (FAVORITES_ICON_PATH, f"我的收藏 ({sum(bool(tool['star']) for tool in tool_configurations)})", "favorites"),
            (RECENT_TOOLS_ICON_PATH, "最近使用", "recent"),
            *[(TOOLS_MENU_ICON_PATH, f"{name} ({category_counts[name]})", f"category:{name}") for name in category_names],
        ]
        for icon_path, text, menu_key in sidebar_items:
            item = QListWidgetItem(QIcon(str(icon_path)), text)
            item.setData(Qt.ItemDataRole.UserRole, menu_key)
            sidebar.addItem(item)
        sidebar.setCurrentRow(0)
        sidebar.currentItemChanged.connect(self._show_tools_for_menu)
        self._sidebar = sidebar
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
        add_button.setToolTip("添加本地工具或网页工具")
        add_button.clicked.connect(self.show_add_tool_dialog)
        action_row.addWidget(add_button)
        settings_button = QPushButton("设置")
        settings_button.setObjectName("secondaryButton")
        settings_button.clicked.connect(self.show_settings)
        action_row.addWidget(settings_button)
        content.addLayout(action_row)
        self._tool_scroll = QScrollArea()
        self._tool_scroll.setObjectName("contentArea")
        self._tool_scroll.setWidgetResizable(True)
        content.addWidget(self._tool_scroll)
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
            #toolGrid { background: transparent; }
            #toolCard { background: #ffffff; border: 1px solid #dce2ec; border-radius: 12px; }
            #toolCard:hover { border-color: #9cc5f5; background: #fafdff; }
            #toolCardTitle { color: #182033; font-size: 15px; font-weight: 700; }
            #toolCardStatus { background: transparent; }
            #toolCardStar { min-width: 22px; max-width: 22px; min-height: 22px; max-height: 22px; padding: 0; border: none; border-radius: 5px; background: transparent; }
            #toolCardStar:hover { background: #eef4fb; }
            #toolCardDescription { color: #64748b; font-size: 12px; }
            #toolCardType { color: #1677e8; font-size: 11px; font-weight: 600; background: #e8f1ff; border-radius: 4px; padding: 2px 6px; }
            #toolCardCategory { color: #64748b; font-size: 11px; }
            #toolCardRun { min-height: 24px; padding: 0 8px; border-radius: 5px; font-size: 11px; }
            #emptyState { background: #ffffff; border: 1px dashed #d5deea; border-radius: 12px; } #emptyTitle { color: #243047; font-size: 20px; font-weight: 700; } #emptyHint { color: #7c8798; font-size: 13px; }
        """)
        self._show_tools_for_menu(sidebar.currentItem())

    def _show_tools_for_menu(self, item: QListWidgetItem | None) -> None:
        """根据左侧菜单更新右侧工具卡片，分类内按权重和名称稳定排序。"""

        if item is None:
            return
        menu_key = str(item.data(Qt.ItemDataRole.UserRole))
        configurations = self._config_store.load_tool_configurations()
        if menu_key == "all":
            title = f"全部工具 ({len(configurations)})"
            selected_tools = configurations
        elif menu_key.startswith("category:"):
            category = menu_key.removeprefix("category:")
            selected_tools = [tool for tool in configurations if tool["category"] == category]
            title = f"{category} ({len(selected_tools)})"
        elif menu_key == "favorites":
            selected_tools = [tool for tool in configurations if bool(tool["star"])]
            title = f"我的收藏 ({len(selected_tools)})"
        else:
            title = "最近使用"
            selected_tools = []

        selected_tools.sort(key=lambda tool: (-int(tool["weight"]), str(tool["name"])))
        self._tool_scroll.setWidget(self._create_tools_widget(selected_tools, title))

    def _create_tools_widget(self, tools: list[dict[str, object]], title: str) -> QWidget:
        """构建卡片网格；卡片本身固定为 200 × 140，便于通过 QSS 定制。"""

        if not tools:
            empty = QFrame()
            empty.setObjectName("emptyState")
            empty_layout = QVBoxLayout(empty)
            empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_title = QLabel("还没有添加工具" if title.startswith("全部工具") else "暂无工具")
            empty_title.setObjectName("emptyTitle")
            hint = QLabel("通过“添加工具”建立你的本地工具库。\nSecForge 仅用于合法、已授权的安全测试与研究。")
            hint.setObjectName("emptyHint")
            hint.setWordWrap(True)
            hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.addWidget(empty_title, alignment=Qt.AlignmentFlag.AlignCenter)
            empty_layout.addWidget(hint, alignment=Qt.AlignmentFlag.AlignCenter)
            return empty

        grid_widget = QWidget()
        grid_widget.setObjectName("toolGrid")
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(2, 2, 2, 2)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(16)
        grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        # 最小工作区可容纳三张 200px 卡片；固定列数也使卡片间距稳定、易于定制。
        columns = 3
        for index, configuration in enumerate(tools):
            grid.addWidget(ToolCard(configuration, self._set_tool_star), index // columns, index % columns)
        return grid_widget

    def _set_tool_star(self, configuration: dict[str, object], starred: bool) -> None:
        """保存收藏状态，并刷新当前列表和左侧收藏计数。"""

        self._config_store.set_tool_configuration_star(configuration, starred)
        configurations = self._config_store.load_tool_configurations()
        favorite_count = sum(bool(tool["star"]) for tool in configurations)
        for index in range(self._sidebar.count()):
            item = self._sidebar.item(index)
            if item.data(Qt.ItemDataRole.UserRole) == "favorites":
                item.setText(f"我的收藏 ({favorite_count})")
                break
        self._show_tools_for_menu(self._sidebar.currentItem())

    def show_settings(self) -> None:
        """显示独立的模态系统设置窗口。"""

        if self.isMinimized():
            self.showNormal()
        self.raise_()
        self.activateWindow()
        SettingsDialog(self._config_store, self).exec()

    def show_add_tool_dialog(self) -> None:
        """显示添加工具窗口；保存成功后更新工具数量提示。"""

        if AddToolDialog(self._config_store, self).exec() == QDialog.DialogCode.Accepted:
            # 保存后重建页面，导航计数与工具卡片立即同步最新配置。
            self._build_ui()

    def closeEvent(self, event: QCloseEvent) -> None:
        """按已保存的常规设置决定关闭主窗口时的行为。"""

        if self._system_tray_available and self._config_store.minimize_to_tray_on_close():
            self.hide()
            event.ignore()
            return
        self.save_window_geometry()
        event.accept()
