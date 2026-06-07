"""YouTube-dl / yt-dlp Integration - Download stream panel for online media."""

import os
import subprocess
import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTextEdit, QProgressBar, QComboBox, QCheckBox, QGroupBox,
    QMessageBox, QFileDialog, QTreeWidget, QTreeWidgetItem, QHeaderView,
    QFormLayout
)
from PySide6.QtCore import Qt, Signal, QThread, QObject, QTimer
from src.core.logger import get_logger
from src.core.storage import storage


class YtDlpWorker(QObject):
    """Worker for running yt-dlp operations in background thread."""
    
    # Signals
    progress_updated = Signal(str, int, int)  # operation, current, total
    format_info_ready = Signal(list)  # list of available formats
    download_complete = Signal(str, str)  # success, message
    error_occurred = Signal(str)  # error message
    log_message = Signal(str)  # log output
    
    def __init__(self):
        super().__init__()
        self.process = None
        self.should_stop = False
        self.logger = get_logger('ytdlp_worker')
    
    def check_ytdlp_available(self):
        """Check if yt-dlp is available."""
        try:
            result = subprocess.run(['yt-dlp', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                self.log_message.emit(f"yt-dlp version: {result.stdout.strip()}")
                return True
        except subprocess.TimeoutExpired:
            self.log_message.emit("yt-dlp check timed out")
        except FileNotFoundError:
            self.log_message.emit("yt-dlp not found")
        except Exception as e:
            self.log_message.emit(f"yt-dlp check error: {e}")
        
        return False
    
    def get_formats(self, url):
        """Get available formats for a URL."""
        try:
            self.should_stop = False
            cmd = ['yt-dlp', '--dump-json', '--no-download', url]
            
            self.process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, universal_newlines=True
            )
            
            stdout, stderr = self.process.communicate()
            
            if self.process.returncode == 0 and not self.should_stop:
                # Parse JSON output
                formats = []
                try:
                    data = json.loads(stdout)
                    
                    # Extract format information
                    if 'formats' in data:
                        for fmt in data['formats']:
                            format_info = {
                                'id': fmt.get('format_id', ''),
                                'ext': fmt.get('ext', ''),
                                'resolution': self._get_resolution(fmt),
                                'fps': fmt.get('fps', 0),
                                'filesize': fmt.get('filesize', 0),
                                'vcodec': fmt.get('vcodec', 'none'),
                                'acodec': fmt.get('acodec', 'none'),
                                'quality': fmt.get('quality', ''),
                                'format_note': fmt.get('format_note', ''),
                                'url': fmt.get('url', '')
                            }
                            formats.append(format_info)
                    
                    self.format_info_ready.emit(formats)
                    self.log_message.emit(f"Found {len(formats)} available formats")
                    
                except json.JSONDecodeError as e:
                    self.error_occurred.emit(f"Failed to parse format info: {e}")
            
            else:
                self.error_occurred.emit(f"Failed to get formats: {stderr}")
                
        except Exception as e:
            self.error_occurred.emit(f"Format extraction error: {e}")
    
    def _get_resolution(self, fmt):
        """Extract resolution string from format data."""
        if 'height' in fmt and 'width' in fmt:
            return f"{fmt['width']}x{fmt['height']}"
        elif 'resolution' in fmt:
            return fmt['resolution']
        elif 'format_note' in fmt:
            return fmt['format_note']
        return "unknown"
    
    def download_media(self, url, format_id, output_path, extra_args=None):
        """Download media with specified format."""
        try:
            self.should_stop = False
            
            # Build command
            cmd = ['yt-dlp']
            
            # Add format selection
            if format_id:
                cmd.extend(['-f', format_id])
            
            # Add output path
            cmd.extend(['-o', os.path.join(output_path, '%(title)s.%(ext)s')])
            
            # Add extra arguments
            if extra_args:
                cmd.extend(extra_args)
            
            # Add URL
            cmd.append(url)
            
            self.log_message.emit(f"Starting download: {' '.join(cmd)}")
            
            # Start process
            self.process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, universal_newlines=True
            )
            
            # Monitor progress
            for line in iter(self.process.stdout.readline, ''):
                if self.should_stop:
                    break
                
                self.log_message.emit(line.strip())
                
                # Parse progress information
                if '[download]' in line:
                    try:
                        # Extract percentage
                        if '%' in line:
                            parts = line.split()
                            for part in parts:
                                if part.endswith('%'):
                                    percentage = float(part.rstrip('%'))
                                    self.progress_updated.emit("download", int(percentage), 100)
                                    break
                    except Exception:
                        pass
            
            # Wait for completion
            self.process.wait()
            
            if not self.should_stop and self.process.returncode == 0:
                self.download_complete.emit("success", "Download completed successfully")
                self.log_message.emit("Download completed successfully")
            else:
                error_msg = "Download cancelled" if self.should_stop else "Download failed"
                self.download_complete.emit("error", error_msg)
                self.log_message.emit(error_msg)
                
        except Exception as e:
            self.error_occurred.emit(f"Download error: {e}")
    
    def stop_operation(self):
        """Stop current operation."""
        self.should_stop = True
        if self.process:
            self.process.terminate()
            self.process.wait(timeout=5)


