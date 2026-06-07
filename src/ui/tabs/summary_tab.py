"""Summary Tab for Transcoder - Overview of encoding settings and preview."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QCheckBox, QFrame, QSizePolicy, QPushButton,
    QTextEdit, QToolButton
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap

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

        # FFmpeg Command Preview
        cmd_title_layout = QHBoxLayout()
        cmd_title_layout.addWidget(QLabel("FFmpeg Command:"))
        cmd_title_layout.addStretch()
        
        self.btn_toggle_cmd = QToolButton()
        self.btn_toggle_cmd.setText("▼")
        self.btn_toggle_cmd.setFixedSize(24, 24)
        self.btn_toggle_cmd.setToolTip("Show/Hide FFmpeg command")
        self.btn_toggle_cmd.setCheckable(True)
        self.btn_toggle_cmd.setChecked(True)
        
        cmd_title_layout.addWidget(self.btn_toggle_cmd)
        info_layout.addLayout(cmd_title_layout)
        
        # Command display (collapsible)
        self.cmd_widget = QWidget()
        cmd_layout = QVBoxLayout(self.cmd_widget)
        cmd_layout.setContentsMargins(0, 5, 0, 0)
        
        self.txt_command = QTextEdit()
        self.txt_command.setMaximumHeight(120)
        self.txt_command.setReadOnly(True)
        self.txt_command.setStyleSheet("""
            QTextEdit {
                background-color: #2a2a2a;
                color: #fff;
                border: 1px solid #555;
                border-radius: 4px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
                padding: 8px;
            }
        """)
        
        # Copy button
        copy_layout = QHBoxLayout()
        copy_layout.addStretch()
        self.btn_copy_cmd = QPushButton("Copy Command")
        self.btn_copy_cmd.setFixedSize(100, 24)
        self.btn_copy_cmd.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        copy_layout.addWidget(self.btn_copy_cmd)
        copy_layout.addStretch()
        
        cmd_layout.addWidget(self.txt_command)
        cmd_layout.addLayout(copy_layout)
        
        info_layout.addWidget(self.cmd_widget)

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

        # Video Preview Area with subtitle burn-in overlay
        self.preview_container = QWidget()
        self.preview_container.setFixedSize(480, 270)
        self.preview_container.setStyleSheet("background-color: #111; border: 1px solid #333;")
        
        # Main preview frame
        self.preview_frame = QLabel()
        self.preview_frame.setAlignment(Qt.AlignCenter)
        self.preview_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Subtitle burn-in preview overlay
        self.subtitle_overlay = QLabel("🔥 SUBTITLES BURNED IN")
        self.subtitle_overlay.setAlignment(Qt.AlignBottom | Qt.AlignCenter)
        self.subtitle_overlay.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 0, 0, 0.7);
                color: white;
                padding: 8px 12px;
                font-size: 12px;
                font-weight: bold;
                border-radius: 4px;
                margin: 8px;
            }
        """)
        self.subtitle_overlay.setVisible(False)  # Hidden by default
        
        # Layout for container
        preview_layout = QVBoxLayout(self.preview_container)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.addWidget(self.preview_frame)
        
        # Position overlay at bottom
        overlay_layout = QVBoxLayout()
        overlay_layout.setContentsMargins(0, 0, 0, 8)
        overlay_layout.addStretch()
        overlay_layout.addWidget(self.subtitle_overlay, 0, Qt.AlignCenter)
        
        self.preview_frame.setLayout(overlay_layout)
        
        right_col.addWidget(self.preview_container)

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

        # Connect signals
        self.btn_toggle_cmd.toggled.connect(self._toggle_command_visibility)
        self.btn_copy_cmd.clicked.connect(self._copy_command)

    def _toggle_command_visibility(self, visible: bool):
        """Toggle FFmpeg command visibility."""
        self.cmd_widget.setVisible(visible)
        self.btn_toggle_cmd.setText("▼" if visible else "▶")

    def _copy_command(self):
        """Copy FFmpeg command to clipboard."""
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        command = self.txt_command.toPlainText()
        if command:
            clipboard.setText(command)
            # Show brief feedback
            original_text = self.btn_copy_cmd.text()
            self.btn_copy_cmd.setText("Copied!")
            # Reset after 2 seconds
            from PySide6.QtCore import QTimer
            QTimer.singleShot(2000, lambda: self.btn_copy_cmd.setText(original_text))

    def set_track_info(self, video_info: str, audio_info: str):
        """Update track information label."""
        self.lbl_tracks.setText(f"{video_info}\n{audio_info}")

    def set_loading_state(self, loading: bool):
        """Show/hide loading state for metadata loading."""
        if loading:
            self.lbl_tracks.setText("Loading metadata...")
            self.lbl_size.setText("Loading...")
            self.lbl_name.setEnabled(False)
            self.combo_format.setEnabled(False)
        else:
            self.lbl_tracks.setText("No file selected")
            self.lbl_size.setText("N/A")
            self.lbl_name.setEnabled(True)
            self.combo_format.setEnabled(True)

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

    def set_ffmpeg_command(self, command: str):
        """Update the FFmpeg command preview."""
        if command:
            self.txt_command.setPlainText(command)
        else:
            self.txt_command.setPlainText("No FFmpeg command available")

    def update_subtitle_burn_preview(self, burn_in_enabled: bool):
        """Update the subtitle burn-in preview overlay visibility."""
        self.subtitle_overlay.setVisible(burn_in_enabled)

    def get_settings(self) -> dict:
        """Return format and checkbox settings."""
        return {
            "format": self.combo_format.currentText().lower(),
            "web_optimized": self.chk_web_optimized.isChecked(),
            "align_av": self.chk_align_av.isChecked(),
            "metadata_passthru": self.chk_metadata.isChecked()
        }
