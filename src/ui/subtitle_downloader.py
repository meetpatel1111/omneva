"""Auto-subtitle download - Integrate OpenSubtitles API to fetch subtitles by file hash."""

import os
import hashlib
import requests
import zipfile
import tempfile
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QGroupBox, QMessageBox, QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QProgressBar
)
from PySide6.QtCore import Qt, Signal, QThread, QObject
from src.core.logger import get_logger


class OpenSubtitlesWorker(QObject):
    """Worker for OpenSubtitles API operations."""
    
    # Signals
    search_complete = Signal(list)  # list of subtitle results
    download_complete = Signal(bool, str, str)  # success, message, file_path
    error_occurred = Signal(str)  # error message
    progress_updated = Signal(int)  # progress percentage
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger('opensubtitles_worker')
        self.api_base_url = "https://api.opensubtitles.com/rest/v1"
        self.user_agent = "Omneva v1.4.1"
        self.should_stop = False
        
        # OpenSubtitles API credentials (you can register for free)
        self.api_key = ""  # Users need to provide their own API key
        
    def calculate_file_hash(self, file_path):
        """Calculate OpenSubtitles hash for file."""
        try:
            file_size = os.path.getsize(file_path)
            
            # Read first and last 64KB of file
            chunk_size = 64 * 1024  # 64KB
            
            with open(file_path, 'rb') as f:
                # Read first chunk
                first_chunk = f.read(chunk_size)
                
                # Seek to last chunk
                if file_size > chunk_size:
                    f.seek(file_size - chunk_size)
                    last_chunk = f.read(chunk_size)
                else:
                    last_chunk = first_chunk
            
            # Calculate hash
            combined = first_chunk + str(file_size).encode('utf-8') + last_chunk
            hash_obj = hashlib.md5(combined)
            
            return hash_obj.hexdigest(), file_size
            
        except Exception as e:
            self.logger.error(f"Failed to calculate file hash: {e}")
            return None, None
    
    def search_subtitles(self, file_path, language="en"):
        """Search for subtitles using OpenSubtitles API."""
        try:
            self.should_stop = False
            
            # Calculate file hash
            file_hash, file_size = self.calculate_file_hash(file_path)
            if not file_hash:
                self.error_occurred.emit("Failed to calculate file hash")
                return
            
            self.progress_updated.emit(25)
            
            # Search for subtitles
            if not self.api_key:
                # Use public search (limited results)
                search_url = f"{self.api_base_url}/subtitles"
                params = {
                    'hash': file_hash,
                    'filesize': file_size,
                    'sublanguageid': language
                }
            else:
                # Use authenticated search
                search_url = f"{self.api_base_url}/search"
                headers = {
                    'User-Agent': self.user_agent,
                    'Api-Key': self.api_key
                }
                params = {
                    'hash': file_hash,
                    'filesize': file_size,
                    'sublanguageid': language
                }
            
            self.progress_updated.emit(50)
            
            # Make API request
            if self.api_key:
                response = requests.get(search_url, headers=headers, params=params, timeout=30)
            else:
                response = requests.get(search_url, params=params, timeout=30)
            
            if response.status_code == 200 and not self.should_stop:
                data = response.json()
                
                # Parse results
                subtitles = []
                if 'data' in data:
                    for item in data['data']:
                        subtitle = {
                            'id': item.get('IDSubtitleFile', ''),
                            'language': item.get('LanguageName', ''),
                            'language_code': item.get('SubLanguageID', ''),
                            'download_count': item.get('DownloadCount', 0),
                            'rating': item.get('SubRating', 0),
                            'format': item.get('SubFormat', ''),
                            'cd_count': item.get('SubCDNumber', 0),
                            'release': item.get('ReleaseName', ''),
                            'filename': item.get('SubFileName', ''),
                            'download_url': item.get('DownloadLink', ''),
                            'zip_download_url': item.get('ZipDownloadLink', '')
                        }
                        subtitles.append(subtitle)
                
                self.progress_updated.emit(100)
                self.search_complete.emit(subtitles)
                self.logger.info(f"Found {len(subtitles)} subtitles")
                
            else:
                self.error_occurred.emit(f"API request failed: {response.status_code}")
                
        except Exception as e:
            self.error_occurred.emit(f"Subtitle search error: {e}")
    
    def download_subtitle(self, subtitle_info, output_path):
        """Download subtitle file."""
        try:
            self.should_stop = False
            
            download_url = subtitle_info.get('zip_download_url') or subtitle_info.get('download_url')
            if not download_url:
                self.error_occurred.emit("No download URL available")
                return
            
            self.progress_updated.emit(25)
            
            # Download subtitle file
            headers = {'User-Agent': self.user_agent}
            response = requests.get(download_url, headers=headers, timeout=60)
            
            if response.status_code == 200 and not self.should_stop:
                self.progress_updated.emit(50)
                
                # Handle ZIP files
                if download_url.endswith('.zip'):
                    # Extract from ZIP
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_file:
                        temp_file.write(response.content)
                        temp_zip_path = temp_file.name
                    
                    self.progress_updated.emit(75)
                    
                    # Extract subtitle file
                    with zipfile.ZipFile(temp_zip_path, 'r') as zip_file:
                        # Find subtitle file in ZIP
                        subtitle_files = [f for f in zip_file.namelist() 
                                       if f.lower().endswith(('.srt', '.vtt', '.ass', '.ssa'))]
                        
                        if subtitle_files:
                            subtitle_file = subtitle_files[0]
                            zip_file.extract(subtitle_file, os.path.dirname(output_path))
                            
                            # Rename to desired output path
                            extracted_path = os.path.join(os.path.dirname(output_path), subtitle_file)
                            os.rename(extracted_path, output_path)
                            
                            self.progress_updated.emit(100)
                            self.download_complete.emit(True, "Subtitle downloaded successfully", output_path)
                        else:
                            self.error_occurred.emit("No subtitle file found in ZIP")
                    
                    # Clean up temp file
                    os.unlink(temp_zip_path)
                    
                else:
                    # Direct subtitle file
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    
                    self.progress_updated.emit(100)
                    self.download_complete.emit(True, "Subtitle downloaded successfully", output_path)
                    
            else:
                self.error_occurred.emit(f"Download failed: {response.status_code}")
                
        except Exception as e:
            self.error_occurred.emit(f"Subtitle download error: {e}")
    
    def stop_operation(self):
        """Stop current operation."""
        self.should_stop = True


