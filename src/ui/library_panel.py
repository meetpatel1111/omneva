"""Library Panel — Playlist and Media Browser."""

import os
import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeView, QSplitter, QFileDialog, QHeaderView, QFrame,
    QLineEdit, QListView, QStackedWidget, QListWidget, QListWidgetItem,
    QTableView, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal, QDir, QSize, QModelIndex
from PySide6.QtWidgets import QFileSystemModel

from src.core.ffprobe_service import FFprobeService
from src.core.utils import is_media_file, format_duration, get_icon
from src.core.playlist_model import PlaylistModel


class MetadataPanel(QFrame):
    """Displays FFprobe metadata for selected file."""
    
    play_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("metadataPanel")
        self.setFixedWidth(280)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel("📋 File Info")
        title.setObjectName("metadataTitle")
        layout.addWidget(title)
        
        self.info_label = QLabel("Select a media file to view details")
        self.info_label.setObjectName("metadataContent")
        self.info_label.setWordWrap(True)
        self.info_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.info_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.info_label, 1)

        self.btn_play = QPushButton("▶  Play This File")
        self.btn_play.setObjectName("metadataPlayBtn")
        self.btn_play.setFixedHeight(36)
        self.btn_play.hide()
        self.btn_play.clicked.connect(self._on_play_clicked)
        layout.addWidget(self.btn_play)

        self._current_path = None

    def show_metadata(self, meta: dict, path: str):
        """Display parsed metadata."""
        self._current_path = path

        if "error" in meta:
            self.info_label.setText(f"⚠ {meta['error']}")
            self.btn_play.hide()
            return

        fmt = meta["format"]
        lines = [
            f"<b>{meta['file_name']}</b>",
            f"",
            f"<b>Format:</b> {fmt['long_name']}",
            f"<b>Duration:</b> {fmt['duration_str']}",
            f"<b>Size:</b> {fmt['size_str']}",
            f"<b>Bitrate:</b> {fmt['bitrate_str']}",
        ]

        # Video streams
        for i, vs in enumerate(meta.get("video_streams", [])):
            lines.append(f"")
            lines.append(f"<b>Video #{i+1}:</b> {vs['codec'].upper()}")
            lines.append(f"  {vs['resolution']} @ {vs['fps']}fps")
            if vs['bitrate_str'] != 'N/A':
                lines.append(f"  {vs['bitrate_str']}")

        # Audio streams
        for i, as_ in enumerate(meta.get("audio_streams", [])):
            lines.append(f"")
            lines.append(f"<b>Audio #{i+1}:</b> {as_['codec'].upper()}")
            lines.append(f"  {as_['channels']}ch, {as_['sample_rate']}Hz")
            if as_['bitrate_str'] != 'N/A':
                lines.append(f"  {as_['bitrate_str']}")

        self.info_label.setText("<br>".join(lines))
        self.btn_play.show()

    def clear(self):
        self.info_label.setText("Select a media file to view details")
        self.btn_play.hide()
        self._current_path = None
        
    def _on_play_clicked(self):
        if self._current_path:
            self.play_requested.emit(self._current_path)


