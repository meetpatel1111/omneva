"""Metadata Editor Integration - Helper functions for integrating metadata editor into main window."""

from PySide6.QtWidgets import QDialog
from src.ui.metadata_editor import MetadataEditorWidget
from src.core.logger import get_logger


def show_metadata_editor_dialog(parent):
    """Show metadata editor dialog as a standalone window."""
    logger = get_logger('metadata_integration')
    
    try:
        # Create dialog with metadata editor
        dialog = QDialog(parent)
        dialog.setWindowTitle("Metadata Editor")
        dialog.setFixedSize(600, 500)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #ffffff;
            }
        """)
        
        # Create layout
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Add metadata editor widget
        editor = MetadataEditorWidget(dialog)
        layout.addWidget(editor)
        
        # Show dialog
        dialog.show()
        
        logger.info("Metadata editor dialog opened")
        
    except Exception as e:
        logger.error(f"Failed to open metadata editor: {e}")
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(parent, "Error", f"Failed to open metadata editor: {e}")
