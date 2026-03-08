"""Omneva Application — QApplication setup, theme, and launch."""

import os
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QIcon
from PySide6.QtCore import Qt

from src.main_window import MainWindow


from src.core.utils import get_icon

class OmnevaApp:
    """Main application wrapper."""

    def __init__(self, argv):
        # High DPI support
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

        self.app = QApplication(argv)
        self.app.setApplicationName("Omneva")
        self.app.setApplicationVersion("1.0.0")
        self.app.setOrganizationName("Omneva Team")
        
        # Set Window Icon
        self.app.setWindowIcon(get_icon("icon.svg"))

        # Default font
        font = QFont("Segoe UI", 10)
        if sys.platform == "darwin":
            font = QFont("SF Pro Display", 13)
        elif sys.platform.startswith("linux"):
            font = QFont("Ubuntu", 10)
        self.app.setFont(font)

        # Load dark theme
        self.set_theme("dark")

        # Check dependencies before creating the main window
        self._check_and_download_dependencies()

        # Create main window
        self.window = MainWindow()

    def _check_and_download_dependencies(self):
        """Check for VLC and FFmpeg. Download if missing."""
        from src.core.utils import find_ffmpeg, find_vlc_lib
        from src.ui.download_dialog import DownloadDialog

        needs_vlc = find_vlc_lib() is None
        needs_ffmpeg = find_ffmpeg() is None

        if sys.platform.startswith("linux") and needs_vlc:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(None, "Missing VLC", "VLC Media Player is missing. Omneva requires it for media playback.\n\nPlease install it using your system's package manager (e.g., 'sudo apt install vlc').")
            needs_vlc = False # We don't auto-download VLC on Linux

        if needs_vlc or needs_ffmpeg:
            dialog = DownloadDialog(needs_vlc, needs_ffmpeg)
            # Show the dialog and start the background download
            dialog.show()
            dialog.start_download()
            dialog.exec() # Block until downloaded or canceled

    def set_theme(self, theme_name: str):
        """Load a QSS theme file."""
        theme_dir = os.path.join(os.path.dirname(__file__), "styles")
        theme_file = os.path.join(theme_dir, f"{theme_name}_theme.qss")
        if os.path.exists(theme_file):
            with open(theme_file, "r", encoding="utf-8") as f:
                self.app.setStyleSheet(f.read())
        else:
            print(f"[Omneva] Theme file not found: {theme_file}")

    def run(self) -> int:
        """Show window and start event loop."""
        self.window.show()
        return self.app.exec()
