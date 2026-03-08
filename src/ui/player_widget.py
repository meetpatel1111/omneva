"""Player Widget — VLC video display + overlay controls (VLC-style)."""

import os
import random
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QFrame, QSizePolicy, QFileDialog, QGraphicsOpacityEffect,
    QListView, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QMouseEvent, QCursor, QIcon

from src.core.vlc_engine import VLCEngine
from src.core.ffprobe_service import FFprobeService
from src.core.utils import format_duration, get_icon
from src.core.playlist_model import PlaylistModel


class VideoSurface(QFrame):
    """Widget where VLC renders video. Shows drag-drop zone when empty."""

    double_clicked = Signal()
    clicked = Signal()
    mouse_moved = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("videoSurface")
        self.setAcceptDrops(True)
        self.setMinimumSize(320, 240)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet("background-color: #000;")
        self.setMouseTracking(True)

        # Placeholder label
        self._placeholder = QLabel(
            "🎬\n\nDrop a file or click Open\nto start playing", self
        )
        self._placeholder.setObjectName("videoPlaceholder")
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._placeholder.setStyleSheet("color: #555; font-size: 16px;")

        layout = QVBoxLayout(self)
        layout.addWidget(self._placeholder)

    def hide_placeholder(self):
        self._placeholder.hide()

    def show_placeholder(self):
        self._placeholder.show()

    def mouseDoubleClickEvent(self, event):
        self.double_clicked.emit()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        elif event.button() == Qt.RightButton:
            # Manually trigger context menu if policy is CustomContextMenu
            if self.contextMenuPolicy() == Qt.CustomContextMenu:
                self.customContextMenuRequested.emit(event.pos())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        self.mouse_moved.emit()
        super().mouseMoveEvent(event)


class PlaylistPanel(QWidget):
    """Side panel for displaying docked playlist (Simple List)."""
    
    file_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(250)
        self.setObjectName("playlistPanel")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header = QLabel("  Docked Playlist")
        header.setObjectName("playlistHeader")
        header.setFixedHeight(30)
        layout.addWidget(header)
        
        # List View
        self.list_view = QListView()
        self.list_view.setObjectName("playlistList")
        self.list_view.setFrameShape(QFrame.NoFrame)
        self.list_view.setAlternatingRowColors(True)
        self.list_view.doubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.list_view)
        
        self._model = None

    def set_model(self, model: PlaylistModel):
        self._model = model
        self.list_view.setModel(model)

    def _on_item_double_clicked(self, index):
        if self._model:
            path = self._model.get_path(index.row())
            if path:
                self.file_requested.emit(path)

    def select_row(self, row):
        if row >= 0:
            idx = self._model.index(row, 0)
            self.list_view.setCurrentIndex(idx)


