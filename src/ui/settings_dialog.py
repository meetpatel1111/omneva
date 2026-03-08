"""Settings Dialog — Configure application preferences."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QFormLayout, QDialogButtonBox,
    QGroupBox
)
from src.core.storage import storage

class SettingsDialog(QDialog):
    """Dialog to configure FFmpeg/FFprobe paths and other settings."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.setMinimumWidth(500)
        self.settings = storage.get_settings()
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # ─── External Tools ─────────────────────────────────
        tools_group = QGroupBox("External Tools")
        form = QFormLayout(tools_group)

        # FFmpeg Path
        self.txt_ffmpeg = QLineEdit()
        self.btn_ffmpeg = QPushButton("Browse...")
        self.btn_ffmpeg.clicked.connect(lambda: self._browse_file(self.txt_ffmpeg))
        
        row_ffmpeg = QHBoxLayout()
        row_ffmpeg.addWidget(self.txt_ffmpeg)
        row_ffmpeg.addWidget(self.btn_ffmpeg)
        form.addRow("FFmpeg Executable:", row_ffmpeg)

        # FFprobe Path
        self.txt_ffprobe = QLineEdit()
        self.btn_ffprobe = QPushButton("Browse...")
        self.btn_ffprobe.clicked.connect(lambda: self._browse_file(self.txt_ffprobe))

        row_ffprobe = QHBoxLayout()
        row_ffprobe.addWidget(self.txt_ffprobe)
        row_ffprobe.addWidget(self.btn_ffprobe)
        form.addRow("FFprobe Executable:", row_ffprobe)

        layout.addWidget(tools_group)

        # ─── Defaults ───────────────────────────────────────
        defaults_group = QGroupBox("Defaults")
        d_form = QFormLayout(defaults_group)

        # Output Directory
        self.txt_output_dir = QLineEdit()
        self.btn_output_dir = QPushButton("Browse...")
        self.btn_output_dir.clicked.connect(self._browse_output_dir)
        
        row_out = QHBoxLayout()
        row_out.addWidget(self.txt_output_dir)
        row_out.addWidget(self.btn_output_dir)
        d_form.addRow("Default Output Directory:", row_out)

        # Default Codecs
        self.txt_audio_codec = QLineEdit()
        self.txt_audio_codec.setPlaceholderText("e.g. aac")
        d_form.addRow("Default Audio Codec:", self.txt_audio_codec)

        self.txt_video_codec = QLineEdit()
        self.txt_video_codec.setPlaceholderText("e.g. h264")
        d_form.addRow("Default Video Codec:", self.txt_video_codec)

        layout.addWidget(defaults_group)

        # ─── Buttons ────────────────────────────────────────
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.buttons.accepted.connect(self._save_settings)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def _browse_file(self, line_edit: QLineEdit):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Executable", "", "Executables (*.exe);;All Files (*)"
        )
        if path:
            line_edit.setText(path)

    def _browse_output_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Select Default Output Directory")
        if path:
            self.txt_output_dir.setText(path)

    def _load_settings(self):
        self.txt_ffmpeg.setText(self.settings.value("ffmpeg_path", ""))
        self.txt_ffprobe.setText(self.settings.value("ffprobe_path", ""))
        self.txt_output_dir.setText(self.settings.value("default_output_dir", ""))
        self.txt_audio_codec.setText(self.settings.value("default_audio_codec", ""))
        self.txt_video_codec.setText(self.settings.value("default_video_codec", ""))

    def _save_settings(self):
        self.settings.setValue("ffmpeg_path", self.txt_ffmpeg.text())
        self.settings.setValue("ffprobe_path", self.txt_ffprobe.text())
        self.settings.setValue("default_output_dir", self.txt_output_dir.text())
        self.settings.setValue("default_audio_codec", self.txt_audio_codec.text())
        self.settings.setValue("default_video_codec", self.txt_video_codec.text())
        self.accept()
