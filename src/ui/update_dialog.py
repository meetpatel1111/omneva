"""Update Dialog - Interface for displaying update information and changelog."""

import os
import webbrowser
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTextEdit, QGroupBox, QMessageBox, QFileDialog, QFormLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QProgressBar, QCheckBox, QFrame, QSplitter, QToolButton,
    QMenu, QAction, QListWidget, QListWidgetItem, QDialog,
    QDialogButtonBox, QTabWidget, QScrollArea, QSpinBox, QCheckBox
)
from PySide6.QtCore import Qt, Signal, QTimer, QThread, pyqtSignal, QObject
from PySide6.QtGui import QIcon, QPixmap, QFont, QDesktopServices, QUrl
from src.core.logger import get_logger
from src.core.updater import get_update_checker, get_update_downloader, get_update_config


class UpdateDownloadWorker(QObject):
    """Worker for downloading updates."""
    
    progress = pyqtSignal(int)  # download progress
    completed = pyqtSignal(str)  # download completed
    failed = pyqtSignal(str)  # download failed
    
    def __init__(self, url: str, filename: str):
        super().__init__()
        self.url = url
        self.filename = filename
        self.downloader = get_update_downloader()
    
    def start_download(self):
        """Start the download."""
        # Connect signals
        self.downloader.download_progress.connect(self.progress)
        self.downloader.download_completed.connect(self.completed)
        self.downloader.download_failed.connect(self.failed)
        
        # Start download
        self.downloader.download_update(self.url, self.filename)


