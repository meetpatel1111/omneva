"""Snapshot Preview Dialog — Show snapshot preview with options."""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from src.core.logger import get_logger


class SnapshotPreviewDialog(QDialog):
    """Dialog showing snapshot preview with options."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Snapshot Preview")
        self.setMinimumSize(600, 500)
        self.setModal(False)
        self.logger = get_logger('snapshot_preview')
        
        self.snapshot_path = None
        self.temp_path = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Snapshot Preview")
        title.setObjectName("dialogTitle")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Preview area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("QScrollArea { background-color: #2b2b2b; border: 1px solid #555; }")
        
        # Preview label
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(400, 300)
        self.preview_label.setStyleSheet("QLabel { background-color: #1e1e1e; color: #888; border: 2px dashed #555; }")
        self.preview_label.setText("No snapshot loaded")
        
        self.scroll_area.setWidget(self.preview_label)
        layout.addWidget(self.scroll_area)
        
        # Info label
        self.info_label = QLabel("")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("color: #888; margin: 5px;")
        layout.addWidget(self.info_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.btn_open_folder = QPushButton("Open Folder")
        self.btn_open_folder.clicked.connect(self._open_folder)
        
        self.btn_copy_path = QPushButton("Copy Path")
        self.btn_copy_path.clicked.connect(self._copy_path)
        
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.clicked.connect(self._delete_snapshot)
        self.btn_delete.setStyleSheet("QPushButton { background-color: #f44336; color: white; }")
        
        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.close)
        
        button_layout.addWidget(self.btn_open_folder)
        button_layout.addWidget(self.btn_copy_path)
        button_layout.addWidget(self.btn_delete)
        button_layout.addStretch()
        button_layout.addWidget(self.btn_close)
        
        layout.addLayout(button_layout)
    
    def show_snapshot(self, snapshot_path: str):
        """Show a snapshot preview."""
        self.snapshot_path = snapshot_path
        
        if not os.path.exists(snapshot_path):
            self.preview_label.setText("Snapshot file not found")
            self.info_label.setText("")
            self.btn_open_folder.setEnabled(False)
            self.btn_copy_path.setEnabled(False)
            self.btn_delete.setEnabled(False)
            return
        
        try:
            # Load and display the image
            pixmap = QPixmap(snapshot_path)
            if pixmap.isNull():
                self.preview_label.setText("Failed to load image")
                self.info_label.setText("")
                self.btn_open_folder.setEnabled(False)
                self.btn_copy_path.setEnabled(False)
                self.btn_delete.setEnabled(False)
                return
            
            # Scale image to fit in dialog while maintaining aspect ratio
            max_size = 600
            if pixmap.width() > max_size or pixmap.height() > max_size:
                pixmap = pixmap.scaled(
                    max_size, max_size, 
                    Qt.AspectRatioMode.KeepAspectRatio, 
                    Qt.TransformationMode.SmoothTransformation
                )
            
            self.preview_label.setPixmap(pixmap)
            self.preview_label.setStyleSheet("")
            
            # Update info
            file_size = os.path.getsize(snapshot_path)
            size_mb = file_size / (1024 * 1024)
            filename = os.path.basename(snapshot_path)
            
            self.info_label.setText(
                f"{filename} • {pixmap.width()}×{pixmap.height()} • {size_mb:.2f} MB"
            )
            
            # Enable buttons
            self.btn_open_folder.setEnabled(True)
            self.btn_copy_path.setEnabled(True)
            self.btn_delete.setEnabled(True)
            
        except Exception as e:
            self.logger.error(f"Error loading snapshot: {e}")
            self.preview_label.setText("Error loading snapshot")
            self.info_label.setText("")
            self.btn_open_folder.setEnabled(False)
            self.btn_copy_path.setEnabled(False)
            self.btn_delete.setEnabled(False)
    
    def _open_folder(self):
        """Open the folder containing the snapshot."""
        if self.snapshot_path and os.path.exists(self.snapshot_path):
            folder = os.path.dirname(self.snapshot_path)
            # Use QFileDialog to open folder (it will open in system file manager)
            QFileDialog.getOpenFileName(self, "Open Folder", folder)
    
    def _copy_path(self):
        """Copy the snapshot path to clipboard."""
        if self.snapshot_path:
            from PySide6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(self.snapshot_path)
            self.info_label.setText("Path copied to clipboard!")
    
    def _delete_snapshot(self):
        """Delete the snapshot file."""
        if not self.snapshot_path:
            return
        
        reply = QMessageBox.question(
            self, 
            "Delete Snapshot", 
            f"Are you sure you want to delete this snapshot?\n\n{os.path.basename(self.snapshot_path)}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                os.remove(self.snapshot_path)
                self.info_label.setText("Snapshot deleted")
                self.preview_label.setText("Snapshot deleted")
                self.preview_label.setStyleSheet("QLabel { background-color: #1e1e1e; color: #888; border: 2px dashed #555; }")
                
                # Disable buttons
                self.btn_open_folder.setEnabled(False)
                self.btn_copy_path.setEnabled(False)
                self.btn_delete.setEnabled(False)
                
                self.snapshot_path = None
                
            except Exception as e:
                self.logger.error(f"Error deleting snapshot: {e}")
                QMessageBox.critical(self, "Error", f"Failed to delete snapshot: {e}")
    
    def closeEvent(self, event):
        """Handle dialog close event."""
        # Clean up any temporary files if needed
        if self.temp_path and os.path.exists(self.temp_path):
            try:
                os.remove(self.temp_path)
            except Exception:
                pass
        
        super().closeEvent(event)
