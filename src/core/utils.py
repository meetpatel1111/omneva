"""Utility helpers — path detection, format checks, time formatting."""

import os
import sys
import shutil
import subprocess


# Supported media extensions
VIDEO_EXTENSIONS = {
    '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v',
    '.mpg', '.mpeg', '.ts', '.3gp', '.ogv', '.vob', '.m2ts', '.mts',
}

AUDIO_EXTENSIONS = {
    '.mp3', '.flac', '.wav', '.aac', '.ogg', '.wma', '.m4a', '.opus',
    '.aiff', '.ape', '.alac',
}

SUBTITLE_EXTENSIONS = {
    '.srt', '.ass', '.ssa', '.sub', '.vtt',
}

MEDIA_EXTENSIONS = VIDEO_EXTENSIONS | AUDIO_EXTENSIONS


def is_media_file(filepath: str) -> bool:
    """Check if file is a supported media file."""
    return os.path.splitext(filepath)[1].lower() in MEDIA_EXTENSIONS


def is_video_file(filepath: str) -> bool:
    return os.path.splitext(filepath)[1].lower() in VIDEO_EXTENSIONS


def is_audio_file(filepath: str) -> bool:
    return os.path.splitext(filepath)[1].lower() in AUDIO_EXTENSIONS


def format_duration(seconds: float) -> str:
    """Format seconds to HH:MM:SS or MM:SS."""
    if seconds <= 0:
        return "00:00"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_size(bytes_count: int) -> str:
    """Format bytes to human readable size."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_count < 1024:
            return f"{bytes_count:.1f} {unit}"
        bytes_count /= 1024
    return f"{bytes_count:.1f} PB"


def format_bitrate(bps: int) -> str:
    """Format bits per second to readable string."""
    if bps <= 0:
        return "N/A"
    kbps = bps / 1000
    if kbps >= 1000:
        return f"{kbps / 1000:.1f} Mbps"
    return f"{kbps:.0f} kbps"


from src.core.storage import storage

def get_local_deps_dir() -> str:
    """Get the local directory where dependencies might be downloaded."""
    appdata = os.getenv("APPDATA")
    if not appdata:
        appdata = os.path.expanduser("~")
    return os.path.join(appdata, "Omneva", "deps")


def find_ffmpeg() -> str | None:
    """Find ffmpeg binary (check local deps, then settings, then PATH)."""
    # 1. Check local downloaded deps
    deps_dir = get_local_deps_dir()
    if sys.platform == "win32":
        local_path = os.path.join(deps_dir, "ffmpeg", "ffmpeg-master-latest-win64-gpl", "bin", "ffmpeg.exe")
    elif sys.platform == "darwin":
        local_path = os.path.join(deps_dir, "ffmpeg", "ffmpeg") # evermeet zip extracts directly
    else:
        local_path = os.path.join(deps_dir, "ffmpeg", "ffmpeg-master-latest-linux64-gpl", "bin", "ffmpeg")
        
    if os.path.isfile(local_path):
        return local_path

    # 2. Check settings
    settings = storage.get_settings()
    path = settings.value("ffmpeg_path", "")
    if path and os.path.isfile(path):
        return path
        
    # 3. Check PATH
    return shutil.which("ffmpeg")


def find_ffprobe() -> str | None:
    """Find ffprobe binary (check local deps, then settings, then PATH)."""
    # 1. Check local downloaded deps
    deps_dir = get_local_deps_dir()
    if sys.platform == "win32":
        local_path = os.path.join(deps_dir, "ffmpeg", "ffmpeg-master-latest-win64-gpl", "bin", "ffprobe.exe")
    elif sys.platform == "darwin":
        local_path = os.path.join(deps_dir, "ffmpeg", "ffprobe")
    else:
        local_path = os.path.join(deps_dir, "ffmpeg", "ffmpeg-master-latest-linux64-gpl", "bin", "ffprobe")
        
    if os.path.isfile(local_path):
        return local_path

    # 2. Check settings
    settings = storage.get_settings()
    path = settings.value("ffprobe_path", "")
    if path and os.path.isfile(path):
        return path
        
    # 3. Check PATH
    return shutil.which("ffprobe")


def find_vlc_lib() -> str | None:
    """Find VLC installation path for libvlc."""
    if sys.platform == "win32":
        # Check local downloaded deps first
        local_path = os.path.join(get_local_deps_dir(), "vlc", "vlc-3.0.21")
        if os.path.isfile(os.path.join(local_path, "libvlc.dll")):
            return local_path

        # Common VLC install paths on Windows
        candidates = [
            os.path.join(os.environ.get("ProgramFiles", ""), "VideoLAN", "VLC"),
            os.path.join(os.environ.get("ProgramFiles(x86)", ""), "VideoLAN", "VLC"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "VideoLAN", "VLC"),
        ]
        for path in candidates:
            if os.path.isfile(os.path.join(path, "libvlc.dll")):
                return path
    elif sys.platform == "darwin":
        # Check local downloaded deps first (inside the app bundle)
        local_path = os.path.join(get_local_deps_dir(), "vlc", "VLC.app", "Contents", "MacOS", "lib")
        if os.path.isfile(os.path.join(local_path, "libvlc.dylib")):
            return local_path
            
        candidates = [
            "/Applications/VLC.app/Contents/MacOS/lib",
            "/usr/local/lib",
        ]
        for path in candidates:
            if os.path.isfile(os.path.join(path, "libvlc.dylib")):
                return path
    else:  # Linux
        # Usually available via system package
        candidates = ["/usr/lib", "/usr/lib64", "/usr/local/lib"]
        for path in candidates:
            if os.path.isfile(os.path.join(path, "libvlc.so")):
                return path

    return None



from PySide6.QtGui import QIcon

def get_icon(name: str) -> QIcon:
    """
    Get QIcon from src/assets.
    Handles dev mode and PyInstaller _MEIPASS.
    """
    # 1. Determine base path
    if hasattr(sys, '_MEIPASS'):
        base_dir = os.path.join(sys._MEIPASS, 'src', 'assets')
    else:
        # Dev mode: this file is src/core/utils.py
        # We want PROJECT_ROOT/src/assets
        # PROJECT_ROOT is ../../ from here
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets'))
    
    path = os.path.join(base_dir, name)
    if os.path.exists(path):
        return QIcon(path)
    
    return QIcon()
