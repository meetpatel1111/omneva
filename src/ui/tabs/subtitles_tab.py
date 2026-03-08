"""
Subtitles Tab — HandBrake-style subtitle track management.
Each subtitle track row has: Source, Language, Forced, Burn In, Default, Offset.
Supports embedded subtitles from source and importing external SRT/ASS files.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QSpinBox, QScrollArea, QFrame, QMenu,
    QCheckBox, QFileDialog,
)
from PySide6.QtCore import Qt, Signal


class SubtitleTrackRow(QFrame):
    """One subtitle track row with all controls."""
    remove_requested = Signal(object)

    def __init__(self, track_label: str = "Track 1", is_external: bool = False, parent=None):
        super().__init__(parent)
        self.setObjectName("subtitleTrackRow")
        self.setFrameShape(QFrame.StyledPanel)
        self.setFixedHeight(44)
        self._is_external = is_external
        self._external_path = ""

        row = QHBoxLayout(self)
        row.setContentsMargins(6, 4, 6, 4)
        row.setSpacing(8)

        # ── Drag handle ──────────────────────────────────────
        handle = QLabel("≡")
        handle.setFixedWidth(18)
        handle.setStyleSheet("color: #888; font-size: 16px;")
        row.addWidget(handle)

        # ── Source ───────────────────────────────────────────
        self.combo_source = QComboBox()
        self.combo_source.addItem(track_label)
        self.combo_source.setMinimumWidth(220)
        row.addWidget(self.combo_source, 3)

        # ── Forced Only ──────────────────────────────────────
        self.chk_forced = QCheckBox("Forced")
        self.chk_forced.setToolTip("Include forced subtitles only")
        row.addWidget(self.chk_forced)

        # ── Burn In ──────────────────────────────────────────
        self.chk_burn_in = QCheckBox("Burn In")
        self.chk_burn_in.setToolTip("Hardcode subtitles into video")
        row.addWidget(self.chk_burn_in)

        # ── Default ──────────────────────────────────────────
        self.chk_default = QCheckBox("Default")
        self.chk_default.setToolTip("Set as default subtitle track")
        row.addWidget(self.chk_default)

        # ── Offset (ms) ─────────────────────────────────────
        lbl_offset = QLabel("Offset:")
        lbl_offset.setStyleSheet("color: #aaa;")
        row.addWidget(lbl_offset)

        self.spin_offset = QSpinBox()
        self.spin_offset.setRange(-10000, 10000)
        self.spin_offset.setValue(0)
        self.spin_offset.setSuffix(" ms")
        self.spin_offset.setSingleStep(100)
        self.spin_offset.setFixedWidth(90)
        row.addWidget(self.spin_offset)

        row.addStretch()

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

    def get_settings(self) -> dict:
        """Return current settings for this subtitle track."""
        return {
            "source":      self.combo_source.currentText(),
            "forced":      self.chk_forced.isChecked(),
            "burn_in":     self.chk_burn_in.isChecked(),
            "default":     self.chk_default.isChecked(),
            "offset":      self.spin_offset.value(),
            "is_external": self._is_external,
            "external_path": self._external_path,
        }


class SubtitlesTab(QWidget):
    """Subtitles tab with track list and toolbar."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tracks: list[SubtitleTrackRow] = []
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

        self.btn_import = QPushButton("Import SRT / ASS …")
        self.btn_import.setFixedHeight(28)
        self.btn_import.clicked.connect(self._import_external)
        toolbar.addWidget(self.btn_import)

        self.btn_reload = QPushButton("Reload")
        self.btn_reload.setFixedHeight(28)
        toolbar.addWidget(self.btn_reload)

        toolbar.addStretch()
        main_layout.addLayout(toolbar)

        # ─── Column Headers ──────────────────────────────────
        header = QHBoxLayout()
        header.setContentsMargins(24, 0, 30, 0)
        header.setSpacing(8)

        for text, stretch, width in [
            ("Source", 3, 0), ("Forced", 0, 55), ("Burn In", 0, 60),
            ("Default", 0, 60), ("Offset", 0, 130),
        ]:
            lbl = QLabel(text)
            lbl.setStyleSheet("color: #aaa; font-weight: bold; font-size: 11px;")
            if stretch:
                header.addWidget(lbl, stretch)
            else:
                lbl.setFixedWidth(width)
                header.addWidget(lbl)

        header.addStretch()
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

    # ── Track Management ─────────────────────────────────────

    def add_track(self, label: str, is_external: bool = False, ext_path: str = ""):
        """Add a subtitle track row."""
        track = SubtitleTrackRow(label, is_external, self)
        track._external_path = ext_path
        track.remove_requested.connect(self._remove_track)
        self.track_list_layout.addWidget(track)
        self._tracks.append(track)

    def _remove_track(self, track: SubtitleTrackRow):
        """Remove a subtitle track row."""
        self.track_list_layout.removeWidget(track)
        if track in self._tracks:
            self._tracks.remove(track)
        track.deleteLater()

    def _show_tracks_menu(self):
        """Show dropdown menu for track management."""
        menu = QMenu(self)
        menu.addAction("Add All Remaining Tracks")
        menu.addSeparator()
        menu.addAction("Clear All Tracks", self._clear_all_tracks)
        menu.exec(self.btn_tracks.mapToGlobal(
            self.btn_tracks.rect().bottomLeft()
        ))

    def _clear_all_tracks(self):
        """Remove all subtitle tracks."""
        while self._tracks:
            track = self._tracks.pop()
            self.track_list_layout.removeWidget(track)
            track.deleteLater()

    def _import_external(self):
        """Import an external SRT/ASS/SSA subtitle file."""
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Import Subtitle File", "",
            "Subtitle Files (*.srt *.ass *.ssa *.sub *.idx *.vtt);;All Files (*)",
        )
        for path in paths:
            import os
            name = os.path.basename(path)
            self.add_track(f"[EXT] {name}", is_external=True, ext_path=path)

    def load_source_tracks(self, subtitle_streams: list[dict]):
        """Auto-populate track rows from FFprobe subtitle stream metadata."""
        self._clear_all_tracks()

        for idx, stream in enumerate(subtitle_streams):
            codec = stream.get("codec_name", "unknown")
            lang = stream.get("tags", {}).get("language", "und")
            title = stream.get("tags", {}).get("title", "")
            forced = stream.get("disposition", {}).get("forced", 0)

            label = f"{idx + 1}  {lang}"
            if title:
                label += f" — {title}"
            label += f" ({codec})"

            self.add_track(label)

            # Auto-check forced if disposition says so
            if forced:
                self._tracks[-1].chk_forced.setChecked(True)

    def get_settings(self) -> list[dict]:
        """Return settings for all subtitle tracks."""
        return [t.get_settings() for t in self._tracks]
