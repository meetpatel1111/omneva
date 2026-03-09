"""Menu Factory — Handles construction of the application's menu bar."""

from PySide6.QtWidgets import QMenuBar, QMenu
from PySide6.QtGui import QAction, QKeySequence

class MenuFactory:
    """Factory to build and organize the complex VLC-style menu bar."""

    def __init__(self, main_window):
        self.mw = main_window

    def create_menubar(self) -> QMenuBar:
        menubar = QMenuBar()
        menubar.setObjectName("appMenuBar")
        menubar.setFixedHeight(24)

        self._create_media_menu(menubar)
        self._create_playback_menu(menubar)
        self._create_audio_menu(menubar)
        self._create_video_menu(menubar)
        self._create_tools_menu(menubar)
        self._create_view_menu(menubar)
        self._create_help_menu(menubar)

        return menubar

    def _create_media_menu(self, menubar):
        menu = menubar.addMenu("&Media")
        
        self.mw.act_open_file = menu.addAction("Open File...")
        self.mw.act_open_file.setShortcut(QKeySequence("Ctrl+O"))

        self.mw.act_open_multiple = menu.addAction("Open Multiple Files...")
        self.mw.act_open_multiple.setShortcut(QKeySequence("Ctrl+Shift+O"))

        self.mw.act_open_folder = menu.addAction("Open Folder...")
        self.mw.act_open_folder.setShortcut(QKeySequence("Ctrl+F"))

        self.mw.act_open_disc = menu.addAction("Open Disc...")
        self.mw.act_open_disc.setShortcut(QKeySequence("Ctrl+D"))

        self.mw.act_open_network = menu.addAction("Open Network Stream...")
        self.mw.act_open_network.setShortcut(QKeySequence("Ctrl+N"))

        self.mw.act_open_capture = menu.addAction("Open Capture Device...")
        self.mw.act_open_capture.setShortcut(QKeySequence("Ctrl+C"))

        self.mw.act_open_clipboard = menu.addAction("Open Location from clipboard")
        self.mw.act_open_clipboard.setShortcut(QKeySequence("Ctrl+V"))

        self.mw.act_recent_menu = menu.addMenu("Open Recent Media")

        menu.addSeparator()

        self.mw.act_save_playlist = menu.addAction("Save Playlist to File...")
        self.mw.act_save_playlist.setShortcut(QKeySequence("Ctrl+Y"))

        self.mw.act_convert = menu.addAction("Convert / Save...")
        self.mw.act_convert.setShortcut(QKeySequence("Ctrl+R"))

        self.mw.act_stream = menu.addAction("Stream...")
        self.mw.act_stream.setShortcut(QKeySequence("Ctrl+S"))

        menu.addSeparator()

        self.mw.act_clear_playlist = menu.addAction("Clear Playlist")
        self.mw.act_clear_playlist.setShortcut(QKeySequence("Ctrl+W"))

        menu.addSeparator()

        self.mw.act_quit_end = menu.addAction("Quit at the end of playlist")
        self.mw.act_quit_end.setCheckable(True)

        self.mw.act_quit = menu.addAction("Quit")
        self.mw.act_quit.setShortcut(QKeySequence("Ctrl+Q"))

    def _create_playback_menu(self, menubar):
        menu = menubar.addMenu("P&layback")

        menu.addMenu("Title")
        menu.addMenu("Chapter")
        menu.addMenu("Program")
        self.mw.act_bookmarks = menu.addAction("Bookmarks")
        self.mw.act_bookmarks.setShortcut(QKeySequence("Ctrl+B"))
        menu.addMenu("Custom Bookmarks")

        self.mw.renderer_menu = menu.addMenu("Renderer")
        self.mw.renderer_menu.aboutToShow.connect(self.mw._populate_renderers)

        speed_menu = menu.addMenu("Speed")
        self.mw.act_speed_faster = speed_menu.addAction("Faster")
        self.mw.act_speed_faster.setShortcut(QKeySequence("]"))
        self.mw.act_speed_normal = speed_menu.addAction("Normal")
        self.mw.act_speed_normal.setShortcut(QKeySequence("="))
        self.mw.act_speed_slower = speed_menu.addAction("Slower")
        self.mw.act_speed_slower.setShortcut(QKeySequence("["))

        menu.addSeparator()

        self.mw.act_jump_fwd = menu.addAction("Jump Forward")
        self.mw.act_jump_fwd.setShortcut(QKeySequence("Right"))

        self.mw.act_jump_back = menu.addAction("Jump Backward")
        self.mw.act_jump_back.setShortcut(QKeySequence("Left"))

        self.mw.act_jump_time = menu.addAction("Jump to Specific Time")
        self.mw.act_jump_time.setShortcut(QKeySequence("Ctrl+T"))

        menu.addSeparator()

        self.mw.act_play_pause = menu.addAction("Play")
        self.mw.act_play_pause.setShortcut(QKeySequence("Space"))

        self.mw.act_stop = menu.addAction("Stop")
        self.mw.act_stop.setShortcut(QKeySequence("S"))

        self.mw.act_prev = menu.addAction("Previous")
        self.mw.act_prev.setShortcut(QKeySequence("P"))

        self.mw.act_next = menu.addAction("Next")
        self.mw.act_next.setShortcut(QKeySequence("Ctrl+Right"))

        menu.addSeparator()

        self.mw.act_restart = menu.addAction("Start from Beginning")
        self.mw.act_restart.setShortcut(QKeySequence("N"))

        self.mw.act_cycle_loop = menu.addAction("Cycle Loop Mode")
        self.mw.act_cycle_loop.setShortcut(QKeySequence("L"))

        self.mw.act_record = menu.addAction("Record")

    def _create_audio_menu(self, menubar):
        menu = menubar.addMenu("&Audio")

        self.mw.act_mute = menu.addAction("Mute")
        self.mw.act_mute.setShortcut(QKeySequence("M"))

        self.mw.act_vol_up = menu.addAction("Volume Up")
        self.mw.act_vol_up.setShortcut(QKeySequence("Ctrl+Up"))

        self.mw.act_vol_down = menu.addAction("Volume Down")
        self.mw.act_vol_down.setShortcut(QKeySequence("Ctrl+Down"))

        menu.addSeparator()
        self.mw.audio_track_menu = menu.addMenu("Audio Track")
        self.mw.audio_track_menu.aboutToShow.connect(self.mw._populate_audio_tracks)

        self.mw.audio_device_menu = menu.addMenu("Audio Device")
        self.mw.audio_device_menu.aboutToShow.connect(self.mw._populate_audio_devices)

        self.mw.stereo_mode_menu = menu.addMenu("Stereo Mode")
        self.mw.stereo_mode_menu.aboutToShow.connect(self.mw._populate_stereo_mode)

        self.mw.vis_menu = menu.addMenu("Visualizations")
        self.mw.vis_menu.aboutToShow.connect(self.mw._populate_visualizations)

        menu.addSeparator()
        self.mw.act_audio_delay_down = menu.addAction("Decrease Audio Delay")
        self.mw.act_audio_delay_down.setShortcut(QKeySequence("J"))

        self.mw.act_audio_delay_up = menu.addAction("Increase Audio Delay")
        self.mw.act_audio_delay_up.setShortcut(QKeySequence("K"))

        menu.addSeparator()
        self.mw.act_cycle_audio = menu.addAction("Cycle Audio Track")
        self.mw.act_cycle_audio.setShortcut(QKeySequence("B"))

    def _create_video_menu(self, menubar):
        menu = menubar.addMenu("&Video")

        self.mw.act_fullscreen = menu.addAction("Fullscreen")
        self.mw.act_fullscreen.setShortcut(QKeySequence("F"))

        menu.addSeparator()

        self.mw.subtitle_track_menu = menu.addMenu("Subtitle Track")
        self.mw.subtitle_track_menu.aboutToShow.connect(self.mw._populate_subtitle_tracks)

        menu.addSeparator()

        ar_menu = menu.addMenu("Aspect Ratio")
        for ratio in ["16:9", "4:3", "1:1", "16:10", "2.21:1", "2.35:1", "2.39:1", "5:4"]:
            ar_menu.addAction(ratio, lambda r=ratio: self.mw.player_page.vlc.set_aspect_ratio(r))
        ar_menu.addSeparator()
        ar_menu.addAction("Default", lambda: self.mw.player_page.vlc.set_aspect_ratio(None))

        self.mw.act_cycle_aspect = menu.addAction("Cycle Aspect Ratio")
        self.mw.act_cycle_aspect.setShortcut(QKeySequence("A"))

        crop_menu = menu.addMenu("Crop")
        for ratio in ["16:9", "4:3", "1:1", "16:10", "2.21:1", "2.35:1", "2.39:1", "5:4"]:
            crop_menu.addAction(ratio, lambda r=ratio: self.mw.player_page.vlc.set_crop(r))
        crop_menu.addSeparator()
        crop_menu.addAction("Default", lambda: self.mw.player_page.vlc.set_crop(None))

        self.mw.act_toggle_autoscale = menu.addAction("Toggle Original Size / Fit")
        self.mw.act_toggle_autoscale.setShortcut(QKeySequence("O"))

        self.mw.act_screenshot = menu.addAction("Take Snapshot")
        self.mw.act_screenshot.setShortcut(QKeySequence("Shift+S"))

        menu.addSeparator()
        self.mw.act_cycle_sub = menu.addAction("Cycle Subtitle Track")
        self.mw.act_cycle_sub.setShortcut(QKeySequence("V"))

        self.mw.act_sub_delay_down = menu.addAction("Decrease Subtitle Delay")
        self.mw.act_sub_delay_down.setShortcut(QKeySequence("G"))

        self.mw.act_sub_delay_up = menu.addAction("Increase Subtitle Delay")
        self.mw.act_sub_delay_up.setShortcut(QKeySequence("H"))

        self.mw.act_cycle_crop = menu.addAction("Cycle Crop")
        self.mw.act_cycle_crop.setShortcut(QKeySequence("C"))

        self.mw.act_cycle_zoom = menu.addAction("Cycle Zoom")
        self.mw.act_cycle_zoom.setShortcut(QKeySequence("Z"))

    def _create_tools_menu(self, menubar):
        menu = menubar.addMenu("Tool&s")

        self.mw.act_effects = menu.addAction("Effects and Filters")
        self.mw.act_effects.setShortcut(QKeySequence("Ctrl+E"))
        
        self.mw.act_vlm = menu.addAction("VLM Configurator")
        self.mw.act_vlm.setShortcut(QKeySequence("Ctrl+Shift+W"))

        self.mw.act_sync = menu.addAction("Track Synchronization")

        menu.addSeparator()

        self.mw.act_tool_transcoder = menu.addAction("Transcoder")

        self.mw.act_tool_converter = menu.addAction("Converter")

        menu.addSeparator()

        self.mw.act_media_info = menu.addAction("Media Information")
        self.mw.act_media_info.setShortcut(QKeySequence("Ctrl+I"))
        
        self.mw.act_codec_info = menu.addAction("Codec Information")
        self.mw.act_codec_info.setShortcut(QKeySequence("Ctrl+J"))

        self.mw.act_messages = menu.addAction("Messages")
        self.mw.act_messages.setShortcut(QKeySequence("Ctrl+M"))

        menu.addSeparator()

        self.mw.act_preferences = menu.addAction("Preferences")
        self.mw.act_preferences.setShortcut(QKeySequence("Ctrl+P"))

    def _create_view_menu(self, menubar):
        menu = menubar.addMenu("V&iew")

        self.mw.act_view_playlist = menu.addAction("Playlist")
        self.mw.act_view_playlist.setShortcut(QKeySequence("Ctrl+L"))

        self.mw.act_docked_playlist = menu.addAction("Docked Playlist")
        self.mw.act_docked_playlist.setCheckable(True)
        self.mw.act_docked_playlist.setChecked(True)
        
        playlist_view_mode = menu.addMenu("Playlist View Mode")
        playlist_view_mode.addAction("Icons", lambda: self.mw.library_page.set_view_mode(self.mw.library_page.VIEW_ICONS))
        playlist_view_mode.addAction("Detailed List", lambda: self.mw.library_page.set_view_mode(self.mw.library_page.VIEW_DETAILS))
        playlist_view_mode.addAction("List", lambda: self.mw.library_page.set_view_mode(self.mw.library_page.VIEW_LIST))

        menu.addSeparator()

        self.mw.act_always_on_top = menu.addAction("Always on top")
        self.mw.act_always_on_top.setCheckable(True)

        self.mw.act_minimal_interface = menu.addAction("Minimal Interface")
        self.mw.act_minimal_interface.setShortcut(QKeySequence("Ctrl+H"))
        self.mw.act_minimal_interface.setCheckable(True)

        self.mw.act_fullscreen_interface = menu.addAction("Fullscreen Interface")
        self.mw.act_fullscreen_interface.setShortcut(QKeySequence("F11"))

        menu.addSeparator()

        self.mw.act_advanced_controls = menu.addAction("Advanced Controls")
        self.mw.act_advanced_controls.setShortcut(QKeySequence("Ctrl+A"))
        self.mw.act_advanced_controls.setCheckable(True)
        
        self.mw.act_status_bar = menu.addAction("Status Bar")
        self.mw.act_status_bar.setCheckable(True)
        self.mw.act_status_bar.setChecked(True)

        menu.addSeparator()

        iface_menu = menu.addMenu("Add Interface")
        iface_menu.addAction("Web Interface")
        iface_menu.addAction("Telnet Interface")
        iface_menu.addAction("Console Interface")
        iface_menu.addAction("Mouse Gestures")

        menu.addAction("VLsub")

    def _create_help_menu(self, menubar):
        menu = menubar.addMenu("&Help")
        
        self.mw.act_shortcuts = menu.addAction("Help")
        self.mw.act_shortcuts.setShortcut(QKeySequence("F1"))

        self.mw.act_about = menu.addAction("About Omneva")
        self.mw.act_about.setShortcut(QKeySequence("Shift+F1"))
        self.mw.act_check_updates = menu.addAction("Check for Updates...")