class OverlayControls(QWidget):
    """Controls bar that overlays on top of video."""
    
    tracks_menu_requested = Signal()
    speed_menu_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("playerControls")
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 6, 16, 8)
        layout.setSpacing(4)

        # ─── Advanced Controls Row (Hidden by default) ──────
        self.advanced_widget = QWidget()
        self.advanced_widget.setVisible(False)
        adv_layout = QHBoxLayout(self.advanced_widget)
        adv_layout.setContentsMargins(0, 0, 0, 0)
        adv_layout.setSpacing(10)

        self.btn_adv_record = QPushButton("⬤")
        self.btn_adv_record.setToolTip("Record")
        self.btn_adv_record.setCheckable(True)
        self.btn_adv_record.setFixedSize(30, 30)
        self.btn_adv_record.setStyleSheet("QPushButton { color: #f44336; } QPushButton:checked { background-color: #f44336; color: white; }")

        self.btn_adv_snapshot = QPushButton("📷")
        self.btn_adv_snapshot.setToolTip("Take Snapshot")
        self.btn_adv_snapshot.setFixedSize(30, 30)

        self.btn_adv_frame = QPushButton("I>")
        self.btn_adv_frame.setToolTip("Frame by Frame")
        self.btn_adv_frame.setFixedSize(30, 30)
        
        self.btn_adv_loop_ab = QPushButton("AB")
        self.btn_adv_loop_ab.setToolTip("Loop A-B (Not implemented)")
        self.btn_adv_loop_ab.setFixedSize(30, 30)
        self.btn_adv_loop_ab.setEnabled(False)

        adv_layout.addStretch()
        adv_layout.addWidget(self.btn_adv_record)
        adv_layout.addWidget(self.btn_adv_snapshot)
        adv_layout.addWidget(self.btn_adv_loop_ab)
        adv_layout.addWidget(self.btn_adv_frame)
        adv_layout.addStretch()

        layout.addWidget(self.advanced_widget)

        # ─── Seek bar ────────────────────────────────────────
        seek_row = QHBoxLayout()
        seek_row.setSpacing(8)

        self.lbl_time = QLabel("00:00")
        self.lbl_time.setObjectName("timeLabel")
        self.lbl_time.setFixedWidth(55)
        self.lbl_time.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.setObjectName("seekSlider")
        self.seek_slider.setRange(0, 1000)
        self.seek_slider.setValue(0)

        self.lbl_duration = QLabel("00:00")
        self.lbl_duration.setObjectName("durationLabel")
        self.lbl_duration.setFixedWidth(55)

        seek_row.addWidget(self.lbl_time)
        seek_row.addWidget(self.seek_slider, 1)
        seek_row.addWidget(self.lbl_duration)
        layout.addLayout(seek_row)

        # ─── Buttons row ────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_open = QPushButton("📂")
        self.btn_open.setToolTip("Open File")
        self.btn_open.setFixedSize(30, 30)

        self.btn_playlist = QPushButton("≣")
        self.btn_playlist.setToolTip("Toggle Docked Playlist")
        self.btn_playlist.setCheckable(True)
        self.btn_playlist.setFixedSize(30, 30)
        
        # Jumps
        self.btn_jump_back = QPushButton("-10s")
        self.btn_jump_back.setFixedSize(40, 30)
        
        self.btn_prev = QPushButton("⏮")
        self.btn_prev.setFixedSize(36, 30)

        self.btn_play = QPushButton("")
        self.btn_play.setIcon(get_icon("play.svg"))
        self.btn_play.setObjectName("btnPlay")
        self.btn_play.setFixedSize(44, 30)

        self.btn_next = QPushButton("⏭")
        self.btn_next.setFixedSize(36, 30)
        
        self.btn_jump_fwd = QPushButton("+10s")
        self.btn_jump_fwd.setFixedSize(40, 30)

        self.btn_stop = QPushButton("")
        self.btn_stop.setIcon(get_icon("stop.svg"))
        self.btn_stop.setFixedSize(36, 30)

        self.btn_mute = QPushButton("")
        self.btn_mute.setIcon(get_icon("volume-high.svg"))
        self.btn_mute.setFixedSize(30, 30)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        self.volume_slider.setFixedWidth(80)

        self.btn_loop = QPushButton("🔁")
        self.btn_loop.setToolTip("Toggle Loop")
        self.btn_loop.setCheckable(True)
        self.btn_loop.setFixedSize(30, 30)

        self.btn_shuffle = QPushButton("🔀")
        self.btn_shuffle.setToolTip("Toggle Shuffle")
        self.btn_shuffle.setCheckable(True)
        self.btn_shuffle.setFixedSize(30, 30)
        
        self.btn_speed = QPushButton("1.0x")
        self.btn_speed.setToolTip("Playback Speed")
        self.btn_speed.setFixedSize(40, 30)
        self.btn_speed.clicked.connect(self.speed_menu_requested.emit)

        self.btn_tracks = QPushButton("⚙ Tracks")
        self.btn_tracks.setFixedHeight(30)
        self.btn_tracks.clicked.connect(self.tracks_menu_requested.emit)
        
        # Apply NoFocus to all buttons to prevent them from stealing Space key
        for btn in self.findChildren(QPushButton):
            btn.setFocusPolicy(Qt.NoFocus)

        self.lbl_info = QLabel("")
        self.lbl_info.setObjectName("mediaInfo")
        self.lbl_info.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_info.hide() 

        self.btn_fullscreen = QPushButton("⛶")
        self.btn_fullscreen.setFixedSize(30, 30)

        btn_row.addWidget(self.btn_open)
        btn_row.addWidget(self.btn_playlist)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_loop)
        btn_row.addWidget(self.btn_shuffle)
        btn_row.addWidget(self.btn_jump_back)
        btn_row.addWidget(self.btn_prev)
        btn_row.addWidget(self.btn_play)
        btn_row.addWidget(self.btn_next)
        btn_row.addWidget(self.btn_jump_fwd)
        btn_row.addWidget(self.btn_stop)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_speed)
        btn_row.addWidget(self.btn_tracks)
        btn_row.addWidget(self.btn_mute)
        btn_row.addWidget(self.volume_slider)
        btn_row.addWidget(self.btn_fullscreen)

        layout.addLayout(btn_row)


