"""Patch file for adding metadata editor integration to main window.

This file contains the code that should be added to main_window.py
to integrate the metadata editor feature.
"""

# Add this import to the imports section in main_window.py:
# from src.ui.metadata_integration import show_metadata_editor_dialog

# Add this signal connection in _connect_signals method:
# self.act_metadata_editor.triggered.connect(self._show_metadata_editor)

# Add this method to MainWindow class:
def _show_metadata_editor(self):
    """Show metadata editor dialog."""
    from src.ui.metadata_integration import show_metadata_editor_dialog
    show_metadata_editor_dialog(self)
