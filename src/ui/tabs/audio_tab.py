"""
Audio Tab — HandBrake-style audio track management.
Each audio track row has: Source, Codec, Quality Mode, Bitrate/Quality,
Mixdown, Samplerate, Gain, DRC.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QSpinBox, QScrollArea, QFrame, QMenu,
)
from PySide6.QtCore import Qt, Signal


# ── Constants ────────────────────────────────────────────────
CODECS = [
    "AAC (avcodec)", "AAC Passthru", "AC3", "E-AC3",
    "TrueHD", "MP3", "MPEG Audio (mpga)",
    "Vorbis", "Opus",
    "FLAC 16-bit", "FLAC 24-bit",
    "ALAC 16-bit", "ALAC 24-bit",
]


BITRATES = [
    "64", "80", "96", "112", "128", "160",
    "192", "224", "256", "320", "384", "448", "512",
]

QUALITY_MODES = ["Bitrate:", "Quality:"]

QUALITY_VALUES = ["1", "2", "3", "4", "5"]

MIXDOWNS = [
    "Mono", "Mono (Left Only)", "Mono (Right Only)", "Stereo",
    "5.1 Surround", "6.1 Surround", "7.1 Surround",
]

SAMPLERATES = [
    "Auto", "8", "11.025", "12", "16", "22.05", "24",
    "32", "44.1", "48", "88.2", "96", "176.4", "192",
]

# Codec → FFmpeg encoder name
CODEC_MAP = {
    "AAC (avcodec)": "aac",
    "AAC Passthru":  "copy",
    "AC3":           "ac3",
    "E-AC3":         "eac3",
    "TrueHD":        "truehd",
    "MP3":           "libmp3lame",
    "MPEG Audio (mpga)": "mp2",
    "Vorbis":        "libvorbis",
    "Opus":          "libopus",
    "FLAC 16-bit":   "flac",

    "FLAC 24-bit":   "flac",
    "ALAC 16-bit":   "alac",
    "ALAC 24-bit":   "alac",
}


class AudioTrackRow(QFrame):
    """One audio track row with all controls."""
    remove_requested = Signal(object)   # emits self

    def __init__(self, track_label: str = "Track 1", parent=None):
        super().__init__(parent)
        self.setObjectName("audioTrackRow")
        self.setFrameShape(QFrame.StyledPanel)
        self.setFixedHeight(44)

        row = QHBoxLayout(self)
        row.setContentsMargins(6, 4, 6, 4)
        row.setSpacing(6)

        # ── Drag handle ──────────────────────────────────────
        handle = QLabel("≡")
        handle.setFixedWidth(18)
        handle.setStyleSheet("color: #888; font-size: 16px;")
        row.addWidget(handle)

        # ── Source ───────────────────────────────────────────
        self.combo_source = QComboBox()
        self.combo_source.addItem(track_label)
        self.combo_source.setMinimumWidth(180)
        row.addWidget(self.combo_source, 2)

        # ── Codec ────────────────────────────────────────────
        self.combo_codec = QComboBox()
        self.combo_codec.addItems(CODECS)
        self.combo_codec.setMinimumWidth(120)
        row.addWidget(self.combo_codec, 1)

        # ── Quality Mode (Bitrate / Quality) ────────────────
        self.combo_quality_mode = QComboBox()
        self.combo_quality_mode.addItems(QUALITY_MODES)
        self.combo_quality_mode.setFixedWidth(80)
        self.combo_quality_mode.currentTextChanged.connect(self._on_quality_mode_changed)
        row.addWidget(self.combo_quality_mode)

        # ── Bitrate / Quality value ──────────────────────────
        self.combo_value = QComboBox()
        self.combo_value.addItems(BITRATES)
        self.combo_value.setCurrentText("320")
        self.combo_value.setFixedWidth(60)
        row.addWidget(self.combo_value)

        # ── Mixdown ──────────────────────────────────────────
        self.combo_mixdown = QComboBox()
        self.combo_mixdown.addItems(MIXDOWNS)
        self.combo_mixdown.setCurrentText("Stereo")
        self.combo_mixdown.setMinimumWidth(110)
        row.addWidget(self.combo_mixdown, 1)

        # ── Samplerate ───────────────────────────────────────
        self.combo_samplerate = QComboBox()
        self.combo_samplerate.addItems(SAMPLERATES)
        self.combo_samplerate.setFixedWidth(65)
        row.addWidget(self.combo_samplerate)

        # ── Gain ─────────────────────────────────────────────
        self.spin_gain = QSpinBox()
        self.spin_gain.setRange(-20, 20)
        self.spin_gain.setValue(0)
        self.spin_gain.setSuffix(" dB")
        self.spin_gain.setFixedWidth(70)
        row.addWidget(self.spin_gain)

        # ── DRC ──────────────────────────────────────────────
        self.spin_drc = QSpinBox()
        self.spin_drc.setRange(0, 4)
        self.spin_drc.setValue(0)
        self.spin_drc.setFixedWidth(50)
        row.addWidget(self.spin_drc)

        # ── Remove button ────────────────────────────────────
        btn_remove = QPushButton("✕")
        btn_remove.setFixedSize(24, 24)
        btn_remove.setToolTip("Remove this track")
        btn_remove.setStyleSheet("""
            QPushButton {
                background: transparent; color: #888;
                border: none; font-size: 14px;
            }
            QPushButton:hover { color: #e74c3c; }
        """)
        btn_remove.clicked.connect(lambda: self.remove_requested.emit(self))
        row.addWidget(btn_remove)

        # Wire codec change to toggle passthru controls
        self.combo_codec.currentTextChanged.connect(self._on_codec_changed)

    def _on_quality_mode_changed(self, mode: str):
        """Switch value dropdown between bitrate values and quality 1-5."""
        self.combo_value.blockSignals(True)
        self.combo_value.clear()
        if mode == "Quality:":
            self.combo_value.addItems(QUALITY_VALUES)
            self.combo_value.setCurrentText("3")
        else:
            self.combo_value.addItems(BITRATES)
            self.combo_value.setCurrentText("320")
        self.combo_value.blockSignals(False)

    def _on_codec_changed(self, codec: str):
        """Disable bitrate/mixdown controls for passthru codecs."""
        is_passthru = "Passthru" in codec
        self.combo_quality_mode.setEnabled(not is_passthru)
        self.combo_value.setEnabled(not is_passthru)
        self.combo_mixdown.setEnabled(not is_passthru)
        self.combo_samplerate.setEnabled(not is_passthru)
        self.spin_gain.setEnabled(not is_passthru)
        self.spin_drc.setEnabled(not is_passthru)

    def get_settings(self) -> dict:
        """Return current settings for this audio track."""
        codec_text = self.combo_codec.currentText()
        return {
            "codec":       codec_text,
            "encoder":     CODEC_MAP.get(codec_text, "aac"),
            "quality_mode": self.combo_quality_mode.currentText(),
            "value":       self.combo_value.currentText(),
            "mixdown":     self.combo_mixdown.currentText(),
            "samplerate":  self.combo_samplerate.currentText(),
            "gain":        self.spin_gain.value(),
            "drc":         self.spin_drc.value(),
            "is_24bit":    "24-bit" in codec_text,
            "is_passthru": "Passthru" in codec_text,
        }


class AudioTab(QWidget):
    """Audio tab with track list and toolbar."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tracks: list[AudioTrackRow] = []
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

        # ─── Toolbar ─────────────────────────────────────────
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        self.btn_tracks = QPushButton("Tracks ▾")
        self.btn_tracks.setFixedHeight(28)
        self.btn_tracks.clicked.connect(self._show_tracks_menu)
        toolbar.addWidget(self.btn_tracks)

        self.btn_selection = QPushButton("Selection Behavior …")
        self.btn_selection.setFixedHeight(28)
        toolbar.addWidget(self.btn_selection)

        self.btn_reload = QPushButton("Reload")
        self.btn_reload.setFixedHeight(28)
        self.btn_reload.clicked.connect(self._reload_tracks)
        toolbar.addWidget(self.btn_reload)

        toolbar.addStretch()
        main_layout.addLayout(toolbar)

        # ─── Column Headers ──────────────────────────────────
        header = QHBoxLayout()
        header.setContentsMargins(24, 0, 30, 0)
        header.setSpacing(6)

        headers = [
            ("Source", 2), ("Codec", 1), ("Quality", 0),
            ("", 0), ("Mixdown", 1), ("Samplerate", 0),
            ("Gain", 0), ("DRC", 0),
        ]
        for text, stretch in headers:
            lbl = QLabel(text)
            lbl.setStyleSheet("color: #aaa; font-weight: bold; font-size: 11px;")
            if stretch:
                header.addWidget(lbl, stretch)
            else:
                min_w = {"Quality": 80, "": 60, "Samplerate": 65,
                         "Gain": 70, "DRC": 50}.get(text, 60)
                lbl.setFixedWidth(min_w)
                header.addWidget(lbl)

        main_layout.addLayout(header)

        # ─── Separator ───────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #444;")
        main_layout.addWidget(sep)

        # ─── Track List (scrollable) ─────────────────────────
        self.track_list_layout = QVBoxLayout()
        self.track_list_layout.setSpacing(4)
        self.track_list_layout.setAlignment(Qt.AlignTop)

        track_container = QWidget()
        track_container.setLayout(self.track_list_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(track_container)
        scroll.setFrameShape(QFrame.NoFrame)
        main_layout.addWidget(scroll, 1)

        # ─── Add default track ───────────────────────────────
        self.add_track(label="Track 1 (Default)")

    # ── Track management ─────────────────────────────────────

    def add_track(self, label: str = ""):
        """Add a new audio track row."""
        if not label:
            label = f"Track {len(self._tracks) + 1}"
        track = AudioTrackRow(label, self)
        track.remove_requested.connect(self._remove_track)
        self.track_list_layout.addWidget(track)
        self._tracks.append(track)

    def _remove_track(self, track: AudioTrackRow):
        """Remove an audio track row (keep at least one)."""
        if len(self._tracks) <= 1:
            return
        self.track_list_layout.removeWidget(track)
        self._tracks.remove(track)
        track.deleteLater()

    def _show_tracks_menu(self):
        """Show dropdown menu for track management."""
        menu = QMenu(self)
        menu.addAction("Add New Track", lambda: self.add_track(
            f"Track {len(self._tracks) + 1}"
        ))
        menu.addSeparator()
        menu.addAction("Add All Remaining Tracks")
        menu.addAction("Clear All Extra Tracks", self._clear_extra_tracks)
        menu.exec(self.btn_tracks.mapToGlobal(
            self.btn_tracks.rect().bottomLeft()
        ))

    def _clear_extra_tracks(self):
        """Remove all tracks except the first one."""
        while len(self._tracks) > 1:
            track = self._tracks.pop()
            self.track_list_layout.removeWidget(track)
            track.deleteLater()

    def _reload_tracks(self):
        """Reload track list (placeholder — will be wired to FFprobe)."""
        pass

    def load_source_tracks(self, audio_streams: list[dict]):
        """Auto-populate track rows from FFprobe audio stream metadata.
        Each dict should have: codec_name, channels, tags (with language), etc."""
        # Clear existing tracks
        while self._tracks:
            track = self._tracks.pop()
            self.track_list_layout.removeWidget(track)
            track.deleteLater()

        if not audio_streams:
            # No audio in source — add a disabled placeholder
            self.add_track("No Audio")
            return

        for idx, stream in enumerate(audio_streams):
            codec = stream.get("codec_name", "unknown")
            channels = stream.get("channels", 2)
            lang = stream.get("tags", {}).get("language", "und")
            ch_label = {1: "Mono", 2: "Stereo", 6: "5.1", 8: "7.1"}.get(
                channels, f"{channels}ch"
            )
            label = f"{idx + 1}  {lang} ({codec}, {ch_label})"
            self.add_track(label)

            # Auto-set mixdown based on source channels
            track = self._tracks[-1]
            if channels >= 8:
                track.combo_mixdown.setCurrentText("7.1 Surround")
            elif channels >= 6:
                track.combo_mixdown.setCurrentText("5.1 Surround")
            elif channels == 1:
                track.combo_mixdown.setCurrentText("Mono")
            else:
                track.combo_mixdown.setCurrentText("Stereo")

    def get_settings(self) -> list[dict]:
        """Return settings for all audio tracks."""
        return [t.get_settings() for t in self._tracks]