class YouTubeDownloaderPanel(QWidget):
    """Panel for YouTube-dl / yt-dlp integration."""
    
    download_requested = Signal(str)  # URL to play after download
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger('youtube_downloader')
        
        self.worker = None
        self.worker_thread = None
        self.current_url = ""
        self.available_formats = []
        self.download_dir = os.path.join(storage.app_data_dir, 'downloads')
        os.makedirs(self.download_dir, exist_ok=True)
        
        self._setup_ui()
        self._setup_worker()
        
        self.logger.debug("YouTube downloader panel initialized")
    
    def _setup_ui(self):
        """Setup the downloader panel UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Header
        header_label = QLabel("Online Media Downloader")
        header_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #ffffff;
                padding: 8px;
            }
        """)
        layout.addWidget(header_label)
        
        # URL input section
        url_group = QGroupBox("Media URL")
        url_group.setStyleSheet("""
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
        
        url_layout = QVBoxLayout()
        
        # URL input
        url_input_layout = QHBoxLayout()
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://www.youtube.com/watch?v=... or other media URL")
        self.url_edit.setStyleSheet("""
            QLineEdit {
                background-color: #3a3a3a;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px;
                font-size: 11px;
            }
            QLineEdit:focus {
                border-color: #6200ea;
            }
        """)
        self.url_edit.returnPressed.connect(self._analyze_url)
        
        self.analyze_btn = QPushButton("🔍 Analyze")
        self.analyze_btn.setStyleSheet("""
            QPushButton {
                background-color: #6200ea;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #7c4dff;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
        """)
        self.analyze_btn.clicked.connect(self._analyze_url)
        
        url_input_layout.addWidget(self.url_edit)
        url_input_layout.addWidget(self.analyze_btn)
        url_layout.addLayout(url_input_layout)
        
        # Quick presets
        preset_layout = QHBoxLayout()
        preset_label = QLabel("Quick presets:")
        preset_label.setStyleSheet("color: #cccccc; font-size: 10px;")
        preset_layout.addWidget(preset_label)
        
        preset_urls = [
            ("YouTube", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
            ("Vimeo", "https://vimeo.com/123456789"),
            ("Twitch", "https://www.twitch.tv/videos/123456789")
        ]
        
        for name, url in preset_urls:
            preset_btn = QPushButton(name)
            preset_btn.setStyleSheet("""
                QPushButton {
                    background-color: #424242;
                    color: white;
                    border: none;
                    border-radius: 3px;
                    padding: 4px 8px;
                    font-size: 9px;
                }
                QPushButton:hover {
                    background-color: #616161;
                }
            """)
            preset_btn.clicked.connect(lambda checked, u=url: self.url_edit.setText(u))
            preset_layout.addWidget(preset_btn)
        
        preset_layout.addStretch()
        url_layout.addLayout(preset_layout)
        url_group.setLayout(url_layout)
        layout.addWidget(url_group)
        
        # Format selection
        format_group = QGroupBox("Format Selection")
        format_group.setStyleSheet("""
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
        
        format_layout = QVBoxLayout()
        
        # Format tree
        self.format_tree = QTreeWidget()
        self.format_tree.setHeaderLabels(["Format", "Resolution", "Size", "Codec", "FPS"])
        self.format_tree.setStyleSheet("""
            QTreeWidget {
                background-color: #3a3a3a;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                selection-background-color: #6200ea;
            }
            QTreeWidget::header {
                background-color: #2a2a2a;
                color: #ffffff;
                border: none;
                border-bottom: 1px solid #555555;
            }
            QTreeWidget::item {
                padding: 4px;
            }
            QTreeWidget::item:selected {
                background-color: #6200ea;
                color: #ffffff;
            }
        """)
        self.format_tree.setAlternatingRowColors(True)
        
        # Set column widths
        header = self.format_tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        
        format_layout.addWidget(self.format_tree)
        
        # Quick format selection
        quick_format_layout = QHBoxLayout()
        
        self.format_combo = QComboBox()
        self.format_combo.addItems([
            "Best Quality",
            "Best Video Only", 
            "Best Audio Only",
            "720p Video",
            "480p Video",
            "360p Video"
        ])
        self.format_combo.setStyleSheet("""
            QComboBox {
                background-color: #3a3a3a;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid #ffffff;
                margin-right: 4px;
            }
        """)
        
        quick_format_layout.addWidget(QLabel("Quick format:"))
        quick_format_layout.addWidget(self.format_combo)
        quick_format_layout.addStretch()
        
        format_layout.addLayout(quick_format_layout)
        format_group.setLayout(format_layout)
        layout.addWidget(format_group)
        
        # Download options
        options_group = QGroupBox("Download Options")
        options_group.setStyleSheet("""
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
        
        options_layout = QFormLayout()
        
        # Output directory
        self.output_edit = QLineEdit(self.download_dir)
        self.output_edit.setStyleSheet("""
            QLineEdit {
                background-color: #3a3a3a;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px;
            }
        """)
        
        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_edit)
        
        browse_btn = QPushButton("Browse")
        browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #424242;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #616161;
            }
        """)
        browse_btn.clicked.connect(self._browse_output_dir)
        output_layout.addWidget(browse_btn)
        
        options_layout.addRow("Output directory:", output_layout)
        
        # Additional options
        self.audio_only_cb = QCheckBox("Audio only")
        self.audio_only_cb.setStyleSheet("color: #ffffff;")
        options_layout.addRow("", self.audio_only_cb)
        
        self.subtitles_cb = QCheckBox("Download subtitles")
        self.subtitles_cb.setStyleSheet("color: #ffffff;")
        options_layout.addRow("", self.subtitles_cb)
        
        self.play_after_cb = QCheckBox("Play after download")
        self.play_after_cb.setStyleSheet("color: #ffffff;")
        self.play_after_cb.setChecked(True)
        options_layout.addRow("", self.play_after_cb)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Progress section
        progress_group = QGroupBox("Progress")
        progress_group.setStyleSheet("""
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
        
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #3a3a3a;
                border: 1px solid #555555;
                border-radius: 4px;
                text-align: center;
                color: #ffffff;
            }
            QProgressBar::chunk {
                background-color: #6200ea;
                border-radius: 3px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #cccccc; font-size: 10px;")
        progress_layout.addWidget(self.status_label)
        
        # Log output
        self.log_edit = QTextEdit()
        self.log_edit.setMaximumHeight(100)
        self.log_edit.setStyleSheet("""
            QTextEdit {
                background-color: #2a2a2a;
                color: #888888;
                border: 1px solid #555555;
                border-radius: 4px;
                font-family: 'Consolas', monospace;
                font-size: 9px;
            }
        """)
        progress_layout.addWidget(self.log_edit)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.download_btn = QPushButton("⬇ Download")
        self.download_btn.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 11px;
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
        self.download_btn.clicked.connect(self._start_download)
        self.download_btn.setEnabled(False)
        
        self.cancel_btn = QPushButton("✕ Cancel")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #ef5350;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
        """)
        self.cancel_btn.clicked.connect(self._cancel_download)
        self.cancel_btn.setEnabled(False)
        
        button_layout.addWidget(self.download_btn)
        button_layout.addWidget(self.cancel_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Set dark theme for the panel
        self.setStyleSheet("""
            YouTubeDownloaderPanel {
                background-color: #1e1e1e;
                color: #ffffff;
            }
        """)
    
    def _setup_worker(self):
        """Setup the yt-dlp worker thread."""
        self.worker = YtDlpWorker()
        self.worker_thread = QThread()
        
        # Move worker to thread
        self.worker.moveToThread(self.worker_thread)
        
        # Connect signals
        self.worker.progress_updated.connect(self._on_progress_updated)
        self.worker.format_info_ready.connect(self._on_formats_ready)
        self.worker.download_complete.connect(self._on_download_complete)
        self.worker.error_occurred.connect(self._on_error_occurred)
        self.worker.log_message.connect(self._on_log_message)
        
        # Start thread
        self.worker_thread.start()
        
        # Check if yt-dlp is available
        QTimer.singleShot(100, self._check_ytdlp)
    
    def _check_ytdlp(self):
        """Check if yt-dlp is available."""
        if self.worker.check_ytdlp_available():
            self.status_label.setText("yt-dlp ready")
            self.analyze_btn.setEnabled(True)
        else:
            self.status_label.setText("yt-dlp not found - please install yt-dlp")
            self.analyze_btn.setEnabled(False)
            self.log_edit.append("yt-dlp is required for download functionality")
            self.log_edit.append("Install with: pip install yt-dlp")
    
    def _analyze_url(self):
        """Analyze URL and get available formats."""
        url = self.url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "Warning", "Please enter a URL to analyze")
            return
        
        self.current_url = url
        self.status_label.setText("Analyzing...")
        self.analyze_btn.setEnabled(False)
        self.format_tree.clear()
        self.available_formats = []
        
        # Start format extraction in worker
        self.worker.get_formats(url)
    
    def _on_formats_ready(self, formats):
        """Handle available formats from worker."""
        self.available_formats = formats
        self._populate_format_tree(formats)
        
        # Enable download button
        self.download_btn.setEnabled(True)
        self.analyze_btn.setEnabled(True)
        self.status_label.setText(f"Found {len(formats)} formats")
        
        self.log_edit.append(f"Found {len(formats)} available formats")
    
    def _populate_format_tree(self, formats):
        """Populate format tree with available formats."""
        self.format_tree.clear()
        
        # Group formats by type
        video_formats = []
        audio_formats = []
        combined_formats = []
        
        for fmt in formats:
            if fmt['vcodec'] != 'none' and fmt['acodec'] != 'none':
                combined_formats.append(fmt)
            elif fmt['vcodec'] != 'none':
                video_formats.append(fmt)
            elif fmt['acodec'] != 'none':
                audio_formats.append(fmt)
        
        # Add combined formats
        if combined_formats:
            combined_item = QTreeWidgetItem(["Combined Formats", "", "", "", ""])
            combined_item.setExpanded(True)
            self.format_tree.addTopLevelItem(combined_item)
            
            for fmt in sorted(combined_formats, key=lambda x: x.get('filesize', 0), reverse=True):
                item = QTreeWidgetItem([
                    fmt['id'],
                    fmt['resolution'],
                    self._format_size(fmt['filesize']),
                    f"{fmt['vcodec']}/{fmt['acodec']}",
                    str(fmt['fps']) if fmt['fps'] else ""
                ])
                item.setData(0, Qt.UserRole, fmt)
                combined_item.addChild(item)
        
        # Add video-only formats
        if video_formats:
            video_item = QTreeWidgetItem(["Video Only", "", "", "", ""])
            video_item.setExpanded(True)
            self.format_tree.addTopLevelItem(video_item)
            
            for fmt in sorted(video_formats, key=lambda x: x.get('filesize', 0), reverse=True):
                item = QTreeWidgetItem([
                    fmt['id'],
                    fmt['resolution'],
                    self._format_size(fmt['filesize']),
                    fmt['vcodec'],
                    str(fmt['fps']) if fmt['fps'] else ""
                ])
                item.setData(0, Qt.UserRole, fmt)
                video_item.addChild(item)
        
        # Add audio-only formats
        if audio_formats:
            audio_item = QTreeWidgetItem(["Audio Only", "", "", "", ""])
            audio_item.setExpanded(True)
            self.format_tree.addTopLevelItem(audio_item)
            
            for fmt in sorted(audio_formats, key=lambda x: x.get('filesize', 0), reverse=True):
                item = QTreeWidgetItem([
                    fmt['id'],
                    "Audio",
                    self._format_size(fmt['filesize']),
                    fmt['acodec'],
                    ""
                ])
                item.setData(0, Qt.UserRole, fmt)
                audio_item.addChild(item)
    
    def _format_size(self, size_bytes):
        """Format file size in human readable format."""
        if size_bytes == 0:
            return "Unknown"
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def _start_download(self):
        """Start download process."""
        if not self.current_url:
            QMessageBox.warning(self, "Warning", "Please analyze a URL first")
            return
        
        # Get selected format
        format_id = self._get_selected_format()
        if not format_id:
            QMessageBox.warning(self, "Warning", "Please select a format")
            return
        
        # Get output directory
        output_dir = self.output_edit.text()
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Cannot create output directory: {e}")
                return
        
        # Build extra arguments
        extra_args = []
        
        if self.audio_only_cb.isChecked():
            extra_args.extend(['-x', '--audio-format', 'best'])
        
        if self.subtitles_cb.isChecked():
            extra_args.extend(['--write-sub', '--write-auto-sub'])
        
        # Start download
        self.status_label.setText("Downloading...")
        self.download_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        
        self.worker.download_media(self.current_url, format_id, output_dir, extra_args)
    
    def _get_selected_format(self):
        """Get selected format ID."""
        selected_items = self.format_tree.selectedItems()
        if selected_items:
            item = selected_items[0]
            format_data = item.data(0, Qt.UserRole)
            if format_data:
                return format_data['id']
        
        # Fallback to quick format selection
        quick_format = self.format_combo.currentText()
        format_map = {
            "Best Quality": "best",
            "Best Video Only": "bestvideo",
            "Best Audio Only": "bestaudio",
            "720p Video": "best[height<=720]",
            "480p Video": "best[height<=480]",
            "360p Video": "best[height<=360]"
        }
        return format_map.get(quick_format, "best")
    
    def _cancel_download(self):
        """Cancel current download."""
        if self.worker:
            self.worker.stop_operation()
            self.status_label.setText("Cancelling...")
            self.cancel_btn.setEnabled(False)
    
    def _browse_output_dir(self):
        """Browse for output directory."""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", self.output_edit.text()
        )
        if directory:
            self.output_edit.setText(directory)
    
    def _on_progress_updated(self, operation, current, total):
        """Handle progress updates."""
        if operation == "download":
            self.progress_bar.setValue(current)
            self.status_label.setText(f"Downloading... {current}%")
    
    def _on_download_complete(self, status, message):
        """Handle download completion."""
        self.status_label.setText(message)
        self.download_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        
        if status == "success" and self.play_after_cb.isChecked():
            # Find downloaded file and play it
            self._find_and_play_downloaded()
    
    def _find_and_play_downloaded(self):
        """Find the most recently downloaded file and play it."""
        try:
            # Get most recent file in download directory
            files = []
            for filename in os.listdir(self.download_dir):
                filepath = os.path.join(self.download_dir, filename)
                if os.path.isfile(filepath):
                    files.append((filepath, os.path.getmtime(filepath)))
            
            if files:
                # Sort by modification time and get the most recent
                files.sort(key=lambda x: x[1], reverse=True)
                latest_file = files[0][0]
                
                self.log_edit.append(f"Playing downloaded file: {latest_file}")
                self.download_requested.emit(latest_file)
                
        except Exception as e:
            self.logger.error(f"Failed to find downloaded file: {e}")
    
    def _on_error_occurred(self, error_message):
        """Handle errors from worker."""
        self.status_label.setText(f"Error: {error_message}")
        self.download_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.log_edit.append(f"ERROR: {error_message}")
        
        QMessageBox.critical(self, "Download Error", error_message)
    
    def _on_log_message(self, message):
        """Handle log messages."""
        self.log_edit.append(message)
        
        # Auto-scroll to bottom
        scrollbar = self.log_edit.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def closeEvent(self, event):
        """Handle panel close."""
        if self.worker:
            self.worker.stop_operation()
        
        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait(1000)
        
        event.accept()
