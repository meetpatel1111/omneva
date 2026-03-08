"""Transcoder Panel — Batch transcoding with presets and progress tracking."""

import os
import subprocess
import tempfile
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QFileDialog, QListWidget, QListWidgetItem,
    QGroupBox, QLineEdit, QTabWidget
)
from PySide6.QtCore import Qt, Signal, QSettings
from PySide6.QtGui import QPixmap

from src.core.ffmpeg_service import FFmpegService, PRESETS
from src.core.ffprobe_service import FFprobeService
from src.core.queue_manager import QueueManager
from src.core.utils import format_duration
from src.core.storage import storage
from src.ui.tabs.video_tab import VideoSettingsTab
from src.ui.tabs.summary_tab import SummaryTab
from src.ui.tabs.dimensions_tab import DimensionsTab
from src.ui.tabs.filters_tab import FiltersTab
from src.ui.tabs.audio_tab import AudioTab
from src.ui.tabs.subtitles_tab import SubtitlesTab
from src.ui.tabs.chapters_tab import ChaptersTab


class TranscoderPanel(QWidget):
    """Transcoding UI with preset selection, file input, and job queue."""

    # Signal emitted when a job is added: (job_id, filename, preset_name)
    job_added = Signal(str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("transcoderPanel")

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

        # ─── Header ─────────────────────────────────────────
        header = QLabel("⚙  Transcoder")
        header.setObjectName("panelHeader")
        layout.addWidget(header)

        # ─── Input Section ───────────────────────────────────
        input_group = QGroupBox("Input Files")
        input_group.setObjectName("inputGroup")
        ig_layout = QVBoxLayout(input_group)

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

        self.tab_summary = SummaryTab()
        self.tabs.addTab(self.tab_summary, "Summary")

        self.tab_dimensions = DimensionsTab()
        self.tabs.addTab(self.tab_dimensions, "Dimensions")

        self.tab_filters = FiltersTab()
        self.tabs.addTab(self.tab_filters, "Filters")

        self.tab_video = VideoSettingsTab()
        self.tabs.addTab(self.tab_video, "Video")

        self.tab_audio = AudioTab()
        self.tabs.addTab(self.tab_audio, "Audio")

        self.tab_subtitles = SubtitlesTab()
        self.tabs.addTab(self.tab_subtitles, "Subtitles")

        self.tab_chapters = ChaptersTab()
        self.tabs.addTab(self.tab_chapters, "Chapters")

        layout.addWidget(self.tabs, 1)

        # ─── Start Button ───────────────────────────────────
        self.btn_start = QPushButton("🚀  Start Transcoding")
        self.btn_start.setObjectName("startBtn")
        self.btn_start.setFixedHeight(40)
        layout.addWidget(self.btn_start)

    def _connect_signals(self):
        self.btn_add_files.clicked.connect(self._add_files)
        self.btn_clear_files.clicked.connect(self._clear_files)
        self.btn_output.clicked.connect(self._pick_output_dir)
        self.btn_start.clicked.connect(self._start_transcoding)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        self.file_list.currentItemChanged.connect(self._on_file_selected)

    # ─── File Selection & Preview ────────────────────────────

    def _on_file_selected(self, current: QListWidgetItem, previous: QListWidgetItem):
        if not current:
            return
        filename = current.text()
        path = next((p for p in self._input_files if os.path.basename(p) == filename), None)
        if path:
            self._update_summary_info(path)
            self._generate_preview(path)

    def _update_summary_info(self, path: str):
        print(f"DEBUG: _update_summary_info called for {path}")
        meta = self.ffprobe.get_metadata(path)
        if "error" in meta:
            print(f"Error getting metadata for {path}: {meta['error']}")
            QMessageBox.warning(self, "Metadata Error", f"Failed to read media info.\n\nError: {meta['error']}\n\nMake sure FFprobe is installed and in your PATH.")
            return

        # Use parsed lists from FFprobeService
        v_streams = meta.get("video_streams", [])
        a_streams = meta.get("audio_streams", [])
        s_streams = meta.get("subtitle_streams", [])
        chapters = meta.get("chapters", [])
        
        print(f"DEBUG: Found {len(v_streams)} video, {len(a_streams)} audio, {len(s_streams)} subs")

        v_stream = v_streams[0] if v_streams else {}
        a_stream = a_streams[0] if a_streams else {}

        w = v_stream.get('width', 0)
        h = v_stream.get('height', 0)
        
        # Note: FFprobeService now includes 'codec_name' alias
        v_info = f"Video: {v_stream.get('codec_name', 'unknown')}, {w}x{h}"
        a_info = f"Audio: {a_stream.get('codec_name', 'unknown')}, {a_stream.get('channels', 0)}ch"
        
        self.tab_summary.set_track_info(v_info, a_info)
        self.tab_summary.set_size_info(w, h)
        self.tab_dimensions.set_source_dimensions(w, h)

        # Populate Audio tab with source audio tracks
        print(f"DEBUG: Loading audio tracks: {a_streams}")
        self.tab_audio.load_source_tracks(a_streams)

        # Populate Subtitles tab with source subtitle tracks
        self.tab_subtitles.load_source_tracks(s_streams)

        # Populate Chapters tab
        self.tab_chapters.load_chapters(chapters)

    def _generate_preview(self, path: str):
        try:
            tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
            tmp.close()
            subprocess.run([
                self.ffmpeg.ffmpeg_path, "-y",
                "-ss", "00:00:05", "-i", path,
                "-frames:v", "1", "-q:v", "5", tmp.name
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            pixmap = QPixmap(tmp.name)
            self.tab_summary.set_preview_image(pixmap)
            os.unlink(tmp.name)
        except Exception as e:
            print(f"Preview generation failed: {e}")

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
                self.tab_summary.combo_format.setCurrentText(fmt)

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
            combo = self.tab_video.combo_encoder
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
        s = self.tab_dimensions.get_settings()
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
        s = self.tab_filters.get_settings()
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
        s = self.tab_video.get_settings()
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
        tracks = self.tab_audio.get_settings()
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
        tracks = self.tab_subtitles.get_settings()
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
        settings = self.tab_chapters.get_settings()
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
        summary_opts = self.tab_summary.get_settings()

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
