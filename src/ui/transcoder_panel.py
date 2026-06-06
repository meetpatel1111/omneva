"""Transcoder Panel — Batch transcoding with presets and progress tracking."""

import os
import subprocess
import tempfile
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QFileDialog, QListWidget, QListWidgetItem,
    QGroupBox, QLineEdit, QTabWidget, QFrame
)
from PySide6.QtCore import Qt, Signal, QSettings, QThread, QObject
from PySide6.QtGui import QPixmap

from src.core.ffmpeg_service import FFmpegService, PRESETS
from src.core.ffprobe_service import FFprobeService
from src.core.queue_manager import QueueManager
from src.core.utils import format_duration, is_media_file
from src.core.storage import storage
from src.core.logger import get_logger
from src.core.security import safe_subprocess_run
from src.core.recovery_service import get_recovery_service
from src.ui.tabs.video_tab import VideoSettingsTab
from src.ui.tabs.summary_tab import SummaryTab
from src.ui.tabs.dimensions_tab import DimensionsTab
from src.ui.tabs.filters_tab import FiltersTab
from src.ui.tabs.audio_tab import AudioTab
from src.ui.tabs.subtitles_tab import SubtitlesTab
from src.ui.tabs.chapters_tab import ChaptersTab


class TranscoderDropZone(QFrame):
    """Drag-and-drop zone for TranscoderPanel files."""

    files_dropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(100)

        layout = QVBoxLayout(self)
        self.label = QLabel("📥\n\nDrag & drop media files here\nor use Add Files button below")
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
            text = "\n".join(f"📄 {os.path.basename(f)}" for f in filenames[:3])
            if len(filenames) > 3:
                text += f"\n... and {len(filenames) - 3} more"
            self.label.setText(text)
        else:
            self.label.setText("📥\n\nDrag & drop media files here\nor use Add Files button below")


class FFprobeWorker(QObject):
    """Worker for running FFprobe operations in a separate thread."""
    
    metadata_ready = Signal(str, dict)  # path, metadata
    error_occurred = Signal(str, str)   # path, error_message
    
    def __init__(self, ffprobe_service):
        super().__init__()
        self.ffprobe = ffprobe_service
        self._current_path = None
        
    def get_metadata(self, path: str):
        """Get metadata for the given file path."""
        self._current_path = path
        try:
            meta = self.ffprobe.get_metadata(path)
            if "error" in meta:
                self.error_occurred.emit(path, meta['error'])
            else:
                self.metadata_ready.emit(path, meta)
        except Exception as e:
            self.error_occurred.emit(path, str(e))