class UpdateDialog(QDialog):
    """Dialog for displaying update information and changelog."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger('update_dialog')
        
        self.release_info = None
        self.download_worker = None
        
        self._setup_ui()
        
        self.logger.debug("Update dialog initialized")
    
    def _setup_ui(self):
        """Setup the update dialog UI."""
        self.setWindowTitle("Update Available")
        self.setFixedSize(600, 500)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Header
        header_layout = QHBoxLayout()
        
        self.icon_label = QLabel("🔄")
        self.icon_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                padding: 8px;
            }
        """)
        header_layout.addWidget(self.icon_label)
        
        self.title_label = QLabel("A New Version is Available!")
        self.title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #ffffff;
                padding: 8px;
            }
        """)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Version information
        version_group = QGroupBox("Version Information")
        version_group.setStyleSheet("""
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
        
        version_layout = QVBoxLayout()
        
        # Current vs New version
        version_info_layout = QHBoxLayout()
        
        current_label = QLabel("Current Version:")
        current_label.setStyleSheet("color: #cccccc; font-size: 11px;")
        version_info_layout.addWidget(current_label)
        
        self.current_version_label = QLabel("1.4.0")
        self.current_version_label.setStyleSheet("""
            QLabel {
                color: #888888;
                font-weight: bold;
                font-size: 11px;
                padding: 4px 8px;
                background-color: #2a2a2a;
                border-radius: 4px;
            }
        """)
        version_info_layout.addWidget(self.current_version_label)
        
        version_info_layout.addStretch()
        
        arrow_label = QLabel("→")
        arrow_label.setStyleSheet("color: #6200ea; font-size: 16px; font-weight: bold;")
        version_info_layout.addWidget(arrow_label)
        
        version_info_layout.addStretch()
        
        new_label = QLabel("New Version:")
        new_label.setStyleSheet("color: #cccccc; font-size: 11px;")
        version_info_layout.addWidget(new_label)
        
        self.new_version_label = QLabel("")
        self.new_version_label.setStyleSheet("""
            QLabel {
                color: #4caf50;
                font-weight: bold;
                font-size: 11px;
                padding: 4px 8px;
                background-color: #1a3a1a;
                border-radius: 4px;
            }
        """)
        version_info_layout.addWidget(self.new_version_label)
        
        version_layout.addLayout(version_info_layout)
        
        version_group.setLayout(version_layout)
        layout.addWidget(version_group)
        
        # Changelog
        changelog_group = QGroupBox("What's New")
        changelog_group.setStyleSheet("""
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
        
        changelog_layout = QVBoxLayout()
        
        self.changelog_text = QTextEdit()
        self.changelog_text.setReadOnly(True)
        self.changelog_text.setStyleSheet("""
            QTextEdit {
                background-color: #2a2a2a;
                color: #cccccc;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px;
                font-size: 10px;
                line-height: 1.4;
            }
        """)
        changelog_layout.addWidget(self.changelog_text)
        
        changelog_group.setLayout(changelog_layout)
        layout.addWidget(changelog_group)
        
        # Download section
        download_group = QGroupBox("Update Options")
        download_group.setStyleSheet("""
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
        
        download_layout = QVBoxLayout()
        
        # Progress bar
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
                background-color: #4caf50;
                border-radius: 3px;
            }
        """)
        self.progress_bar.setVisible(False)
        download_layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Ready to download")
        self.status_label.setStyleSheet("color: #cccccc; font-size: 10px;")
        download_layout.addWidget(self.status_label)
        
        download_group.setLayout(download_layout)
        layout.addWidget(download_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.download_btn = QPushButton("Download Update")
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
        button_layout.addWidget(self.download_btn)
        
        self.later_btn = QPushButton("Remind Me Later")
        self.later_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #ffa726;
            }
        """)
        self.later_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.later_btn)
        
        self.skip_btn = QPushButton("Skip This Version")
        self.skip_btn.setStyleSheet("""
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
        """)
        self.skip_btn.clicked.connect(self._skip_version)
        button_layout.addWidget(self.skip_btn)
        
        layout.addLayout(button_layout)
        
        # Set dark theme
        self.setStyleSheet("""
            UpdateDialog {
                background-color: #1e1e1e;
                color: #ffffff;
            }
        """)
    
    def set_release_info(self, release_info: Dict[str, Any]):
        """Set release information and update UI."""
        self.release_info = release_info
        
        # Update version labels
        tag_name = release_info.get('tag_name', '').lstrip('v')
        self.new_version_label.setText(tag_name)
        
        # Update changelog
        checker = get_update_checker()
        changelog = checker.get_changelog(release_info)
        self.changelog_text.setPlainText(changelog)
        
        self.logger.info(f"Update dialog set for version {tag_name}")
    
    def _start_download(self):
        """Start downloading the update."""
        if not self.release_info:
            return
        
        try:
            checker = get_update_checker()
            download_url = checker.get_download_url(self.release_info)
            
            if not download_url:
                QMessageBox.critical(self, "Error", "No download URL available for this release.")
                return
            
            # Get filename from URL
            filename = os.path.basename(download_url)
            if not filename or '.' not in filename:
                filename = "omneva_update.exe"
            
            # Update UI
            self.download_btn.setEnabled(False)
            self.later_btn.setEnabled(False)
            self.skip_btn.setEnabled(False)
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.status_label.setText("Downloading update...")
            
            # Start download worker
            self.download_worker = UpdateDownloadWorker(download_url, filename)
            self.download_worker.progress.connect(self._on_download_progress)
            self.download_worker.completed.connect(self._on_download_completed)
            self.download_worker.failed.connect(self._on_download_failed)
            
            # Start download in thread
            thread = QThread()
            self.download_worker.moveToThread(thread)
            thread.started.connect(self.download_worker.start_download)
            thread.start()
            
            self.download_thread = thread
            
            self.logger.info(f"Started download: {download_url}")
            
        except Exception as e:
            self.logger.error(f"Failed to start download: {e}")
            QMessageBox.critical(self, "Error", f"Failed to start download: {e}")
            self._reset_download_ui()
    
    def _on_download_progress(self, progress):
        """Handle download progress."""
        self.progress_bar.setValue(progress)
        self.status_label.setText(f"Downloading update... {progress}%")
    
    def _on_download_completed(self, file_path):
        """Handle download completion."""
        self.progress_bar.setValue(100)
        self.status_label.setText(f"Download completed: {os.path.basename(file_path)}")
        
        # Show completion dialog
        reply = QMessageBox.question(
            self, 'Download Complete',
            f'Update downloaded successfully!\n\nFile: {os.path.basename(file_path)}\n\nWould you like to open the download folder?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            # Open download folder
            download_dir = os.path.dirname(file_path)
            QDesktopServices.openUrl(QUrl.fromLocalFile(download_dir))
        
        # Close dialog
        self.accept()
        
        # Clean up thread
        if hasattr(self, 'download_thread') and self.download_thread:
            self.download_thread.quit()
            self.download_thread.wait()
        
        self.logger.info(f"Download completed: {file_path}")
    
    def _on_download_failed(self, error_message):
        """Handle download failure."""
        self.status_label.setText(f"Download failed: {error_message}")
        QMessageBox.critical(self, "Download Failed", f"Failed to download update:\n{error_message}")
        self._reset_download_ui()
        
        # Clean up thread
        if hasattr(self, 'download_thread') and self.download_thread:
            self.download_thread.quit()
            self.download_thread.wait()
        
        self.logger.error(f"Download failed: {error_message}")
    
    def _reset_download_ui(self):
        """Reset download UI to initial state."""
        self.download_btn.setEnabled(True)
        self.later_btn.setEnabled(True)
        self.skip_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("Ready to download")
    
    def _skip_version(self):
        """Skip this version."""
        if self.release_info:
            config = get_update_config()
            tag_name = self.release_info.get('tag_name', '').lstrip('v')
            config.set('skip_version', tag_name)
            
            self.logger.info(f"Skipped version: {tag_name}")
        
        self.reject()


class NoUpdateDialog(QDialog):
    """Dialog for when no updates are available."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger('no_update_dialog')
        
        self._setup_ui()
        
        self.logger.debug("No update dialog initialized")
    
    def _setup_ui(self):
        """Setup the no update dialog UI."""
        self.setWindowTitle("Check for Updates")
        self.setFixedSize(400, 200)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Message
        message_label = QLabel("✅ You're using the latest stable version of Omneva!")
        message_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #4caf50;
                font-weight: bold;
                padding: 16px;
                text-align: center;
            }
        """)
        message_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(message_label)
        
        # Current version
        version_label = QLabel("Current version: 1.4.0 (Stable)")
        version_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #cccccc;
                padding: 8px;
                text-align: center;
            }
        """)
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)
        
        # Note about stable releases
        note_label = QLabel("Only stable releases are checked for updates")
        note_label.setStyleSheet("""
            QLabel {
                font-size: 10px;
                color: #888888;
                font-style: italic;
                padding: 4px;
                text-align: center;
            }
        """)
        note_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(note_label)
        
        layout.addStretch()
        
        # Close button
        close_btn = QPushButton("OK")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #6200ea;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #7c4dff;
            }
        """)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        # Set dark theme
        self.setStyleSheet("""
            NoUpdateDialog {
                background-color: #1e1e1e;
                color: #ffffff;
            }
        """)


def show_update_dialog(parent, release_info: Dict[str, Any]):
    """Show update dialog with release information."""
    dialog = UpdateDialog(parent)
    dialog.set_release_info(release_info)
    return dialog.exec_()


def show_no_update_dialog(parent):
    """Show dialog when no updates are available."""
    dialog = NoUpdateDialog(parent)
    return dialog.exec_()
