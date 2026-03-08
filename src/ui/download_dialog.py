"""Download progress dialog for fetching missing dependencies."""

import os
import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton, QHBoxLayout,
    QMessageBox
)
from PySide6.QtCore import Qt
from src.core.downloader import DependencyDownloader


class DownloadDialog(QDialog):
    """A dialog to display download progress for missing dependencies."""

    def __init__(self, needs_vlc: bool, needs_ffmpeg: bool, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Downloading Dependencies")
        self.setFixedSize(450, 200)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.needs_vlc = needs_vlc
        self.needs_ffmpeg = needs_ffmpeg

        self._setup_ui()

        # Setup downloader
        self.downloader = DependencyDownloader()
        self.downloader.progress_update.connect(self._on_progress_update)
        self.downloader.status_update.connect(self._on_status_update)
        self.downloader.error_occurred.connect(self._on_error)
        self.downloader.all_finished.connect(self._on_finished)

        # Dictionary to track progress per task
        self.task_progress = {}

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel("<h2>Omneva Needs Additional Dependencies</h2>")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        msg = []
        if self.needs_vlc: msg.append("VLC Media Player")
        if self.needs_ffmpeg: msg.append("FFmpeg & FFprobe")
        
        msg_str = '\n- '.join(msg)
        info = QLabel(f"Downloading required files to play and transcode media:\n- {msg_str}\n\nThis will only happen once.")
        info.setWordWrap(True)
        layout.addWidget(info)

        self.lbl_status = QLabel("Preparing to download...")
        self.lbl_status.setObjectName("statusLabel")
        layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_cancel.setEnabled(False) # Disable cancel for simplicity since threads are hard to interrupt safely here

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def start_download(self):
        """Start the download process."""
        self.downloader.start_downloads(self.needs_vlc, self.needs_ffmpeg)

    def _on_status_update(self, msg: str):
        self.lbl_status.setText(msg)

    def _on_progress_update(self, task_name: str, bytes_read: int, total_bytes: int):
        self.task_progress[task_name] = (bytes_read, total_bytes)
        
        # Calculate combined progress
        total_read = 0
        total_expected = 0
        indeterminate = False

        for name, (read, expected) in self.task_progress.items():
            if expected == 0:
                indeterminate = True
                break
            total_read += read
            total_expected += expected

        if indeterminate:
            self.progress_bar.setRange(0, 0) # Indeterminate mode (e.g. extracting)
            self.progress_bar.setFormat("Extracting...")
        elif total_expected > 0:
            self.progress_bar.setRange(0, 100)
            percent = int((total_read / total_expected) * 100)
            self.progress_bar.setValue(percent)
            self.progress_bar.setFormat(f"%p%  ({total_read // (1024*1024)} MB / {total_expected // (1024*1024)} MB)")

    def _on_error(self, error_msg: str):
        QMessageBox.critical(self, "Download Error", f"An error occurred while downloading dependencies:\n{error_msg}")
        self.reject()

    def _on_finished(self):
        if not self.downloader.has_errors:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(100)
            self.lbl_status.setText("All downloads complete!")
            self.accept()
        else:
            self.reject()
