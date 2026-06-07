"""Library Panel — Playlist and Media Browser."""

import os
import hashlib
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeView, QSplitter, QFileDialog, QHeaderView, QFrame,
    QLineEdit, QListView, QStackedWidget, QListWidget, QListWidgetItem,
    QTableView, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal, QDir, QSize, QObject, QSortFilterProxyModel
from PySide6.QtWidgets import QFileSystemModel

from src.core.ffprobe_service import FFprobeService
from src.core.ffmpeg_service import FFmpegService
from src.core.utils import is_media_file, get_icon
from src.core.playlist_model import PlaylistModel
from src.ui.network_bookmarks import NetworkBookmarksPanel
from src.ui.youtube_downloader import YouTubeDownloaderPanel


class ThumbnailCache:
    """Cache for storing and managing thumbnail images."""
    
    def __init__(self, cache_dir: Optional[str] = None):
        import tempfile
        
        self.cache_dir = cache_dir or os.path.join(tempfile.gettempdir(), "omneva_thumbnails")
        os.makedirs(self.cache_dir, exist_ok=True)
        self._cache: dict[str, str] = {}
        
    def get_thumbnail_path(self, file_path: str) -> str:
        """Get cached thumbnail path for a file."""
        # Create a unique filename based on file path and modification time
        try:
            mtime = os.path.getmtime(file_path)
            hash_input = f"{file_path}_{mtime}"
            hash_hex = hashlib.md5(hash_input.encode()).hexdigest()
            return os.path.join(self.cache_dir, f"{hash_hex}.jpg")
        except Exception:
            return os.path.join(self.cache_dir, f"{hashlib.md5(file_path.encode()).hexdigest()}.jpg")
    
    def has_thumbnail(self, file_path: str) -> bool:
        """Check if thumbnail exists for file."""
        thumbnail_path = self.get_thumbnail_path(file_path)
        return os.path.exists(thumbnail_path)
    
    def get_thumbnail(self, file_path: str) -> str:
        """Get thumbnail path if exists, None otherwise."""
        if self.has_thumbnail(file_path):
            return self.get_thumbnail_path(file_path)
        return None


class ThumbnailWorker(QObject):
    """Worker for generating thumbnails in background."""
    
    thumbnail_ready = Signal(str, str)  # file_path, thumbnail_path
    error_occurred = Signal(str, str)   # file_path, error_message
    
    def __init__(self, ffmpeg_service: FFmpegService, thumbnail_cache: ThumbnailCache):
        super().__init__()
        self.ffmpeg = ffmpeg_service
        self.cache = thumbnail_cache
        
    def generate_thumbnail(self, file_path: str):
        """Generate thumbnail for the given file."""
        if not is_media_file(file_path):
            return
            
        thumbnail_path = self.cache.get_thumbnail_path(file_path)
        
        try:
            success = self.ffmpeg.generate_thumbnail(
                input_path=file_path,
                output_path=thumbnail_path,
                timestamp=1.0,  # Generate thumbnail at 1 second
                width=160
            )
            if success:
                self.thumbnail_ready.emit(file_path, thumbnail_path)
            else:
                self.error_occurred.emit(file_path, "Failed to generate thumbnail")
        except Exception as e:
            self.error_occurred.emit(file_path, str(e))