class FileBrowserWidget(QWidget):
    """Refactored File Browser with Metadata Splitter."""

    play_requested = Signal(str)

    VIEW_ICONS = 0
    VIEW_DETAILS = 1
    VIEW_LIST = 2

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ffprobe = FFprobeService()
        self._current_path = None

        self._setup_ui()
        self._connect_signals()

        # Open home directory by default
        home = QDir.homePath()
        self._navigate_to(home)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ─── Toolbar ────────────────────────────────────────
        toolbar = QWidget()
        toolbar.setObjectName("libraryToolbar")
        toolbar.setFixedHeight(40)
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(8, 4, 8, 4)
        tb_layout.setSpacing(6)

        self.btn_back = QPushButton("←")
        self.btn_back.setFixedSize(28, 28)
        self.btn_up = QPushButton("↑")
        self.btn_up.setFixedSize(28, 28)
        self.btn_home = QPushButton("🏠")
        self.btn_home.setFixedSize(28, 28)

        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Path...")

        self.btn_browse = QPushButton("📂")
        self.btn_browse.setFixedSize(28, 28)

        tb_layout.addWidget(self.btn_back)
        tb_layout.addWidget(self.btn_up)
        tb_layout.addWidget(self.btn_home)
        tb_layout.addWidget(self.path_edit, 1)
        tb_layout.addWidget(self.btn_browse)

        layout.addWidget(toolbar)

        # ─── Splitter: File View + Metadata ─────────────────
        splitter = QSplitter(Qt.Horizontal)
        splitter.setObjectName("librarySplitter")

        # File system model
        self.fs_model = QFileSystemModel()
        self.fs_model.setRootPath("")
        self.fs_model.setFilter(QDir.AllDirs | QDir.Files | QDir.NoDotAndDotDot)

        # View Stack (Tree vs List)
        self.view_stack = QStackedWidget()
        
        # 1. Tree View (Detailed)
        self.tree = QTreeView()
        self.tree.setModel(self.fs_model)
        self.tree.setSelectionMode(QTreeView.SingleSelection)
        self.tree.setAnimated(True)
        self.tree.setSortingEnabled(True)
        self.tree.hideColumn(2) # Type
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        
        # 2. List View (Icons/List)
        self.list_view = QListView()
        self.list_view.setModel(self.fs_model)
        self.list_view.setSelectionMode(QListView.SingleSelection)
        self.list_view.setViewMode(QListView.IconMode)
        self.list_view.setGridSize(QSize(100, 100))
        self.list_view.setIconSize(QSize(80, 80))
        self.list_view.setResizeMode(QListView.Adjust)
        self.list_view.setWrapping(True)
        self.list_view.setWordWrap(True)

        self.view_stack.addWidget(self.tree)      # Index 0
        self.view_stack.addWidget(self.list_view) # Index 1

        # Metadata panel
        self.metadata_panel = MetadataPanel()

        splitter.addWidget(self.view_stack)
        splitter.addWidget(self.metadata_panel)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, True) # Allow hiding metadata
        splitter.setSizes([600, 250])

        layout.addWidget(splitter, 1)

    def _connect_signals(self):
        # Tree signals
        self.tree.clicked.connect(self._on_item_clicked)
        self.tree.doubleClicked.connect(self._on_item_double_clicked)
        # List signals
        self.list_view.clicked.connect(self._on_item_clicked)
        self.list_view.doubleClicked.connect(self._on_item_double_clicked)
        
        self.btn_browse.clicked.connect(self._browse_folder)
        self.btn_up.clicked.connect(self._go_up)
        self.btn_home.clicked.connect(lambda: self._navigate_to(QDir.homePath()))
        self.path_edit.returnPressed.connect(
            lambda: self._navigate_to(self.path_edit.text())
        )
        self.metadata_panel.play_requested.connect(self.play_requested.emit)

    def set_view_mode(self, mode: int):
        if mode == self.VIEW_DETAILS:
            self.view_stack.setCurrentWidget(self.tree)
        elif mode == self.VIEW_ICONS:
            self.view_stack.setCurrentWidget(self.list_view)
            self.list_view.setViewMode(QListView.IconMode)
            self.list_view.setGridSize(QSize(100, 100))
            self.list_view.setIconSize(QSize(64, 64))
        elif mode == self.VIEW_LIST:
            self.view_stack.setCurrentWidget(self.list_view)
            self.list_view.setViewMode(QListView.ListMode)
            self.list_view.setGridSize(QSize()) 
            self.list_view.setIconSize(QSize(16, 16))

    def _navigate_to(self, path: str):
        if os.path.isdir(path):
            index = self.fs_model.setRootPath(path)
            self.tree.setRootIndex(index)
            self.list_view.setRootIndex(index)
            self.path_edit.setText(path)

    def _on_item_clicked(self, index):
        path = self.fs_model.filePath(index)
        if os.path.isfile(path) and is_media_file(path):
            self._current_path = path
            meta = self.ffprobe.get_metadata(path)
            self.metadata_panel.show_metadata(meta, path)
        else:
            self._current_path = None
            self.metadata_panel.clear()

    def _on_item_double_clicked(self, index):
        path = self.fs_model.filePath(index)
        if os.path.isdir(path):
            self._navigate_to(path)
        elif os.path.isfile(path) and is_media_file(path):
            self.play_requested.emit(path)

    def _browse_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Browse Folder")
        if path:
            self._navigate_to(path)

    def _go_up(self):
        current = self.path_edit.text()
        parent = os.path.dirname(current)
        if parent and parent != current:
            self._navigate_to(parent)


