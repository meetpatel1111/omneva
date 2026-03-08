"""MainWindow — Primary application window with horizontal nav bar."""

import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QStackedWidget, QSizePolicy, QFrame, QLabel,
    QMenuBar, QMenu, QFileDialog, QInputDialog, QMessageBox,
    QApplication,
)
from PySide6.QtCore import Qt, QSize, QDateTime, QStandardPaths, QSettings
from PySide6.QtGui import QIcon, QAction, QKeySequence, QClipboard
from src.core.storage import storage
from src.ui.titlebar import TitleBar
from src.ui.player_widget import PlayerWidget
from src.ui.library_panel import LibraryPanel
from src.ui.transcoder_panel import TranscoderPanel
from src.ui.converter_panel import ConverterPanel
from src.ui.queue_panel import QueuePanel
from src.ui.settings_dialog import SettingsDialog


class NavButton(QPushButton):
    """Navigation button for the horizontal nav bar."""

    def __init__(self, text: str, icon_text: str = "", parent=None):
        super().__init__(parent)
        self.setText(f"{icon_text}  {text}")
        self.setObjectName("navBtn")
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)


class MainWindow(QMainWindow):
    """Frameless main window with horizontal navigation bar."""

    PAGE_PLAYER = 0
    PAGE_LIBRARY = 1
    PAGE_TRANSCODER = 2
    PAGE_CONVERTER = 3
    PAGE_QUEUE = 4

    MAX_RECENT = 10

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Omneva")
        self.setMinimumSize(1000, 650)
        self.resize(1280, 800)
        self._is_fullscreen = False
        self._quit_at_end = False
        self.setWindowFlags(Qt.FramelessWindowHint)
        
        # Use storage-managed settings
        self._settings = storage.get_settings()

        self._setup_ui()
        self._connect_signals()
        
        # Load verified theme or default
        saved_theme = self._settings.value("theme", "dark")
        self._set_theme(saved_theme)
        
        self._navigate(self.PAGE_PLAYER)
        self._history_stack = []
        self._forward_stack = []
        self._current_media = None


    def _setup_ui(self):
        # Central widget
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        self.root_layout = QVBoxLayout(central)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)

        # ─── Titlebar ───────────────────────────────────────
        self.titlebar = TitleBar()
        self.root_layout.addWidget(self.titlebar)

        # ─── Menu Bar ───────────────────────────────────────
        self.menubar = self._create_menubar()
        self.root_layout.addWidget(self.menubar)

        # ─── Content pages (stacked) ────────────────────────
        self.stack = QStackedWidget()
        self.stack.setObjectName("contentStack")

        self.player_page = PlayerWidget()
        self.library_page = LibraryPanel()
        self.transcoder_page = TranscoderPanel()
        self.converter_page = ConverterPanel()
        self.queue_page = QueuePanel()

        self.stack.addWidget(self.player_page)      # index 0
        self.stack.addWidget(self.library_page)      # index 1
        self.stack.addWidget(self.transcoder_page)   # index 2
        self.stack.addWidget(self.converter_page)    # index 3
        self.stack.addWidget(self.queue_page)        # index 4

        # Share playlist model with Library Panel
        self.library_page.set_playlist_model(self.player_page.playlist_model)

        self.root_layout.addWidget(self.stack, 1)

        # Start Renderer Discovery
        self.player_page.vlc.start_renderer_discovery()


    def _set_theme(self, theme_name: str):
        """Load and apply a QSS theme."""
        # 1. Update Settings
        self._settings.setValue("theme", theme_name)
        
        # 2. Load File
        base_dir = os.path.dirname(__file__)
        theme_file = os.path.join(base_dir, "styles", f"{theme_name}_theme.qss")
        
        if os.path.exists(theme_file):
            with open(theme_file, "r", encoding="utf-8") as f:
                QApplication.instance().setStyleSheet(f.read())
        else:
            print(f"Theme file not found: {theme_file}")

    def _create_menubar(self) -> QMenuBar:
        """Build VLC-style menu bar."""
        menubar = QMenuBar()
        menubar.setObjectName("appMenuBar")
        menubar.setFixedHeight(24)

        # ─── Media ──────────────────────────────────────────
        media_menu = menubar.addMenu("&Media")

        self.act_open_file = media_menu.addAction("Open File...")
        self.act_open_file.setShortcut(QKeySequence("Ctrl+O"))

        self.act_open_multiple = media_menu.addAction("Open Multiple Files...")
        self.act_open_multiple.setShortcut(QKeySequence("Ctrl+Shift+O"))

        self.act_open_folder = media_menu.addAction("Open Folder...")
        self.act_open_folder.setShortcut(QKeySequence("Ctrl+F"))

        self.act_open_disc = media_menu.addAction("Open Disc...")
        self.act_open_disc.setShortcut(QKeySequence("Ctrl+D"))

        self.act_open_network = media_menu.addAction("Open Network Stream...")
        self.act_open_network.setShortcut(QKeySequence("Ctrl+N"))

        self.act_open_capture = media_menu.addAction("Open Capture Device...")
        self.act_open_capture.setShortcut(QKeySequence("Ctrl+C"))

        self.act_open_clipboard = media_menu.addAction("Open Location from clipboard")
        self.act_open_clipboard.setShortcut(QKeySequence("Ctrl+V"))

        self.act_recent_menu = media_menu.addMenu("Open Recent Media")

        media_menu.addSeparator()

        self.act_save_playlist = media_menu.addAction("Save Playlist to File...")
        self.act_save_playlist.setShortcut(QKeySequence("Ctrl+Y"))

        self.act_convert = media_menu.addAction("Convert / Save...")
        self.act_convert.setShortcut(QKeySequence("Ctrl+R"))

        self.act_stream = media_menu.addAction("Stream...")
        self.act_stream.setShortcut(QKeySequence("Ctrl+S"))

        media_menu.addSeparator()

        self.act_clear_playlist = media_menu.addAction("Clear Playlist")
        self.act_clear_playlist.setShortcut(QKeySequence("Ctrl+W"))

        media_menu.addSeparator()

        self.act_quit_end = media_menu.addAction("Quit at the end of playlist")
        self.act_quit_end.setCheckable(True)

        self.act_quit = media_menu.addAction("Quit")
        self.act_quit.setShortcut(QKeySequence("Ctrl+Q"))

        # ─── Playback ───────────────────────────────────────
        # ─── Playback ───────────────────────────────────────
        playback_menu = menubar.addMenu("P&layback")


        playback_menu.addMenu("Title")
        playback_menu.addMenu("Chapter")
        playback_menu.addMenu("Program")
        self.act_bookmarks = playback_menu.addAction("Bookmarks")
        self.act_bookmarks.setShortcut(QKeySequence("Ctrl+B"))
        playback_menu.addMenu("Custom Bookmarks")

        self.renderer_menu = playback_menu.addMenu("Renderer")
        self.renderer_menu.aboutToShow.connect(self._populate_renderers)


        speed_menu = playback_menu.addMenu("Speed")
        self.act_speed_faster = speed_menu.addAction("Faster")
        self.act_speed_faster.setShortcut(QKeySequence("]"))
        self.act_speed_normal = speed_menu.addAction("Normal")
        self.act_speed_normal.setShortcut(QKeySequence("="))
        self.act_speed_slower = speed_menu.addAction("Slower")
        self.act_speed_slower.setShortcut(QKeySequence("["))

        playback_menu.addSeparator()

        self.act_jump_fwd = playback_menu.addAction("Jump Forward")
        self.act_jump_fwd.setShortcut(QKeySequence("Right"))

        self.act_jump_back = playback_menu.addAction("Jump Backward")
        self.act_jump_back.setShortcut(QKeySequence("Left"))

        self.act_jump_time = playback_menu.addAction("Jump to Specific Time")
        self.act_jump_time.setShortcut(QKeySequence("Ctrl+T"))

        playback_menu.addSeparator()

        self.act_play_pause = playback_menu.addAction("Play")
        self.act_play_pause.setShortcut(QKeySequence("Space"))

        self.act_stop = playback_menu.addAction("Stop")
        self.act_stop.setShortcut(QKeySequence("S"))

        self.act_prev = playback_menu.addAction("Previous")
        self.act_prev.setShortcut(QKeySequence("P"))

        self.act_next = playback_menu.addAction("Next")
        self.act_next.setShortcut(QKeySequence("N"))

        self.act_record = playback_menu.addAction("Record")

        # ─── Audio ──────────────────────────────────────────
        audio_menu = menubar.addMenu("&Audio")

        self.act_mute = audio_menu.addAction("Mute")
        self.act_mute.setShortcut(QKeySequence("M"))

        self.act_vol_up = audio_menu.addAction("Volume Up")
        self.act_vol_up.setShortcut(QKeySequence("Ctrl+Up"))

        self.act_vol_down = audio_menu.addAction("Volume Down")
        self.act_vol_down.setShortcut(QKeySequence("Ctrl+Down"))

        audio_menu.addSeparator()
        self.audio_track_menu = audio_menu.addMenu("Audio Track")
        self.audio_track_menu.aboutToShow.connect(self._populate_audio_tracks)

        self.audio_device_menu = audio_menu.addMenu("Audio Device")
        self.audio_device_menu.aboutToShow.connect(self._populate_audio_devices)

        self.stereo_mode_menu = audio_menu.addMenu("Stereo Mode")
        self.stereo_mode_menu.aboutToShow.connect(self._populate_stereo_mode)

        self.vis_menu = audio_menu.addMenu("Visualizations")
        self.vis_menu.aboutToShow.connect(self._populate_visualizations)

        # ─── Video ──────────────────────────────────────────
        video_menu = menubar.addMenu("&Video")

        self.act_fullscreen = video_menu.addAction("Fullscreen")
        self.act_fullscreen.setShortcut(QKeySequence("F"))

        video_menu.addSeparator()

        self.subtitle_track_menu = video_menu.addMenu("Subtitle Track")
        self.subtitle_track_menu.aboutToShow.connect(self._populate_subtitle_tracks)

        video_menu.addSeparator()

        ar_menu = video_menu.addMenu("Aspect Ratio")
        for ratio in ["16:9", "4:3", "1:1", "16:10", "2.21:1", "2.35:1", "2.39:1", "5:4"]:
            ar_menu.addAction(ratio, lambda r=ratio: self.player_page.vlc.set_aspect_ratio(r))
        ar_menu.addSeparator()
        ar_menu.addAction("Default", lambda: self.player_page.vlc.set_aspect_ratio(None))

        crop_menu = video_menu.addMenu("Crop")
        for ratio in ["16:9", "4:3", "1:1", "16:10", "2.21:1", "2.35:1", "2.39:1", "5:4"]:
            crop_menu.addAction(ratio, lambda r=ratio: self.player_page.vlc.set_crop(r))
        crop_menu.addSeparator()
        crop_menu.addAction("Default", lambda: self.player_page.vlc.set_crop(None))

        self.act_screenshot = video_menu.addAction("Take Snapshot")
        self.act_screenshot.setShortcut(QKeySequence("Shift+S"))

        # ─── Tools ──────────────────────────────────────────
        tools_menu = menubar.addMenu("Tool&s")

        
        self.act_effects = tools_menu.addAction("Effects and Filters")
        self.act_effects.setShortcut(QKeySequence("Ctrl+E"))
        self.act_effects.triggered.connect(lambda: self._open_effects_dialog(0))
        
        self.act_vlm = tools_menu.addAction("VLM Configurator")
        self.act_vlm.setShortcut(QKeySequence("Ctrl+Shift+W"))
        self.act_vlm.triggered.connect(self._show_vlm_config)

        self.act_sync = tools_menu.addAction("Track Synchronization")

        self.act_sync.triggered.connect(lambda: self._open_effects_dialog(2))

        tools_menu.addSeparator()

        self.act_tool_transcoder = tools_menu.addAction("Transcoder")
        self.act_tool_transcoder.triggered.connect(lambda: self._navigate(self.PAGE_TRANSCODER))

        self.act_tool_converter = tools_menu.addAction("Converter")
        self.act_tool_converter.triggered.connect(lambda: self._navigate(self.PAGE_CONVERTER))

        tools_menu.addSeparator()

        self.act_media_info = tools_menu.addAction("Media Information")
        self.act_media_info.setShortcut(QKeySequence("Ctrl+I"))
        
        self.act_codec_info = tools_menu.addAction("Codec Information")
        self.act_codec_info.setShortcut(QKeySequence("Ctrl+J"))

        self.act_messages = tools_menu.addAction("Messages")
        self.act_messages.setShortcut(QKeySequence("Ctrl+M"))

        tools_menu.addSeparator()


        self.act_preferences = tools_menu.addAction("Preferences")
        self.act_preferences.setShortcut(QKeySequence("Ctrl+P"))



        # ─── View ───────────────────────────────────────────
        view_menu = menubar.addMenu("V&iew")


        self.act_view_playlist = view_menu.addAction("Playlist")
        self.act_view_playlist.setShortcut(QKeySequence("Ctrl+L"))
        self.act_view_playlist.triggered.connect(self._toggle_playlist_view)

        self.act_docked_playlist = view_menu.addAction("Docked Playlist")
        self.act_docked_playlist.setCheckable(True)
        self.act_docked_playlist.setChecked(True) # Placeholder state
        
        playlist_view_mode = view_menu.addMenu("Playlist View Mode")
        playlist_view_mode.addAction("Icons", lambda: self.library_page.set_view_mode(self.library_page.VIEW_ICONS))
        playlist_view_mode.addAction("Detailed List", lambda: self.library_page.set_view_mode(self.library_page.VIEW_DETAILS))
        playlist_view_mode.addAction("List", lambda: self.library_page.set_view_mode(self.library_page.VIEW_LIST))

        view_menu.addSeparator()

        self.act_always_on_top = view_menu.addAction("Always on top")
        self.act_always_on_top.setCheckable(True)
        self.act_always_on_top.triggered.connect(self._toggle_always_on_top)

        self.act_minimal_interface = view_menu.addAction("Minimal Interface")
        self.act_minimal_interface.setShortcut(QKeySequence("Ctrl+H"))
        self.act_minimal_interface.setCheckable(True)
        self.act_minimal_interface.triggered.connect(self._toggle_minimal_interface)

        self.act_fullscreen_interface = view_menu.addAction("Fullscreen Interface")
        self.act_fullscreen_interface.setShortcut(QKeySequence("F11"))
        self.act_fullscreen_interface.triggered.connect(self.toggle_video_fullscreen)

        view_menu.addSeparator()

        self.act_advanced_controls = view_menu.addAction("Advanced Controls")
        self.act_advanced_controls.setShortcut(QKeySequence("Ctrl+A"))
        self.act_advanced_controls.setCheckable(True)

        self.act_advanced_controls.triggered.connect(self._toggle_advanced_controls)
        
        self.act_status_bar = view_menu.addAction("Status Bar")
        self.act_status_bar.setCheckable(True)
        self.act_status_bar.setChecked(True)
        self.act_status_bar.triggered.connect(self._toggle_status_bar)

        view_menu.addSeparator()

        iface_menu = view_menu.addMenu("Add Interface")
        iface_menu.addAction("Web Interface")
        iface_menu.addAction("Telnet Interface")
        iface_menu.addAction("Console Interface")
        iface_menu.addAction("Mouse Gestures")

        view_menu.addAction("VLsub")

        # ─── Help ───────────────────────────────────────────
        help_menu = menubar.addMenu("&Help")
        
        self.act_shortcuts = help_menu.addAction("Keyboard Shortcuts")
        self.act_shortcuts.setShortcut(QKeySequence("Shift+F1"))


        self.act_about = help_menu.addAction("About Omneva")
        self.act_check_updates = help_menu.addAction("Check for Updates...")

        # Initialize StatusBar
        self.statusbar = self.statusBar()
        self.statusbar.showMessage("Ready")

        return menubar

    def _connect_signals(self):
        """Wire up all signals."""
        # Titlebar
        self.titlebar.minimize_clicked.connect(self.showMinimized)
        self.titlebar.maximize_clicked.connect(self._toggle_maximize)
        self.titlebar.close_clicked.connect(self.close)

        # Library → Player: play selected file
        self.library_page.play_file_requested.connect(self._play_from_library)

    def _play_from_library(self, file_path: str):
        """Play selected file from library."""
        self._play_media(file_path)


        # Transcoder → QueuePanel: wire job signals
        self.transcoder_page.job_added.connect(self._on_job_added)
        self.transcoder_page.queue.job_progress.connect(self.queue_page.on_job_progress)
        self.transcoder_page.queue.job_completed.connect(self.queue_page.on_job_completed)
        self.transcoder_page.queue.job_failed.connect(self.queue_page.on_job_failed)

        # Player signals
        self.player_page.fullscreen_requested.connect(self.toggle_video_fullscreen)
        self.player_page.title_changed.connect(self._update_title)
        self.player_page.context_menu_requested.connect(self._show_context_menu)
        self.player_page.snapshot_requested.connect(self._take_snapshot)
        self.player_page.jump_to_time_requested.connect(self._jump_to_time)
        self.player_page.resize_requested.connect(self._resize_window)
        self.player_page.help_requested.connect(self._show_shortcuts)

        # ─── Menu actions ────────────────────────────────────
        self.act_open_file.triggered.connect(self.player_page._open_file)
        self.act_open_multiple.triggered.connect(self._open_multiple_files)
        self.act_open_folder.triggered.connect(self._open_folder)
        self.act_open_disc.triggered.connect(self._open_disc)
        self.act_open_network.triggered.connect(self._open_network)
        self.act_open_capture.triggered.connect(self._open_capture)
        self.act_open_clipboard.triggered.connect(self._open_clipboard)
        self.act_save_playlist.triggered.connect(self._save_playlist)
        self.act_clear_playlist.triggered.connect(self._on_clear_playlist_triggered)
        self.act_convert.triggered.connect(lambda: self._navigate(self.PAGE_CONVERTER))
        self.act_stream.triggered.connect(self._open_stream)
        self.act_quit_end.triggered.connect(self._toggle_quit_at_end)
        self.act_quit.triggered.connect(self.close)

        self.act_play_pause.triggered.connect(self.player_page._toggle_play)
        self.act_stop.triggered.connect(self.player_page.vlc.stop)
        self.act_prev.triggered.connect(self.player_page.vlc.previous_chapter)
        self.act_next.triggered.connect(self.player_page.vlc.next_chapter)
        self.act_record.triggered.connect(self.player_page.vlc.toggle_record)

        self.act_speed_faster.triggered.connect(lambda: self.player_page._set_speed(round(self.player_page.vlc.get_rate() + 0.05, 2)))
        self.act_speed_normal.triggered.connect(lambda: self.player_page._set_speed(1.0))
        self.act_speed_slower.triggered.connect(lambda: self.player_page._set_speed(round(self.player_page.vlc.get_rate() - 0.05, 2)))


        self.act_jump_fwd.triggered.connect(lambda: self.player_page.vlc.seek_relative(10))
        self.act_jump_back.triggered.connect(lambda: self.player_page.vlc.seek_relative(-10))
        self.act_jump_time.triggered.connect(self._jump_to_time)

        self.act_mute.triggered.connect(self.player_page.vlc.toggle_mute)
        self.act_vol_up.triggered.connect(self.player_page.vlc.volume_up)
        self.act_vol_down.triggered.connect(self.player_page.vlc.volume_down)

        self.act_fullscreen.triggered.connect(self.toggle_video_fullscreen)
        self.act_screenshot.triggered.connect(self._take_snapshot)

        self.act_media_info.triggered.connect(self._show_media_info)
        self.act_codec_info.triggered.connect(self._show_codec_info)
        self.act_preferences.triggered.connect(self._show_preferences)

        self.act_about.triggered.connect(self._show_about)
        self.act_check_updates.triggered.connect(self._check_updates)
        self.act_shortcuts.triggered.connect(self._show_shortcuts)
        self.act_messages.triggered.connect(self._show_messages)
        self.act_effects.triggered.connect(lambda: self._open_effects_dialog(0))
        self.act_sync.triggered.connect(lambda: self._open_effects_dialog(2))


        # History shortcuts
        self.act_history_back = QAction(self)
        self.act_history_back.setShortcut(QKeySequence("Shift+G"))
        self.act_history_back.triggered.connect(self._history_back)
        self.addAction(self.act_history_back)

        self.act_history_forward = QAction(self)
        self.act_history_forward.setShortcut(QKeySequence("Shift+H"))
        self.act_history_forward.triggered.connect(self._history_forward)
        self.addAction(self.act_history_forward)




    def _show_messages(self):
        """Show the VLC-style Messages dialog."""
        from src.ui.tools_dialogs import MessagesDialog
        dlg = MessagesDialog(self)
        dlg.exec()

    def _show_vlm_config(self):
        """Show a placeholder for the VLM Configurator."""
        QMessageBox.information(
            self, "VLM Configurator",
            "The VLM Configurator is not yet implemented.\n"
            "This tool is used for professional streaming and broadcasting."
        )

    # ─── Media Open Handlers ──────────────────────────────────


    def _open_disc(self):
        """Open Disc — show selection dialog."""
        from src.ui.tools_dialogs import OpenDiscDialog
        dlg = OpenDiscDialog(self)
        if dlg.exec():
            mrl = dlg.get_mrl()
            self._navigate(self.PAGE_PLAYER)
            self.player_page.load_and_play(mrl)
            self._add_to_recent(mrl)


    def _open_capture(self):
        """Open Capture Device — show info."""
        QMessageBox.information(
            self, "Open Capture Device",
            "Capture device support is not yet available.\n"
            "Use VLC or OBS for capture."
        )

    def _open_clipboard(self):
        """Open a URL from the system clipboard."""
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()
        if text and (text.startswith("http://") or text.startswith("https://")
                     or text.startswith("rtsp://") or text.startswith("rtmp://")
                     or os.path.isfile(text)):
            self._navigate(self.PAGE_PLAYER)
            self.player_page.load_and_play(text)
            self._add_to_recent(text)
        else:
            QMessageBox.information(
                self, "Open from Clipboard",
                "No valid media URL or file path found in clipboard."
            )

    def _open_network(self):
        """Open a network stream URL."""
        url, ok = QInputDialog.getText(self, "Open Network Stream", "Enter a network URL:")
        if ok and url:
            self._navigate(self.PAGE_PLAYER)
            self.player_page.vlc.play(url)
            self._add_to_recent(url)

    def _on_job_added(self, job_id, input_path, job_name):
        """Handle new job from transcoder: add to queue and switch view."""
        self.queue_page.add_job(job_id, input_path, job_name)
        self._navigate(self.PAGE_QUEUE)

    def _open_stream(self):
        """Stream — show info dialog."""
        QMessageBox.information(
            self, "Stream",
            "Streaming output is not yet available.\n"
            "Use the Transcoder or Converter panels to process media."
        )

    def _save_playlist(self):
        """Save current transcoder input files as an M3U playlist."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Playlist", "playlist.m3u",
            "M3U Playlist (*.m3u);;All Files (*)"
        )
        if not path:
            return
        files = getattr(self.transcoder_page, '_input_files', [])
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write('#EXTM3U\n')
                for fp in files:
                    f.write(f'{fp}\n')
            QMessageBox.information(self, "Saved", f"Playlist saved to:\n{path}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save playlist:\n{e}")

    def _toggle_quit_at_end(self):
        """Toggle quit-at-end-of-playlist flag."""
        self._quit_at_end = self.act_quit_end.isChecked()


    def _exit_fullscreen(self):
        """Leave fullscreen — restore chrome."""
        self._is_fullscreen = False
        self.titlebar.show()
        self.menubar.show()
        if self.act_status_bar.isChecked():
            self.statusbar.show()
        central = self.centralWidget()
        central.setStyleSheet("")
        self.player_page.set_fullscreen_mode(False)
        self.showNormal()

    def _resize_window(self, scale: float):
        """Resize window based on current video size and scale factor."""
        # Get video size
        w, h = self.player_page.vlc.player.video_get_size(0)
        if w > 0 and h > 0:
            new_w = int(w * scale)
            new_h = int(h * scale)
            # Add some margin for UI if not minimal
            if not getattr(self, '_minimal_interface', False):
                 new_h += 80 # Approx header/footer height
            
            # Constraint: don't exceed screen size
            from PySide6.QtGui import QGuiApplication
            screen = QGuiApplication.primaryScreen().availableGeometry()
            new_w = min(new_w, screen.width() - 40)
            new_h = min(new_h, screen.height() - 40)
            
            self.resize(new_w, new_h)
            self.player_page._show_info(f"Window Zoom: {int(scale*100)}%")

    def _play_media(self, file_path: str, push_history: bool = True):
        """Internal helper to play media and track history."""
        if push_history and self._current_media:
            self._history_stack.append(self._current_media)
            self._forward_stack.clear()
        
        self._current_media = file_path
        self._navigate(self.PAGE_PLAYER)
        self.player_page.load_and_play(file_path)
        self._add_to_recent(file_path)

    def _history_back(self):
        """Go back in play history."""
        if not self._history_stack:
            self.player_page._show_info("No more history")
            return
        
        if self._current_media:
            self._forward_stack.append(self._current_media)
        
        prev_media = self._history_stack.pop()
        self._current_media = prev_media
        self.player_page.load_and_play(prev_media)
        self.player_page._show_info("History Back")

    def _history_forward(self):
        """Go forward in play history."""
        if not self._forward_stack:
            self.player_page._show_info("No more forward history")
            return
        
        if self._current_media:
            self._history_stack.append(self._current_media)
        
        next_media = self._forward_stack.pop()
        self._current_media = next_media
        self.player_page.load_and_play(next_media)
        self.player_page._show_info("History Forward")

    def _open_folder(self):

        """Open a folder and play the first media file found."""
        folder = QFileDialog.getExistingDirectory(self, "Open Folder")
        if folder:
            import os
            media_exts = ('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv',
                          '.webm', '.m4v', '.mp3', '.flac', '.wav', '.aac',
                          '.ogg', '.wma', '.m4a', '.opus')
            for f in sorted(os.listdir(folder)):
                if f.lower().endswith(media_exts):
                    self._play_media(os.path.join(folder, f))
                    break


    def keyPressEvent(self, event):
        """Escape exits fullscreen."""
        if event.key() == Qt.Key_Escape and self._is_fullscreen:
            self._exit_fullscreen()
            return
        if event.key() == Qt.Key_F and not event.modifiers():
            if self.stack.currentIndex() == self.PAGE_PLAYER:
                self.toggle_video_fullscreen()
                return
        super().keyPressEvent(event)

    # ─── Resize grip (bottom-right corner) ──────────────────
    def mousePressEvent(self, event):
        if event.position().x() > self.width() - 10 and event.position().y() > self.height() - 10:
            self._resize_drag = True
            self._resize_start = event.globalPosition().toPoint()
            self._resize_size = self.size()
        else:
            self._resize_drag = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if getattr(self, '_resize_drag', False):
            delta = event.globalPosition().toPoint() - self._resize_start
            new_w = max(self.minimumWidth(), self._resize_size.width() + delta.x())
            new_h = max(self.minimumHeight(), self._resize_size.height() + delta.y())
            self.resize(new_w, new_h)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._resize_drag = False
        super().mouseReleaseEvent(event)

    def _on_clear_playlist_triggered(self):
        """Handle Ctrl+W: Clear playlist."""
        if hasattr(self.library_page, 'playlist_view'):
             self.library_page.playlist_view._clear_playlist()
        self.player_page._show_info("Playlist Cleared")

    def _add_to_recent(self, file_path: str):
        """Add to recent files (SQLite)."""
        if not file_path or not os.path.exists(file_path):
            return
            
        storage.add_to_history(file_path)
        self._update_recent_menu()

    def _update_recent_menu(self):
        """Rebuild the Recent Media submenu from SQLite."""
        self.act_recent_menu.clear()
        recent = storage.get_history(limit=self.MAX_RECENT)
        
        if not recent:
            self.act_recent_menu.addAction("(No recent files)").setEnabled(False)
            return
            
        for filepath in recent:
            display = os.path.basename(filepath)
            action = self.act_recent_menu.addAction(display)
            action.triggered.connect(lambda checked, p=filepath: self._play_recent(p))
            
        self.act_recent_menu.addSeparator()
        self.act_recent_menu.addAction("Clear Recent", self._clear_recent)

    def _play_recent(self, file_path: str):
        """Play a file from recent media."""
        self._play_media(file_path)


    def _clear_recent(self):
        """Clear recent files list."""
        storage.clear_history()
        self._update_recent_menu()

    # ─── Dynamic Audio/Subtitle Track Menus ──────────────────

    def _populate_audio_tracks(self):
        """Build audio track submenu from VLC's available tracks."""
        self.audio_track_menu.clear()
        tracks = self.player_page.vlc.get_audio_tracks()
        if not tracks:
            self.audio_track_menu.addAction("(No audio tracks)").setEnabled(False)
            return
        for track_id, name in tracks:
            action = self.audio_track_menu.addAction(name)
            action.setCheckable(True)
            action.triggered.connect(lambda checked, tid=track_id: self.player_page.vlc.set_audio_track(tid))

    def _populate_subtitle_tracks(self):
        """Build subtitle track submenu from VLC's available tracks."""
        self.subtitle_track_menu.clear()
        self.subtitle_track_menu.addAction(
            "Add Subtitle File...", self._add_subtitle_file
        )
        self.subtitle_track_menu.addSeparator()

        tracks = self.player_page.vlc.get_subtitle_tracks()
        if not tracks:
            self.subtitle_track_menu.addAction("(No subtitle tracks)").setEnabled(False)
            return
        for track_id, name in tracks:
            action = self.subtitle_track_menu.addAction(name)
            action.setCheckable(True)
            action.triggered.connect(lambda checked, tid=track_id: self.player_page.vlc.set_subtitle_track(tid))

    def _add_subtitle_file(self):
        """Load an external subtitle file into the player."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Add Subtitle File", "",
            "Subtitle Files (*.srt *.ass *.ssa *.sub *.vtt);;All Files (*)"
        )
        if path:
            self.player_page.vlc.set_subtitle_file(path)

    # ─── View Menu Handlers ──────────────────────────────────
    
    def _toggle_playlist_view(self):
        """Toggle between Player and Library view (Ctrl+L)."""
        # VLC style: Ctrl+L toggles playlist.
        # If we are on Player, go to Library.
        # If we are on Library, go to Player.
        # If we are on any other page, go to Player (or Library?).
        if self.stack.currentIndex() == self.PAGE_LIBRARY:
            self._navigate(self.PAGE_PLAYER)
        else:
            self._navigate(self.PAGE_LIBRARY)

    def _toggle_always_on_top(self):
        """Toggle WindowStaysOnTopHint."""
        on = self.act_always_on_top.isChecked()
        flags = self.windowFlags()
        if on:
            flags |= Qt.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowStaysOnTopHint
        
        # Changing flags hides the window, so we must show it again
        self.setWindowFlags(flags)
        self.show()

    def _toggle_minimal_interface(self):
        """Toggle Minimal Interface (Ctrl+H) - Hide TitleBar and MenuBar."""
        minimal = self.act_minimal_interface.isChecked()
        if minimal:
            self.titlebar.hide()
            self.menubar.hide()
            self.statusbar.hide()
        else:
            self.titlebar.show()
            self.menubar.show()
            if self.act_status_bar.isChecked():
                self.statusbar.show()

    def _toggle_status_bar(self):
        """Toggle Status Bar visibility."""
        visible = self.act_status_bar.isChecked()
        self.statusbar.setVisible(visible)

    def _toggle_advanced_controls(self):
        """Toggle Advanced Controls in Player."""
        visible = self.act_advanced_controls.isChecked()
        self.player_page.set_advanced_visible(visible)
        
    def _update_title(self, title: str):
        """Update window title."""
        self.titlebar.set_title(f"Omneva - {title}")

    def toggle_video_fullscreen(self):
        """Toggle fullscreen mode for the player."""
        if self._is_fullscreen:
            self._exit_fullscreen()
        else:
            self._enter_fullscreen()
    
    # ─── Playback Helpers ────────────────────────────────────
    
    def _jump_to_time(self):
        """Jump to a specific time in seconds."""
        seconds, ok = QInputDialog.getInt(self, "Jump to Time", "Enter time in seconds:", 0, 0, 360000)
        if ok:
            self.player_page.vlc.seek(float(seconds))

    def _take_snapshot(self):
        """Take a snapshot of the current video frame."""
        pictures_dir = QStandardPaths.writableLocation(QStandardPaths.PicturesLocation)
        timestamp = QDateTime.currentDateTime().toString("yyyyMMdd_HHmmss")
        filename = f"omneva_snapshot_{timestamp}.png"
        path = f"{pictures_dir}/{filename}"
        
        # Use player call if simpler, but MainWindow handles path logic well
        # vlc.take_snapshot(path, w, h)
        if self.player_page.vlc.take_snapshot(path, 0, 0):
             QMessageBox.information(self, "Snapshot", f"Saved to:\n{path}")
        else:
             # Just in case
             pass

    def _show_context_menu(self, global_pos):
        """Show context menu for player."""
        menu = QMenu(self)
        
        # Playback controls
        if self.player_page.vlc.is_playing():
            menu.addAction(self.act_play_pause)
        else:
            menu.addAction(self.act_play_pause)
            
        menu.addAction(self.act_stop)
        menu.addSeparator()
        
        # Tracks
        # We can add the existing submenus if they are QMenus
        # But act_audio_track_menu is a QMenu added to menubar
        # We can create new submenus or reuse actions?
        # Reusing actions is safer.
        
        a_menu = menu.addMenu("Audio Tracks")
        tracks = self.player_page.vlc.get_audio_tracks()
        if not tracks:
            a_menu.addAction("(No audio tracks)").setEnabled(False)
        else:
            # Fix: iterate items()
            for tid, name in tracks.items():
                act = a_menu.addAction(name)
                act.setCheckable(True)
                act.triggered.connect(lambda checked, t=tid: self.player_page.vlc.set_audio_track(t))

        s_menu = menu.addMenu("Subtitle Tracks")
        subs = self.player_page.vlc.get_subtitle_tracks()
        if not subs:
            s_menu.addAction("(No subtitle tracks)").setEnabled(False)
        else:
            # Fix: iterate items()
            for tid, name in subs.items():
                act = s_menu.addAction(name)
                act.setCheckable(True)
                act.triggered.connect(lambda checked, t=tid: self.player_page.vlc.set_subtitle_track(t))
                
        menu.addSeparator()
        menu.addAction(self.act_fullscreen)
        menu.addAction(self.act_screenshot)
        menu.addSeparator()
        menu.addAction(self.act_media_info)
        menu.addAction(self.act_codec_info)
        
        menu.exec(global_pos)

    def _show_media_info(self):
        """Show media info dialog with FFprobe data."""
        if not self.player_page.vlc.is_playing():
            QMessageBox.information(self, "Media Information", "No media playing.")
            return

        rate = self.player_page.vlc.get_rate()
        vol = self.player_page.vlc.get_volume()
        dur = self.player_page.vlc.get_duration()
        pos = self.player_page.vlc.get_position()

        info = (
            f"Playback Rate: {rate}x\n"
            f"Volume: {vol}%\n"
            f"Muted: {self.player_page.vlc.is_muted()}\n"
            f"Duration: {dur:.1f}s\n"
            f"Position: {pos:.1f}s"
        )
        QMessageBox.information(self, "Current Media Info", info)



    def _show_codec_info(self):
        """Show codec information for the current media."""
        if not self.player_page.vlc.is_playing():
            QMessageBox.information(self, "Codec Information", "No media playing.")
            return

        audio_tracks = self.player_page.vlc.get_audio_tracks()
        sub_tracks = self.player_page.vlc.get_subtitle_tracks()

        lines = ["Audio Tracks:"]
        if audio_tracks:
            # Handle dict or list
            items = audio_tracks.items() if isinstance(audio_tracks, dict) else audio_tracks
            for tid, name in items:
                lines.append(f"  • [{tid}] {name}")
        else:
            lines.append("  (none)")

        lines.append("\nSubtitle Tracks:")
        if sub_tracks:
            items = sub_tracks.items() if isinstance(sub_tracks, dict) else sub_tracks
            for tid, name in items:
                lines.append(f"  • [{tid}] {name}")
        else:
            lines.append("  (none)")

        QMessageBox.information(self, "Codec Information", "\n".join(lines))

    def _show_about(self):
        """Show About dialog."""
        QMessageBox.about(
            self,
            "About Omneva",
            "<h3>Omneva v1.0.0</h3>"
            "<p>A native, modern media player and transcoder.</p>"
            "<p>Built with Python, PySide6, and VLC.</p>"
            "<p>© 2025 Omneva Team</p>"
        )

    def _check_updates(self):
        """Check for updates dialog."""
        QMessageBox.information(
            self, "Check for Updates",
            "You are running Omneva v1.0.0.\n\n"
            "No updates available. You're on the latest version!"
        )

    def _show_shortcuts(self):
        """Show keyboard shortcuts dialog."""
        shortcuts = [
            ("General", "----------"),
            ("Open File", "Ctrl+O"),
            ("Open Multiple", "Ctrl+Shift+O"),
            ("Open Folder", "Ctrl+F"),
            ("Open Disc", "Ctrl+D"),
            ("Open Network", "Ctrl+N"),
            ("Open Clipboard", "Ctrl+V"),
            ("Quit", "Ctrl+Q"),
            ("Fullscreen", "F / Esc"),
            ("Preferences", "Ctrl+P"),
            ("Media Info", "Ctrl+I"),
            ("Codec Info", "Ctrl+J"),
            ("Playback", "----------"),
            ("Play/Pause", "Space"),
            ("Stop", "S"),
            ("Previous/Next", "P / N"),
            ("Jump Backward", "Left Arrow"),
            ("Jump Forward", "Right Arrow"),
            ("Jump to Time", "Ctrl+T"),
            ("Volume Up/Down", "Up / Down Arrow"),
            ("Mute", "M"),
            ("Speed Faster", "]"),
            ("Speed Slower", "["),
            ("Speed Normal", "="),
            ("Snapshot", "Shift+S"),
        ]

        rows = []
        for action, keys in shortcuts:
            if keys == "----------":
                rows.append(f"<tr><td colspan='2' style='font-weight:bold; padding-top:10px;'>{action}</td></tr>")
            else:
                rows.append(f"<tr><td style='padding-right:20px;'>{action}</td><td style='font-family:monospace; font-weight:bold;'>{keys}</td></tr>")

        html = f"""
        <h3>Keyboard Shortcuts</h3>
        <table cellspacing='0' cellpadding='2'>
            {''.join(rows)}
        </table>
        """
        QMessageBox.information(self, "Keyboard Shortcuts", html)

    def _show_preferences(self):
        """Show settings dialog."""
        dlg = SettingsDialog(self)
        if dlg.exec_():
            pass

    def _show_context_menu(self, pos):
        """Show VLC-style right-click context menu."""
        menu = QMenu(self)

        # 1. Playback Controls
        menu.addAction(self.act_play_pause)
        menu.addAction(self.act_stop)
        menu.addAction(self.act_prev)
        menu.addAction(self.act_next)
        menu.addAction(self.act_record)
        menu.addSeparator()

        # 2. Audio
        audio_menu = menu.addMenu("Audio")
        audio_menu.addAction(self.act_mute)
        audio_menu.addAction(self.act_vol_up)
        audio_menu.addAction(self.act_vol_down)
        audio_menu.addSeparator()
        ctx_audio_tracks = audio_menu.addMenu("Audio Track")
        tracks = self.player_page.vlc.get_audio_tracks()
        if tracks:
            # tracks is now a dict {id: name}
            items = tracks.items() if isinstance(tracks, dict) else tracks
            for tid, name in items:
                act = ctx_audio_tracks.addAction(name)
                act.triggered.connect(lambda c, t=tid: self.player_page.vlc.set_audio_track(t))
        else:
            ctx_audio_tracks.addAction("(No audio tracks)").setEnabled(False)

        # 3. Video
        video_menu = menu.addMenu("Video")
        video_menu.addAction(self.act_fullscreen)
        video_menu.addAction(self.act_screenshot)
        video_menu.addSeparator()

        # Subtitle tracks
        ctx_sub_tracks = video_menu.addMenu("Subtitle Track")
        ctx_sub_tracks.addAction("Add Subtitle File...", self._add_subtitle_file)
        ctx_sub_tracks.addSeparator()
        sub_tracks = self.player_page.vlc.get_subtitle_tracks()
        if sub_tracks:
            items = sub_tracks.items() if isinstance(sub_tracks, dict) else sub_tracks
            for tid, name in items:
                act = ctx_sub_tracks.addAction(name)
                act.triggered.connect(lambda c, t=tid: self.player_page.vlc.set_subtitle_track(t))
        else:
            ctx_sub_tracks.addAction("(No subtitle tracks)").setEnabled(False)

        video_menu.addSeparator()
        # Re-create Aspect/Crop menus since actions weren't stored
        ar_menu = video_menu.addMenu("Aspect Ratio")
        for ratio in ["16:9", "4:3", "1:1", "16:10", "2.21:1", "2.35:1", "2.39:1", "5:4"]:
            ar_menu.addAction(ratio, lambda r=ratio: self.player_page.vlc.set_aspect_ratio(r))
        ar_menu.addSeparator()
        ar_menu.addAction("Default", lambda: self.player_page.vlc.set_aspect_ratio(None))

        crop_menu = video_menu.addMenu("Crop")
        for ratio in ["16:9", "4:3", "1:1", "16:10", "2.21:1", "2.35:1", "2.39:1", "5:4"]:
            crop_menu.addAction(ratio, lambda r=ratio: self.player_page.vlc.set_crop(r))
        crop_menu.addSeparator()
        crop_menu.addAction("Default", lambda: self.player_page.vlc.set_crop(None))

        # 4. Playback
        playback_menu = menu.addMenu("Playback")
        speed_menu = playback_menu.addMenu("Speed")
        speed_menu.addAction(self.act_speed_faster)
        speed_menu.addAction(self.act_speed_normal)
        speed_menu.addAction(self.act_speed_slower)
        playback_menu.addAction(self.act_jump_fwd)
        playback_menu.addAction(self.act_jump_back)
        playback_menu.addAction(self.act_jump_time)

        menu.addSeparator()

        # 5. View
        view_menu = menu.addMenu("View")
        view_menu.addAction(self.act_view_player)
        view_menu.addAction(self.act_view_library)
        view_menu.addAction(self.act_view_transcoder)
        view_menu.addAction(self.act_view_converter)

        # 6. Tools
        tools_menu = menu.addMenu("Tools")
        tools_menu.addAction(self.act_media_info)
        tools_menu.addAction(self.act_codec_info)
        tools_menu.addAction(self.act_transcode)
        tools_menu.addAction(self.act_converter_menu)

        # 7. Open Media
        open_menu = menu.addMenu("Open Media")
        open_menu.addAction(self.act_open_file)
        open_menu.addAction(self.act_open_multiple)
        open_menu.addAction(self.act_open_folder)
        open_menu.addAction(self.act_open_disc)
        open_menu.addAction(self.act_open_network)
        open_menu.addAction(self.act_open_capture)

        menu.addSeparator()
        menu.addAction(self.act_quit)

        menu.exec_(pos)

    def _navigate(self, page_index: int):
        """Switch to a page."""
        self.stack.setCurrentIndex(page_index)

    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
        self.titlebar.update_maximize_button(self.isMaximized())

    def _play_from_library(self, file_path: str):
        """Switch to player and play the given file."""
        self._navigate(self.PAGE_PLAYER)
        self.player_page.load_and_play(file_path)
        self._add_to_recent(file_path)

    def _update_title(self, filename: str):
        """Update titlebar text with currently playing filename."""
        if filename:
            self.titlebar.set_title(f"{filename} — Omneva")
        else:
            self.titlebar.set_title("Omneva")

    # ─── Fullscreen (video only) ────────────────────────────
    
    def _enter_fullscreen(self):
        """Go fullscreen — hide chrome, show only video."""
        self._is_fullscreen = True
        self.titlebar.hide()
        self.menubar.hide()
        self.statusbar.hide()
        central = self.centralWidget()
        central.setStyleSheet("QWidget#centralWidget { border: none; border-radius: 0; background: #000; }")
        self.player_page.set_fullscreen_mode(True)
        self.showFullScreen()

    def _add_subtitle_file(self):
        """Open dialog to load an external subtitle file."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Subtitle File",
            "",
            "Subtitles (*.srt *.ass *.ssa *.vtt *.sub);;All Files (*)",
        )
        if path:
            self.player_page.vlc.set_subtitle_file(path)

    def _exit_fullscreen(self):
        """Leave fullscreen — restore chrome."""
        self._is_fullscreen = False
        self.titlebar.show()
        self.menubar.show()
        central = self.centralWidget()
        central.setStyleSheet("")
        self.player_page.set_fullscreen_mode(False)
        self.showNormal()

    def _open_folder(self):
        """Open a folder and play the first media file found."""
        folder = QFileDialog.getExistingDirectory(self, "Open Folder")
        if folder:
            import os
            media_exts = ('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv',
                          '.webm', '.m4v', '.mp3', '.flac', '.wav', '.aac',
                          '.ogg', '.wma', '.m4a', '.opus')
            for f in sorted(os.listdir(folder)):
                if f.lower().endswith(media_exts):
                    self._navigate(self.PAGE_PLAYER)
                    self.player_page.load_and_play(os.path.join(folder, f))
                    break

    # ─── Resize grip (bottom-right corner) ──────────────────
    def mousePressEvent(self, event):
        if event.position().x() > self.width() - 10 and event.position().y() > self.height() - 10:
            self._resize_drag = True
            self._resize_start = event.globalPosition().toPoint()
            self._resize_size = self.size()
        else:
            self._resize_drag = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if getattr(self, '_resize_drag', False):
            delta = event.globalPosition().toPoint() - self._resize_start
            new_w = max(self.minimumWidth(), self._resize_size.width() + delta.x())
            new_h = max(self.minimumHeight(), self._resize_size.height() + delta.y())
            self.resize(new_w, new_h)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._resize_drag = False
        super().mouseReleaseEvent(event)

    # ─── Advanced Features ──────────────────────────────────

    def _open_multiple_files(self):
        """Open multiple files and add them to playlist."""
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Open Media Files",
            "",
            "Media Files (*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.webm *.m4v "
            "*.mp3 *.flac *.wav *.aac *.ogg *.wma *.m4a *.opus);;All Files (*)",
        )
        if paths:
            self._navigate(self.PAGE_PLAYER)
            # Play first, add rest
            first = paths[0]
            self.player_page.load_and_play(first)
            self._add_to_recent(first)
            
            for p in paths[1:]:
                self.player_page._playlist_files.append(p)
                self.player_page.playlist_panel.add_file(p)

    def _add_to_recent(self, file_path: str):
        """Add file to recent list in QSettings and update menu."""
        if not os.path.exists(file_path): return
        
        recent = self._settings.value("recentFiles", [])
        # Ensure list
        if not isinstance(recent, list):
            recent = []
            
        # Remove if exists, insert at 0
        if file_path in recent:
            recent.remove(file_path)
        recent.insert(0, file_path)
        
        # Trim
        if len(recent) > self.MAX_RECENT:
            recent = recent[:self.MAX_RECENT]
            
        self._settings.setValue("recentFiles", recent)
        self._update_recent_menu()

    def _update_recent_menu(self):
        """Populate the Recent Media menu."""
        self.act_recent_menu.clear()
        recent = self._settings.value("recentFiles", [])
        if not recent or not isinstance(recent, list):
            self.act_recent_menu.addAction("(No recent media)").setEnabled(False)
            return
            
        for path in recent:
            if os.path.exists(path):
                act = self.act_recent_menu.addAction(os.path.basename(path))
                act.triggered.connect(lambda checked=False, p=path: self._play_from_library(p))
            else:
                # Cleanup? Maybe later
                pass
        
        self.act_recent_menu.addSeparator()
        self.act_recent_menu.addAction("Clear Recent Media", self._clear_recent)

    def _clear_recent(self):
        self._settings.setValue("recentFiles", [])
        self._update_recent_menu()

    # ─── Dynamic Menus ──────────────────────────────────────

    def _populate_audio_tracks(self):
        self.audio_track_menu.clear()
        tracks = self.player_page.vlc.get_audio_tracks()
        
        # Add Disable option (usually id -1 or 0 depending on VLC version, but typically we just select a track)
        # Actually VLC often has 'Disable' as id -1. But get_audio_tracks returns valid tracks.
        
        if not tracks:
            self.audio_track_menu.addAction("(No audio tracks)").setEnabled(False)
            return

        for tid, name in tracks.items():
            act = self.audio_track_menu.addAction(name)
            act.setCheckable(True)
            # We don't easily know current track from API wrapper yet, but could add get_audio_track()
            # For now just connect action
            act.triggered.connect(lambda checked=False, t=tid: self.player_page.vlc.set_audio_track(t))

    def _populate_subtitle_tracks(self):
        self.subtitle_track_menu.clear()
        self.subtitle_track_menu.addAction("Add Subtitle File...", self._add_subtitle_file)
        self.subtitle_track_menu.addSeparator()
        
        tracks = self.player_page.vlc.get_subtitle_tracks()
        if not tracks:
            self.subtitle_track_menu.addAction("(No subtitle tracks)").setEnabled(False)
            return

        for tid, name in tracks.items():
            act = self.subtitle_track_menu.addAction(name)
            act.setCheckable(True)
            act.triggered.connect(lambda checked=False, t=tid: self.player_page.vlc.set_subtitle_track(t))

    def _populate_audio_devices(self):
        self.audio_device_menu.clear()
        devices = self.player_page.vlc.get_audio_output_devices()
        
        if not devices:
            self.audio_device_menu.addAction("Default")
            return

        for dev in devices:
            name = dev["description"]
            dev_id = dev["id"]
            act = self.audio_device_menu.addAction(name)
            act.setCheckable(True)
            # Check if current? Hard to know without getting it.
            act.triggered.connect(lambda checked=False, d=dev_id: self.player_page.vlc.set_audio_output_device(d))

    def _populate_stereo_mode(self):
        self.stereo_mode_menu.clear()
        # Common modes from vlc.AudioOutputChannel
        import vlc
        modes = [
            ("Stereo", vlc.AudioOutputChannel.Stereo),
            ("Mono", vlc.AudioOutputChannel.Mono),
            ("Left", vlc.AudioOutputChannel.Left),
            ("Right", vlc.AudioOutputChannel.Right),
            ("Reverse Stereo", vlc.AudioOutputChannel.ReverseStereo),
        ]
        
        curr = self.player_page.vlc.get_stereo_mode()
        
        for label, mode in modes:
            act = self.stereo_mode_menu.addAction(label)
            act.setCheckable(True)
            if curr == mode:
                act.setChecked(True)
            act.triggered.connect(lambda checked=False, m=mode: self.player_page.vlc.set_stereo_mode(m))

    def _populate_visualizations(self):
        self.vis_menu.clear()
        self.vis_menu.addAction("(Visualizations not yet implemented)").setEnabled(False)
        # To implement: need audio_filter list and set_audio_filter logic in engine

    # ─── Tools Dialogs ──────────────────────────────────────

    def _open_effects_dialog(self, tab_index=0):
        from src.ui.tools_dialogs import EffectsAndFiltersDialog
        
        if not hasattr(self, 'effects_dlg') or self.effects_dlg is None:
             self.effects_dlg = EffectsAndFiltersDialog(self.player_page.vlc, self)
             
        try:
            self.effects_dlg.tabs.setCurrentIndex(tab_index if isinstance(tab_index, int) else 0)
            self.effects_dlg.show()
            self.effects_dlg.raise_()
            self.effects_dlg.activateWindow()
        except RuntimeError:
            self.effects_dlg = EffectsAndFiltersDialog(self.player_page.vlc, self)
            self.effects_dlg.tabs.setCurrentIndex(tab_index if isinstance(tab_index, int) else 0)
            self.effects_dlg.show()

    def _show_media_info(self):
        """Show Media Information Dialog (General tab)."""
        from src.ui.tools_dialogs import MediaInfoDialog
        
        if not hasattr(self, 'media_info_dlg') or self.media_info_dlg is None:
            self.media_info_dlg = MediaInfoDialog(self.player_page.vlc, self, initial_tab=0)
        
        try:
            self.media_info_dlg.tabs.setCurrentIndex(0)
            self.media_info_dlg.show()
            self.media_info_dlg.raise_()
            self.media_info_dlg.activateWindow()
        except RuntimeError:
            self.media_info_dlg = MediaInfoDialog(self.player_page.vlc, self, initial_tab=0)
            self.media_info_dlg.show()

    def _show_codec_info(self):
        """Show Media Information Dialog (Codec tab)."""
        self._open_effects_dialog(2) # Fallback if dedicated dialog isn't ready
        # Actually, MediaInfoDialog has a codec tab at index 2.
        self._show_media_info()
        self.media_info_dlg.tabs.setCurrentIndex(2)

    def _show_about(self):
        from src.ui.tools_dialogs import AboutDialog
        dlg = AboutDialog(self)
        dlg.exec()

    def _show_preferences(self):
        self._on_settings_clicked()

    def _check_updates(self):
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Check for Updates", "You are using the latest version of Omneva.")

    def _open_effects_dialog(self, initial_tab=0):
        """Open the Video Effects and Synchronization dialog."""
        from src.ui.tools_dialogs import VideoEffectsDialog
        dlg = VideoEffectsDialog(self.player_page.vlc, self)
        dlg.tabs.setCurrentIndex(initial_tab)
        dlg.show() # Non-modal so user can see effects live

    def _populate_renderers(self):
        """Dynamically list discovered renderers in the menu."""
        self.renderer_menu.clear()
        
        # Local playback option
        act_local = self.renderer_menu.addAction("Local")
        act_local.setCheckable(True)
        act_local.setChecked(True) # TODO: Track current renderer
        act_local.triggered.connect(lambda: self.player_page.vlc.set_renderer(None))
        
        self.renderer_menu.addSeparator()
        
        renderers = self.player_page.vlc._renderers
        if not renderers:
            act_none = self.renderer_menu.addAction("No renderers found")
            act_none.setEnabled(False)
        else:
            for name in renderers:
                act = self.renderer_menu.addAction(name)
                act.setCheckable(True)
                act.triggered.connect(lambda checked, n=name: self.player_page.vlc.set_renderer(n))

    def closeEvent(self, event):
        """Stop discovery and cleanup on close."""
        self.player_page.vlc.stop_renderer_discovery()
        super().closeEvent(event)