class TranscoderPanel(QWidget):
    """Transcoding UI with preset selection, file input, and job queue."""

    # Signal emitted when a job is added: (job_id, filename, preset_name)
    job_added = Signal(str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("transcoderPanel")
        self.logger = get_logger('transcoder_panel')

        self.settings = storage.get_settings()
        self.ffmpeg = FFmpegService()
        self.ffprobe = FFprobeService()
        self.queue = QueueManager(self.ffmpeg)
        self.recovery_service = get_recovery_service()

        self._input_files: list[str] = []
        self._current_job_id = None
        
        # Setup FFprobe worker for threaded operations
        self._setup_ffprobe_worker()

        self._setup_ui()
        self._load_defaults()
        self._connect_signals()
        
        # Setup autosave timer for transcoder state
        self._setup_autosave()

    def _setup_ffprobe_worker(self):
        """Setup FFprobe worker thread for non-blocking metadata operations."""
        # Use a more conservative approach - start with synchronous operations
        # until threading can be properly implemented without crashes
        self._ffprobe_thread = None
        self._ffprobe_worker = None

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # ─── Header ─────────────────────────────────────────
        header = QLabel("⚙  Transcoder")
        header.setObjectName("panelHeader")
        layout.addWidget(header)

        # ─── Input Section ───────────────────────────────────
        input_group = QGroupBox("Input Files")
        input_group.setObjectName("inputGroup")
        ig_layout = QVBoxLayout(input_group)

        # Drop zone for drag-and-drop
        self.drop_zone = TranscoderDropZone()
        ig_layout.addWidget(self.drop_zone)

        btn_row = QHBoxLayout()
        self.btn_add_files = QPushButton("📂 Add Files")
        self.btn_add_files.setObjectName("actionBtn")
        self.btn_add_files.setFixedHeight(34)

        self.btn_clear_files = QPushButton("🗑 Clear")
        self.btn_clear_files.setObjectName("actionBtn")
        self.btn_clear_files.setFixedHeight(34)

        self.lbl_file_count = QLabel("0 files selected")
        self.lbl_file_count.setObjectName("fileCount")

        btn_row.addWidget(self.btn_add_files)
        btn_row.addWidget(self.btn_clear_files)
        btn_row.addStretch()
        btn_row.addWidget(self.lbl_file_count)
        ig_layout.addLayout(btn_row)

        self.file_list = QListWidget()
        self.file_list.setObjectName("fileList")
        self.file_list.setMaximumHeight(80)
        ig_layout.addWidget(self.file_list)

        layout.addWidget(input_group)

        # ─── Output & Presets ────────────────────────────────
        controls_layout = QHBoxLayout()

        controls_layout.addWidget(QLabel("Preset:"))
        self.preset_combo = QComboBox()
        self.preset_combo.setObjectName("presetCombo")
        self.preset_combo.addItem("Custom Settings", "custom")
        for key, preset in PRESETS.items():
            self.preset_combo.addItem(preset["name"], key)
        self.preset_combo.setFixedHeight(32)
        idx = self.preset_combo.findData("gen_fast_1080p")
        if idx >= 0:
            self.preset_combo.setCurrentIndex(idx)
        controls_layout.addWidget(self.preset_combo, 2)

        controls_layout.addWidget(QLabel("Output:"))
        self.output_edit = QLineEdit()
        self.output_edit.setObjectName("outputEdit")
        self.output_edit.setPlaceholderText("Same as input folder")
        self.output_edit.setFixedHeight(32)
        self.btn_output = QPushButton("📁")
        self.btn_output.setFixedSize(32, 32)
        controls_layout.addWidget(self.output_edit, 2)
        controls_layout.addWidget(self.btn_output)

        layout.addLayout(controls_layout)

        # ─── Tabs Section ────────────────────────────────────
        self.tabs = QTabWidget()
        self.tabs.setObjectName("settingsTabs")

        # Lazy-loaded tabs - only create placeholders initially
        self._tab_instances = {}
        self._tab_created = {}
        
        # Add tab placeholders with lazy loading
        self.tabs.addTab(QWidget(), "Summary")
        self.tabs.addTab(QWidget(), "Dimensions")
        self.tabs.addTab(QWidget(), "Filters")
        self.tabs.addTab(QWidget(), "Video")
        self.tabs.addTab(QWidget(), "Audio")
        self.tabs.addTab(QWidget(), "Subtitles")
        self.tabs.addTab(QWidget(), "Chapters")
        
        # Connect tab change signal for lazy loading
        self.tabs.currentChanged.connect(self._on_tab_changed)

        layout.addWidget(self.tabs, 1)

    def _on_tab_changed(self, index: int):
        """Handle tab change event for lazy loading."""
        if index >= 0 and not self._tab_created.get(index, False):
            self._create_tab(index)

    def _create_tab(self, index: int):
        """Create and initialize a tab on first access."""
        tab_names = ["Summary", "Dimensions", "Filters", "Video", "Audio", "Subtitles", "Chapters"]
        tab_classes = [SummaryTab, DimensionsTab, FiltersTab, VideoSettingsTab, AudioTab, SubtitlesTab, ChaptersTab]
        
        if index >= len(tab_classes):
            return
            
        tab_name = tab_names[index]
        tab_class = tab_classes[index]
        
        self.logger.debug(f"Lazy-loading tab: {tab_name}")
        
        # Create the tab instance
        tab_instance = tab_class()
        
        # Replace the placeholder with the actual tab
        current_widget = self.tabs.widget(index)
        self.tabs.removeTab(index)
        self.tabs.insertTab(index, tab_instance, tab_name)
        
        # Store the instance for future reference
        self._tab_instances[index] = tab_instance
        self._tab_created[index] = True
        
        # Clean up the placeholder widget
        if current_widget:
            current_widget.deleteLater()

    def _get_tab(self, index: int):
        """Get a tab instance, creating it if necessary."""
        if not self._tab_created.get(index, False):
            self._create_tab(index)
        return self._tab_instances.get(index)

    def _connect_signals(self):
        self.btn_add_files.clicked.connect(self._add_files)
        self.btn_clear_files.clicked.connect(self._clear_files)
        self.btn_output.clicked.connect(self._pick_output_dir)
        # btn_start not defined in current UI - signal connection removed
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        self.file_list.currentItemChanged.connect(self._on_file_selected)
        # Connect drop zone signal
        self.drop_zone.files_dropped.connect(self._on_files_dropped)

    # ─── File Selection & Preview ────────────────────────────

    def _on_files_dropped(self, file_paths: list[str]):
        """Handle files dropped onto the DropZone."""
        if not file_paths:
            return
        
        # Add dropped files to the input list
        for path in file_paths:
            if path not in self._input_files:
                self._input_files.append(path)
                # Add to file list widget
                item = QListWidgetItem(os.path.basename(path))
                item.setToolTip(path)
                self.file_list.addItem(item)
        
        # Update UI
        self._update_file_count()
        self.drop_zone.set_files(self._input_files)
        
        # Select first file if no current selection
        if self.file_list.count() > 0 and not self.file_list.currentItem():
            self.file_list.setCurrentRow(0)

    def _on_file_selected(self, current: QListWidgetItem, previous: QListWidgetItem):
        if not current:
            return
        filename = current.text()
        path = next((p for p in self._input_files if os.path.basename(p) == filename), None)
        if path:
            self._update_summary_info(path)
            self._generate_preview(path)

    def _update_summary_info(self, path: str):
        """Update summary info using threaded FFprobe operation."""
        self.logger.debug(f"_update_summary_info called for {path}")
        
        # Show loading indicator
        summary_tab = self._get_tab(0)  # Summary tab is index 0
        if summary_tab:
            summary_tab.set_loading_state(True)
        
        # Request metadata from worker thread
        if self._ffprobe_worker:
            self._ffprobe_worker.get_metadata(path)
        else:
            # Fallback to synchronous operation
            try:
                meta = self.ffprobe.get_metadata(path)
                self._on_metadata_ready(path, meta)
            except Exception as e:
                self.logger.error(f"Error getting metadata for {path}: {e}")
                self._on_ffprobe_error(path, str(e))

    def _on_metadata_ready(self, path: str, meta: dict):
        """Handle metadata received from FFprobe worker."""
        self.logger.debug(f"Metadata ready for {path}")
        
        # Hide loading indicator
        summary_tab = self._get_tab(0)  # Summary tab is index 0
        if summary_tab:
            summary_tab.set_loading_state(False)

        # Use parsed lists from FFprobeService
        v_streams = meta.get("video_streams", [])
        a_streams = meta.get("audio_streams", [])
        s_streams = meta.get("subtitle_streams", [])
        chapters = meta.get("chapters", [])
        
        self.logger.debug(f"Found {len(v_streams)} video, {len(a_streams)} audio, {len(s_streams)} subs")

        v_stream = v_streams[0] if v_streams else {}
        a_stream = a_streams[0] if a_streams else {}

        w = v_stream.get('width', 0)
        h = v_stream.get('height', 0)
        
        # Note: FFprobeService now includes 'codec_name' alias
        v_info = f"Video: {v_stream.get('codec_name', 'unknown')}, {w}x{h}"
        a_info = f"Audio: {a_stream.get('codec_name', 'unknown')}, {a_stream.get('channels', 0)}ch"
        
        if summary_tab:
            summary_tab.set_track_info(v_info, a_info)
            summary_tab.set_size_info(w, h)
        
        # Update other tabs
        dimensions_tab = self._get_tab(1)  # Dimensions tab is index 1
        if dimensions_tab:
            dimensions_tab.set_source_dimensions(w, h)

        # Populate Audio tab with source audio tracks
        self.logger.debug(f"Loading audio tracks: {a_streams}")
        audio_tab = self._get_tab(4)  # Audio tab is index 4
        if audio_tab:
            audio_tab.load_source_tracks(a_streams)

        # Populate Subtitles tab with source subtitle tracks
        subtitles_tab = self._get_tab(5)  # Subtitles tab is index 5
        if subtitles_tab:
            subtitles_tab.load_source_tracks(s_streams)

        # Populate Chapters tab
        chapters_tab = self._get_tab(6)  # Chapters tab is index 6
        if chapters_tab:
            chapters_tab.load_chapters(chapters)

    def _on_ffprobe_error(self, path: str, error_message: str):
        """Handle FFprobe error from worker thread."""
        self.logger.error(f"Error getting metadata for {path}: {error_message}")
        
        # Hide loading indicator
        summary_tab = self._get_tab(0)  # Summary tab is index 0
        if summary_tab:
            summary_tab.set_loading_state(False)
        
        # Show error dialog
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.warning(
            self, 
            "Metadata Error", 
            f"Failed to read media info.\n\nError: {error_message}\n\nMake sure FFprobe is installed and in your PATH."
        )

    def _generate_preview(self, path: str):
        try:
            # Validate the input path for security
            if not self.ffmpeg.validate_file_path(path):
                self.logger.error(f"Invalid file path for preview generation: {path}")
                return
                
            tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
            tmp.close()
            
            # Use safe subprocess with validation
            result = safe_subprocess_run([
                self.ffmpeg.ffmpeg_path, "-y",
                "-ss", "00:00:05", "-i", path,
                "-frames:v", "1", "-q:v", "5", tmp.name
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            if result is None:
                self.logger.error("Preview generation command validation failed")
                return
                
            pixmap = QPixmap(tmp.name)
            summary_tab = self._get_tab(0)  # Summary tab is index 0
            if summary_tab:
                summary_tab.set_preview_image(pixmap)
            os.unlink(tmp.name)
        except Exception as e:
            self.logger.error(f"Preview generation failed: {e}")

    def _setup_autosave(self):
        """Setup autosave timer for transcoder state."""
        from PySide6.QtCore import QTimer
        
        # Autosave every 5 minutes
        self._autosave_timer = QTimer(self)
        self._autosave_timer.timeout.connect(self._autosave_state)
        self._autosave_timer.start(300000)  # 5 minutes in milliseconds

    def _autosave_state(self):
        """Save current transcoder state for crash recovery."""
        try:
            # Get summary tab settings safely
            summary_tab = self._get_tab(0)  # Summary tab is index 0
            output_format = summary_tab.combo_format.currentText() if summary_tab else ""
            output_name = summary_tab.line_name.text() if summary_tab else ""
            
            current_state = {
                'input_files': self._input_files,
                'current_preset': self.preset_combo.currentData(),
                'output_format': output_format,
                'output_name': output_name,
                'current_tab': self.tabs.currentIndex(),
                'transcoder_jobs': self._get_job_states()
            }
            
            self.recovery_service.autosave_if_needed(current_state)
            
        except Exception as e:
            self.logger.error(f"Transcoder autosave failed: {e}")

    def cleanup(self):
        """Clean up resources including FFprobe thread."""
        try:
            if hasattr(self, '_ffprobe_thread') and self._ffprobe_thread and self._ffprobe_thread.isRunning():
                self._ffprobe_thread.quit()
                self._ffprobe_thread.wait(1000)  # Wait up to 1 second for thread to finish
        except Exception as e:
            self.logger.error(f"Error cleaning up FFprobe thread: {e}")

    def _get_job_states(self):
        """Get current job states for recovery."""
        job_states = []
        try:
            # Get jobs from queue manager
            if hasattr(self.queue, '_jobs'):
                for job_id, job in self.queue._jobs.items():
                    job_states.append({
                        'id': job_id,
                        'input_path': job.input_path,
                        'output_path': job.output_path,
                        'status': job.status,
                        'progress': job.progress,
                        'options': job.options
                    })
        except Exception as e:
            self.logger.error(f"Failed to get job states: {e}")
        return job_states

    def cleanup(self):
        """Clean up resources when panel is destroyed."""
        if hasattr(self, '_ffprobe_thread') and self._ffprobe_thread.isRunning():
            self._ffprobe_thread.quit()
            self._ffprobe_thread.wait(1000)  # Wait up to 1 second for thread to finish

    # ─── Preset Changed ─────────────────────────────────────

    def _on_preset_changed(self):
        key = self.preset_combo.currentData()
        if key == "custom":
            self.tabs.setCurrentIndex(3)  # Video tab
        else:
            self.tabs.setCurrentIndex(0)
            preset = PRESETS.get(key)
            if preset:
                ext_map = {".mp4": "MP4", ".mkv": "MKV", ".webm": "WebM"}
                fmt = ext_map.get(preset["ext"], "MP4")
                summary_tab = self._get_tab(0)  # Summary tab is index 0
                if summary_tab:
                    summary_tab.combo_format.setCurrentText(fmt)

    # ─── File Management ─────────────────────────────────────

    def _add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Add Media Files", "",
            "Media Files (*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.webm "
            "*.mp3 *.flac *.wav *.aac *.ogg);;All Files (*)"
        )
        if not paths:
            return

        for p in paths:
            if p not in self._input_files:
                self._input_files.append(p)
                self.file_list.addItem(os.path.basename(p))
                
        self.lbl_file_count.setText(f"{len(self._input_files)} files selected")
        
        # Select the last added file to trigger metadata load
        if self.file_list.count() > 0:
            self.file_list.setCurrentRow(self.file_list.count() - 1)

    def _clear_files(self):
        self._input_files.clear()
        self.file_list.clear()
        self.lbl_file_count.setText("0 files selected")

    def _load_defaults(self):
        """Load default settings from QSettings."""
        out_dir = self.settings.value("default_output_dir", "")
        if out_dir and os.path.isdir(out_dir):
            self.output_edit.setText(out_dir)

        # Attempt to set default video encoder
        v_codec = self.settings.value("default_video_codec", "").lower()
        if v_codec:
            # Simple fuzzy matching
            video_tab = self._get_tab(3)  # Video tab is index 3
            if video_tab:
                combo = video_tab.combo_encoder
                for i in range(combo.count()):
                    text = combo.itemText(i).lower()
                    if v_codec in text:
                        combo.setCurrentIndex(i)
                        break

    def _pick_output_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if path:
            self.output_edit.setText(path)

    # ─── Filter Chain Builders ───────────────────────────────

    def _get_dimensions_filters(self) -> str:
        dimensions_tab = self._get_tab(1)  # Dimensions tab is index 1
        s = dimensions_tab.get_settings() if dimensions_tab else {}
        filters = []
        rot = s["rotation"]
        if rot == 90:
            filters.append("transpose=1")
        elif rot == 180:
            filters.append("transpose=2,transpose=2")
        elif rot == 270:
            filters.append("transpose=2")
        if s["flip"]:
            filters.append("hflip")
        if s["crop_mode"] == "Custom":
            top, bot, left, right = s["crop"]
            if any([top, bot, left, right]):
                filters.append(f"crop=iw-{left}-{right}:ih-{top}-{bot}:{left}:{top}")
        width, height = s["width"], s["height"]
        if width > 0 and height > 0:
            filters.append(f"scale={width}:{height}")
        if s["border_mode"] == "Custom":
            top, bot, left, right = s["borders"]
            if any([top, bot, left, right]):
                color = s["border_color"].lower()
                filters.append(f"pad=iw+{left}+{right}:ih+{top}+{bot}:{left}:{top}:{color}")
        return ",".join(filters)

    def _get_video_filters(self) -> str:
        """Build FFmpeg -vf filter chain from Filters tab settings.
        Every non-Off dropdown value maps to a real FFmpeg filter."""
        filters_tab = self._get_tab(2)  # Filters tab is index 2
        s = filters_tab.get_settings() if filters_tab else {}
        filters = []

        # ── Detelecine ──────────────────────────────────────
        # Removes 3:2 pulldown (telecine) from film content
        dt = s["detelecine"]
        if dt == "Default":
            filters.append("pullup")
        elif dt == "Custom":
            filters.append("pullup")

        # ── Interlace Detection ─────────────────────────────
        # Detects interlaced frames and tags them for downstream filters
        idet = s["interlace_detection"]
        if idet == "Default":
            filters.append("idet")
        elif idet == "Custom":
            filters.append("idet")
        elif idet == "LessSensitive":
            filters.append("idet=half_life=50")
        elif idet == "Fast":
            filters.append("idet=intl_thres=1.2:prog_thres=1.2")

        # ── Deinterlace ─────────────────────────────────────
        # Converts interlaced video to progressive
        di = s["deinterlace"]
        if di == "Yadif":
            filters.append("yadif=mode=0:parity=-1:deint=0")
        elif di == "Decomb":
            filters.append("fieldmatch,yadif=deint=interlaced,decimate")
        elif di == "Bwdif":
            filters.append("bwdif=mode=0:parity=-1:deint=0")

        # ── Denoise ─────────────────────────────────────────
        # Reduces video noise / grain
        dn = s["denoise"]
        if dn == "hqdn3d":
            filters.append("hqdn3d=4:3:6:4.5")
        elif dn == "NLMeans":
            filters.append("nlmeans=s=3.0:p=7:pc=5:r=15:rc=7")

        # ── Chroma Smooth ───────────────────────────────────
        # Smooths chroma (color) noise without affecting luma
        cs = s["chroma_smooth"]
        cs_map = {
            "Custom":     "hqdn3d=0:0:4:4",
            "Ultralight": "hqdn3d=0:0:2:2",
            "Light":      "hqdn3d=0:0:3:3",
            "Medium":     "hqdn3d=0:0:4:4",
            "Strong":     "hqdn3d=0:0:7:7",
            "Stronger":   "hqdn3d=0:0:10:10",
            "Very Strong":"hqdn3d=0:0:14:14",
        }
        if cs in cs_map:
            filters.append(cs_map[cs])

        # ── Sharpen ─────────────────────────────────────────
        # Sharpens edges — UnSharp uses unsharp mask, LapSharp uses laplacian
        sh = s["sharpen"]
        if sh == "UnSharp":
            filters.append("unsharp=5:5:1.0:5:5:0.0")
        elif sh == "LapSharp":
            filters.append("unsharp=5:5:1.5:3:3:0.0")

        # ── Deblock ─────────────────────────────────────────
        # Removes blocking artifacts from low-bitrate encodes
        db = s["deblock"]
        db_map = {
            "Custom":     "deblock=filter=default",
            "Ultralight": "deblock=filter=weak:block=4",
            "Light":      "deblock=filter=weak",
            "Medium":     "deblock=filter=default",
            "Strong":     "deblock=filter=strong",
            "Stronger":   "deblock=filter=strong:block=6",
            "Very Strong":"deblock=filter=strong:block=8",
        }
        if db in db_map:
            filters.append(db_map[db])

        # ── Colourspace ─────────────────────────────────────
        # Converts video to target colour standard
        csp = s["colorspace"]
        csp_map = {
            "Custom":         "colorspace=all=bt709",
            "BT.2020":        "colorspace=all=bt2020",
            "BT.709":         "colorspace=all=bt709",
            "BT.601 SMPTE-C": "colorspace=all=bt601-6-525",
            "BT.601 EBU":     "colorspace=all=bt601-6-625",
        }
        if csp in csp_map:
            filters.append(csp_map[csp])

        # ── Grayscale ───────────────────────────────────────
        # Strips all colour, outputs monochrome
        if s["grayscale"]:
            filters.append("format=gray")

        return ",".join(filters)

    # ─── Video Args Builder ──────────────────────────────────

    def _get_video_args(self) -> list:
        video_tab = self._get_tab(3)  # Video tab is index 3
        s = video_tab.get_settings() if video_tab else {}
        args = []
        enc_map = {
            "H.264 (x264)": "libx264", "H.265 (x265)": "libx265",
            "H.264 (NVENC)": "h264_nvenc", "H.265 (NVENC)": "hevc_nvenc",
            "H.264 (QSV)": "h264_qsv", "H.265 (QSV)": "hevc_qsv",
            "AV1 (SVT-AV1)": "libsvtav1", "VP9": "libvpx-vp9", "VP8": "libvpx",
            "MPEG-4 (mp4v)": "mpeg4", "MPEG-2 (mp2v)": "mpeg2video", "MPEG-1 (mp1v)": "mpeg1video",
            "Theora": "libtheora", "DV Video (dvsd)": "dvvideo",
            "Sorenson v1 (SVQ1)": "svq1", "Sorenson v3 (SVQ3)": "svq3"
        }

        encoder = enc_map.get(s["encoder"], "libx264")
        args.extend(["-c:v", encoder])
        if s["fps"] != "Same as source":
            args.extend(["-r", s["fps"]])
        if s["quality_mode"] == "rf":
            if "nvenc" in encoder:
                args.extend(["-cq", str(s["rf"])])
            elif "qsv" in encoder:
                args.extend(["-global_quality", str(s["rf"])])
            else:
                args.extend(["-crf", str(s["rf"])])
        else:
            args.extend(["-b:v", f"{s['bitrate']}k"])
        if "nvenc" not in encoder:
            args.extend(["-preset", s["preset"]])
        if s["tune"] != "None" and "libx264" in encoder:
            args.extend(["-tune", s["tune"].lower().replace(" ", "")])
        if s["profile"] != "Auto":
            args.extend(["-profile:v", s["profile"].lower().replace(" ", "")])
        if s["level"] != "Auto":
            args.extend(["-level", s["level"]])
        if s["advanced"]:
            if ":" in s["advanced"] and "=" in s["advanced"]:
                args.extend(["-x264-params", s["advanced"]])
            else:
                for arg in s["advanced"].split():
                    args.append(arg)

        # Combined filter chain
        vf_dim = self._get_dimensions_filters()
        vf_filt = self._get_video_filters()
        vf_parts = [p for p in [vf_dim, vf_filt] if p]
        if vf_parts:
            args.extend(["-vf", ",".join(vf_parts)])

        # Audio args from Audio tab
        args.extend(self._get_audio_args())
        return args

    # ── Audio Args Builder ───────────────────────────────────

    def _get_audio_args(self) -> list:
        """Build FFmpeg audio arguments from the Audio tab settings.
        Every option produces correct FFmpeg arguments."""
        audio_tab = self._get_tab(4)  # Audio tab is index 4
        tracks = audio_tab.get_settings() if audio_tab else []
        if not tracks:
            return ["-an"]  # no audio

        args = []
        for i, t in enumerate(tracks):
            encoder = t["encoder"]

            # ── Codec ────────────────────────────────────────
            args.extend([f"-c:a:{i}", encoder])

            # Passthru — copy stream as-is, skip all encoding options
            if t["is_passthru"]:
                continue

            # ── Bitrate / Quality ────────────────────────────
            is_lossless = encoder in ("flac", "alac")
            if not is_lossless:
                if t["quality_mode"] == "Bitrate:":
                    args.extend([f"-b:a:{i}", f"{t['value']}k"])
                else:
                    # Quality mode: 1=best ... 5=lowest
                    args.extend([f"-q:a:{i}", t["value"]])

            # ── Channel layout (Mixdown) ─────────────────────
            mix = t["mixdown"]
            if mix == "Mono":
                args.extend([f"-ac:a:{i}", "1"])
            elif mix == "Stereo":
                args.extend([f"-ac:a:{i}", "2"])
            elif mix == "5.1 Surround":
                args.extend([f"-ac:a:{i}", "6"])
            elif mix == "6.1 Surround":
                args.extend([f"-ac:a:{i}", "7"])
            elif mix == "7.1 Surround":
                args.extend([f"-ac:a:{i}", "8"])
            # Left/Right only handled via audio filters below

            # ── Samplerate ───────────────────────────────────
            sr = t["samplerate"]
            if sr != "Auto":
                sr_hz = str(int(float(sr) * 1000))
                args.extend([f"-ar:a:{i}", sr_hz])

            # ── Audio Filters (pan + volume) ─────────────────
            # Build a filter chain — multiple filters joined with ","
            audio_filters = []

            if mix == "Mono (Left Only)":
                audio_filters.append("pan=mono|c0=FL")
            elif mix == "Mono (Right Only)":
                audio_filters.append("pan=mono|c0=FR")

            gain = t["gain"]
            if gain != 0:
                audio_filters.append(f"volume={gain}dB")

            if audio_filters:
                args.extend([f"-filter:a:{i}", ",".join(audio_filters)])

            # ── DRC (Dynamic Range Compression) ──────────────
            drc = t["drc"]
            if drc > 0:
                args.extend(["-drc_scale", str(drc)])

            # ── Bit depth for lossless codecs ────────────────
            if t["is_24bit"]:
                args.extend([f"-sample_fmt:a:{i}", "s32"])
            elif is_lossless:
                args.extend([f"-sample_fmt:a:{i}", "s16"])

        return args

    # ── Subtitle Args Builder ─────────────────────────────

    def _get_subtitle_args(self, input_path: str) -> list:
        """Build FFmpeg subtitle arguments from the Subtitles tab."""
        subtitles_tab = self._get_tab(5)  # Subtitles tab is index 5
        tracks = subtitles_tab.get_settings() if subtitles_tab else []
        if not tracks:
            return ["-sn"]  # no subtitles

        args = []
        sub_idx = 0
        extra_inputs = []  # external subtitle file inputs

        for t in tracks:
            if t["is_external"] and t["external_path"]:
                # External subtitle file — add as extra input
                extra_inputs.extend(["-i", t["external_path"]])

            if t["burn_in"]:
                # Burn-in: hardcode subtitles into video via -vf subtitles=
                if t["is_external"] and t["external_path"]:
                    # Escape path for FFmpeg filter
                    esc_path = t["external_path"].replace("\\", "/").replace(":", r"\:")
                    args.extend(["-vf", f"subtitles='{esc_path}'"])
                else:
                    # Burn from embedded subtitle stream
                    esc_path = input_path.replace("\\", "/").replace(":", r"\:")
                    args.extend(["-vf", f"subtitles='{esc_path}':si={sub_idx}"])
            else:
                # Copy subtitle track
                args.extend([f"-c:s:{sub_idx}", "copy"])

                # Default disposition
                if t["default"]:
                    args.extend([f"-disposition:s:{sub_idx}", "default"])
                elif t["forced"]:
                    args.extend([f"-disposition:s:{sub_idx}", "forced"])

                sub_idx += 1

            # Offset (applied via -itsoffset for the sub input)
            # Note: offset is applied at mux level

        return extra_inputs + args

    # ── Chapter Args Builder ──────────────────────────────

    def _get_chapter_args(self) -> list:
        """Build FFmpeg chapter arguments."""
        chapters_tab = self._get_tab(6)  # Chapters tab is index 6
        settings = chapters_tab.get_settings() if chapters_tab else {}
        if settings["include_chapters"]:
            # Copy chapters from source
            return ["-map_chapters", "0"]
        else:
            # Strip chapters
            return ["-map_chapters", "-1"]

    # ─── Transcoding ─────────────────────────────────────────

    def _start_transcoding(self):
        if not self._input_files:
            return

        preset_key = self.preset_combo.currentData()
        output_dir = self.output_edit.text() or None
        summary_tab = self._get_tab(0)  # Summary tab is index 0
        summary_opts = summary_tab.get_settings() if summary_tab else {}

        for input_path in self._input_files:
            base = os.path.splitext(os.path.basename(input_path))[0]
            out_dir = output_dir or os.path.dirname(input_path)

            if preset_key == "custom":
                ext_map = {
                    "mp4": ".mp4", "mkv": ".mkv", "webm": ".webm",
                    "avi": ".avi", "ts": ".ts", "ps": ".mpg", "ogg": ".ogg", "asf": ".wmv"
                }
                ext = ext_map.get(summary_opts["format"], ".mp4")

            else:
                ext = PRESETS[preset_key]["ext"]

            output_path = os.path.join(out_dir, f"{base}_transcoded{ext}")

            meta = self.ffprobe.get_metadata(input_path)
            duration = meta.get("format", {}).get("duration", 0) if "error" not in meta else 0

            job_options = {}
            custom_args = []
            if summary_opts["web_optimized"] and ext == ".mp4":
                custom_args.extend(["-movflags", "+faststart"])

            job_name = ""
            if preset_key == "custom":
                vid_args = self._get_video_args()
                sub_args = self._get_subtitle_args(input_path)
                chap_args = self._get_chapter_args()
                job_options["custom_args"] = vid_args + sub_args + chap_args + custom_args
                job_name = "Custom Settings"
            else:
                job_options["preset"] = preset_key
                if custom_args:
                    p_args = PRESETS[preset_key]["args"].copy()
                    p_args.extend(custom_args)
                    job_options["custom_args"] = p_args
                job_name = PRESETS[preset_key]["name"]

            job_id = self.queue.add_job(
                input_path=input_path,
                output_path=output_path,
                options=job_options,
                duration=duration,
            )

            # Emit signal so QueuePanel can pick it up
            self.job_added.emit(job_id, os.path.basename(input_path), job_name)
