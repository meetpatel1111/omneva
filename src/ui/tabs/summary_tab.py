"""Summary Tab for Transcoder - Overview of encoding settings and preview."""

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QCheckBox, QFrame, QScrollArea, QSizePolicy, QPushButton
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QImage

class SummaryTab(QWidget):
    """
    Summary tab matching HandBrake's layout.
    Displays Format selection, basic options, track summary, and video preview.
    """
    format_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("summaryTab")
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(20)

        # ─── Left Column: Settings & Info ───────────────────
        left_col = QVBoxLayout()
        left_col.setSpacing(15)
        left_col.setAlignment(Qt.AlignTop)

        # Format Section
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Format:"))
        
        self.combo_format = QComboBox()
        self.combo_format.addItems(["MP4", "MKV", "WebM", "AVI", "TS", "PS", "Ogg", "ASF"])

        self.combo_format.setFixedWidth(120)
        format_layout.addWidget(self.combo_format)
        format_layout.addStretch()
        left_col.addLayout(format_layout)

        # Checkboxes
        self.chk_web_optimized = QCheckBox("Web Optimized")
        self.chk_web_optimized.setToolTip("Optimize for streaming (faststart)")
        self.chk_align_av = QCheckBox("Align A/V Start")
        self.chk_ipod = QCheckBox("iPod 5G Support") # Legacy, but requested
        self.chk_metadata = QCheckBox("Passthru Common Metadata")
        self.chk_metadata.setChecked(True)

        left_col.addWidget(self.chk_web_optimized)
        left_col.addWidget(self.chk_align_av)
        left_col.addWidget(self.chk_ipod)
        left_col.addWidget(self.chk_metadata)

        # Separator
        line1 = QFrame()
        line1.setFrameShape(QFrame.HLine)
        line1.setFrameShadow(QFrame.Sunken)
        left_col.addWidget(line1)

        # Info Section (Tracks, Filters, Size)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(10)

        # Tracks
        lbl_tracks_title = QLabel("Tracks:")
        lbl_tracks_title.setStyleSheet("font-weight: bold;")
        self.lbl_tracks = QLabel("No source selected")
        self.lbl_tracks.setWordWrap(True)
        self.lbl_tracks.setStyleSheet("color: #aaa;")
        
        info_layout.addWidget(lbl_tracks_title)
        info_layout.addWidget(self.lbl_tracks)

        # Filters
        lbl_filters_title = QLabel("Filters:")
        lbl_filters_title.setStyleSheet("font-weight: bold;")
        self.lbl_filters = QLabel("None")
        self.lbl_filters.setStyleSheet("color: #aaa;")
        
        info_layout.addWidget(lbl_filters_title)
        info_layout.addWidget(self.lbl_filters)

        # Size
        lbl_size_title = QLabel("Size:")
        lbl_size_title.setStyleSheet("font-weight: bold;")
        self.lbl_size = QLabel("0x0 storage, 0x0 display")
        self.lbl_size.setStyleSheet("color: #aaa;")
        
        info_layout.addWidget(lbl_size_title)
        info_layout.addWidget(self.lbl_size)

        left_col.addLayout(info_layout)
        left_col.addStretch() # Push everything up

        # Wrap left column in a frame or just add to main
        left_widget = QWidget()
        left_widget.setLayout(left_col)
        left_widget.setFixedWidth(300) # Fixed width for settings sidebar
        
        main_layout.addWidget(left_widget)

        # ─── Right Column: Preview ──────────────────────────
        right_col = QVBoxLayout()
        right_col.setContentsMargins(0, 0, 0, 0)
        
        preview_header = QLabel("Source Preview:")
        right_col.addWidget(preview_header)

        # Video Preview Area
        self.preview_frame = QLabel()
        self.preview_frame.setAlignment(Qt.AlignCenter)
        self.preview_frame.setStyleSheet("background-color: #111; border: 1px solid #333;")
        self.preview_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.preview_frame.setMinimumSize(480, 270)
        
        right_col.addWidget(self.preview_frame)

        # Preview Controls
        ctrl_layout = QHBoxLayout()
        ctrl_layout.addStretch()
        
        self.btn_prev_preview = QPushButton("<")
        self.btn_prev_preview.setFixedSize(30, 24)
        
        self.lbl_preview_count = QLabel("Preview 0 of 0")
        self.lbl_preview_count.setStyleSheet("background-color: #222; padding: 2px 8px; border-radius: 4px;")

        self.btn_next_preview = QPushButton(">")
        self.btn_next_preview.setFixedSize(30, 24)

        ctrl_layout.addWidget(self.btn_prev_preview)
        ctrl_layout.addWidget(self.lbl_preview_count)
        ctrl_layout.addWidget(self.btn_next_preview)
        ctrl_layout.addStretch()
        
        right_col.addLayout(ctrl_layout)

        main_layout.addLayout(right_col)

    def set_track_info(self, video_info: str, audio_info: str):
        """Update track information label."""
        self.lbl_tracks.setText(f"{video_info}\n{audio_info}")

    def set_size_info(self, width: int, height: int):
        """Update resolution info."""
        self.lbl_size.setText(f"{width}x{height} storage, {width}x{height} display")

    def set_preview_image(self, pixmap: QPixmap):
        """Update the preview image."""
        if not pixmap.isNull():
            # Scale to fit while keeping aspect ratio
            scaled = pixmap.scaled(
                self.preview_frame.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.preview_frame.setPixmap(scaled)
        else:
            self.preview_frame.setText("No Preview Available")

    def get_settings(self) -> dict:
        """Return format and checkbox settings."""
        return {
            "format": self.combo_format.currentText().lower(),
            "web_optimized": self.chk_web_optimized.isChecked(),
            "align_av": self.chk_align_av.isChecked(),
            "metadata_passthru": self.chk_metadata.isChecked()
        }
