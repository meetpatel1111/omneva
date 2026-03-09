"""VLC Engine — python-vlc wrapper for LibVLC playback."""

import sys
import os
import vlc

from PySide6.QtCore import QObject, Signal, QTimer


class VLCEngine(QObject):
    """Wraps python-vlc to provide a clean playback API."""

    # Signals to update UI
    position_changed = Signal(float)     # current position in seconds
    duration_changed = Signal(float)     # total duration in seconds
    state_changed = Signal(str)          # "playing", "paused", "stopped", "ended"
    volume_changed = Signal(int)         # 0-100
    mute_changed = Signal(bool)          # True/False
    media_changed = Signal(str)          # file path
    renderer_item_added = Signal(object) # vlc.RendererItem
    renderer_item_deleted = Signal(object)


    def __init__(self, parent=None):
        super().__init__(parent)

        # Add VLC to DLL search path on Windows
        vlc_path = self._find_vlc_path()
        if vlc_path and sys.platform == "win32":
            os.add_dll_directory(vlc_path)

        args = [
            # Basic configuration
            "--no-xlib",          # Linux: no X11 dependency for threads
            "--quiet",            # Suppress console output
            "--no-video-title-show",  # No video title overlay
            
            # Hardware acceleration (compatible with VLC)
            "--avcodec-hw",       # Enable hardware decoding (compatible)
            
            # Performance optimizations
            "--ffmpeg-threads=4", # Multi-threaded decoding
            
            # Network optimizations
            "--network-caching=1000", # 1s network cache
            "--rtsp-tcp",         # Use TCP for RTSP (more reliable)
        ]
        
        # In PyInstaller EXEs, libvlc fails to find plugins because the process dir != VLC dir
        # By explicitly passing --plugin-path, audio plugins (and others) load correctly.
        if vlc_path:
            plugin_path = os.path.join(vlc_path, "plugins")
            if os.path.exists(plugin_path):
                args.append(f"--plugin-path={plugin_path}")

        # Create VLC instance
        try:
            self.instance = vlc.Instance(args)
            if self.instance is None:
                # Fallback to basic args if advanced args fail
                basic_args = ["--no-xlib", "--quiet"]
                self.instance = vlc.Instance(basic_args)
                if self.instance is None:
                    raise Exception("Failed to create VLC instance with basic args")
        except Exception as e:
            print(f"VLC instance creation failed: {e}")
            raise
        
        self.player = self.instance.media_player_new()
        
        # Disable VLC's internal input handling so Qt gets events
        self.player.video_set_mouse_input(False)
        self.player.video_set_key_input(False)

        self._current_file = None
        self._current_file = None
        self._duration = 0.0
        self._last_state = "stopped"

        # Poll timer for position updates (VLC doesn't have native signals)
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(250)  # 4 updates/sec
        self._poll_timer.timeout.connect(self._poll_state)

        self._audio_delay = 0 # in ms
        self._spu_delay = 0 # in ms
        self._spu_scale = 1.0
        self._audio_sync_bookmark = None # time in ms

        self._spu_sync_bookmark = None # time in ms

        # Granular Crop state (pixels)
        self._crop_top = 0
        self._crop_left = 0
        self._crop_bottom = 0
        self._crop_right = 0

        # Playlist Bookmarks (1-10) -> {index: (path, time_ms)}
        self._bookmarks = {}

        # Renderer Discovery
        self._discoverers = []
        self._renderers = {} # name -> item

        # Loop modes: 0=Off, 1=One, 2=All
        self._loop_mode = 0




    def _find_vlc_path(self) -> str | None:
        """Locate VLC installation."""
        from src.core.utils import find_vlc_lib
        return find_vlc_lib()

    # ─── Embedding ──────────────────────────────────────────

    def set_window(self, win_id: int):
        """Embed VLC video output into a Qt widget by native window handle."""
        if sys.platform == "win32":
            self.player.set_hwnd(win_id)
        elif sys.platform == "darwin":
            self.player.set_nsobject(win_id)
        else:  # Linux
            self.player.set_xwindow(win_id)

    # ─── Playback Controls ──────────────────────────────────

    def load(self, file_path: str):
        """Load a media file without playing."""
        self._current_file = file_path

        # Handle disc protocols
        if not (file_path.startswith("dvd://") or file_path.startswith("bluray://") or file_path.startswith("vcd://")):
            self.media = self.instance.media_new(file_path)
        else:
            self.media = self.instance.media_new_location(file_path)

        # Parse asynchronously
        self.media.parse_with_options(vlc.MediaParseFlag.local, 0)
        self.player.set_media(self.media)
        self._duration = 0.0
        self.media_changed.emit(file_path)


    def play(self, file_path: str = None):
        """Play a file or resume current media."""
        if file_path:
            self.load(file_path)
        
        # Ensure media is set if we are resuming
        if not self.player.get_media() and hasattr(self, 'media'):
            self.player.set_media(self.media)
            
        self.player.play()
        self._poll_timer.start()
        self.state_changed.emit("playing")

    def pause(self):
        """Toggle pause."""
        self.player.pause()
        if self.player.is_playing():
            self.state_changed.emit("playing")
        else:
            self.state_changed.emit("paused")

    def stop(self):
        """Stop playback."""
        self.player.stop()
        self._poll_timer.stop()
        self.state_changed.emit("stopped")
        self.position_changed.emit(0.0)

    def toggle_play_pause(self):
        """Toggle between play and pause."""
        state = self.player.get_state()
        if state == vlc.State.Playing:
            self.pause()
        elif state in (vlc.State.Paused, vlc.State.Stopped, vlc.State.Ended):
            if state == vlc.State.Ended and self._current_file:
                self.play(self._current_file)
            else:
                self.play()
        elif self._current_file:
            self.play(self._current_file)

    # ─── Seeking ────────────────────────────────────────────

    def seek(self, seconds: float):
        """Seek to absolute position in seconds."""
        if self._duration > 0:
            position = max(0.0, min(1.0, seconds / self._duration))
            self.player.set_position(position)

    def seek_relative(self, delta_seconds: float):
        """Seek forward/backward by delta seconds."""
        current = self.get_position()
        self.seek(current + delta_seconds)

    def get_position(self) -> float:
        """Get current position in seconds."""
        pos = self.player.get_position()  # 0.0 - 1.0
        if pos < 0:
            return 0.0
        return pos * self._duration

    def get_duration(self) -> float:
        """Get total duration in seconds."""
        return self._duration

    # ─── Volume ─────────────────────────────────────────────

    def set_volume(self, volume: int):
        """Set volume (0-100)."""
        vol = max(0, min(100, volume))
        self.player.audio_set_volume(vol)
        self.volume_changed.emit(vol)

    def get_volume(self) -> int:
        return self.player.audio_get_volume()

    def toggle_mute(self):
        self.set_mute(not self.is_muted())

    def set_mute(self, muted: bool):
        self.player.audio_set_mute(muted)
        self.mute_changed.emit(muted)
        # Also emit volume changed to update slider if needed (optional)
        self.volume_changed.emit(self.get_volume())

    def volume_up(self):
        """Increase volume by 5%."""
        current = self.get_volume()
        self.set_volume(current + 5)

    def volume_down(self):
        """Decrease volume by 5%."""
        current = self.get_volume()
        self.set_volume(current - 5)

    def is_muted(self) -> bool:
        return bool(self.player.audio_get_mute())

    def get_audio_delay(self):
        """Get audio delay in microseconds."""
        return self.player.audio_get_delay()

    def set_audio_delay(self, delay_ms: int):
        """Set audio delay in milliseconds."""
        # VLC API uses microseconds
        self.player.audio_set_delay(delay_ms * 1000)
        return delay_ms

    def change_audio_delay(self, delta_ms: int):
        """Change audio delay by delta_ms."""
        current_us = self.player.audio_get_delay()
        new_ms = (current_us // 1000) + delta_ms
        self.set_audio_delay(new_ms)
        return new_ms

    def get_subtitle_delay(self):
        """Get subtitle delay in microseconds."""
        return self.player.video_get_spu_delay()

    def set_subtitle_delay(self, delay_ms: int):
        """Set subtitle delay in milliseconds."""
        # VLC API uses microseconds
        self.player.video_set_spu_delay(delay_ms * 1000)
        return delay_ms

    def change_subtitle_delay(self, delta_ms: int):
        """Change subtitle delay by delta_ms."""
        current_us = self.player.video_get_spu_delay()
        new_ms = (current_us // 1000) + delta_ms
        self.set_subtitle_delay(new_ms)
        return new_ms

    def toggle_subtitles(self):
        """Toggle subtitles on or off."""
        current = self.player.video_get_spu()
        if current == -1:
            # Try to find first available track
            tracks = self.player.video_get_spu_description()
            if tracks and len(tracks) > 1:
                 # tracks[0] is 'Disable', tracks[1] is usually first track
                 self.player.video_set_spu(tracks[1][0])
                 return True
        else:
            self.player.video_set_spu(-1)
            return False
        return False

    # ─── Audio Output / Devices ─────────────────────────────

    def get_audio_output_devices(self) -> list[dict]:
        """Get list of audio output devices."""
        devices = self.player.audio_output_device_enum()
        if not devices:
            return []
        
        result = []
        curr = devices
        while curr:
            result.append({
                "id": curr.contents.device,
                "name": curr.contents.description.decode('utf-8') if curr.contents.description else "Unknown"
            })
            curr = curr.contents.next
        
        vlc.libvlc_audio_output_device_list_release(devices)
        return result

    def cycle_audio_device(self):
        """Cycle through available audio output devices."""
        devices = self.get_audio_output_devices()
        if not devices:
            return "Default"
            
        current_id = self.player.audio_output_device_get()
        
        # Simple cycle
        current_idx = -1
        for i, d in enumerate(devices):
            if d["id"] == current_id:
                current_idx = i
                break
        
        next_idx = (current_idx + 1) % len(devices)
        next_device = devices[next_idx]
        
        self.player.audio_output_device_set(None, next_device["id"])
        return next_device["name"]

        # Assuming only default audio output module for now
        # libvlc_audio_output_device_enum( mp, psz_audio_output )
        
        # In python-vlc, player.audio_output_device_enum() returns start of list
        # But we need to know WHICH audio output module to enum for.
        # usually None works for default
        
        devices = []
        mods = self.player.audio_output_device_enum()
        if mods:
            # It returns a ctypes pointer to LP_AudioOutputDevice
            # We iterate it
            curr = mods
            while curr:
                dev = curr.contents
                devices.append({
                    "id": dev.device.decode('utf-8') if dev.device else None,
                    "description": dev.description.decode('utf-8') if dev.description else "Unknown"
                })
                curr = dev.next
            vlc.libvlc_audio_output_device_list_release(mods)
        return devices

    def set_audio_output_device(self, device_id: str):
        """Set audio output device."""
        self.player.audio_output_device_set(None, device_id)

    # ─── Stereo Mode ────────────────────────────────────────

    def get_stereo_mode(self):
        """Get current audio channel/stereo mode."""
        return self.player.audio_get_channel()

    def set_stereo_mode(self, mode: int):
        """Set audio channel. mode is vlc.AudioOutputChannel.* constant."""
        self.player.audio_set_channel(mode)


    # ─── Video Control ──────────────────────────────────────

    def set_aspect_ratio(self, ratio: str | None):
        """Set video aspect ratio (e.g. '16:9', '4:3', None to reset)."""
        if ratio:
            self.player.video_set_aspect_ratio(ratio.encode())
        else:
            self.player.video_set_aspect_ratio(None)

    def cycle_aspect_ratio(self):
        """Cycle through common aspect ratios."""
        ratios = [None, "16:9", "4:3", "16:10", "2.35:1", "1:1"]
        current = self.player.video_get_aspect_ratio()
        current_str = current.decode('utf-8') if current else None
        
        try:
            idx = ratios.index(current_str)
            next_idx = (idx + 1) % len(ratios)
        except ValueError:
            next_idx = 0
            
        self.set_aspect_ratio(ratios[next_idx])
        return ratios[next_idx] or "Default"

    def set_crop(self, crop: str | None):
        """Set video crop (e.g. '16:9', '4:3', None to reset)."""
        if crop:
            self.player.video_set_crop_geometry(crop.encode())
        else:
            self.player.video_set_crop_geometry(None)

    def cycle_crop(self):
        """Cycle through common crop geometries."""
        crops = [None, "16:9", "4:3", "16:10", "2.35:1", "1:1"]
        current = self.player.video_get_crop_geometry()
        current_str = current.decode('utf-8') if current else None
        
        try:
            idx = crops.index(current_str)
            next_idx = (idx + 1) % len(crops)
        except ValueError:
            next_idx = 0
            
        self.set_crop(crops[next_idx])
        
        # Reset granular crop when cycling preset ratios
        self._crop_top = 0
        self._crop_left = 0
        self._crop_bottom = 0
        self._crop_right = 0
        
        return crops[next_idx] or "Original"

    def adjust_pixel_crop(self, side: str, delta: int):
        """
        Adjust crop by delta pixels on a specific side.
        side: 'top', 'bottom', 'left', 'right'
        """
        if side == 'top': self._crop_top = max(0, self._crop_top + delta)
        elif side == 'bottom': self._crop_bottom = max(0, self._crop_bottom + delta)
        elif side == 'left': self._crop_left = max(0, self._crop_left + delta)
        elif side == 'right': self._crop_right = max(0, self._crop_right + delta)

        # Get video size to calculate final geometry
        width, height = self.get_video_size()
        if width <= 0 or height <= 0:
            # Fallback if no video yet
            return "No Video"

        # width x height + left + top
        w = width - self._crop_left - self._crop_right
        h = height - self._crop_top - self._crop_bottom
        
        # Clamp to avoid negative dimensions
        w = max(1, w)
        h = max(1, h)
        
        geom = f"{w}x{h}+{self._crop_left}+{self._crop_top}"
        self.player.video_set_crop_geometry(geom.encode())
        return f"Crop {side.capitalize()}: {getattr(self, f'_crop_{side}')}px"

        w = self.player.video_get_width()
        h = self.player.video_get_height()
        return w, h

    # ─── Bookmarks ──────────────────────────────────────────

    def set_bookmark(self, index: int):
        """Save current file and time to a bookmark slot (1-10)."""
        path = self._current_file
        if not path:
            return "No Media"
        
        time_ms = self.player.get_time()
        self._bookmarks[index] = (path, time_ms)
        from src.core.utils import format_duration
        return f"Set Bookmark {index}: {format_duration(time_ms/1000)}"

    def get_bookmark(self, index: int):
        """Get bookmark data (path, time_ms) for a slot."""
        return self._bookmarks.get(index)



    def is_muted(self) -> bool:
        return bool(self.player.audio_get_mute())

    # ─── Chapters / Titles ──────────────────────────────────

    def next_chapter(self):
        """Skip to next chapter (if supported by media)."""
        self.player.chapter_next()

    def previous_chapter(self):
        """Skip to previous chapter (if supported by media)."""
        self.player.chapter_previous()

    # ─── DVD / Menu Navigation ───

    def navigate_up(self):
        """Navigate up in DVD menu."""
        self.player.navigate(vlc.NavigateMode.up)

    def navigate_down(self):
        """Navigate down in DVD menu."""
        self.player.navigate(vlc.NavigateMode.down)

    def navigate_left(self):
        """Navigate left in DVD menu."""
        self.player.navigate(vlc.NavigateMode.left)

    def navigate_right(self):
        """Navigate right in DVD menu."""
        self.player.navigate(vlc.NavigateMode.right)

    def navigate_activate(self):
        """Activate current menu item in DVD menu."""
        self.player.navigate(vlc.NavigateMode.activate)

    def toggle_disc_menu(self):
        """Toggle disk menu."""
        # VLC Shift+M usually toggles the root menu
        # This is often handled by a specific title skip or navigate call
        # We'll use the 'activate' or 'root' if supported. 
        # Actually navigate(vlc.NavigateMode.activate) on some discs opens menu.
        # But 'title set' to 0 often goes to menu.
        self.player.title_set(0) 
        return "Disc Menu"


    def next_title(self):
        """Skip to next title."""
        curr = self.player.get_title()
        if curr != -1:
            self.player.set_title(curr + 1)

    def previous_title(self):
        """Skip to previous title."""
        curr = self.player.get_title()
        if curr > 0:
            self.player.set_title(curr - 1)

    def cycle_audio_track(self):
        """Cycle through available audio tracks."""
        tracks = self.player.audio_get_track_description()
        if not tracks or len(tracks) <= 1: return None
        
        current = self.player.audio_get_track()
        ids = [t[0] for t in tracks]
        try:
            idx = ids.index(current)
            next_idx = (idx + 1) % len(ids)
            # Skip 'Disable' (usually -1) if we have other options
            if ids[next_idx] == -1 and len(ids) > 1:
                next_idx = (next_idx + 1) % len(ids)
        except ValueError:
            next_idx = 1 if len(ids) > 1 else 0
            
        self.player.audio_set_track(ids[next_idx])
        return tracks[next_idx][1].decode('utf-8') if next_idx < len(tracks) else "Default"

    def cycle_subtitle_track(self):
        """Cycle through available subtitle tracks."""
        tracks = self.player.video_get_spu_description()
        if not tracks: return None
        
        current = self.player.video_get_spu()
        ids = [t[0] for t in tracks]
        try:
            idx = ids.index(current)
            next_idx = (idx + 1) % len(ids)
        except ValueError:
            next_idx = 0
            
        self.player.video_set_spu(ids[next_idx])
        return tracks[next_idx][1].decode('utf-8') if next_idx < len(tracks) else "Disabled"

    def cycle_subtitle_reverse(self):
        """Cycle through available subtitle tracks in reverse."""
        tracks = self.player.video_get_spu_description()
        if not tracks: return None
        
        current = self.player.video_get_spu()
        ids = [t[0] for t in tracks]
        try:
            idx = ids.index(current)
            next_idx = (idx - 1) % len(ids)
        except ValueError:
            next_idx = len(ids) - 1
            
        self.player.video_set_spu(ids[next_idx])
        return tracks[next_idx][1].decode('utf-8') if next_idx < len(tracks) else "Disabled"

    def cycle_zoom(self, reverse=False):
        """Cycle through zoom levels."""
        zooms = [0.0, 0.25, 0.5, 1.0, 2.0] 
        current = self.player.video_get_scale()
        if current <= 0: current = 1.0
        
        diffs = [abs(z - current) for z in zooms]
        idx = diffs.index(min(diffs))
        
        if reverse:
            next_idx = (idx - 1) % len(zooms)
        else:
            next_idx = (idx + 1) % len(zooms)
            
        new_zoom = zooms[next_idx]
        self.player.video_set_scale(new_zoom)
        return f"{new_zoom}x" if new_zoom > 0 else "Auto"


    def toggle_deinterlace(self):
        """Toggle deinterlacing on/off (defaults to yadif)."""
        if not hasattr(self, '_deinterlace_on'): self._deinterlace_on = False
        self._deinterlace_on = not self._deinterlace_on
        
        mode = "yadif" if self._deinterlace_on else None
        self.player.video_set_deinterlace(mode.encode() if mode else None)
        return f"Deinterlace: {'On (yadif)' if self._deinterlace_on else 'Off'}"

    def cycle_deinterlace_modes(self):
        """Cycle through different deinterlace modes."""
        modes = ["discard", "blend", "mean", "bob", "linear", "x", "yadif", "yadif2x", "phosphor", "ivtc"]
        if not hasattr(self, '_deinterlace_idx'): self._deinterlace_idx = -1
        
        self._deinterlace_idx = (self._deinterlace_idx + 1) % len(modes)
        mode = modes[self._deinterlace_idx]
        self._deinterlace_on = True
        self.player.video_set_deinterlace(mode.encode())
        return f"Deinterlace: {mode}"

    def toggle_wallpaper(self):
        """
        Toggle wallpaper mode.
        Note: This is highly dependent on VOUT (DirectX/Direct3D).
        """
        if not hasattr(self, '_wallpaper_on'): self._wallpaper_on = False
        self._wallpaper_on = not self._wallpaper_on
        
        # In LibVLC, this often requires setting an option at media player creation.
        # However, we can try to toggle the 'video-wallpaper' variable if exposed.
        # Most python-vlc bindings don't expose vlc_variable_set directly on the player easily.
        # We can try to use libvlc_video_set_callbacks or Win32 reparenting if we really wanted it.
        # For now, we'll return a message as a placeholder if it's not directly supported.
        return f"Wallpaper Mode: {'Enabled' if self._wallpaper_on else 'Disabled'} (DirectX only)"


    def toggle_autoscale(self):
        """Toggle video autoscale (Stretch vs Original)."""
        current = self.player.video_get_scale()
        # If scale is 0, it means autoscale is on. If not 0, it's fixed.
        # But VLC toggle 'O' usually toggles between 'Scale to fit' and 'Original Size' (no-scale).
        if current == 1.0:
            self.player.video_set_scale(0) # 0 = Autoscale/Fit
            return "Fit to Window"
        else:
            self.player.video_set_scale(1.0) # 1.0 = Original size
            return "Original Size"

    def get_scale(self):
        """Get video scale factor."""
        s = self.player.video_get_scale()
        return s if s > 0 else 1.0

    def set_scale(self, scale: float):
        """Set video scale factor."""
        # VLC limit check
        scale = max(0.1, min(10.0, scale))
        self.player.video_set_scale(scale)

    def change_viewpoint_fov(self, delta: float):
        """
        Adjust Field of View (FOV) for 360 degree video.
        delta: positive to expand (zoom out), negative to shrink (zoom in).
        """
        # Current viewpoint (yaw, pitch, roll, fov)
        # FOV is in degrees. VLC default is usually 80.
        if not hasattr(self, '_fov'): self._fov = 80.0
        
        self._fov = max(10, min(150, self._fov + delta))
        self.player.video_set_viewpoint(0, 0, 0, self._fov, False)
        return f"FOV: {int(self._fov)}°"

        return scale

    def increase_scale(self):
        """Increase scale factor by 0.1."""
        curr = self.get_scale()
        return self.set_scale(round(curr + 0.1, 1))

    def decrease_scale(self):
        """Decrease scale factor by 0.1."""
        curr = self.get_scale()
        return self.set_scale(round(curr - 0.1, 1))


    def set_spu_scale(self, scale: float):
        """Set subtitle scale factor."""
        self._spu_scale = max(0.1, min(5.0, scale))
        # Note: True font scaling in LibVLC requires setting 'sub-text-scale'
        # which is usually an instance-level option. For now, we track the state.
        return self._spu_scale

    def get_spu_scale(self):
        return getattr(self, '_spu_scale', 1.0)


    def cycle_program(self, reverse=False):
        """Cycle through programs (Service IDs) for TS/DVB streams."""
        # LibVLC doesn't provide a list usually. We increment/decrement.
        curr = self.player.program_get()
        if reverse:
            new_p = curr - 1 if curr > 0 else 0
        else:
            new_p = curr + 1
        self.player.program_set(new_p)
        return self.player.program_get()



    def next_frame(self):
        """Advance video by one frame."""
        self.player.next_frame()

    def toggle_record(self):
        """
        Toggle recording. 
        Note: True recording requires setting --sout on media load. 
        For now we will implement this as 'Take Snapshot'.
        """
        # Save to Pictures/Omneva
        from PySide6.QtCore import QStandardPaths, QDateTime
        
        pic_dir = QStandardPaths.writableLocation(QStandardPaths.PicturesLocation)
        save_dir = os.path.join(pic_dir, "Omneva")
        os.makedirs(save_dir, exist_ok=True)
        
        timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd_HH-mm-ss")
        filename = f"snapshot_{timestamp}.png"
        path = os.path.join(save_dir, filename)
        
        self.take_snapshot(path, 0, 0)
        return path

    def get_video_size(self) -> tuple[int, int]:
        """Get current video dimensions (width, height)."""
        try:
            # Get video track dimensions
            tracks = self.get_video_tracks()
            if tracks:
                # Try to get dimensions from current media
                if hasattr(self, 'media') and self.media:
                    # Get media info
                    media_info = self.media.get_parsed()
                    if media_info:
                        # Extract video dimensions from media info
                        for track in media_info.get_tracks():
                            if track.get_type() == vlc.TrackType.Video:
                                return (track.get_width(), track.get_height())
                
                # Fallback: try VLC player dimensions
                width = self.player.video_get_width()
                height = self.player.video_get_height()
                if width > 0 and height > 0:
                    return (width, height)
                    
        except Exception:
            pass
            
        # Default fallback
        return (0, 0)

    def take_snapshot(self, path: str, width: int = 0, height: int = 0):
        """Take a snapshot of the current video."""
        self.player.video_take_snapshot(0, path, width, height)

    # ─── Video Effects (Adjust) ─────────────────────────────

    def enable_video_adjust(self, enable: bool):
        """Enable or disable video adjust filters (Contrast, Brightness, etc.)."""
        self.player.video_set_adjust_float(vlc.VideoAdjustOption.Enable, 1.0 if enable else 0.0)

    def set_brightness(self, brightness: float):
        """Set video brightness (0.0 to 2.0, 1.0 is default)."""
        brightness = max(0.0, min(2.0, brightness))
        self.player.video_set_adjust_float(vlc.VideoAdjustOption.Brightness, brightness)

    def get_brightness(self) -> float:
        """Get current video brightness."""
        return self.player.video_get_adjust_float(vlc.VideoAdjustOption.Brightness)

    def set_contrast(self, contrast: float):
        """Set video contrast (0.0 to 2.0, 1.0 is default)."""
        contrast = max(0.0, min(2.0, contrast))
        self.player.video_set_adjust_float(vlc.VideoAdjustOption.Contrast, contrast)

    def get_contrast(self) -> float:
        """Get current video contrast."""
        return self.player.video_get_adjust_float(vlc.VideoAdjustOption.Contrast)

    def set_saturation(self, saturation: float):
        """Set video saturation (0.0 to 3.0, 1.0 is default)."""
        saturation = max(0.0, min(3.0, saturation))
        self.player.video_set_adjust_float(vlc.VideoAdjustOption.Saturation, saturation)

    def get_saturation(self) -> float:
        """Get current video saturation."""
        return self.player.video_get_adjust_float(vlc.VideoAdjustOption.Saturation)

    def set_hue(self, hue: float):
        """Set video hue (-180 to 180, 0 is default)."""
        hue = max(-180.0, min(180.0, hue))
        self.player.video_set_adjust_float(vlc.VideoAdjustOption.Hue, hue)

    def get_hue(self) -> float:
        """Get current video hue."""
        return self.player.video_get_adjust_float(vlc.VideoAdjustOption.Hue)

    def set_gamma(self, gamma: float):
        """Set video gamma (0.01 to 10.0, 1.0 is default)."""
        gamma = max(0.01, min(10.0, gamma))
        self.player.video_set_adjust_float(vlc.VideoAdjustOption.Gamma, gamma)

    def get_gamma(self) -> float:
        """Get current video gamma."""
        return self.player.video_get_adjust_float(vlc.VideoAdjustOption.Gamma)

    def reset_video_adjustments(self):
        """Reset all video adjustments to defaults."""
        self.set_brightness(1.0)
        self.set_contrast(1.0)
        self.set_saturation(1.0)
        self.set_hue(0.0)
        self.set_gamma(1.0)

    def set_adjust_float(self, option_id, value: float):
        """Set float adjust option (Contrast, Brightness, Saturation, Gamma)."""
        # option_id from vlc.VideoAdjustOption
        self.player.video_set_adjust_float(option_id, value)

    def set_adjust_int(self, option_id, value: int):
        """Set integer adjust option."""
        self.player.video_set_adjust_int(option_id, value)

    # ─── Synchronization ───

    def set_subtitle_delay(self, delay_ms):
        """Set subtitle delay in milliseconds."""
        # LibVLC uses microseconds for SPU delay
        self.player.video_set_spu_delay(delay_ms * 1000)
        self._spu_delay = delay_ms
        return delay_ms

    def get_subtitle_delay(self):
        """Get subtitle delay in milliseconds."""
        return self._spu_delay

    def bookmark_audio_sync(self):
        """Bookmark current playback time for audio sync."""
        self._audio_sync_bookmark = self.player.get_time()
        return self._audio_sync_bookmark

    def bookmark_subtitle_sync(self):
        """Bookmark current playback time for subtitle sync."""
        self._spu_sync_bookmark = self.player.get_time()
        return self._spu_sync_bookmark

    def synchronize_audio_subtitle(self):
        """Synchronize audio and subtitle based on bookmarks."""
        if self._audio_sync_bookmark is not None and self._spu_sync_bookmark is not None:
            # Shift = Subtitle_Time - Audio_Time
            diff = self._spu_sync_bookmark - self._audio_sync_bookmark
            self.set_subtitle_delay(diff)
            return diff
        return None

    def reset_sync(self):
        """Reset all synchronization delays."""
        self.set_audio_delay(0)
        self.set_subtitle_delay(0)
        self._audio_sync_bookmark = None
        self._spu_sync_bookmark = None
        return 0

        """Set int adjust option (Hue)."""
        self.player.video_set_adjust_int(option_id, value)

    # ─── Audio Equalizer ────────────────────────────────────

    def setup_equalizer(self):
        """Initialize equalizer."""
        # We need to create an equalizer object and assign it to the player
        if not hasattr(self, 'equalizer'):
            self.equalizer = vlc.AudioEqualizer()
            self.player.set_equalizer(self.equalizer)

    def set_equalizer_enabled(self, enabled: bool):
        """Enable or disable equalizer."""
        if enabled:
            if not hasattr(self, 'equalizer'):
                self.setup_equalizer()
        else:
            # Create a flat equalizer (disabled)
            flat_eq = vlc.AudioEqualizer()
            self.player.set_equalizer(flat_eq)

    def set_equalizer_band(self, band_index: int, amp: float):
        """Set amplification for a specific band (index 0-9). amp: -20.0 to 20.0"""
        if not hasattr(self, 'equalizer'):
            self.setup_equalizer()
        amp = max(-20.0, min(20.0, amp))
        self.equalizer.set_amp_at_index(amp, band_index)
        self.player.set_equalizer(self.equalizer)

    def get_equalizer_band(self, band_index: int) -> float:
        """Get amplification for a specific band."""
        if not hasattr(self, 'equalizer'):
            return 0.0
        return self.equalizer.get_amp_at_index(band_index)

    def set_equalizer_preamp(self, preamp: float):
        """Set global preamp. preamp: -20.0 to 20.0"""
        if not hasattr(self, 'equalizer'):
            self.setup_equalizer()
        preamp = max(-20.0, min(20.0, preamp))
        self.equalizer.set_preamp(preamp)
        self.player.set_equalizer(self.equalizer)

    def get_equalizer_preamp(self) -> float:
        """Get current preamp value."""
        if not hasattr(self, 'equalizer'):
            return 0.0
        return self.equalizer.get_preamp()

    def get_equalizer_frequencies(self) -> list[float]:
        """Get frequency values for each band (Hz)."""
        # Standard 10-band equalizer frequencies
        return [60, 170, 310, 600, 1000, 3000, 6000, 12000, 14000, 16000]

    def get_equalizer_presets(self) -> list[str]:
        """Get list of preset names."""
        if not hasattr(vlc, 'libvlc_audio_equalizer_get_preset_count'):
            return []
        count = vlc.libvlc_audio_equalizer_get_preset_count()
        presets = []
        for i in range(count):
            name = vlc.libvlc_audio_equalizer_get_preset_name(i)
            presets.append(name.decode() if isinstance(name, bytes) else name)
        return presets

    def set_equalizer_preset(self, preset_index: int):
        """Apply a preset by index."""
        self.equalizer = vlc.AudioEqualizer.new_from_preset(preset_index)
        self.player.set_equalizer(self.equalizer)

    def reset_equalizer(self):
        """Reset equalizer to flat settings."""
        self.set_equalizer_preamp(0.0)
        for i in range(10):
            self.set_equalizer_band(i, 0.0)

    # ─── Audio Filters ─────────────────────────────────────

    def enable_audio_filter(self, filter_name: str, enabled: bool):
        """Enable or disable an audio filter."""
        # Common VLC audio filters: "compressor", "spatializer", "equalizer", "normvol"
        if enabled:
            self.player.add_filter(filter_name)
        else:
            # VLC MediaPlayer doesn't have remove_filter method
            # We need to get current filters and rebuild without this one
            pass  # For now, just don't add the filter

    def set_compressor(self, enabled: bool, **kwargs):
        """Configure compressor."""
        self.enable_audio_filter("compressor", enabled)
        if enabled and hasattr(self, 'equalizer'):
            # VLC compressor uses equalizer API internally
            # Additional parameters can be set via media options if needed
            pass

    def set_spatializer(self, enabled: bool, **kwargs):
        """Configure spatializer."""
        self.enable_audio_filter("spatializer", enabled)

    def set_stereo_widener(self, enabled: bool, **kwargs):
        """Configure stereo widener."""
        self.enable_audio_filter("stereo_widener", enabled)

    def set_normalizer(self, enabled: bool, **kwargs):
        """Enable volume normalizer."""
        self.enable_audio_filter("normvol", enabled)

    def set_pitch_shift(self, enabled: bool, pitch_factor: float = 1.0):
        """Enable pitch shifting (requires scaletempo)."""
        if enabled:
            # This is more complex and requires media options
            # For now, we'll use rate adjustment as approximation
            self.set_rate(pitch_factor)
        else:
            self.set_rate(1.0)

    # ─── Renderer Discovery (Casting) ───────────────────────

    def start_renderer_discovery(self):
        """Start discovering renderers (Chromecast, UPnP etc)."""
        # Discoverers available: 'mdns', 'upnp'
        for name in ['mdns', 'upnp']:
            d = self.instance.renderer_discoverer_new(name)
            if d:
                em = d.event_manager()
                em.event_attach(vlc.EventType.RendererDiscovererItemAdded, self._on_renderer_added)
                em.event_attach(vlc.EventType.RendererDiscovererItemDeleted, self._on_renderer_deleted)
                d.start()
                self._discoverers.append(d)

    def stop_renderer_discovery(self):
        """Stop all discoverers."""
        for d in self._discoverers:
            d.stop()
        self._discoverers.clear()
        self._renderers.clear()

    @vlc.callbackmethod
    def _on_renderer_added(self, event, data):
        item = event.u.renderer_discoverer_item_added.item
        name = item.name().decode() if isinstance(item.name(), bytes) else item.name()
        self._renderers[name] = item
        self.renderer_item_added.emit(name)

    @vlc.callbackmethod
    def _on_renderer_deleted(self, event, data):
        item = event.u.renderer_discoverer_item_deleted.item
        name = item.name().decode() if isinstance(item.name(), bytes) else item.name()
        if name in self._renderers:
            del self._renderers[name]
        self.renderer_item_deleted.emit(name)

    def set_renderer(self, name: str | None):
        """Set the output renderer (cast to device). None to play locally."""
        if name and name in self._renderers:
            self.player.set_renderer(self._renderers[name])
        else:
            # Passing None to set_renderer resets to local display
            self.player.set_renderer(None)

    # ─── Extended Video Effects ─────────────────────────────

    def set_rotate(self, angle: int):
        """Set video rotation (0, 90, 180, 270)."""
        # VLC rotate filter: --video-filter=transform {--transform-type=90}
        # In LibVLC, we can try to set the transform-type variable
        # But for simple display rotation, we often use the vout-filter
        # A more robust way in libVLC is using self.player.video_set_transform
        if hasattr(self.player, 'video_set_transform'):
             # vlc.VideoTransform.Rotate90 etc
             mapping = {
                 0: vlc.VideoTransform.Identity,
                 90: vlc.VideoTransform.Rotate90,
                 180: vlc.VideoTransform.Rotate180,
                 270: vlc.VideoTransform.Rotate270,
                 -1: vlc.VideoTransform.Hflip,
                 -2: vlc.VideoTransform.Vflip
             }
             self.player.video_set_transform(mapping.get(angle, vlc.VideoTransform.Identity))
             return angle
        return 0

    def set_mirror(self, horizontal=True, vertical=False):
        """Flip video."""
        if horizontal:
            self.set_rotate(-1)
        elif vertical:
            self.set_rotate(-2)
        else:
            self.set_rotate(0)


    def set_equalizer_preset(self, index: int):
        """Apply a preset by index."""
        # Create new equalizer from preset
        self.equalizer = vlc.AudioEqualizer.new_from_preset(index)
        self.player.set_equalizer(self.equalizer)


    def set_rate(self, rate: float):
        """Set playback rate (1.0 is normal)."""
        self.player.set_rate(rate)

    def get_rate(self) -> float:
        """Get current playback rate."""
        return self.player.get_rate()

    def get_length(self):
        """Get total duration in ms."""
        return self.player.get_length()

    def get_meta(self, meta_type):
        """Get metadata from current media."""
        m = getattr(self, 'media', None)
        if not m:
            m = self.player.get_media()
        
        if m:
            # Check parsed status
            try:
                status = m.get_parsed_status()
                # Status: skipped, failed, timeout, done
                # If not done, try to parse
                if str(status) != 'done':
                    # Use local | network to be safe
                    m.parse_with_options(vlc.MediaParseFlag.local | vlc.MediaParseFlag.network, 0)
            except:
                pass
            return m.get_meta(meta_type)
        return None

    def get_tracks_info(self):
        """Get track info (Codec, Language, etc.) using safe manual ctypes."""
        # Using manual ctypes to avoid python-vlc wrapper crashes on Windows with some versions.
        m = getattr(self, 'media', None)
        if not m:
            m = self.player.get_media()
            
        if not m:
            return []

        try:
            import ctypes
            
            # 1. Get libvlc instance
            # Try to find existing loaded library
            libvlc = None
            if hasattr(vlc, 'libvlc'):
                libvlc = vlc.libvlc
            else:
                try:
                    libvlc = ctypes.CDLL("libvlc.dll")
                except:
                    try:
                        libvlc = ctypes.CDLL("libvlc")
                    except:
                        pass
            
            if not libvlc or not hasattr(libvlc, 'libvlc_media_tracks_get'):
                # Fallback to python-vlc if we can't load DLL (unlikely)
                return []

            # 2. Define Structures
            class VideoTrack(ctypes.Structure):
                _fields_ = [
                    ("i_height", ctypes.c_uint), # NOTE: Height is first in libvlc_video_track_t!
                    ("i_width", ctypes.c_uint),
                    ("i_sar_num", ctypes.c_uint),
                    ("i_sar_den", ctypes.c_uint),
                    ("i_frame_rate_num", ctypes.c_uint),
                    ("i_frame_rate_den", ctypes.c_uint),
                    ("i_orientation", ctypes.c_int),
                    ("i_projection", ctypes.c_int),
                ]

            class AudioTrack(ctypes.Structure):
                _fields_ = [
                    ("i_channels", ctypes.c_uint),
                    ("i_rate", ctypes.c_uint),
                ]

            class SubtitleTrack(ctypes.Structure):
                _fields_ = [
                    ("psz_encoding", ctypes.c_char_p),
                ]

            class MediaTrack(ctypes.Structure):
                _fields_ = [
                    ("i_codec", ctypes.c_uint32),
                    ("i_original_fourcc", ctypes.c_uint32),
                    ("i_id", ctypes.c_int),
                    ("i_type", ctypes.c_int), # -1:Unknown, 0:Audio, 1:Video, 2:Text
                    ("i_profile", ctypes.c_int),
                    ("i_level", ctypes.c_int),
                    ("u", ctypes.c_void_p), # Union pointer
                    ("i_bitrate", ctypes.c_uint),
                    ("psz_language", ctypes.c_char_p),
                    ("psz_description", ctypes.c_char_p),
                ]
            
            # 3. Setup arguments
            get_tracks_func = libvlc.libvlc_media_tracks_get
            get_tracks_func.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.POINTER(ctypes.POINTER(MediaTrack)))]
            get_tracks_func.restype = ctypes.c_uint

            tracks_pp = ctypes.POINTER(ctypes.POINTER(MediaTrack))()
            
            # 4. Call function
            # Access internal pointer: usually _as_parameter_ for vlc.Media
            m_ptr = None
            if hasattr(m, '_as_parameter_'):
                m_ptr = m._as_parameter_
            else:
                m_ptr = m
                
            count = get_tracks_func(m_ptr, ctypes.byref(tracks_pp))
            
            result = []
            if count > 0 and tracks_pp:
                for i in range(count):
                    ptr = tracks_pp[i]
                    if not ptr: continue
                    track = ptr.contents
                    
                    # Safe Decode Codec
                    codec_str = ""
                    try:
                        codec_bytes = track.i_codec.to_bytes(4, byteorder='little')
                        codec_str = codec_bytes.decode('ascii', errors='ignore').replace('\x00', '')
                    except:
                        codec_str = str(track.i_codec)

                    # Safe Decode Original FourCC
                    orig_codec_str = None
                    if track.i_original_fourcc > 0:
                        try:
                            orig_bytes = track.i_original_fourcc.to_bytes(4, byteorder='little')
                            orig_codec_str = orig_bytes.decode('ascii', errors='ignore').replace('\x00', '')
                        except: pass

                    # Safe Decode Strings
                    lang_str = None
                    if track.psz_language:
                        try: lang_str = track.psz_language.decode('utf-8', errors='ignore')
                        except: pass
                        
                    desc_str = None
                    if track.psz_description:
                        try: desc_str = track.psz_description.decode('utf-8', errors='ignore')
                        except: pass

                    # Basic Data
                    t_data = {
                        'id': track.i_id,
                        'type': track.i_type, # -1:Unknown, 0:Audio, 1:Video, 2:Text
                        'codec': codec_str,
                        'original_codec': orig_codec_str,
                        'profile': track.i_profile,
                        'level': track.i_level,
                        'bitrate': track.i_bitrate,
                        'language': lang_str, 
                        'description': desc_str,
                        'video': None,
                        'audio': None,
                        'subtitle': None
                    }
                    
                    # Detailed Extraction via Union Cast
                    if track.u:
                        if track.i_type == 1: # Video
                            try:
                                v = ctypes.cast(track.u, ctypes.POINTER(VideoTrack)).contents
                                t_data['video'] = {
                                    'width': v.i_width,
                                    'height': v.i_height,
                                    'frame_rate_num': v.i_frame_rate_num,
                                    'frame_rate_den': v.i_frame_rate_den,
                                    'sar_num': v.i_sar_num,
                                    'sar_den': v.i_sar_den,
                                    'orientation': v.i_orientation, # 0=Top-Left
                                    'projection': v.i_projection,
                                }
                            except: pass
                            
                        elif track.i_type == 0: # Audio
                            try:
                                a = ctypes.cast(track.u, ctypes.POINTER(AudioTrack)).contents
                                t_data['audio'] = {
                                    'channels': a.i_channels,
                                    'rate': a.i_rate
                                }
                            except: pass

                        elif track.i_type == 2: # Subtitle
                            try:
                                s = ctypes.cast(track.u, ctypes.POINTER(SubtitleTrack)).contents
                                enc = ""
                                if s.psz_encoding:
                                    enc = s.psz_encoding.decode('utf-8', errors='ignore')
                                t_data['subtitle'] = {
                                    'encoding': enc
                                }
                            except: pass

                    result.append(t_data)

                # 5. Free memory
                release_func = libvlc.libvlc_media_tracks_release
                release_func.argtypes = [ctypes.POINTER(ctypes.POINTER(MediaTrack)), ctypes.c_uint]
                release_func(tracks_pp, count)

            return result

        except Exception as e:
            # print(f"Error in manual tracks info: {e}")
            return []

    def get_stats(self):
        """Get runtime statistics."""
        m = getattr(self, 'media', None)
        if not m:
            m = self.player.get_media()
            
        if m:
            stats = vlc.MediaStats()
            if m.get_stats(stats):
                return stats
        return None

    # ─── State ──────────────────────────────────────────────

    def is_playing(self) -> bool:
        return self.player.is_playing() == 1

    def get_state_str(self) -> str:
        state = self.player.get_state()
        state_map = {
            vlc.State.NothingSpecial: "stopped",
            vlc.State.Opening: "loading",
            vlc.State.Buffering: "buffering",
            vlc.State.Playing: "playing",
            vlc.State.Paused: "paused",
            vlc.State.Stopped: "stopped",
            vlc.State.Ended: "ended",
            vlc.State.Error: "error",
        }
        return state_map.get(state, "unknown")

    # ─── Subtitle ───────────────────────────────────────────

    def set_subtitle_file(self, sub_path: str):
        """Load an external subtitle file."""
        if os.path.isfile(sub_path):
            self.player.video_set_subtitle_file(sub_path)
            return True
        return False

    def add_subtitle_file(self, sub_path: str):
        """Add external subtitle file to current media."""
        # This requires media options, more complex than set_subtitle_file
        if hasattr(self, 'media') and os.path.isfile(sub_path):
            self.media.add_option(f":sub-file={sub_path}")
            # Reload media to apply subtitle
            current_pos = self.get_position()
            self.player.set_media(self.media)
            if current_pos > 0:
                self.seek(current_pos)
            return True
        return False

    def get_supported_subtitle_formats(self) -> list[str]:
        """Get list of supported subtitle formats."""
        return [
            "srt", "ass", "ssa", "vtt", "sub", "idx", "webvtt", 
            "sbv", "dfxp", "ttml", "lrc", "smi", "smil"
        ]

    def is_subtitle_file(self, file_path: str) -> bool:
        """Check if file is a subtitle file based on extension."""
        ext = os.path.splitext(file_path)[1].lower().lstrip('.')
        return ext in self.get_supported_subtitle_formats()

    def set_subtitle_encoding(self, encoding: str):
        """Set subtitle file encoding."""
        if hasattr(self, 'media'):
            self.media.add_option(f":subsdec={encoding}")
            # Reload media to apply encoding
            current_pos = self.get_position()
            self.player.set_media(self.media)
            if current_pos > 0:
                self.seek(current_pos)

    def set_subtitle_position(self, position: int):
        """Set subtitle position (0-100, from top to bottom)."""
        if hasattr(self, 'media'):
            pos = max(0, min(100, position))
            self.media.add_option(f":sub-pos={pos}")
            # Reload media to apply position
            current_pos = self.get_position()
            self.player.set_media(self.media)
            if current_pos > 0:
                self.seek(current_pos)

    def set_subtitle_size(self, size: int):
        """Set subtitle font size (0-100)."""
        if hasattr(self, 'media'):
            sz = max(0, min(100, size))
            self.media.add_option(f":sub-size={sz}")
            # Reload media to apply size
            current_pos = self.get_position()
            self.player.set_media(self.media)
            if current_pos > 0:
                self.seek(current_pos)

    def set_subtitle_color(self, color_hex: str):
        """Set subtitle color (hex format like '#FFFFFF')."""
        if hasattr(self, 'media') and color_hex.startswith('#'):
            self.media.add_option(f":sub-color={color_hex[1:]}")
            # Reload media to apply color
            current_pos = self.get_position()
            self.player.set_media(self.media)
            if current_pos > 0:
                self.seek(current_pos)

    def set_subtitle_bold(self, bold: bool):
        """Enable or disable bold subtitles."""
        if hasattr(self, 'media'):
            self.media.add_option(f":sub-bold={'1' if bold else '0'}")
            # Reload media to apply bold
            current_pos = self.get_position()
            self.player.set_media(self.media)
            if current_pos > 0:
                self.seek(current_pos)

    def get_subtitle_tracks(self) -> dict:
        """Get list of available subtitle tracks as {id: name}."""
        # video_get_spu_description returns list of (id, name)
        desc = self.player.video_get_spu_description()
        if not desc:
            return {}
        return {d[0]: (d[1].decode() if isinstance(d[1], bytes) else d[1]) for d in desc}

    def set_subtitle_track(self, track_id: int):
        """Set subtitle track by ID."""
        self.player.video_set_spu(track_id)

    def disable_subtitles(self):
        """Disable all subtitles."""
        self.player.video_set_spu(-1)

    def get_current_subtitle_track(self) -> int:
        """Get current subtitle track ID."""
        return self.player.video_get_spu()

    # ─── Audio Tracks ───────────────────────────────────────

    def get_audio_tracks(self) -> dict:
        """Get list of available audio tracks as {id: name}."""
        # audio_get_track_description returns list of (id, name)
        desc = self.player.audio_get_track_description()
        if not desc:
            return {}
        return {d[0]: (d[1].decode() if isinstance(d[1], bytes) else d[1]) for d in desc}

    def set_audio_track(self, track_id: int):
        self.player.audio_set_track(track_id)

    def set_audio_delay(self, delay_ms: int):
        """Set audio delay in milliseconds."""
        self.player.audio_set_delay(delay_ms * 1000) # VLC takes microseconds

    def get_audio_delay(self) -> int:
        """Get audio delay in milliseconds."""
        return self.player.audio_get_delay() // 1000

    # ─── Video Effects (Extended) ───────────────────────────

    def set_crop(self, top=0, left=0, bottom=0, right=0):
        """Set video crop borders (pixels)."""
        # video_set_crop_border is not always exposed in binding, checking...
        # If not, we might use string geometry '100x100+10+10' via video_set_crop_geometry
        # But let's try direct border if available, else geometry is harder to calc from borders without knowing src size.
        # Actually standard VLC crop is geometry.
        # Let's try to find an API or valid geometry string. 
        # For now, stub or basic geometry string if we knew size. 
        # Wait, libvlc_video_set_crop_geometry takes a string like "100x100+0+0".
        # This crop UI is "pixels from border". That's distinct.
        # There isn't a direct "crop border" API in standard python-vlc.
        # We will stub this for now or print log.
        pass

    # vlc.VideoLogoOption enums (Hardcoded to avoid AttributeError if vlc module binding varies)
    _LOGO_ENABLE = 0
    _LOGO_FILE = 1
    _LOGO_X = 2
    _LOGO_Y = 3
    _LOGO_DELAY = 4
    _LOGO_REPEAT = 5
    _LOGO_OPACITY = 6
    _LOGO_POSITION = 7

    # vlc.VideoMarqueeOption enums
    _MARQ_ENABLE = 0
    _MARQ_TEXT = 1
    _MARQ_COLOR = 2
    _MARQ_OPACITY = 3
    _MARQ_POSITION = 4
    _MARQ_REFRESH = 5
    _MARQ_SIZE = 6
    _MARQ_TIMEOUT = 7
    _MARQ_X = 8
    _MARQ_Y = 9

    def set_logo(self, file_path, opacity=255, x=0, y=0):
        """Set OSD Logo."""
        if not file_path:
            self.player.video_set_logo_int(self._LOGO_ENABLE, 0)
        else:
            self.player.video_set_logo_string(self._LOGO_FILE, file_path)
            self.player.video_set_logo_int(self._LOGO_OPACITY, opacity)
            self.player.video_set_logo_int(self._LOGO_X, x)
            self.player.video_set_logo_int(self._LOGO_Y, y)
            self.player.video_set_logo_int(self._LOGO_ENABLE, 1)

    def set_marquee(self, text, position=0, size=24, color=0xFFFFFF):
        """Set OSD Text (Marquee)."""
        if not text:
            self.player.video_set_marquee_int(self._MARQ_ENABLE, 0)
        else:
            self.player.video_set_marquee_string(self._MARQ_TEXT, text)
            self.player.video_set_marquee_int(self._MARQ_POSITION, position) # 0=Center, 1=Left, 2=Right, 4=Top, 8=Bottom
            self.player.video_set_marquee_int(self._MARQ_SIZE, size)
            self.player.video_set_marquee_int(self._MARQ_COLOR, color)
            self.player.video_set_marquee_int(self._MARQ_ENABLE, 1)

    def set_subtitle_fps(self, fps):
        """Set subtitle FPS (Stub - LibVLC limitation)."""
        # LibVLC does not support changing this at runtime easily.
        pass

    def set_subtitle_duration_factor(self, factor):
        """Set subtitle duration factor (Stub - LibVLC limitation)."""
        pass

    # Stubs for Filters (Runtime filter adding is complex with basic wrapping)
    def set_filter_sharpen(self, enabled: bool, sigma: float): pass
    def set_filter_sepia(self, enabled: bool, intensity: int): pass
    def set_filter_rotate(self, enabled: bool, angle: float): pass
    def set_filter_wall(self, enabled: bool, rows: int, cols: int): pass
    
    # Advanced Video Stubs
    def set_filter_antiflicker(self, enabled: bool, soften: float): pass
    def set_filter_motionblur(self, enabled: bool, factor: int): pass
    def set_filter_spatialblur(self, enabled: bool, sigma: float): pass
    def set_filter_clone(self, enabled: bool, count: int): pass
    def set_filter_denoiser(self, enabled: bool, spat_luma: float, temp_luma: float, spat_chroma: float, temp_chroma: float): pass
    def set_filter_anaglyph(self, enabled: bool): pass
    def set_filter_mirror(self, enabled: bool): pass
    def set_filter_psychedelic(self, enabled: bool): pass
    def set_filter_waves(self, enabled: bool): pass
    def set_filter_water(self, enabled: bool): pass
    def set_filter_motiondetect(self, enabled: bool): pass

    # ─── Audio Filters (Stubs/Best Effort) ──────────────────

    def set_pitch(self, pitch: float):
        """Set pitch shift (scale). wrapper for set_rate for now."""
        # Genuine pitch shifting without speed change requires scaletempo or pitch filter
        # For now, we map to rate
        self.set_rate(pitch)


    # ─── Polling ────────────────────────────────────────────

    def _poll_state(self):
        """Periodically called to emit position/state signals."""
        state = self.player.get_state()

        # Update duration if not yet known
        length = self.player.get_length()
        if length > 0:
            self._duration = length / 1000.0
            self.duration_changed.emit(self._duration)

        # Emit position
        pos = self.get_position()
        self.position_changed.emit(pos)

        # Emit state if changed
        state_str = "stopped"
        if state == vlc.State.Playing: state_str = "playing"
        elif state == vlc.State.Paused: state_str = "paused"
        elif state == vlc.State.Stopped: state_str = "stopped"
        elif state == vlc.State.Ended: state_str = "ended"
        elif state == vlc.State.Error: state_str = "error"

        if state_str != self._last_state:
            self._last_state = state_str
            self.state_changed.emit(state_str)

        # Check for ended
        if state == vlc.State.Ended:
            if self._loop_mode == 1: # Loop One
                self.restart()
            elif self._loop_mode == 2: # Loop All
                # For now, treat Loop All same as Loop One if no playlist manager
                self.restart()
            else:
                self._poll_timer.stop()
        elif state == vlc.State.Error:
            self._poll_timer.stop()

    def restart(self):
        """Restart current media from the beginning."""
        if self._current_file:
            self.player.set_time(0)
            self.player.play()
            self._poll_timer.start()
            return True
        return False

    def cycle_loop_mode(self):
        """Cycle through loop modes: Off -> One -> All -> Off."""
        self._loop_mode = (self._loop_mode + 1) % 3
        modes = ["Off", "One", "All"]
        return modes[self._loop_mode]

    # ─── Media Options ───────────────────────────────────────

    def set_track_selection(self, audio_track: int = None, video_track: int = None, subtitle_track: int = None):
        """Select specific tracks for playback."""
        if hasattr(self, 'media'):
            if audio_track is not None:
                self.media.add_option(f":audio-track={audio_track}")
            if video_track is not None:
                self.media.add_option(f":video-track={video_track}")
            if subtitle_track is not None:
                self.media.add_option(f":sub-track={subtitle_track}")
            
            # Reload media to apply track selection
            current_pos = self.get_position()
            self.player.set_media(self.media)
            if current_pos > 0:
                self.seek(current_pos)

    def get_video_tracks(self) -> dict:
        """Get list of available video tracks as {id: name}."""
        desc = self.player.video_get_track_description()
        if not desc:
            return {}
        return {d[0]: (d[1].decode() if isinstance(d[1], bytes) else d[1]) for d in desc}

    def set_video_track(self, track_id: int):
        """Set video track by ID."""
        self.player.video_set_track(track_id)

    def set_caching_options(self, network_cache: int = 1000, disc_cache: int = 300, file_cache: int = 300):
        """Configure caching behavior for different media types."""
        if hasattr(self, 'media'):
            # Network caching (in ms)
            self.media.add_option(f":network-caching={network_cache}")
            # Disc caching (in ms) 
            self.media.add_option(f":disc-caching={disc_cache}")
            # File caching (in ms)
            self.media.add_option(f":file-caching={file_cache}")
            
            # Live streaming caching
            self.media.add_option(f":live-caching={network_cache}")
            
            # Reload media to apply caching
            current_pos = self.get_position()
            self.player.set_media(self.media)
            if current_pos > 0:
                self.seek(current_pos)

    def set_playback_options(self, start_time: float = None, stop_time: float = None, 
                           run_time: float = None, ab_loop_start: float = None, 
                           ab_loop_stop: float = None):
        """Set playback start/stop times and A-B loop."""
        if hasattr(self, 'media'):
            if start_time is not None:
                self.media.add_option(f":start-time={int(start_time)}")
            if stop_time is not None:
                self.media.add_option(f":stop-time={int(stop_time)}")
            if run_time is not None:
                self.media.add_option(f":run-time={int(run_time)}")
            if ab_loop_start is not None:
                self.media.add_option(f":ab-loop-start={int(ab_loop_start)}")
            if ab_loop_stop is not None:
                self.media.add_option(f":ab-loop-stop={int(ab_loop_stop)}")
            
            # Reload media to apply playback options
            current_pos = self.get_position()
            self.player.set_media(self.media)
            if current_pos > 0:
                self.seek(current_pos)

    def set_playback_speed(self, speed: float = 1.0):
        """Set default playback speed for media."""
        if hasattr(self, 'media'):
            self.media.add_option(f":rate={speed}")
            # Reload media to apply speed
            current_pos = self.get_position()
            self.player.set_media(self.media)
            if current_pos > 0:
                self.seek(current_pos)

    def set_audio_options(self, audio_delay: int = None, audio_channel: int = None):
        """Set audio-specific options."""
        if hasattr(self, 'media'):
            if audio_delay is not None:
                self.media.add_option(f":audio-desync={audio_delay}")
            if audio_channel is not None:
                self.media.add_option(f":audio-channel={audio_channel}")
            
            # Reload media to apply audio options
            current_pos = self.get_position()
            self.player.set_media(self.media)
            if current_pos > 0:
                self.seek(current_pos)

    def set_video_options(self, video_width: int = None, video_height: int = None, 
                         crop_geometry: str = None, aspect_ratio: str = None):
        """Set video-specific options."""
        if hasattr(self, 'media'):
            if video_width is not None and video_height is not None:
                self.media.add_option(f":width={video_width}")
                self.media.add_option(f":height={video_height}")
            if crop_geometry is not None:
                self.media.add_option(f":crop={crop_geometry}")
            if aspect_ratio is not None:
                self.media.add_option(f":aspect-ratio={aspect_ratio}")
            
            # Reload media to apply video options
            current_pos = self.get_position()
            self.player.set_media(self.media)
            if current_pos > 0:
                self.seek(current_pos)

    def set_subtitle_options(self, subtitle_delay: int = None, subtitle_fps: float = None,
                          subtitle_format: str = None, subtitle_encoding: str = None):
        """Set subtitle-specific options."""
        if hasattr(self, 'media'):
            if subtitle_delay is not None:
                self.media.add_option(f":sub-delay={subtitle_delay}")
            if subtitle_fps is not None:
                self.media.add_option(f":sub-fps={subtitle_fps}")
            if subtitle_format is not None:
                self.media.add_option(f":sub-type={subtitle_format}")
            if subtitle_encoding is not None:
                self.media.add_option(f":subsdec={subtitle_encoding}")
            
            # Reload media to apply subtitle options
            current_pos = self.get_position()
            self.player.set_media(self.media)
            if current_pos > 0:
                self.seek(current_pos)

    def set_network_options(self, http_user_agent: str = None, http_referrer: str = None,
                          http_proxy: str = None, timeout: int = None):
        """Set network streaming options."""
        if hasattr(self, 'media'):
            if http_user_agent is not None:
                self.media.add_option(f":http-user-agent={http_user_agent}")
            if http_referrer is not None:
                self.media.add_option(f":http-referrer={http_referrer}")
            if http_proxy is not None:
                self.media.add_option(f":http-proxy={http_proxy}")
            if timeout is not None:
                self.media.add_option(f":http-timeout={timeout}")
            
            # Reload media to apply network options
            current_pos = self.get_position()
            self.player.set_media(self.media)
            if current_pos > 0:
                self.seek(current_pos)

    def reset_media_options(self):
        """Reset all media options to defaults."""
        if hasattr(self, 'media'):
            # Clear existing options by creating new media object
            current_file = self._current_file
            if current_file:
                self.load(current_file)

    # ─── Cleanup ────────────────────────────────────────────

    def release(self):
        """Clean up VLC resources."""
        self._poll_timer.stop()
        self.player.stop()
        self.player.release()
        self.instance.release()
