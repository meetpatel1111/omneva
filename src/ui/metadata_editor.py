"""Metadata Editor - ID3/MP4 metadata editor using FFmpeg and mutagen."""

import os
import subprocess
import json
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTextEdit, QGroupBox, QMessageBox, QFileDialog, QFormLayout,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QSpinBox, QCheckBox, QScrollArea, QFrame,
    QProgressBar, QSplitter, QToolButton, QMenu, QAction
)
from PySide6.QtCore import Qt, Signal, QThread, QObject, QTimer
from PySide6.QtGui import QIcon, QPixmap, QFont
from src.core.logger import get_logger
from src.core.storage import storage


class MetadataWorker(QObject):
    """Worker for metadata operations using FFmpeg."""
    
    # Signals
    metadata_loaded = Signal(dict)  # metadata dictionary
    metadata_saved = Signal(bool, str)  # success, message
    error_occurred = Signal(str)  # error message
    progress_updated = Signal(int)  # progress percentage
    
    def __init__(self):
        super().__init__()
        self.process = None
        self.should_stop = False
        self.logger = get_logger('metadata_worker')
    
    def load_metadata(self, file_path):
        """Load metadata from media file using FFprobe."""
        try:
            self.should_stop = False
            
            # Use FFprobe to get metadata
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', '-show_streams', file_path
            ]
            
            self.process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, universal_newlines=True
            )
            
            stdout, stderr = self.process.communicate()
            
            if self.process.returncode == 0 and not self.should_stop:
                data = json.loads(stdout)
                metadata = self._parse_metadata(data, file_path)
                self.metadata_loaded.emit(metadata)
            else:
                self.error_occurred.emit(f"Failed to load metadata: {stderr}")
                
        except Exception as e:
            self.error_occurred.emit(f"Metadata loading error: {e}")
    
    def _parse_metadata(self, data, file_path):
        """Parse FFprobe output into metadata dictionary."""
        metadata = {
            'file_path': file_path,
            'file_name': os.path.basename(file_path),
            'file_size': os.path.getsize(file_path),
            'duration': 0,
            'format': '',
            'bitrate': 0,
            'title': '',
            'artist': '',
            'album': '',
            'date': '',
            'genre': '',
            'track': '',
            'album_artist': '',
            'comment': '',
            'copyright': '',
            'encoder': '',
            'language': '',
            'description': '',
            'synopsis': '',
            'rating': 0,
            'year': '',
            'tags': []
        }
        
        # Extract format information
        if 'format' in data:
            fmt = data['format']
            metadata['duration'] = float(fmt.get('duration', 0))
            metadata['format'] = fmt.get('format_name', '')
            metadata['bitrate'] = int(fmt.get('bit_rate', 0))
            
            # Extract tags from format
            tags = fmt.get('tags', {})
            for key, value in tags.items():
                key_lower = key.lower()
                if key_lower in ['title', 'artist', 'album', 'date', 'genre', 'track', 
                               'album_artist', 'comment', 'copyright', 'encoder', 
                               'language', 'description', 'synopsis']:
                    metadata[key_lower] = value
                elif key_lower == 'rating':
                    try:
                        metadata[key_lower] = int(float(value))
                    except:
                        pass
                elif key_lower == 'year':
                    metadata[key_lower] = value
                else:
                    metadata['tags'].append(f"{key}: {value}")
        
        # Extract stream information
        if 'streams' in data:
            for stream in data['streams']:
                if stream.get('codec_type') == 'video':
                    metadata['video_codec'] = stream.get('codec_name', '')
                    metadata['width'] = stream.get('width', 0)
                    metadata['height'] = stream.get('height', 0)
                    metadata['fps'] = stream.get('r_frame_rate', '')
                elif stream.get('codec_type') == 'audio':
                    metadata['audio_codec'] = stream.get('codec_name', '')
                    metadata['audio_channels'] = stream.get('channels', 0)
                    metadata['audio_sample_rate'] = stream.get('sample_rate', 0)
        
        return metadata
    
    def save_metadata(self, file_path, metadata):
        """Save metadata to media file using FFmpeg."""
        try:
            self.should_stop = False
            
            # Build FFmpeg command for metadata
            cmd = ['ffmpeg', '-i', file_path]
            
            # Add metadata flags
            metadata_flags = {
                'title': metadata.get('title', ''),
                'artist': metadata.get('artist', ''),
                'album': metadata.get('album', ''),
                'date': metadata.get('date', ''),
                'genre': metadata.get('genre', ''),
                'track': metadata.get('track', ''),
                'album_artist': metadata.get('album_artist', ''),
                'comment': metadata.get('comment', ''),
                'copyright': metadata.get('copyright', ''),
                'encoder': metadata.get('encoder', ''),
                'language': metadata.get('language', ''),
                'description': metadata.get('description', ''),
                'synopsis': metadata.get('synopsis', ''),
                'rating': str(metadata.get('rating', 0)),
                'year': metadata.get('year', '')
            }
            
            for key, value in metadata_flags.items():
                if value:
                    cmd.extend(['-metadata', f"{key}={value}"])
            
            # Output file (overwrite)
            output_file = file_path
            cmd.extend(['-y', '-c', 'copy', output_file])
            
            self.process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, universal_newlines=True
            )
            
            stdout, stderr = self.process.communicate()
            
            if self.process.returncode == 0 and not self.should_stop:
                self.metadata_saved.emit(True, "Metadata saved successfully")
            else:
                self.metadata_saved.emit(False, f"Failed to save metadata: {stderr}")
                
        except Exception as e:
            self.metadata_saved.emit(False, f"Metadata saving error: {e}")
    
    def stop_operation(self):
        """Stop current operation."""
        self.should_stop = True
        if self.process:
            self.process.terminate()
            self.process.wait(timeout=5)


