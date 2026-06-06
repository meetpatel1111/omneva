"""Network Stream Bookmarks - Save and manage RTSP/RTMP/HLS URLs in sidebar."""

import json
import os
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLineEdit, QLabel, QFrame, QMessageBox, QInputDialog,
    QMenu, QAbstractItemView, QStyle
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QAction, QCursor, QPixmap
from src.core.logger import get_logger
from src.core.storage import storage


class NetworkBookmark:
    """Data model for network stream bookmark."""
    
    def __init__(self, name, url, protocol="http", description="", tags=None):
        self.name = name
        self.url = url
        self.protocol = protocol.lower()
        self.description = description
        self.tags = tags or []
        self.created_at = datetime.now().isoformat()
        self.last_accessed = None
        self.access_count = 0
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'name': self.name,
            'url': self.url,
            'protocol': self.protocol,
            'description': self.description,
            'tags': self.tags,
            'created_at': self.created_at,
            'last_accessed': self.last_accessed,
            'access_count': self.access_count
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary."""
        bookmark = cls(
            data['name'],
            data['url'],
            data.get('protocol', 'http'),
            data.get('description', ''),
            data.get('tags', [])
        )
        bookmark.created_at = data.get('created_at', bookmark.created_at)
        bookmark.last_accessed = data.get('last_accessed')
        bookmark.access_count = data.get('access_count', 0)
        return bookmark
    
    def get_protocol_icon(self):
        """Get icon based on protocol."""
        protocol_icons = {
            'rtsp': '📹',
            'rtmp': '🎬',
            'hls': '📱',
            'http': '🌐',
            'https': '🌐',
            'udp': '📡',
            'rtp': '📡',
            'mms': '📺'
        }
        return protocol_icons.get(self.protocol, '🌐')
    
    def is_valid_url(self):
        """Basic URL validation."""
        if not self.url:
            return False
        
        # Check for valid protocol
        valid_protocols = ['rtsp', 'rtmp', 'hls', 'http', 'https', 'udp', 'rtp', 'mms']
        if self.protocol not in valid_protocols:
            return False
        
        # Basic URL structure check
        if '://' not in self.url:
            return False
        
        return True


class NetworkBookmarkWidget(QListWidgetItem):
    """Custom widget for displaying network bookmarks in list."""
    
    bookmark_selected = Signal(object)  # NetworkBookmark
    bookmark_double_clicked = Signal(object)  # NetworkBookmark
    
    def __init__(self, bookmark, parent=None):
        super().__init__(parent)
        self.bookmark = bookmark
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the bookmark widget UI."""
        # Create custom widget
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)
        
        # Header with icon and name
        header_layout = QHBoxLayout()
        
        # Protocol icon
        icon_label = QLabel(self.bookmark.get_protocol_icon())
        icon_label.setStyleSheet("font-size: 16px;")
        header_layout.addWidget(icon_label)
        
        # Name
        name_label = QLabel(self.bookmark.name)
        name_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                color: #ffffff;
            }
        """)
        header_layout.addWidget(name_label)
        
        header_layout.addStretch()
        
        # Access count
        if self.bookmark.access_count > 0:
            count_label = QLabel(f"👤 {self.bookmark.access_count}")
            count_label.setStyleSheet("""
                QLabel {
                    font-size: 10px;
                    color: #888888;
                }
            """)
            header_layout.addWidget(count_label)
        
        layout.addLayout(header_layout)
        
        # URL
        url_label = QLabel(self.bookmark.url[:50] + "..." if len(self.bookmark.url) > 50 else self.bookmark.url)
        url_label.setStyleSheet("""
            QLabel {
                font-size: 9px;
                color: #6200ea;
            }
        """)
        layout.addWidget(url_label)
        
        # Description or tags
        if self.bookmark.description:
            desc_label = QLabel(self.bookmark.description[:60] + "..." if len(self.bookmark.description) > 60 else self.bookmark.description)
            desc_label.setStyleSheet("""
                QLabel {
                    font-size: 8px;
                    color: #cccccc;
                    font-style: italic;
                }
            """)
            layout.addWidget(desc_label)
        elif self.bookmark.tags:
            tags_label = QLabel(" | ".join([f"#{tag}" for tag in self.bookmark.tags[:3]]))
            tags_label.setStyleSheet("""
                QLabel {
                    font-size: 8px;
                    color: #888888;
                }
            """)
            layout.addWidget(tags_label)
        
        # Set widget as list item
        widget.setStyleSheet("""
            QWidget {
                background-color: #2a2a2a;
                border: 1px solid #6200ea;
                border-radius: 4px;
                margin: 2px;
            }
            QWidget:hover {
                background-color: #3a3a3a;
                border-color: #7c4dff;
            }
        """)
        
        self.setSizeHint(self.sizeHint())
        self.setData(Qt.UserRole, self.bookmark)


class NetworkBookmarksPanel(QWidget):
    """Sidebar panel for managing network stream bookmarks."""
    
    bookmark_selected = Signal(object)  # NetworkBookmark
    bookmark_double_clicked = Signal(object)  # NetworkBookmark
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger('network_bookmarks')
        
        self.bookmarks = []
        self.bookmarks_file = os.path.join(storage.get_app_data_dir(), 'network_bookmarks.json')
        
        self._setup_ui()
        self._load_bookmarks()
        
        self.logger.debug("Network bookmarks panel initialized")
    
    def _setup_ui(self):
        """Setup the bookmarks panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Header
        header_label = QLabel("Network Streams")
        header_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: bold;
                color: #ffffff;
                padding: 4px;
            }
        """)
        layout.addWidget(header_label)
        
        # Add bookmark controls
        controls_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("➕ Add")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #6200ea;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 9px;
            }
            QPushButton:hover {
                background-color: #7c4dff;
            }
        """)
        self.add_btn.clicked.connect(self._add_bookmark)
        
        self.import_btn = QPushButton("📥 Import")
        self.import_btn.setStyleSheet("""
            QPushButton {
                background-color: #424242;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 9px;
            }
            QPushButton:hover {
                background-color: #616161;
            }
        """)
        self.import_btn.clicked.connect(self._import_bookmarks)
        
        controls_layout.addWidget(self.add_btn)
        controls_layout.addWidget(self.import_btn)
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)
        
        # Search/filter
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search bookmarks...")
        self.search_edit.setStyleSheet("""
            QLineEdit {
                background-color: #3a3a3a;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 9px;
            }
            QLineEdit:focus {
                border-color: #6200ea;
            }
        """)
        self.search_edit.textChanged.connect(self._filter_bookmarks)
        layout.addWidget(self.search_edit)
        
        # Bookmarks list
        self.bookmarks_list = QListWidget()
        self.bookmarks_list.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item {
                background-color: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
            QListWidget::item:selected {
                background-color: #6200ea;
                border-radius: 4px;
            }
        """)
        self.bookmarks_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.bookmarks_list.itemClicked.connect(self._on_item_clicked)
        
        # Enable context menu
        self.bookmarks_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.bookmarks_list.customContextMenuRequested.connect(self._show_context_menu)
        
        layout.addWidget(self.bookmarks_list)
        
        # Status bar
        self.status_label = QLabel("No bookmarks")
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 8px;
                color: #888888;
                padding: 4px;
            }
        """)
        layout.addWidget(self.status_label)
        
        self._update_status()
    
    def _load_bookmarks(self):
        """Load bookmarks from file."""
        try:
            if os.path.exists(self.bookmarks_file):
                with open(self.bookmarks_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.bookmarks = [NetworkBookmark.from_dict(item) for item in data]
                    self._refresh_list()
                    self.logger.info(f"Loaded {len(self.bookmarks)} network bookmarks")
            else:
                self.logger.debug("No bookmarks file found, starting fresh")
        except Exception as e:
            self.logger.error(f"Failed to load bookmarks: {e}")
    
    def _save_bookmarks(self):
        """Save bookmarks to file."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.bookmarks_file), exist_ok=True)
            
            with open(self.bookmarks_file, 'w', encoding='utf-8') as f:
                json.dump([bookmark.to_dict() for bookmark in self.bookmarks], f, indent=2)
            
            self.logger.info(f"Saved {len(self.bookmarks)} network bookmarks")
        except Exception as e:
            self.logger.error(f"Failed to save bookmarks: {e}")
    
    def _add_bookmark(self):
        """Add a new bookmark."""
        dialog = AddBookmarkDialog(self)
        if dialog.exec_() == 1:
            bookmark = dialog.get_bookmark()
            if bookmark and bookmark.is_valid_url():
                self.bookmarks.append(bookmark)
                self._save_bookmarks()
                self._refresh_list()
                self.logger.info(f"Added bookmark: {bookmark.name}")
    
    def _import_bookmarks(self):
        """Import bookmarks from M3U or plain text file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Bookmarks",
            "",
            "M3U Files (*.m3u);;Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                imported_count = 0
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for line_num, line in enumerate(lines, 1):
                        line = line.strip()
                        if line and not line.startswith('#'):
                            # Try to detect protocol
                            protocol = 'http'
                            if line.startswith('rtsp://'):
                                protocol = 'rtsp'
                            elif line.startswith('rtmp://'):
                                protocol = 'rtmp'
                            elif line.startswith('hls://'):
                                protocol = 'hls'
                            elif line.startswith('https://'):
                                protocol = 'https'
                            
                            # Create bookmark
                            bookmark = NetworkBookmark(
                                f"Imported Stream {imported_count + 1}",
                                line,
                                protocol,
                                f"Imported from {os.path.basename(file_path)}"
                            )
                            
                            if bookmark.is_valid_url():
                                self.bookmarks.append(bookmark)
                                imported_count += 1
                
                if imported_count > 0:
                    self._save_bookmarks()
                    self._refresh_list()
                    self.logger.info(f"Imported {imported_count} bookmarks from {file_path}")
                    QMessageBox.information(self, "Import Complete", 
                                          f"Successfully imported {imported_count} bookmarks.")
                else:
                    QMessageBox.warning(self, "Import Failed", 
                                      "No valid stream URLs found in the file.")
            
            except Exception as e:
                self.logger.error(f"Failed to import bookmarks: {e}")
                QMessageBox.critical(self, "Import Error", 
                                  f"Failed to import bookmarks: {e}")
    
    def _filter_bookmarks(self, text):
        """Filter bookmarks based on search text."""
        self._refresh_list(search_text=text.lower())
    
    def _refresh_list(self, search_text=""):
        """Refresh the bookmarks list."""
        self.bookmarks_list.clear()
        
        filtered_bookmarks = self.bookmarks
        if search_text:
            filtered_bookmarks = [
                bookmark for bookmark in self.bookmarks
                if search_text in bookmark.name.lower() or 
                   search_text in bookmark.url.lower() or
                   search_text in bookmark.description.lower() or
                   any(search_text in tag.lower() for tag in bookmark.tags)
            ]
        
        for bookmark in filtered_bookmarks:
            item = NetworkBookmarkWidget(bookmark)
            self.bookmarks_list.addItem(item)
        
        self._update_status()
    
    def _on_item_clicked(self, item):
        """Handle bookmark selection."""
        if isinstance(item, NetworkBookmarkWidget):
            bookmark = item.bookmark
            bookmark.access_count += 1
            bookmark.last_accessed = datetime.now().isoformat()
            self._save_bookmarks()
            self.bookmark_selected.emit(bookmark)
    
    def _on_item_double_clicked(self, item):
        """Handle bookmark double-click."""
        if isinstance(item, NetworkBookmarkWidget):
            bookmark = item.bookmark
            bookmark.access_count += 1
            bookmark.last_accessed = datetime.now().isoformat()
            self._save_bookmarks()
            self.bookmark_double_clicked.emit(bookmark)
    
    def _show_context_menu(self, position):
        """Show context menu for bookmark."""
        item = self.bookmarks_list.itemAt(position)
        if not isinstance(item, NetworkBookmarkWidget):
            return
        
        bookmark = item.bookmark
        menu = QMenu(self)
        
        # Play action
        play_action = QAction("▶ Play Stream", self)
        play_action.triggered.connect(lambda: self.bookmark_double_clicked.emit(bookmark))
        menu.addAction(play_action)
        
        menu.addSeparator()
        
        # Edit action
        edit_action = QAction("✏️ Edit", self)
        edit_action.triggered.connect(lambda: self._edit_bookmark(bookmark))
        menu.addAction(edit_action)
        
        # Copy URL action
        copy_action = QAction("📋 Copy URL", self)
        copy_action.triggered.connect(lambda: self._copy_url(bookmark))
        menu.addAction(copy_action)
        
        menu.addSeparator()
        
        # Delete action
        delete_action = QAction("🗑️ Delete", self)
        delete_action.triggered.connect(lambda: self._delete_bookmark(bookmark))
        menu.addAction(delete_action)
        
        menu.exec_(self.mapToGlobal(position))
    
    def _edit_bookmark(self, bookmark):
        """Edit an existing bookmark."""
        dialog = AddBookmarkDialog(self, bookmark)
        if dialog.exec_() == 1:
            updated_bookmark = dialog.get_bookmark()
            if updated_bookmark and updated_bookmark.is_valid_url():
                # Update bookmark in list
                index = self.bookmarks.index(bookmark)
                self.bookmarks[index] = updated_bookmark
                self._save_bookmarks()
                self._refresh_list()
                self.logger.info(f"Updated bookmark: {updated_bookmark.name}")
    
    def _copy_url(self, bookmark):
        """Copy bookmark URL to clipboard."""
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(bookmark.url)
        self.logger.info(f"Copied URL to clipboard: {bookmark.url}")
    
    def _delete_bookmark(self, bookmark):
        """Delete a bookmark."""
        reply = QMessageBox.question(
            self, 'Delete Bookmark',
            f'Are you sure you want to delete "{bookmark.name}"?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.bookmarks.remove(bookmark)
            self._save_bookmarks()
            self._refresh_list()
            self.logger.info(f"Deleted bookmark: {bookmark.name}")
    
    def _update_status(self):
        """Update status label."""
        count = len(self.bookmarks)
        if count == 0:
            self.status_label.setText("No bookmarks")
        else:
            self.status_label.setText(f"{count} bookmark{'s' if count != 1 else ''}")


class AddBookmarkDialog(QDialog):
    """Dialog for adding/editing network bookmarks."""
    
    def __init__(self, parent=None, bookmark=None):
        super().__init__(parent)
        self.bookmark = bookmark
        self.setWindowTitle("Add Network Stream Bookmark" if bookmark is None else "Edit Network Stream Bookmark")
        self.setModal(True)
        self.setFixedSize(400, 250)
        
        self._setup_ui()
        self._populate_fields()
        
        self.logger.debug("Add bookmark dialog initialized")
    
    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)
        
        # URL
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("URL:"))
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("rtsp://server/stream or rtmp://server/stream")
        url_layout.addWidget(self.url_edit)
        layout.addLayout(url_layout)
        
        # Protocol
        protocol_layout = QHBoxLayout()
        protocol_layout.addWidget(QLabel("Protocol:"))
        self.protocol_combo = QLineEdit()
        self.protocol_combo.setPlaceholderText("Auto-detect")
        protocol_layout.addWidget(self.protocol_combo)
        layout.addLayout(protocol_layout)
        
        # Description
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("Description:"))
        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("Optional description")
        desc_layout.addWidget(self.desc_edit)
        layout.addLayout(desc_layout)
        
        # Tags
        tags_layout = QHBoxLayout()
        tags_layout.addWidget(QLabel("Tags:"))
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("live, sports, news (comma-separated)")
        tags_layout.addWidget(self.tags_edit)
        layout.addLayout(tags_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.save_btn = QPushButton("Save")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #6200ea;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #7c4dff;
            }
        """)
        self.save_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
        
        # Set dark theme
        self.setStyleSheet("""
            QDialog {
                background-color: #2a2a2a;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QLineEdit {
                background-color: #3a3a3a;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px;
            }
            QLineEdit:focus {
                border-color: #6200ea;
            }
        """)
    
    def _populate_fields(self):
        """Populate fields if editing existing bookmark."""
        if self.bookmark:
            self.name_edit.setText(self.bookmark.name)
            self.url_edit.setText(self.bookmark.url)
            self.protocol_combo.setText(self.bookmark.protocol)
            self.desc_edit.setText(self.bookmark.description)
            self.tags_edit.setText(", ".join(self.bookmark.tags))
    
    def get_bookmark(self):
        """Get the bookmark data from dialog."""
        name = self.name_edit.text().strip()
        url = self.url_edit.text().strip()
        protocol = self.protocol_combo.text().strip()
        description = self.desc_edit.text().strip()
        tags_text = self.tags_edit.text().strip()
        tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()]
        
        # Auto-detect protocol if not specified
        if not protocol:
            if url.startswith('rtsp://'):
                protocol = 'rtsp'
            elif url.startswith('rtmp://'):
                protocol = 'rtmp'
            elif url.startswith('hls://'):
                protocol = 'hls'
            elif url.startswith('https://'):
                protocol = 'https'
            else:
                protocol = 'http'
        
        return NetworkBookmark(name, url, protocol, description, tags)
