"""Omneva Application — QApplication setup, theme, and launch."""

import os
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QIcon
from PySide6.QtCore import Qt

from src.main_window import MainWindow
from src.core.logger import get_logger
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
        self.app.setApplicationVersion("1.2.0")
        self.app.setOrganizationName("Omneva")
        self.logger = get_logger('app')
        
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

        # Try to create main window with VLC fallback
        try:
            self.window = MainWindow()
        except Exception as e:
            # Check if this is a VLC-related error
            if "VLC" in str(e) or "vlc" in str(e).lower():
                self._show_vlc_error_dialog(e)
                return
            else:
                # Re-raise non-VLC errors
                raise

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

    def _show_vlc_error_dialog(self, error):
        """Show a user-friendly dialog when VLC is not available."""
        from PySide6.QtWidgets import QMessageBox, QPushButton
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("VLC Not Available")
        msg_box.setText("VLC Media Player could not be initialized.")
        msg_box.setInformativeText(
            "Omneva requires VLC Media Player for media playback. "
            "Please install VLC and restart the application."
        )
        
        # Add detailed error information
        detailed_text = f"Error details:\n{str(error)}\n\n"
        if sys.platform == "win32":
            detailed_text += "Download VLC from: https://www.videolan.org/vlc/\n"
            detailed_text += "Make sure to install the 64-bit version if you're using 64-bit Omneva."
        elif sys.platform == "darwin":
            detailed_text += "Install VLC using: brew install vlc\n"
            detailed_text += "Or download from: https://www.videolan.org/vlc/"
        else:
            detailed_text += "Install VLC using your system package manager:\n"
            detailed_text += "  Ubuntu/Debian: sudo apt install vlc\n"
            detailed_text += "  Fedora: sudo dnf install vlc\n"
            detailed_text += "  Arch: sudo pacman -S vlc"
        
        msg_box.setDetailedText(detailed_text)
        
        # Add a "Download VLC" button
        download_button = QPushButton("Download VLC")
        msg_box.addButton(download_button, QMessageBox.ActionRole)
        msg_box.addButton(QMessageBox.Ok)
        
        msg_box.exec()
        
        # Handle button clicks
        if msg_box.clickedButton() == download_button:
            QDesktopServices.openUrl(QUrl("https://www.videolan.org/vlc/"))

    def set_theme(self, theme_name: str):
        """Load a QSS theme file."""
        theme_dir = os.path.join(os.path.dirname(__file__), "styles")
        theme_file = os.path.join(theme_dir, f"{theme_name}_theme.qss")
        if os.path.exists(theme_file):
            with open(theme_file, "r", encoding="utf-8") as f:
                self.app.setStyleSheet(f.read())
        else:
            self.logger.warning(f"Theme file not found: {theme_file}")

    def run(self) -> int:
        """Show window and start event loop."""
        self.window.show()
        return self.app.exec()