class SubtitleDownloaderWidget(QWidget):
    """Main subtitle downloader widget."""
    
    subtitle_downloaded = Signal(str)  # subtitle file path
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger('subtitle_downloader')
        
        self.current_file = ""
        self.worker = None
        self.worker_thread = None
        self.search_results = []
        
        self._setup_ui()
        self._setup_worker()
        
        self.logger.debug("Subtitle downloader widget initialized")
    
    def _setup_ui(self):
        """Setup the subtitle downloader UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Header
        header_label = QLabel("Auto Subtitle Downloader")
        header_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #ffffff;
                padding: 8px;
            }
        """)
        layout.addWidget(header_label)
        
        # File selection section
        file_group = QGroupBox("Media File")
        file_group.setStyleSheet("""
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
        
        file_layout = QVBoxLayout()
        
        # File input
        file_input_layout = QHBoxLayout()
        
        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("""
            QLabel {
                color: #cccccc;
                font-size: 10px;
                padding: 4px;
            }
        """)
        file_input_layout.addWidget(self.file_label)
        
        file_input_layout.addStretch()
        
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
        file_input_layout.addWidget(self.browse_btn)
        
        file_layout.addLayout(file_input_layout)
        
        # Language selection
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("Language:"))
        
        self.language_combo = QComboBox()
        self.language_combo.addItems([
            ("en", "English"),
            ("es", "Spanish"),
            ("fr", "French"),
            ("de", "German"),
            ("it", "Italian"),
            ("pt", "Portuguese"),
            ("ru", "Russian"),
            ("ja", "Japanese"),
            ("ko", "Korean"),
            ("zh", "Chinese"),
            ("ar", "Arabic"),
            ("hi", "Hindi"),
            ("all", "All Languages")
        ])
        self.language_combo.setStyleSheet("""
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
        lang_layout.addWidget(self.language_combo)
        lang_layout.addStretch()
        
        file_layout.addLayout(lang_layout)
        
        # Search button
        search_layout = QHBoxLayout()
        
        self.search_btn = QPushButton("🔍 Search Subtitles")
        self.search_btn.setStyleSheet("""
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
        self.search_btn.clicked.connect(self._search_subtitles)
        self.search_btn.setEnabled(False)
        search_layout.addWidget(self.search_btn)
        search_layout.addStretch()
        
        file_layout.addLayout(search_layout)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # API key section
        api_group = QGroupBox("OpenSubtitles API")
        api_group.setStyleSheet("""
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
        
        api_layout = QVBoxLayout()
        
        api_info = QLabel("Get free API key from opensubtitles.com")
        api_info.setStyleSheet("""
            QLabel {
                color: #888888;
                font-size: 9px;
                font-style: italic;
            }
        """)
        api_layout.addWidget(api_info)
        
        api_input_layout = QHBoxLayout()
        api_input_layout.addWidget(QLabel("API Key:"))
        
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setPlaceholderText("Optional - Enter your API key for better results")
        self.api_key_edit.setStyleSheet("""
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
        self.api_key_edit.textChanged.connect(self._update_api_key)
        api_input_layout.addWidget(self.api_key_edit)
        
        api_layout.addLayout(api_input_layout)
        api_group.setLayout(api_layout)
        layout.addWidget(api_group)
        
        # Results section
        results_group = QGroupBox("Search Results")
        results_group.setStyleSheet("""
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
        
        results_layout = QVBoxLayout()
        
        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels([
            "Language", "Format", "Rating", "Downloads", "Release", "Actions"
        ])
        self.results_table.setStyleSheet("""
            QTableWidget {
                background-color: #3a3a3a;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                selection-background-color: #6200ea;
                gridline-color: #555555;
            }
            QTableWidget::header {
                background-color: #2a2a2a;
                color: #ffffff;
                border: none;
                border-bottom: 1px solid #555555;
            }
            QTableWidget::item {
                padding: 4px;
            }
            QTableWidget::item:selected {
                background-color: #6200ea;
                color: #ffffff;
            }
        """)
        
        # Set column widths
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        results_layout.addWidget(self.results_table)
        
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
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
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        # Set dark theme
        self.setStyleSheet("""
            SubtitleDownloaderWidget {
                background-color: #1e1e1e;
                color: #ffffff;
            }
        """)
    
    def _setup_worker(self):
        """Setup the subtitle worker thread."""
        self.worker = OpenSubtitlesWorker()
        self.worker_thread = QThread()
        
        # Move worker to thread
        self.worker.moveToThread(self.worker_thread)
        
        # Connect signals
        self.worker.search_complete.connect(self._on_search_complete)
        self.worker.download_complete.connect(self._on_download_complete)
        self.worker.error_occurred.connect(self._on_error_occurred)
        self.worker.progress_updated.connect(self._on_progress_updated)
        
        # Start thread
        self.worker_thread.start()
    
    def _browse_file(self):
        """Browse for media file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Media File",
            "",
            "Media Files (*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.webm *.mpg *.mpeg);;All Files (*)"
        )
        
        if file_path:
            self.current_file = file_path
            self.file_label.setText(f"File: {os.path.basename(file_path)}")
            self.search_btn.setEnabled(True)
            self.browse_btn.setText("Change")
    
    def _search_subtitles(self):
        """Search for subtitles."""
        if not self.current_file:
            QMessageBox.warning(self, "Warning", "Please select a media file first")
            return
        
        # Get selected language
        lang_code = self.language_combo.currentData() or self.language_combo.currentText().split()[0]
        
        self.status_label.setText("Searching subtitles...")
        self.search_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.results_table.setRowCount(0)
        
        # Start subtitle search in worker
        self.worker.search_subtitles(self.current_file, lang_code)
    
    def _update_api_key(self):
        """Update API key in worker."""
        if self.worker:
            self.worker.api_key = self.api_key_edit.text().strip()
    
    def _on_search_complete(self, subtitles):
        """Handle search results."""
        self.search_results = subtitles
        self._populate_results_table(subtitles)
        
        self.status_label.setText(f"Found {len(subtitles)} subtitles")
        self.search_btn.setEnabled(True)
        self.progress_bar.setValue(100)
    
    def _populate_results_table(self, subtitles):
        """Populate results table with subtitle data."""
        self.results_table.setRowCount(len(subtitles))
        
        for row, subtitle in enumerate(subtitles):
            # Language
            lang_item = QTableWidgetItem(subtitle.get('language', ''))
            lang_item.setData(Qt.UserRole, subtitle)
            self.results_table.setItem(row, 0, lang_item)
            
            # Format
            format_item = QTableWidgetItem(subtitle.get('format', ''))
            self.results_table.setItem(row, 1, format_item)
            
            # Rating
            rating_item = QTableWidgetItem(f"{subtitle.get('rating', 0):.1f}")
            self.results_table.setItem(row, 2, rating_item)
            
            # Downloads
            downloads_item = QTableWidgetItem(str(subtitle.get('download_count', 0)))
            self.results_table.setItem(row, 3, downloads_item)
            
            # Release
            release_item = QTableWidgetItem(subtitle.get('release', ''))
            self.results_table.setItem(row, 4, release_item)
            
            # Actions (Download button)
            download_btn = QPushButton("Download")
            download_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4caf50;
                    color: white;
                    border: none;
                    border-radius: 3px;
                    padding: 4px 8px;
                    font-size: 9px;
                }
                QPushButton:hover {
                    background-color: #66bb6a;
                }
            """)
            download_btn.clicked.connect(lambda checked, s=subtitle: self._download_subtitle(s))
            self.results_table.setCellWidget(row, 5, download_btn)
    
    def _download_subtitle(self, subtitle_info):
        """Download selected subtitle."""
        if not self.current_file:
            QMessageBox.warning(self, "Warning", "Please select a media file first")
            return
        
        # Generate output path
        media_dir = os.path.dirname(self.current_file)
        media_name = os.path.splitext(os.path.basename(self.current_file))[0]
        
        # Determine subtitle format
        subtitle_format = subtitle_info.get('format', 'srt').lower()
        if subtitle_format not in ['srt', 'vtt', 'ass', 'ssa']:
            subtitle_format = 'srt'
        
        subtitle_filename = f"{media_name}.{subtitle_format}"
        subtitle_path = os.path.join(media_dir, subtitle_filename)
        
        # Check if file already exists
        if os.path.exists(subtitle_path):
            reply = QMessageBox.question(
                self, 'File Exists',
                f'Subtitle file "{subtitle_filename}" already exists. Overwrite?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
        
        self.status_label.setText("Downloading subtitle...")
        self.progress_bar.setValue(0)
        
        # Start subtitle download in worker
        self.worker.download_subtitle(subtitle_info, subtitle_path)
    
    def _on_download_complete(self, success, message, file_path):
        """Handle download completion."""
        self.status_label.setText(message)
        self.progress_bar.setValue(100)
        
        if success and file_path:
            self.subtitle_downloaded.emit(file_path)
            QMessageBox.information(self, "Success", f"Subtitle downloaded to: {file_path}")
        else:
            QMessageBox.critical(self, "Error", message)
    
    def _on_error_occurred(self, error_message):
        """Handle errors from worker."""
        self.status_label.setText(f"Error: {error_message}")
        self.search_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        
        QMessageBox.critical(self, "Error", error_message)
    
    def _on_progress_updated(self, progress):
        """Handle progress updates."""
        self.progress_bar.setValue(progress)
    
    def closeEvent(self, event):
        """Handle widget close."""
        if self.worker:
            self.worker.stop_operation()
        
        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait(1000)
        
        event.accept()


class SubtitleDownloaderDialog(QWidget):
    """Dialog wrapper for subtitle downloader."""
    
    subtitle_downloaded = Signal(str)  # subtitle file path
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Auto Subtitle Downloader")
        self.setFixedSize(700, 600)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.downloader = SubtitleDownloaderWidget()
        self.downloader.subtitle_downloaded.connect(self.subtitle_downloaded.emit)
        layout.addWidget(self.downloader)
        
        self.setStyleSheet("""
            SubtitleDownloaderDialog {
                background-color: #1e1e1e;
                color: #ffffff;
            }
        """)
