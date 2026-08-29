from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QPoint, QSize, Qt
from PyQt6.QtGui import QIcon, QMouseEvent
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QMainWindow, QPushButton, QScrollArea, QVBoxLayout, QWidget

from resources import CLOSE_ICON_PATH, MAXIMIZE_ICON_PATH, MINIMIZE_ICON_PATH


class TitleBar(QFrame):
    """用于移动窗口并承载窗口控制按钮的自定义标题栏。"""

    def __init__(self, window: QMainWindow) -> None:
        super().__init__(window)
        self._window = window
        self._drag_offset: QPoint | None = None
        self.setObjectName("titleBar")
        self.setFixedHeight(52)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 10, 0)
        layout.setSpacing(8)
        title = QLabel("SecForge")
        title.setObjectName("windowTitle")
        title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        subtitle = QLabel("网安工具箱 by Tanyiqu")
        subtitle.setObjectName("windowSubtitle")
        subtitle.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch()
        self._minimize_button = self._make_button(MINIMIZE_ICON_PATH, "最小化")
        self._maximize_button = self._make_button(MAXIMIZE_ICON_PATH, "最大化")
        self._close_button = self._make_button(CLOSE_ICON_PATH, "关闭", "closeButton")
        self._minimize_button.clicked.connect(window.showMinimized)
        self._maximize_button.clicked.connect(self._toggle_maximized)
        self._close_button.clicked.connect(window.close)
        layout.addWidget(self._minimize_button)
        layout.addWidget(self._maximize_button)
        layout.addWidget(self._close_button)

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
            self._maximize_button.setToolTip("最大化")
        else:
            self._window.showMaximized()
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
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_maximized()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SecForge · 网安工具箱")
        self.setMinimumSize(860, 560)
        self.resize(1180, 740)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._build_ui()

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
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(18)
        sidebar = QListWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(202)
        sidebar.addItems(["▦  全部工具 (0)", "★  我的收藏", "◷  最近使用", "────────────", "▣  信息收集 (0)", "▣  漏洞扫描 (0)", "▣  Web 工具 (0)", "▣  密码工具 (0)", "▣  其他工具 (0)"])
        sidebar.setCurrentRow(0)
        layout.addWidget(sidebar)

        content = QVBoxLayout()
        search = QLineEdit()
        search.setPlaceholderText("搜索名称 / 标签 / 描述")
        action_row = QHBoxLayout()
        action_row.addWidget(search, 1)
        add_button = QPushButton("+ 添加工具")
        add_button.setEnabled(False)
        add_button.setToolTip("工具管理功能即将提供")
        action_row.addWidget(add_button)
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
            #windowButton, #closeButton { border: none; border-radius: 6px; background: transparent; color: #45536a; font-size: 18px; }
            #windowButton:hover { background: #eaf0f8; } #closeButton:hover { background: #e95353; color: white; }
            #sidebar { background: #ffffff; border: 1px solid #e0e6ef; border-radius: 10px; padding: 8px; outline: 0; color: #364153; font-size: 13px; }
            #sidebar::item { height: 34px; border-radius: 6px; padding-left: 8px; } #sidebar::item:selected { background: #e8f1ff; color: #1677e8; font-weight: 600; } #sidebar::item:hover { background: #f3f6fa; }
            QLineEdit { min-height: 36px; background: #ffffff; border: 1px solid #d9e0ea; border-radius: 8px; padding: 0 12px; color: #243047; } QLineEdit:focus { border-color: #1677e8; }
            QPushButton { min-height: 36px; padding: 0 15px; background: #1677e8; border: none; border-radius: 8px; color: white; font-weight: 600; } QPushButton:disabled { background: #9fc8f5; color: #f7fbff; }
            #contentArea { border: none; background: transparent; } #contentArea > QWidget > QWidget { background: transparent; }
            #emptyState { background: #ffffff; border: 1px dashed #d5deea; border-radius: 12px; } #emptyTitle { color: #243047; font-size: 20px; font-weight: 700; } #emptyHint { color: #7c8798; font-size: 13px; }
        """)
