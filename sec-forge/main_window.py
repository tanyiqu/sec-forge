from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QMainWindow, QPushButton, QScrollArea, QToolBar, QVBoxLayout, QWidget


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SecForge · 网安工具箱")
        self.resize(1100, 700)
        self._build_ui()

    def _build_ui(self) -> None:
        toolbar = QToolBar("主工具栏", self)
        toolbar.setMovable(False)
        toolbar.addWidget(QLabel("  SecForge · 网安工具箱  "))
        toolbar.addSeparator()
        settings_button = QPushButton("设置")
        settings_button.setEnabled(False)
        toolbar.addWidget(settings_button)
        self.addToolBar(toolbar)

        root = QWidget()
        layout = QHBoxLayout(root)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        sidebar = QListWidget()
        sidebar.setFixedWidth(190)
        sidebar.addItems(["全部工具 (0)", "收藏", "最近使用", "────────", "信息收集 (0)", "漏洞扫描 (0)", "Web 工具 (0)", "密码工具 (0)", "其他工具 (0)"])
        sidebar.setCurrentRow(0)
        layout.addWidget(sidebar)

        content = QVBoxLayout()
        search = QLineEdit()
        search.setPlaceholderText("搜索名称 / 标签 / 描述")
        content.addWidget(search)
        empty = QFrame()
        empty_layout = QVBoxLayout(empty)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel("还没有添加工具")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        hint = QLabel("通过“添加工具”建立你的本地工具库。SecForge 仅用于合法、已授权的安全测试与研究。")
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        add_button = QPushButton("+ 添加工具")
        add_button.setEnabled(False)
        empty_layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(hint, alignment=Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(add_button, alignment=Qt.AlignmentFlag.AlignCenter)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(empty)
        content.addWidget(scroll)
        layout.addLayout(content, 1)
        self.setCentralWidget(root)
