"""Converter Panel — Quick format conversion with drag-and-drop."""

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QFileDialog, QFrame, QProgressBar, QLineEdit
)
from PySide6.QtCore import Qt, Signal, QSettings

from src.core.ffmpeg_service import FFmpegService, PRESETS
from src.core.ffprobe_service import FFprobeService
from src.core.queue_manager import QueueManager
from src.core.storage import storage
from src.core.utils import is_media_file


# Quick conversion targets
QUICK_PRESETS = {
    "WAV (Uncompressed)": {"ext": ".wav", "args": ["-vn", "-c:a", "pcm_s16le"]},
    "Portable (MPEG-1)": {"ext": ".mpg", "args": ["-c:v", "mpeg1video", "-q:v", "4", "-c:a", "mp2", "-b:a", "128k", "-f", "mpeg"]},
    "DVD (MPEG-2)": {"ext": ".mpg", "args": ["-c:v", "mpeg2video", "-q:v", "2", "-c:a", "ac3", "-b:a", "192k", "-f", "vob"]},
    "AVI (Legacy)": {"ext": ".avi", "args": ["-c:v", "libx264", "-crf", "23", "-c:a", "mp3"]},
    "OGG (Theora/Vorbis)": {"ext": ".ogg", "args": ["-c:v", "libtheora", "-q:v", "6", "-c:a", "libvorbis", "-q:a", "5"]},
}



class DropZone(QFrame):
    """Drag-and-drop zone for files."""

    files_dropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(120)

        layout = QVBoxLayout(self)
        self.label = QLabel("📥\n\nDrag & drop files here\nor click Browse below")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setObjectName("dropLabel")
        layout.addWidget(self.label)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setProperty("dragOver", True)
            self.style().polish(self)

    def dragLeaveEvent(self, event):
        self.setProperty("dragOver", False)
        self.style().polish(self)

    def dropEvent(self, event):
        self.setProperty("dragOver", False)
        self.style().polish(self)
        paths = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isfile(path) and is_media_file(path):
                paths.append(path)
        if paths:
            self.files_dropped.emit(paths)

    def set_files(self, filenames: list[str]):
        if filenames:
            text = "\n".join(f"📄 {f}" for f in filenames[:5])
            if len(filenames) > 5:
                text += f"\n... and {len(filenames) - 5} more"
            self.label.setText(text)
        else:
            self.label.setText("📥\n\nDrag & drop files here\nor click Browse below")


class ConverterPanel(QWidget):
    """Quick format converter with drag-and-drop input."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("converterPanel")

        self.settings = storage.get_settings()
        self.ffmpeg = FFmpegService()
        self.ffprobe = FFprobeService()
        self.queue = QueueManager(self.ffmpeg)
        self._input_files: list[str] = []

        self._setup_ui()
        self._load_defaults()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Header
        header = QLabel("🔄  Quick Converter")
        header.setObjectName("panelHeader")
        layout.addWidget(header)

        desc = QLabel("Convert media files to different formats with a single click.")
        desc.setObjectName("panelDesc")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Drop zone
        self.drop_zone = DropZone()
        layout.addWidget(self.drop_zone)

        # Browse button
        self.btn_browse = QPushButton("📂 Browse Files")
        self.btn_browse.setObjectName("actionBtn")
        self.btn_browse.setFixedHeight(34)
        layout.addWidget(self.btn_browse)

        # Format selection
        fmt_row = QHBoxLayout()
        fmt_row.addWidget(QLabel("Convert to:"))
        self.format_combo = QComboBox()
        self.format_combo.setObjectName("formatCombo")
        self.format_combo.setFixedHeight(32)
        for name in QUICK_PRESETS:
            self.format_combo.addItem(name)
        fmt_row.addWidget(self.format_combo, 1)
        layout.addLayout(fmt_row)

        # Output directory
        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("Save to:"))
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("Same as source folder")
        self.output_edit.setFixedHeight(32)
        self.btn_output = QPushButton("📁")
        self.btn_output.setFixedSize(32, 32)
        out_row.addWidget(self.output_edit, 1)
        out_row.addWidget(self.btn_output)
        layout.addLayout(out_row)

        # Convert button
        self.btn_convert = QPushButton("⚡  Convert Now")
        self.btn_convert.setObjectName("startBtn")
        self.btn_convert.setFixedHeight(42)
        layout.addWidget(self.btn_convert)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("convertProgress")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        self.lbl_status = QLabel("")
        self.lbl_status.setObjectName("convertStatus")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_status)

        layout.addStretch(1)

    def _connect_signals(self):
        self.drop_zone.files_dropped.connect(self._set_files)
        self.btn_browse.clicked.connect(self._browse_files)
        self.btn_output.clicked.connect(self._pick_output_dir)
        self.btn_convert.clicked.connect(self._start_conversion)

        self.queue.job_progress.connect(self._on_progress)
        self.queue.job_completed.connect(self._on_completed)
        self.queue.job_failed.connect(self._on_failed)
        self.queue.queue_empty.connect(self._on_all_done)

    def _set_files(self, paths: list[str]):
        self._input_files = paths
        self.drop_zone.set_files([os.path.basename(p) for p in paths])

    def _browse_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Files", "",
            "Media Files (*.mp4 *.mkv *.avi *.mov *.flv *.webm "
            "*.mp3 *.flac *.wav *.aac *.ogg *.wma);;All Files (*)"
        )
        if paths:
            self._set_files(paths)

    def _load_defaults(self):
        """Load default settings from QSettings."""
        out_dir = self.settings.value("default_output_dir", "")
        if out_dir and os.path.isdir(out_dir):
            self.output_edit.setText(out_dir)

    def _pick_output_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if path:
            self.output_edit.setText(path)

    def _start_conversion(self):
        if not self._input_files:
            return

        format_name = self.format_combo.currentText()
        fmt_config = QUICK_PRESETS.get(format_name)
        if not fmt_config:
            return

        output_dir = self.output_edit.text() or None

        self.progress_bar.show()
        self.progress_bar.setValue(0)
        self._completed_count = 0
        self._total_count = len(self._input_files)
        self.lbl_status.setText(f"Converting 0/{self._total_count}...")

        for input_path in self._input_files:
            base = os.path.splitext(os.path.basename(input_path))[0]
            out_dir = output_dir or os.path.dirname(input_path)
            output_path = os.path.join(out_dir, f"{base}{fmt_config['ext']}")

            # Get duration
            meta = self.ffprobe.get_metadata(input_path)
            duration = meta.get("format", {}).get("duration", 0) if "error" not in meta else 0

            options = {}
            if "preset" in fmt_config:
                options["preset"] = fmt_config["preset"]
            elif "args" in fmt_config:
                options["custom_args"] = fmt_config["args"]

            self.queue.add_job(
                input_path=input_path,
                output_path=output_path,
                options=options,
                duration=duration,
            )

    def _on_progress(self, job_id: str, percent: float, speed: str):
        # Show progress of current job
        overall = ((self._completed_count / self._total_count) * 100
                   + percent / self._total_count)
        self.progress_bar.setValue(int(overall))

    def _on_completed(self, job_id: str):
        self._completed_count += 1
        self.lbl_status.setText(f"Converting {self._completed_count}/{self._total_count}...")

    def _on_failed(self, job_id: str, error: str):
        self._completed_count += 1
        self.lbl_status.setText(f"⚠ Error on file (continuing...)")

    def _on_all_done(self):
        self.progress_bar.setValue(100)
        self.lbl_status.setText(f"✅ All {self._total_count} files converted!")