class PlaylistViewWidget(QWidget):
    """Widget displaying the current playlist model."""
    
    play_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._model = None
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header / Toolbar
        toolbar = QWidget()
        toolbar.setFixedHeight(40)
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(8, 4, 8, 4)
        
        title = QLabel("Current Playlist")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.clicked.connect(self._clear_playlist)
        
        tb_layout.addWidget(title)
        tb_layout.addStretch()
        tb_layout.addWidget(self.btn_clear)
        
        layout.addWidget(toolbar)
        
        # Table View
        self.table = QTableView()
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setShowGrid(False)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch) # Title
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents) # Duration
        
        layout.addWidget(self.table)
        
        self.table.doubleClicked.connect(self._on_double_click)

    def set_model(self, model: PlaylistModel):
        self._model = model
        self.table.setModel(model)
        self.table.selectionModel().currentChanged.connect(self._on_selection_changed)

    def _on_double_click(self, index):
        if self._model:
            path = self._model.get_path(index.row())
            if path:
                self.play_requested.emit(path)

    def _on_selection_changed(self, current, previous):
        pass # Handle selection sync if needed

    def _clear_playlist(self):
        if self._model:
            self._model.clear()


class LibraryPanel(QWidget):
    """Main Panel: Sidebar + Content (Playlist or FileBrowser)."""

    play_file_requested = Signal(str)

    VIEW_ICONS = 0
    VIEW_DETAILS = 1
    VIEW_LIST = 2

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("libraryPanel")

        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # ─── Sidebar ────────────────────────────────────────
        self.sidebar = QListWidget()
        self.sidebar.setObjectName("librarySidebar")
        self.sidebar.setFixedWidth(200)
        self.sidebar.setFrameShape(QFrame.NoFrame)
        self.sidebar.setStyleSheet("background-color: #2b2b2b; border-right: 1px solid #3d3d3d;")
        
        # Add items
        item_pl = QListWidgetItem("Playlist")
        item_pl.setData(Qt.UserRole, "playlist")
        self.sidebar.addItem(item_pl)
        
        item_mc = QListWidgetItem("My Computer")
        item_mc.setData(Qt.UserRole, "browser")
        self.sidebar.addItem(item_mc)
        
        # Placeholders to match VLC look
        self.sidebar.addItem(QListWidgetItem("Devices"))
        self.sidebar.addItem(QListWidgetItem("Local Network"))
        self.sidebar.addItem(QListWidgetItem("Internet"))

        self.sidebar.setCurrentRow(0)
        self.sidebar.currentItemChanged.connect(self._on_sidebar_changed)

        layout.addWidget(self.sidebar)

        # ─── Content Stack ──────────────────────────────────
        self.stack = QStackedWidget()
        
        # Page 1: Playlist
        self.playlist_page = PlaylistViewWidget()
        self.playlist_page.play_requested.connect(self.play_file_requested.emit)
        
        # Page 2: File Browser
        self.browser_page = FileBrowserWidget()
        self.browser_page.play_requested.connect(self.play_file_requested.emit)
        
        self.stack.addWidget(self.playlist_page)
        self.stack.addWidget(self.browser_page)
        
        layout.addWidget(self.stack, 1)

    def set_playlist_model(self, model: PlaylistModel):
        """Connect to shared playlist model."""
        self.playlist_page.set_model(model)

    def _on_sidebar_changed(self, current, previous):
        if not current: return
        data = current.data(Qt.UserRole)
        
        if data == "playlist":
            self.stack.setCurrentWidget(self.playlist_page)
        elif data == "browser":
            self.stack.setCurrentWidget(self.browser_page)
        else:
            # Placeholder pages
            pass

    def set_view_mode(self, mode: int):
        """Pass view mode to browser page (or playlist if we implement modes there)."""
        # Primarily for browser
        self.browser_page.set_view_mode(mode)
