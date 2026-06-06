"""Subtitle Downloader Integration - Helper functions for integrating subtitle downloader into main window."""

from PySide6.QtWidgets import QDialog
from src.ui.subtitle_downloader import SubtitleDownloaderWidget
from src.core.logger import get_logger


def show_subtitle_downloader_dialog(parent):
    """Show subtitle downloader dialog as a standalone window."""
    logger = get_logger('subtitle_integration')
    
    try:
        # Create dialog with subtitle downloader
        dialog = QDialog(parent)
        dialog.setWindowTitle("Auto Subtitle Downloader")
        dialog.setFixedSize(700, 600)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #ffffff;
            }
        """)
        
        # Create layout
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Add subtitle downloader widget
        downloader = SubtitleDownloaderWidget(dialog)
        layout.addWidget(downloader)
        
        # Show dialog
        dialog.show()
        
        logger.info("Subtitle downloader dialog opened")
        
    except Exception as e:
        logger.error(f"Failed to open subtitle downloader: {e}")
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(parent, "Error", f"Failed to open subtitle downloader: {e}")