class PlayerWidget(QWidget):
    """Full media player with VLC engine and VLC-style overlay controls."""

    # Signals to MainWindow
    fullscreen_requested = Signal()
    title_changed = Signal(str)
    context_menu_requested = Signal(object) # pos
    snapshot_requested = Signal()
    jump_to_time_requested = Signal()
    resize_requested = Signal(float)
    help_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("playerWidget")
        self.setMouseTracking(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)

        self.vlc = VLCEngine()
        self.ffprobe = FFprobeService()
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAcceptDrops(True)
        self._is_seeking = False
        self._controls_visible = True
        self._current_file = None
        self._is_fullscreen = False

        self.playlist_model = PlaylistModel()

        self._setup_ui()
        self._connect_signals()

        # Auto-hide controls timer (VLC-style: hide after 3s)
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.setInterval(3000)
        self._hide_timer.timeout.connect(self._auto_hide_controls)

        # Cursor hide timer
        self._cursor_timer = QTimer(self)
        self._cursor_timer.setSingleShot(True)
        self._cursor_timer.setInterval(3200)
        self._cursor_timer.timeout.connect(self._hide_cursor)

    def _setup_ui(self):
        # HBox for playlist + video
        self._main_hbox = QHBoxLayout(self)
        self._main_hbox.setContentsMargins(0, 0, 0, 0)
        self._main_hbox.setSpacing(0)
        
        # Center container (Video + Controls)
        self._center_container = QWidget()
        self._center_layout = QVBoxLayout(self._center_container)
        self._center_layout.setContentsMargins(0, 0, 0, 0)
        self._center_layout.setSpacing(0)

        # ─── Video Surface ──────────────────────────────────
        self.video_surface = VideoSurface()
        self.video_surface.setContextMenuPolicy(Qt.CustomContextMenu)
        self.video_surface.customContextMenuRequested.connect(self._on_context_menu)
        self._center_layout.addWidget(self.video_surface, 1)

        # ─── Controls (overlay-capable) ─────────────────────
        self.controls = OverlayControls(self)
        self._center_layout.addWidget(self.controls)
        
        # Add center to main HBox
        self._main_hbox.addWidget(self._center_container, 1)
        
        # ─── Docked Playlist Panel ─────────────────────────
        self.playlist_panel = PlaylistPanel()
        self.playlist_panel.set_model(self.playlist_model)
        self.playlist_panel.hide() # Hidden by default
        self._main_hbox.addWidget(self.playlist_panel)

    def _on_context_menu(self, pos):
        """Emit context menu request with global position."""
        global_pos = self.sender().mapToGlobal(pos)
        self.context_menu_requested.emit(global_pos)

    def _connect_signals(self):
        # VLC engine → UI
        self.vlc.position_changed.connect(self._on_position_changed)
        self.vlc.duration_changed.connect(self._on_duration_changed)
        self.vlc.state_changed.connect(self._on_state_changed)
        self.vlc.volume_changed.connect(self._on_volume_changed)

        # UI → VLC engine
        self.controls.btn_play.clicked.connect(self._toggle_play)
        self.controls.btn_stop.clicked.connect(self.vlc.stop)
        self.controls.btn_mute.clicked.connect(self.vlc.toggle_mute)
        self.controls.btn_open.clicked.connect(self._open_file)
        self.controls.btn_fullscreen.clicked.connect(self._request_fullscreen)
        
        # New buttons
        self.controls.btn_jump_back.clicked.connect(lambda: self.vlc.seek_relative(-10))
        self.controls.btn_jump_fwd.clicked.connect(lambda: self.vlc.seek_relative(10))
        self.controls.btn_prev.clicked.connect(self._play_prev)
        self.controls.btn_next.clicked.connect(self._play_next)
        
        # Advanced Buttons
        self.controls.btn_adv_record.clicked.connect(self._toggle_record)
        self.controls.btn_adv_snapshot.clicked.connect(self.snapshot_requested.emit)
        self.controls.btn_adv_frame.clicked.connect(self.vlc.next_frame)
        
        self.controls.btn_playlist.toggled.connect(self._toggle_playlist_panel)
        self.controls.tracks_menu_requested.connect(self._show_tracks_menu)
        self.controls.speed_menu_requested.connect(self._show_speed_menu)
        
        self.vlc.mute_changed.connect(self._on_mute_changed)

        # Playlist Signal (Docked)
        self.playlist_panel.file_requested.connect(self.load_and_play)

        # Seek slider
        self.controls.seek_slider.sliderPressed.connect(self._on_seek_pressed)
        self.controls.seek_slider.sliderReleased.connect(self._on_seek_released)

        # Volume slider
        self.controls.volume_slider.valueChanged.connect(self.vlc.set_volume)

        # Video surface
        self.video_surface.clicked.connect(self._on_surface_clicked)
        self.video_surface.double_clicked.connect(self._request_fullscreen)
        self.video_surface.mouse_moved.connect(self._on_mouse_activity)

    # ─── Public API ──────────────────────────────────────────

    def set_advanced_visible(self, visible: bool):
        """Toggle advanced controls row."""
        self.controls.advanced_widget.setVisible(visible)
        # Resize/Reposition if needed (layout handles it usually, but if overlay...)
        if self._is_fullscreen:
            self._reposition_overlay()

    def load_and_play(self, file_path: str):
        """Load a media file and start playing."""
        if not os.path.isfile(file_path):
            return
            
        # Add to playlist if not present
        idx = self.playlist_model.add_file(file_path)
            
        self._current_file = file_path
        self.playlist_model.set_current_index(idx)
        self.playlist_panel.select_row(idx)

        self.video_surface.hide_placeholder()

        # Embed VLC into the video surface
        win_id = int(self.video_surface.winId())
        self.vlc.set_window(win_id)
        self.vlc.play(file_path)

        # Update filename in titlebar (like VLC: "filename - VLC media player")
        basename = os.path.basename(file_path)
        self.title_changed.emit(basename)
        self.controls.lbl_info.setText(basename)

        # Get metadata for duration
        meta = self.ffprobe.get_metadata(file_path)
        if "error" not in meta:
            dur = meta["format"]["duration"]
            self.controls.lbl_duration.setText(format_duration(dur))
            # Update model with metadata
            self.playlist_model.update_metadata(file_path, duration=dur)
            
    def _play_next(self):
        count = self.playlist_model.rowCount()
        if count == 0: return

        current_idx = self.playlist_model.get_current_index()
        next_idx = -1
        
        if self.controls.btn_shuffle.isChecked():
            next_idx = random.randint(0, count - 1)
        else:
            next_idx = current_idx + 1
            # Loop check
            if next_idx >= count:
                if self.controls.btn_loop.isChecked():
                    next_idx = 0
                else:
                    self.vlc.stop()
                    return

        path = self.playlist_model.get_path(next_idx)
        if path:
            self.load_and_play(path)
        
    def _play_prev(self):
        count = self.playlist_model.rowCount()
        if count == 0: return
        
        current_idx = self.playlist_model.get_current_index()
        prev_idx = (current_idx - 1) % count
        
        path = self.playlist_model.get_path(prev_idx)
        if path:
            self.load_and_play(path)

    def _toggle_playlist_panel(self, checked):
        self.playlist_panel.setVisible(checked)

    def _toggle_play(self):
        self.vlc.toggle_play_pause()

    def _request_fullscreen(self):
        self.fullscreen_requested.emit()

    def _toggle_record(self):
        path = self.vlc.toggle_record()
        # Provide feedback
        if self.vlc.is_recording:
             self.controls.btn_adv_record.setStyleSheet("QPushButton { background-color: #f44336; color: white; border: 1px solid #d32f2f; }")
        else:
             self.controls.btn_adv_record.setStyleSheet("QPushButton { color: #f44336; background-color: transparent; }")

    def set_fullscreen_mode(self, entering: bool):
        """Called by MainWindow when entering/exiting fullscreen."""
        self._is_fullscreen = entering
        if entering:
            # Remove controls from layout, make them overlay
            self._center_layout.removeWidget(self.controls)
            self.controls.setParent(self)
            self.controls.setObjectName("playerControlsOverlay")
            self._reposition_overlay()
            self.controls.show()
            self.controls.raise_()
            self._hide_timer.start()
            self.playlist_panel.hide() # Force hide docked playlist in fullscreen
            self.setFocus() # Ensure we get key events
        else:
            # Return controls to layout
            self.controls.setObjectName("playerControls")
            self._center_layout.addWidget(self.controls)
            self._show_controls()
            self.setCursor(Qt.ArrowCursor)
            self.video_surface.setCursor(Qt.ArrowCursor)
            self._hide_timer.stop()
            self._cursor_timer.stop()
            
            # Restore playlist visibility if button checked
            if self.controls.btn_playlist.isChecked():
                self.playlist_panel.show()

    def _reposition_overlay(self):
        """Position the overlay controls at the bottom of the widget."""
        if self._is_fullscreen and self.controls:
            w = self.width()
            h = self.controls.height() # This will include advanced row if visible
            self.controls.setGeometry(0, self.height() - h, w, h)

    def resizeEvent(self, event):
        """Keep overlay positioned at bottom on resize."""
        super().resizeEvent(event)
        if self._is_fullscreen:
            self._reposition_overlay()

    # ─── Event Handlers ─────────────────────────────────────

    def _on_position_changed(self, pos: float):
        """Update seek slider and time label."""
        if not self._is_seeking:
            self.controls.seek_slider.blockSignals(True)
            self.controls.seek_slider.setValue(int(pos * 1000))
            self.controls.seek_slider.blockSignals(False)
        
        self.controls.lbl_time.setText(format_duration(pos))

    def _on_duration_changed(self, dur: float):
        """Update slider range and duration label."""
        self.controls.seek_slider.setMaximum(int(dur * 1000))
        self.controls.lbl_duration.setText(format_duration(dur))

    def _on_state_changed(self, state: str):
        """Handle player state changes."""
        if state == "playing":
            self.controls.btn_play.setIcon(get_icon("pause.svg"))
        elif state in ("paused", "stopped"):
            self.controls.btn_play.setIcon(get_icon("play.svg"))
        elif state == "ended":
            self.controls.btn_play.setIcon(get_icon("play.svg"))
            # Auto-play next
            QTimer.singleShot(0, self._play_next)

    def _on_volume_changed(self, vol: int):
        """Update volume slider and mute icon."""
        self.controls.volume_slider.blockSignals(True)
        self.controls.volume_slider.setValue(vol)
        self.controls.volume_slider.blockSignals(False)
        
        if not self.vlc.is_muted():
            if vol == 0:
                self.controls.btn_mute.setIcon(get_icon("volume-mute.svg"))
            elif vol < 50:
                self.controls.btn_mute.setIcon(get_icon("volume-low.svg"))
            else:
                self.controls.btn_mute.setIcon(get_icon("volume-high.svg"))

    def _on_mute_changed(self, muted: bool):
        """Update mute button icon when mute state changes."""
        if muted:
            self.controls.btn_mute.setIcon(get_icon("volume-mute.svg"))
        else:
            vol = self.controls.volume_slider.value()
            if vol == 0:
                self.controls.btn_mute.setIcon(get_icon("volume-mute.svg"))
            elif vol < 50:
                self.controls.btn_mute.setIcon(get_icon("volume-low.svg"))
            else:
                self.controls.btn_mute.setIcon(get_icon("volume-high.svg"))

    def _on_seek_pressed(self):
        """User started dragging seek slider."""
        self._is_seeking = True

    def _on_seek_released(self):
        """User finished dragging."""
        self._is_seeking = False
        val = self.controls.seek_slider.value()
        seconds = val / 1000.0
        self.vlc.seek(seconds)

    def _on_mouse_activity(self):
        """Show controls when mouse moves in fullscreen."""
        if self._is_fullscreen:
            self._show_controls()
            self._hide_timer.start(3000) # Hide after 3s

    def _show_controls(self):
        """Show the controls overlay."""
        self.controls.show()
        self.setCursor(Qt.ArrowCursor)

    def _auto_hide_controls(self):
        """Hide the controls overlay."""
        if self._is_fullscreen:
            self.controls.hide()
            self.setCursor(Qt.BlankCursor) # Hide cursor

    def _hide_cursor(self):
        """Hide cursor in fullscreen."""
        if self._is_fullscreen:
            self.setCursor(Qt.BlankCursor)

    # ─── File Dialog ─────────────────────────────────────────

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Media File",
            "",
            "Media Files (*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.webm *.m4v "
            "*.mp3 *.flac *.wav *.aac *.ogg *.wma *.m4a *.opus);;All Files (*)",
        )
        if path:
            self.load_and_play(path)
    
    def _on_surface_clicked(self):
        """Clicking surface opens file if empty, otherwise toggles play."""
        if not self._current_file:
            self._open_file()
        else:
            self._toggle_play()

    def _show_tracks_menu(self):
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QAction
        
        menu = QMenu(self)
        
        # Audio Tracks
        a_menu = menu.addMenu("Audio Tracks")
        tracks = self.vlc.get_audio_tracks()
        if not tracks:
            a_menu.addAction("No audio tracks").setEnabled(False)
        else:
            for tid, name in tracks.items():
                act = a_menu.addAction(name)
                act.triggered.connect(lambda checked=False, t=tid: self.vlc.set_audio_track(t))
        
        # Subtitle Tracks
        s_menu = menu.addMenu("Subtitle Tracks")
        subs = self.vlc.get_subtitle_tracks()
        if not subs:
            s_menu.addAction("No subtitle tracks").setEnabled(False)
        else:
            for tid, name in subs.items():
                act = s_menu.addAction(name)
                act.triggered.connect(lambda checked=False, t=tid: self.vlc.set_subtitle_track(t))
                
        menu.exec(QCursor.pos())

    def _show_speed_menu(self):
        from PySide6.QtWidgets import QMenu, QActionGroup
        menu = QMenu(self)
        
        speeds = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 4.0]
        group = QActionGroup(menu)
        current = self.vlc.get_rate()
        
        for s in speeds:
            act = menu.addAction(f"{s}x")
            act.setCheckable(True)
            if abs(current - s) < 0.01:
                act.setChecked(True)
            act.triggered.connect(lambda checked=False, rate=s: self._set_speed(rate))
            group.addAction(act)
            
        menu.exec(QCursor.pos())

    def _set_speed(self, rate):
        self.vlc.set_rate(rate)
        self.controls.btn_speed.setText(f"{rate}x")

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts directly in the widget."""
        key = event.key()
        modifiers = event.modifiers()
        
        # ─── Playback ───
        if key == Qt.Key_Space:
            self._toggle_play()
        elif key == Qt.Key_S:
            self.vlc.stop()
        elif key == Qt.Key_N:
            self._play_next()
        elif key == Qt.Key_P:
            self._play_prev()
        elif key == Qt.Key_E:
            self.vlc.next_frame()
        elif key == Qt.Key_R:
            self.controls.btn_shuffle.click() # Reuse existing toggle logic
            self._show_info(f"Shuffle: {'On' if self.controls.btn_shuffle.isChecked() else 'Off'}")
        elif key == Qt.Key_L:
            self.controls.btn_loop.click() 
            self._show_info(f"Loop: {'On' if self.controls.btn_loop.isChecked() else 'Off'}")

        # ─── Volume / Audio ───
        elif key == Qt.Key_M:
            if modifiers & Qt.ShiftModifier:
                 self.vlc.toggle_disc_menu()
                 self._show_info("Disc Menu")
            else:
                self.vlc.toggle_mute()
        elif key == Qt.Key_Up:
            if modifiers & Qt.ControlModifier:
                 self.vlc.volume_up()
            else:
                 self.vlc.navigate_up()
        elif key == Qt.Key_Down:
            if modifiers & Qt.ControlModifier:
                 self.vlc.volume_down()
            else:
                 self.vlc.navigate_down()
        elif key in (Qt.Key_Return, Qt.Key_Enter):
             self.vlc.navigate_activate()
             self._show_info("Select")

        elif key == Qt.Key_B:
            track = self.vlc.cycle_audio_track()
            if track: self._show_info(f"Audio Track: {track}")
        elif key == Qt.Key_K:
            if modifiers & Qt.ShiftModifier:
                if modifiers & Qt.ControlModifier:
                    self.vlc.reset_sync()
                    self._show_info("Sync Reset")
                else:
                    self.vlc.synchronize_audio_subtitle()
                    self._show_info("Audio/Sub Synchronized")
            else:
                delay = self.vlc.set_audio_delay(round(self.vlc.get_audio_delay() + 50))
                self._show_info(f"Audio Delay: {delay}ms")
        elif key == Qt.Key_J:
            if modifiers & Qt.ShiftModifier:
                self.vlc.bookmark_subtitle_sync()
                self._show_info("Subtitle Sync Bookmark Set")
            else:
                delay = self.vlc.set_audio_delay(round(self.vlc.get_audio_delay() - 50))
                self._show_info(f"Audio Delay: {delay}ms")
        elif key == Qt.Key_H:
            if modifiers == (Qt.ControlModifier | Qt.ShiftModifier):
                self.vlc.bookmark_audio_sync()
                self._show_info("Audio Sync Bookmark Set")
            elif modifiers & Qt.ShiftModifier:
                # Let Shift+H bubble up to MainWindow (History Forward)
                super().keyPressEvent(event)
                return
            else:
                delay = self.vlc.set_subtitle_delay(round(self.vlc.get_subtitle_delay() + 50))
                self._show_info(f"Subtitle Delay: {delay}ms")
        elif key == Qt.Key_G:
            if modifiers & Qt.ShiftModifier:
                # Let Shift+G bubble up to MainWindow (History Back)
                super().keyPressEvent(event)
                return
            else:
                delay = self.vlc.set_subtitle_delay(round(self.vlc.get_subtitle_delay() - 50))
                self._show_info(f"Subtitle Delay: {delay}ms")


        # ─── Navigation (Seeking) ───
        elif key == Qt.Key_Left:
            if modifiers & Qt.ShiftModifier:
                self.vlc.seek_relative(-5)
            elif modifiers & (Qt.ControlModifier | Qt.AltModifier) == (Qt.ControlModifier | Qt.AltModifier):
                self.vlc.seek_relative(-300) # 5 min
            elif modifiers & Qt.ControlModifier:
                self.vlc.seek_relative(-60) # 1 min
            elif modifiers & Qt.AltModifier:
                self.vlc.seek_relative(-10) # 10 sec
            else:
                # For DVD navigation, we could try to navigate left first,
                # but standard VLC behavior is usually seeking unless in a menu.
                # Since we can't easily detect menu state perfectly, we'll favor seeking
                # but call navigate too? No, let's keep it simple: 
                # If no modifiers, it seeks. If we wanted pure DVD nav, we'd need a toggle.
                # However, the user explicitly asked for "Arrows: Navigate menus".
                # We'll call both or let user decide. 
                # Actually, VLC 'navigate' call while NOT in menu usually does nothing.
                self.vlc.navigate_left()
                self.vlc.seek_relative(-10) 
        elif key == Qt.Key_Right:
            if modifiers & Qt.ShiftModifier:
                self.vlc.seek_relative(5)
            elif modifiers & (Qt.ControlModifier | Qt.AltModifier) == (Qt.ControlModifier | Qt.AltModifier):
                self.vlc.seek_relative(300) # 5 min
            elif modifiers & Qt.ControlModifier:
                self.vlc.seek_relative(60) # 1 min
            elif modifiers & Qt.AltModifier:
                self.vlc.seek_relative(10) # 10 sec
            else:
                self.vlc.navigate_right()
                self.vlc.seek_relative(10) 


        # ─── Video / Display ───
        elif key == Qt.Key_F:
            self._request_fullscreen()
        elif key == Qt.Key_Escape and self._is_fullscreen:
            self._request_fullscreen()
        elif key == Qt.Key_V:
            if modifiers & Qt.AltModifier:
                track = self.vlc.cycle_subtitle_reverse()
            elif modifiers & Qt.ShiftModifier:
                on = self.vlc.toggle_subtitles()
                self._show_info(f"Subtitles: {'On' if on else 'Off'}")
                return # Don't do common actions
            else:
                track = self.vlc.cycle_subtitle_track()
            self._show_info(f"Subtitle: {track or 'Disabled'}")
        elif key == Qt.Key_A:
            ratio = self.vlc.cycle_aspect_ratio()
            self._show_info(f"Aspect Ratio: {ratio}")
        elif key == Qt.Key_C:
            crop = self.vlc.cycle_crop()
            self._show_info(f"Crop: {crop}")
        elif key == Qt.Key_Z:
            if modifiers & Qt.ShiftModifier:
                zoom = self.vlc.cycle_zoom(reverse=True)
            else:
                zoom = self.vlc.cycle_zoom()
            self._show_info(f"Zoom: {zoom}")
        elif key == Qt.Key_D:
            if modifiers & Qt.ShiftModifier:
                mode = self.vlc.cycle_deinterlace_modes()
                self._show_info(mode)
            elif modifiers & Qt.AltModifier:
                info = self.vlc.adjust_pixel_crop('left', -1 if modifiers & Qt.ShiftModifier else 1)
                self._show_info(info)
            else:
                mode = self.vlc.toggle_deinterlace()
                self._show_info(mode)
        elif modifiers & Qt.AltModifier:
            delta = -1 if modifiers & Qt.ShiftModifier else 1
            if key == Qt.Key_R:
                info = self.vlc.adjust_pixel_crop('top', delta)
                self._show_info(info)
            elif key == Qt.Key_C:
                info = self.vlc.adjust_pixel_crop('bottom', delta)
                self._show_info(info)
            elif key == Qt.Key_F:
                info = self.vlc.adjust_pixel_crop('right', delta)
                self._show_info(info)


        elif modifiers & Qt.ShiftModifier and key == Qt.Key_S:

            # Snapshot
            self.snapshot_requested.emit()
        elif modifiers & Qt.ShiftModifier and key == Qt.Key_R:
            # Record
            self._toggle_record()
        elif key == Qt.Key_X:
            if modifiers & Qt.ShiftModifier:
                prog = self.vlc.cycle_program(reverse=True)
            else:
                prog = self.vlc.cycle_program()
            self._show_info(f"Program: {prog}")
        elif key == Qt.Key_W:
            mode = self.vlc.toggle_wallpaper()
            self._show_info(mode)



        # ─── Speed ───
        elif key == Qt.Key_Plus:
            rate = self.vlc.get_rate() + 0.1
            self._set_speed(round(rate, 1))
            self._show_info(f"Speed: {self.vlc.get_rate()}x")
        elif key == Qt.Key_Equal:
            self._set_speed(1.0)
            self._show_info("Speed: 1.0x")
        elif key == Qt.Key_Minus:
            rate = self.vlc.get_rate() - 0.1
            self._set_speed(round(rate, 1))
            self._show_info(f"Speed: {self.vlc.get_rate()}x")
        elif key == Qt.Key_0:
            self._set_speed(1.0)
            self._show_info("Speed: 1.0x")
        elif key == Qt.Key_BracketRight:
            rate = self.vlc.get_rate() + 0.05
            self._set_speed(round(rate, 2))
            self._show_info(f"Speed: {self.vlc.get_rate()}x")
        elif key == Qt.Key_BracketLeft:
            rate = self.vlc.get_rate() - 0.05
            self._set_speed(round(rate, 2))
            self._show_info(f"Speed: {self.vlc.get_rate()}x")

        # ─── Title / Chapter ───
        elif modifiers & Qt.ShiftModifier:
            if key == Qt.Key_O:
                self.vlc.previous_title()
                self._show_info("Previous Title")
            elif key == Qt.Key_B:
                self.vlc.next_title()
                self._show_info("Next Title")
            elif key == Qt.Key_P:
                self.vlc.previous_chapter()
                self._show_info("Previous Chapter")
            elif key == Qt.Key_N:
                self.vlc.next_chapter()
                self._show_info("Next Chapter")

        # ─── Display / Resizing ───
        elif key == Qt.Key_O:
            msg = self.vlc.toggle_autoscale()
            self._show_info(msg)
        elif modifiers & Qt.AltModifier:
            if key == Qt.Key_1: self.resize_requested.emit(0.25)
            elif key == Qt.Key_2: self.resize_requested.emit(0.5)
            elif key == Qt.Key_3: self.resize_requested.emit(1.0)
            elif key == Qt.Key_4: self.resize_requested.emit(2.0)
            
        elif key == Qt.Key_PageUp:
            msg = self.vlc.change_viewpoint_fov(-5) # Shrink FOV (Zoom in)
            self._show_info(msg)
        elif key == Qt.Key_PageDown:
            msg = self.vlc.change_viewpoint_fov(5) # Expand FOV (Zoom out)
            self._show_info(msg)


        # ─── Misc ───
        elif key == Qt.Key_T:
            if modifiers & Qt.ControlModifier:
                self.jump_to_time_requested.emit()
            else:
                from src.core.utils import format_duration
                curr = self.vlc.get_position()
                dur = self.vlc.get_duration()
                self._show_info(f"{format_duration(curr)} / {format_duration(dur)}")
        elif key == Qt.Key_I:

             self._show_controls()
             self._show_info("Interface Visible")
        elif key >= Qt.Key_F1 and key <= Qt.Key_F12:
            idx = key - Qt.Key_F1 + 1
            if idx > 10: return
            
            if modifiers & Qt.ControlModifier:
                # Set Bookmark
                msg = self.vlc.set_bookmark(idx)
                self._show_info(msg)
            elif not modifiers:
                # Go to Bookmark
                data = self.vlc.get_bookmark(idx)
                if data:
                    path, time_ms = data
                    self.load_and_play(path)
                    # We need to wait for media to load before seeking
                    # vlc_engine.play is async-ish
                    QTimer.singleShot(500, lambda: self.vlc.player.set_time(time_ms))
                    self._show_info(f"Jump to Bookmark {idx}")
                else:
                    self._show_info(f"Bookmark {idx} empty")

        elif modifiers & Qt.AltModifier and key == Qt.Key_O:

             if modifiers & Qt.ShiftModifier:
                 self.vlc.decrease_scale()
             else:
                 self.vlc.increase_scale()
             self._show_info(f"Scale: {self.vlc.get_scale()}x")
        elif modifiers & Qt.ControlModifier and key == Qt.Key_0:
             self.vlc.set_spu_scale(1.0)
             self._show_info("Subtitles Scale: 1.0")
            
        else:
            super().keyPressEvent(event)
            return

        # Common actions for handled keys
        self._show_controls()
        self._hide_timer.start(3000)
        event.accept()

    def _show_info(self, text: str):
        """Show temporary info message on the overlay."""
        self.controls.lbl_info.setText(text)
        # Clear after 2 seconds
        if not hasattr(self, '_info_clear_timer'):
            self._info_clear_timer = QTimer(self)
            self._info_clear_timer.setSingleShot(True)
            self._info_clear_timer.timeout.connect(lambda: self.controls.lbl_info.setText(""))
        
        self._info_clear_timer.stop()
        self._info_clear_timer.start(2000)


    def wheelEvent(self, event):
        """Handle mouse wheel for volume (default) or subtitle scaling (Ctrl)."""
        modifiers = event.modifiers()
        delta = event.angleDelta().y()
        
        if modifiers & Qt.ControlModifier:
            # Subtitle Scaling
            # User request: Wheel Up = Scale Down, Wheel Down = Scale Up
            current = self.vlc.get_spu_scale()
            if delta > 0: # Up
                new_scale = current - 0.1
            else: # Down
                new_scale = current + 0.1
            
            actual = self.vlc.set_spu_scale(new_scale)
            self._show_info(f"Subtitles Scale: {actual:.1f}")
        else:
            # Volume
            if delta > 0:
                self.vlc.volume_up()
            else:
                self.vlc.volume_down()
        
        self._show_controls()
        event.accept()


    def _on_mute_changed(self, muted: bool):
        """Update mute button icon."""
        from src.core.utils import get_icon
        icon_name = "volume-mute.svg" if muted else "volume-high.svg"
        self.controls.btn_mute.setIcon(get_icon(icon_name))
