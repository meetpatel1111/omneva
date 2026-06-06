"""Patch file for adding subtitle downloader integration to main window.

This file contains the code that should be added to main_window.py
to integrate the subtitle downloader feature.
"""

# Add this import to the imports section in main_window.py:
# from src.ui.subtitle_integration import show_subtitle_downloader_dialog

# Add this signal connection in _connect_signals method:
# self.act_subtitle_downloader.triggered.connect(self._show_subtitle_downloader)

# Add this method to MainWindow class:
def _show_subtitle_downloader(self):
    """Show subtitle downloader dialog."""
    from src.ui.subtitle_integration import show_subtitle_downloader_dialog
    show_subtitle_downloader_dialog(self)