class MetadataEditorWidget(QWidget):
    """Main metadata editor widget."""
    
    metadata_changed = Signal()  # Signal when metadata is modified
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger('metadata_editor')
        
        self.current_file = ""
        self.current_metadata = {}
        self.worker = None
        self.worker_thread = None
        self.is_modified = False
        
        self._setup_ui()
        self._setup_worker()
        
        self.logger.debug("Metadata editor widget initialized")
    
    def _setup_ui(self):
        """Setup the metadata editor UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Header
        header_layout = QHBoxLayout()
        
        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: bold;
                color: #ffffff;
                padding: 4px;
            }
        """)
        header_layout.addWidget(self.file_label)
        
        header_layout.addStretch()
        
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #6200ea;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #7c4dff;
            }
        """)
        self.browse_btn.clicked.connect(self._browse_file)
        header_layout.addWidget(self.browse_btn)
        
        self.load_btn = QPushButton("Load")
        self.load_btn.setStyleSheet("""
            QPushButton {
                background-color: #424242;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #616161;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
        """)
        self.load_btn.clicked.connect(self._load_metadata)
        self.load_btn.setEnabled(False)
        header_layout.addWidget(self.load_btn)
        
        self.save_btn = QPushButton("Save")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #66bb6a;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
        """)
        self.save_btn.clicked.connect(self._save_metadata)
        self.save_btn.setEnabled(False)
        header_layout.addWidget(self.save_btn)
        
        layout.addLayout(header_layout)
        
        # File info section
        info_group = QGroupBox("File Information")
        info_group.setStyleSheet("""
            QGroupBox {
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
            }
        """)
        
        info_layout = QFormLayout()
        
        self.info_file_name = QLabel("")
        self.info_file_size = QLabel("")
        self.info_duration = QLabel("")
        self.info_format = QLabel("")
        self.info_bitrate = QLabel("")
        
        info_layout.addRow("File Name:", self.info_file_name)
        info_layout.addRow("File Size:", self.info_file_size)
        info_layout.addRow("Duration:", self.info_duration)
        info_layout.addRow("Format:", self.info_format)
        info_layout.addRow("Bitrate:", self.info_bitrate)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Metadata tabs
        self.metadata_tabs = QTabWidget()
        self.metadata_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #555555;
                background-color: #2a2a2a;
            }
            QTabWidget::tab-bar {
                alignment: left;
            }
            QTabBar::tab {
                background-color: #3a3a3a;
                color: #ffffff;
                border: 1px solid #555555;
                border-bottom: none;
                padding: 6px 12px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #6200ea;
                border-color: #6200ea;
            }
        """)
        
        # Basic metadata tab
        basic_tab = QWidget()
        basic_layout = QFormLayout(basic_tab)
        
        self.title_edit = QLineEdit()
        self.title_edit.setStyleSheet("""
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
        self.title_edit.textChanged.connect(self._mark_modified)
        
        self.artist_edit = QLineEdit()
        self.artist_edit.setStyleSheet(self.title_edit.styleSheet())
        self.artist_edit.textChanged.connect(self._mark_modified)
        
        self.album_edit = QLineEdit()
        self.album_edit.setStyleSheet(self.title_edit.styleSheet())
        self.album_edit.textChanged.connect(self._mark_modified)
        
        self.date_edit = QLineEdit()
        self.date_edit.setStyleSheet(self.title_edit.styleSheet())
        self.date_edit.textChanged.connect(self._mark_modified)
        
        self.genre_edit = QLineEdit()
        self.genre_edit.setStyleSheet(self.title_edit.styleSheet())
        self.genre_edit.textChanged.connect(self._mark_modified)
        
        self.track_edit = QLineEdit()
        self.track_edit.setStyleSheet(self.title_edit.styleSheet())
        self.track_edit.textChanged.connect(self._mark_modified)
        
        self.year_edit = QLineEdit()
        self.year_edit.setStyleSheet(self.title_edit.styleSheet())
        self.year_edit.textChanged.connect(self._mark_modified)
        
        basic_layout.addRow("Title:", self.title_edit)
        basic_layout.addRow("Artist:", self.artist_edit)
        basic_layout.addRow("Album:", self.album_edit)
        basic_layout.addRow("Date:", self.date_edit)
        basic_layout.addRow("Genre:", self.genre_edit)
        basic_layout.addRow("Track:", self.track_edit)
        basic_layout.addRow("Year:", self.year_edit)
        
        self.metadata_tabs.addTab(basic_tab, "Basic")
        
        # Advanced metadata tab
        advanced_tab = QWidget()
        advanced_layout = QFormLayout(advanced_tab)
        
        self.album_artist_edit = QLineEdit()
        self.album_artist_edit.setStyleSheet(self.title_edit.styleSheet())
        self.album_artist_edit.textChanged.connect(self._mark_modified)
        
        self.comment_edit = QTextEdit()
        self.comment_edit.setMaximumHeight(80)
        self.comment_edit.setStyleSheet("""
            QTextEdit {
                background-color: #3a3a3a;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px;
            }
            QTextEdit:focus {
                border-color: #6200ea;
            }
        """)
        self.comment_edit.textChanged.connect(self._mark_modified)
        
        self.copyright_edit = QLineEdit()
        self.copyright_edit.setStyleSheet(self.title_edit.styleSheet())
        self.copyright_edit.textChanged.connect(self._mark_modified)
        
        self.language_edit = QLineEdit()
        self.language_edit.setStyleSheet(self.title_edit.styleSheet())
        self.language_edit.textChanged.connect(self._mark_modified)
        
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        self.description_edit.setStyleSheet(self.comment_edit.styleSheet())
        self.description_edit.textChanged.connect(self._mark_modified)
        
        self.rating_spin = QSpinBox()
        self.rating_spin.setRange(0, 10)
        self.rating_spin.setStyleSheet("""
            QSpinBox {
                background-color: #3a3a3a;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 4px;
            }
            QSpinBox:focus {
                border-color: #6200ea;
            }
        """)
        self.rating_spin.valueChanged.connect(self._mark_modified)
        
        advanced_layout.addRow("Album Artist:", self.album_artist_edit)
        advanced_layout.addRow("Comment:", self.comment_edit)
        advanced_layout.addRow("Copyright:", self.copyright_edit)
        advanced_layout.addRow("Language:", self.language_edit)
        advanced_layout.addRow("Description:", self.description_edit)
        advanced_layout.addRow("Rating:", self.rating_spin)
        
        self.metadata_tabs.addTab(advanced_tab, "Advanced")
        
        # Technical info tab
        technical_tab = QWidget()
        technical_layout = QFormLayout(technical_tab)
        
        self.video_codec_label = QLabel("")
        self.audio_codec_label = QLabel("")
        self.resolution_label = QLabel("")
        self.fps_label = QLabel("")
        self.audio_channels_label = QLabel("")
        self.sample_rate_label = QLabel("")
        
        technical_layout.addRow("Video Codec:", self.video_codec_label)
        technical_layout.addRow("Audio Codec:", self.audio_codec_label)
        technical_layout.addRow("Resolution:", self.resolution_label)
        technical_layout.addRow("FPS:", self.fps_label)
        technical_layout.addRow("Audio Channels:", self.audio_channels_label)
        technical_layout.addRow("Sample Rate:", self.sample_rate_label)
        
        self.metadata_tabs.addTab(technical_tab, "Technical")
        
        layout.addWidget(self.metadata_tabs)
        
        # Status bar
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #888888;
                font-size: 9px;
                padding: 4px;
            }
        """)
        layout.addWidget(self.status_label)
        
        # Set dark theme
        self.setStyleSheet("""
            MetadataEditorWidget {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
        """)
    
    def _setup_worker(self):
        """Setup the metadata worker thread."""
        self.worker = MetadataWorker()
        self.worker_thread = QThread()
        
        # Move worker to thread
        self.worker.moveToThread(self.worker_thread)
        
        # Connect signals
        self.worker.metadata_loaded.connect(self._on_metadata_loaded)
        self.worker.metadata_saved.connect(self._on_metadata_saved)
        self.worker.error_occurred.connect(self._on_error_occurred)
        
        # Start thread
        self.worker_thread.start()
    
    def _browse_file(self):
        """Browse for media file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Media File",
            "",
            "Media Files (*.mp3 *.wav *.flac *.aac *.ogg *.m4a *.mp4 *.avi *.mkv *.mov *.wmv *.flv *.webm);;All Files (*)"
        )
        
        if file_path:
            self.current_file = file_path
            self.file_label.setText(f"File: {os.path.basename(file_path)}")
            self.load_btn.setEnabled(True)
            self.browse_btn.setText("Change")
            
            # Auto-load metadata
            self._load_metadata()
    
    def _load_metadata(self):
        """Load metadata from current file."""
        if not self.current_file:
            QMessageBox.warning(self, "Warning", "Please select a file first")
            return
        
        self.status_label.setText("Loading metadata...")
        self.load_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        
        # Start metadata loading in worker
        self.worker.load_metadata(self.current_file)
    
    def _save_metadata(self):
        """Save metadata to current file."""
        if not self.current_file:
            QMessageBox.warning(self, "Warning", "Please select a file first")
            return
        
        # Collect metadata from UI
        metadata = {
            'title': self.title_edit.text(),
            'artist': self.artist_edit.text(),
            'album': self.album_edit.text(),
            'date': self.date_edit.text(),
            'genre': self.genre_edit.text(),
            'track': self.track_edit.text(),
            'year': self.year_edit.text(),
            'album_artist': self.album_artist_edit.text(),
            'comment': self.comment_edit.toPlainText(),
            'copyright': self.copyright_edit.text(),
            'language': self.language_edit.text(),
            'description': self.description_edit.toPlainText(),
            'rating': self.rating_spin.value()
        }
        
        self.status_label.setText("Saving metadata...")
        self.save_btn.setEnabled(False)
        
        # Start metadata saving in worker
        self.worker.save_metadata(self.current_file, metadata)
    
    def _on_metadata_loaded(self, metadata):
        """Handle loaded metadata."""
        self.current_metadata = metadata
        self._populate_ui(metadata)
        
        self.status_label.setText("Metadata loaded successfully")
        self.load_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.is_modified = False
    
    def _populate_ui(self, metadata):
        """Populate UI with metadata."""
        # File info
        self.info_file_name.setText(metadata.get('file_name', ''))
        self.info_file_size.setText(self._format_size(metadata.get('file_size', 0)))
        self.info_duration.setText(self._format_duration(metadata.get('duration', 0)))
        self.info_format.setText(metadata.get('format', ''))
        self.info_bitrate.setText(f"{metadata.get('bitrate', 0)} bps")
        
        # Basic metadata
        self.title_edit.setText(metadata.get('title', ''))
        self.artist_edit.setText(metadata.get('artist', ''))
        self.album_edit.setText(metadata.get('album', ''))
        self.date_edit.setText(metadata.get('date', ''))
        self.genre_edit.setText(metadata.get('genre', ''))
        self.track_edit.setText(metadata.get('track', ''))
        self.year_edit.setText(metadata.get('year', ''))
        
        # Advanced metadata
        self.album_artist_edit.setText(metadata.get('album_artist', ''))
        self.comment_edit.setPlainText(metadata.get('comment', ''))
        self.copyright_edit.setText(metadata.get('copyright', ''))
        self.language_edit.setText(metadata.get('language', ''))
        self.description_edit.setPlainText(metadata.get('description', ''))
        self.rating_spin.setValue(metadata.get('rating', 0))
        
        # Technical info
        self.video_codec_label.setText(metadata.get('video_codec', ''))
        self.audio_codec_label.setText(metadata.get('audio_codec', ''))
        
        if metadata.get('width') and metadata.get('height'):
            self.resolution_label.setText(f"{metadata['width']}x{metadata['height']}")
        else:
            self.resolution_label.setText("")
        
        self.fps_label.setText(metadata.get('fps', ''))
        
        if metadata.get('audio_channels'):
            self.audio_channels_label.setText(str(metadata['audio_channels']))
        else:
            self.audio_channels_label.setText("")
        
        if metadata.get('audio_sample_rate'):
            self.sample_rate_label.setText(f"{metadata['audio_sample_rate']} Hz")
        else:
            self.sample_rate_label.setText("")
    
    def _format_size(self, size_bytes):
        """Format file size in human readable format."""
        if size_bytes == 0:
            return "0 B"
        
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
    
    def _format_duration(self, duration_seconds):
        """Format duration in human readable format."""
        if duration_seconds == 0:
            return "00:00:00"
        
        hours = int(duration_seconds // 3600)
        minutes = int((duration_seconds % 3600) // 60)
        seconds = int(duration_seconds % 60)
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def _on_metadata_saved(self, success, message):
        """Handle metadata save result."""
        self.status_label.setText(message)
        self.save_btn.setEnabled(True)
        
        if success:
            self.is_modified = False
            QMessageBox.information(self, "Success", "Metadata saved successfully!")
        else:
            QMessageBox.critical(self, "Error", f"Failed to save metadata: {message}")
    
    def _on_error_occurred(self, error_message):
        """Handle errors from worker."""
        self.status_label.setText(f"Error: {error_message}")
        self.load_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        
        QMessageBox.critical(self, "Error", error_message)
    
    def _mark_modified(self):
        """Mark metadata as modified."""
        if not self.is_modified:
            self.is_modified = True
            self.metadata_changed.emit()
            self.status_label.setText("Modified - Save to apply changes")
    
    def closeEvent(self, event):
        """Handle widget close."""
        if self.worker:
            self.worker.stop_operation()
        
        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait(1000)
        
        event.accept()


class MetadataEditorDialog(QWidget):
    """Dialog wrapper for metadata editor."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Metadata Editor")
        self.setFixedSize(600, 500)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.editor = MetadataEditorWidget()
        layout.addWidget(self.editor)
        
        self.setStyleSheet("""
            MetadataEditorDialog {
                background-color: #1e1e1e;
                color: #ffffff;
            }
        """)
