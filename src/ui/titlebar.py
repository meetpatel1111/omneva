"""Custom frameless titlebar with window controls."""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QMouseEvent


class TitleBar(QWidget):
    """Custom titlebar for frameless window."""

    # Signals
    minimize_clicked = Signal()
    maximize_clicked = Signal()
    close_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("titleBar")
        self.setFixedHeight(28)
        self._drag_pos = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 4, 0)
        layout.setSpacing(0)

        # App icon & title
        self.icon_label = QLabel("🎬")
        self.icon_label.setObjectName("titleIcon")
        self.icon_label.setFixedWidth(20)

        self.title_label = QLabel("Omneva")
        self.title_label.setObjectName("titleText")
        self.title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # Window control buttons
        btn_style = "titleBarBtn"

        self.btn_minimize = QPushButton("─")
        self.btn_minimize.setObjectName("btnMinimize")
        self.btn_minimize.setProperty("class", btn_style)
        self.btn_minimize.setFixedSize(36, 24)
        self.btn_minimize.clicked.connect(self.minimize_clicked.emit)

        self.btn_maximize = QPushButton("□")
        self.btn_maximize.setObjectName("btnMaximize")
        self.btn_maximize.setProperty("class", btn_style)
        self.btn_maximize.setFixedSize(36, 24)
        self.btn_maximize.clicked.connect(self.maximize_clicked.emit)

        self.btn_close = QPushButton("✕")
        self.btn_close.setObjectName("btnClose")
        self.btn_close.setProperty("class", btn_style)
        self.btn_close.setFixedSize(36, 24)
        self.btn_close.clicked.connect(self.close_clicked.emit)

        layout.addWidget(self.icon_label)
        layout.addWidget(self.title_label)
        layout.addStretch()
        layout.addWidget(self.btn_minimize)
        layout.addWidget(self.btn_maximize)
        layout.addWidget(self.btn_close)

    def set_title(self, title: str):
        """Update the titlebar text."""
        self.title_label.setText(title)

    def update_maximize_button(self, is_maximized: bool):
        """Toggle maximize/restore icon."""
        self.btn_maximize.setText("❐" if is_maximized else "□")

    # ─── Drag to move window ────────────────────────────────
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            # Un-maximize if dragging while maximized
            win = self.window()
            if win.isMaximized():
                win.showNormal()
                # Reposition so cursor stays on titlebar
                self._drag_pos = QPoint(win.width() // 2, 20)
            win.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_pos = None
        event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """Double-click to toggle maximize."""
        if event.button() == Qt.LeftButton:
            self.maximize_clicked.emit()