class LibraryFFprobeWorker(QObject):
    """Worker for running FFprobe operations in LibraryPanel."""
    
    metadata_ready = Signal(str, dict)  # path, metadata
    error_occurred = Signal(str, str)   # path, error_message
    
    def __init__(self, ffprobe_service):
        super().__init__()
        self.ffprobe = ffprobe_service
        self._current_path = None
        
    def get_metadata(self, path: str):
        """Get metadata for the given file path."""
        self._current_path = path
        try:
            meta = self.ffprobe.get_metadata(path)
            if "error" in meta:
                self.error_occurred.emit(path, meta['error'])
            else:
                self.metadata_ready.emit(path, meta)
        except Exception as e:
            self.error_occurred.emit(path, str(e))


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
            "",
            f"<b>Format:</b> {fmt['long_name']}",
            f"<b>Duration:</b> {fmt['duration_str']}",
            f"<b>Size:</b> {fmt['size_str']}",
            f"<b>Bitrate:</b> {fmt['bitrate_str']}",
        ]

        # Video streams
        for i, vs in enumerate(meta.get("video_streams", [])):
            lines.append("")
            lines.append(f"<b>Video #{i+1}:</b> {vs['codec'].upper()}")
            lines.append(f"  {vs['resolution']} @ {vs['fps']}fps")
            if vs['bitrate_str'] != 'N/A':
                lines.append(f"  {vs['bitrate_str']}")

        # Audio streams
        for i, as_ in enumerate(meta.get("audio_streams", [])):
            lines.append("")
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
        self.ffmpeg = FFmpegService()
        self._current_path = None
        
        # Setup thumbnail system
        self.thumbnail_cache = ThumbnailCache()
        self._thumbnail_thread = None
        self._thumbnail_worker = None

        self._setup_ui()
        self._setup_thumbnail_system()
        self._connect_signals()

        # Open home directory by default
        home = QDir.homePath()
        self._navigate_to(home)

    def _setup_thumbnail_system(self):
        """Setup thumbnail generation system (disabled due to QThread destruction issues)."""
        # Threading disabled temporarily - using synchronous operations
        self._thumbnail_thread = None
        self._thumbnail_worker = None

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
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 Search files...")
        self.search_edit.setFixedWidth(200)

        self.btn_browse = QPushButton("📂")
        self.btn_browse.setFixedSize(28, 28)

        tb_layout.addWidget(self.btn_back)
        tb_layout.addWidget(self.btn_up)
        tb_layout.addWidget(self.btn_home)
        tb_layout.addWidget(self.path_edit, 1)
        tb_layout.addWidget(self.search_edit)
        tb_layout.addWidget(self.btn_browse)

        layout.addWidget(toolbar)

        # ─── Splitter: File View + Metadata ─────────────────
        splitter = QSplitter(Qt.Horizontal)
        splitter.setObjectName("librarySplitter")

        # File system model
        self.fs_model = QFileSystemModel()
        self.fs_model.setRootPath("")
        self.fs_model.setFilter(QDir.AllDirs | QDir.Files | QDir.NoDotAndDotDot)

        # Proxy model for filtering
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.fs_model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_model.setRecursiveFilteringEnabled(True)

        # View Stack (Tree vs List)
        self.view_stack = QStackedWidget()
        
        # 1. Tree View (Detailed)
        self.tree = QTreeView()
        self.tree.setModel(self.proxy_model)
        self.tree.setSelectionMode(QTreeView.SingleSelection)
        self.tree.setAnimated(True)
        self.tree.setSortingEnabled(True)
        self.tree.hideColumn(2) # Type
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        
        # 2. List View (Icons/List)
        self.list_view = QListView()
        self.list_view.setModel(self.proxy_model)
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
            self.list_view.setViewMode(QListView.ViewMode.IconMode)
            self.list_view.setGridSize(QSize(100, 100))
            self.list_view.setIconSize(QSize(64, 64))
        elif mode == self.VIEW_LIST:
            self.view_stack.setCurrentWidget(self.list_view)
            self.list_view.setViewMode(QListView.ViewMode.ListMode)
            self.list_view.setGridSize(QSize()) 
            self.list_view.setIconSize(QSize(16, 16))

    def _navigate_to(self, path: str):
        if os.path.isdir(path):
            index = self.fs_model.setRootPath(path)
            self.tree.setRootIndex(index)
            self.list_view.setRootIndex(index)
            self.path_edit.setText(path)
            
            # Generate thumbnails for media files in this directory (with delay to avoid blocking)
            from PySide6.QtCore import QTimer
            QTimer.singleShot(100, self._update_visible_thumbnails)

    def _on_item_clicked(self, index):
        path = self.fs_model.filePath(index)
        if os.path.isfile(path) and is_media_file(path):
            self._current_path = path
            # Generate thumbnail for this file
            self._generate_thumbnail_sync(path)
            # Use synchronous FFprobe operation (temporary fallback)
            try:
                meta = self.ffprobe.get_metadata(path)
                self.metadata_panel.show_metadata(meta, path)
            except Exception as e:
                print(f"Error getting metadata for {path}: {e}")
        else:
            self._current_path = None
            self.metadata_panel.clear()
    
    def _update_visible_thumbnails(self):
        """Generate thumbnails for currently visible media files."""
        if self.view_stack.currentWidget() == self.list_view:
            # Get visible items in list view and generate thumbnails
            for i in range(self.list_view.count()):
                index = self.proxy_model.index(i, 0)
                if index.isValid():
                    path = self.fs_model.filePath(index)
                    if is_media_file(path) and not self.thumbnail_cache.has_thumbnail(path):
                        # Generate thumbnail in background (synchronous for now)
                        self._generate_thumbnail_sync(path)

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

        # FFprobe worker setup (disabled temporarily due to threading issues)
        self.ffprobe = FFprobeService()
        self._ffprobe_worker = None
        self._ffprobe_thread = None

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
        
        # Add Network Bookmarks
        item_network = QListWidgetItem("Network Streams")
        item_network.setData(Qt.UserRole, "network")
        self.sidebar.addItem(item_network)
        
        # Add YouTube Downloader
        item_downloader = QListWidgetItem("Online Downloader")
        item_downloader.setData(Qt.UserRole, "downloader")
        self.sidebar.addItem(item_downloader)
        
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
        
        # Page 3: Network Bookmarks
        self.network_page = NetworkBookmarksPanel()
        self.network_page.bookmark_double_clicked.connect(self._on_network_bookmark_selected)
        
        # Page 4: YouTube Downloader
        self.downloader_page = YouTubeDownloaderPanel()
        self.downloader_page.download_requested.connect(self._on_download_complete)
        
        self.stack.addWidget(self.playlist_page)
        self.stack.addWidget(self.browser_page)
        self.stack.addWidget(self.network_page)
        self.stack.addWidget(self.downloader_page)
        
        layout.addWidget(self.stack, 1)
        
        # FFprobe worker signals (disabled temporarily)
        if self._ffprobe_worker:
            self._ffprobe_worker.metadata_ready.connect(self._on_metadata_ready)
            self._ffprobe_worker.error_occurred.connect(self._on_ffprobe_error)

    def set_playlist_model(self, model: PlaylistModel):
        """Connect to shared playlist model."""
        self.playlist_page.set_model(model)

    def _on_metadata_ready(self, path: str, meta: dict):
        """Handle metadata received from FFprobe worker."""
        try:
            if hasattr(self, 'browser_page') and hasattr(self.browser_page, 'metadata_panel'):
                self.browser_page.metadata_panel.show_metadata(meta, path)
        except Exception as e:
            print(f"Error processing metadata for {path}: {e}")

    def _on_ffprobe_error(self, path: str, error_message: str):
        """Handle FFprobe error from worker thread."""
        print(f"Error getting metadata for {path}: {error_message}")

    def _on_search_changed(self, text: str):
        """Handle search text changes to filter files."""
        # Set filter pattern for the proxy model
        if text.strip():
            self.proxy_model.setFilterRegularExpression(text)
        else:
            self.proxy_model.setFilterRegularExpression("")
    
    def _generate_thumbnail_sync(self, file_path: str) -> str:
        """Generate thumbnail synchronously (temporary fallback)."""
        if not is_media_file(file_path):
            return None
            
        # Check if thumbnail already exists
        if self.thumbnail_cache.has_thumbnail(file_path):
            return self.thumbnail_cache.get_thumbnail(file_path)
        
        # Generate thumbnail synchronously
        thumbnail_path = self.thumbnail_cache.get_thumbnail_path(file_path)
        try:
            success = self.ffmpeg.generate_thumbnail(
                input_path=file_path,
                output_path=thumbnail_path,
                timestamp=1.0,  # Generate thumbnail at 1 second
                width=160
            )
            if success:
                return thumbnail_path
        except Exception:
            pass
        return None
    
    def _get_file_icon_with_thumbnail(self, file_path: str) -> str:
        """Get file icon, with thumbnail for media files."""
        if is_media_file(file_path):
            thumbnail_path = self._generate_thumbnail_sync(file_path)
            if thumbnail_path and os.path.exists(thumbnail_path):
                return thumbnail_path
        
        # Fallback to default file icon
        return get_icon(file_path)
    
    def _on_thumbnail_ready(self, file_path: str, thumbnail_path: str):
        """Handle thumbnail generation completion."""
        # Update the file view to show the new thumbnail
        # This would require a custom model implementation for full functionality
        pass
    
    def _on_thumbnail_error(self, file_path: str, error_message: str):
        """Handle thumbnail generation error."""
        print(f"Thumbnail generation error for {file_path}: {error_message}")
    
    def cleanup(self):
        """Clean up resources including thumbnail thread."""
        try:
            if hasattr(self, '_thumbnail_thread') and self._thumbnail_thread and self._thumbnail_thread.isRunning():
                self._thumbnail_thread.quit()
                self._thumbnail_thread.wait(1000)  # Wait up to 1 second for thread to finish
        except Exception as e:
            print(f"Error cleaning up thumbnail thread: {e}")

    def _on_sidebar_changed(self, current, previous):
        if not current:
            return
        data = current.data(Qt.UserRole)
        
        if data == "playlist":
            self.stack.setCurrentWidget(self.playlist_page)
        elif data == "browser":
            self.stack.setCurrentWidget(self.browser_page)
        elif data == "network":
            self.stack.setCurrentWidget(self.network_page)
        elif data == "downloader":
            self.stack.setCurrentWidget(self.downloader_page)
        else:
            # Placeholder pages
            pass
    
    def _on_network_bookmark_selected(self, bookmark):
        """Handle network bookmark selection."""
        if bookmark and bookmark.url:
            self.play_file_requested.emit(bookmark.url)
    
    def _on_download_complete(self, file_path):
        """Handle download completion."""
        if file_path and os.path.exists(file_path):
            self.play_file_requested.emit(file_path)

    def set_view_mode(self, mode: int):
        """Pass view mode to browser page (or playlist if we implement modes there)."""
        # Primarily for browser
        self.browser_page.set_view_mode(mode)
