"""Dependency downloader for Windows (VLC and FFmpeg)."""

import os
import sys
import zipfile
import tempfile
import urllib.request
from typing import Callable
from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool

# Official fallback URLs for Windows binaries and libraries.
VLC_WIN64_URL = "https://get.videolan.org/vlc/last/win64/vlc-3.0.21-win64.zip"
FFMPEG_WIN64_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"

# macOS URLs
VLC_MAC_URL = "https://get.videolan.org/vlc/last/macosx/vlc-3.0.21-universal.dmg"
FFMPEG_MAC_URL = "https://evermeet.cx/ffmpeg/getrelease/zip"
FFPROBE_MAC_URL = "https://evermeet.cx/ffmpeg/getrelease/ffprobe/zip"

# Linux URLs
FFMPEG_LINUX64_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz"

def get_deps_dir() -> str:
    """Get the local directory to store downloaded dependencies."""
    appdata = os.getenv("APPDATA")
    if not appdata:
        appdata = os.path.expanduser("~")
    path = os.path.join(appdata, "Omneva", "deps")
    os.makedirs(path, exist_ok=True)
    return path


class DownloadWorker(QRunnable):
    """Worker thread for downloading and extracting files."""
    
    class Signals(QObject):
        progress = Signal(str, int, int) # task_name, bytes_read, total_bytes
        status = Signal(str)           # current status message
        finished = Signal(bool, str)   # success, error_message

    def __init__(self, task_name: str, url: str, extract_dir: str, suffix: str = ".zip"):
        super().__init__()
        self.task_name = task_name
        self.url = url
        self.extract_dir = extract_dir
        self.suffix = suffix
        self.signals = self.Signals()

    def run(self):
        try:
            self.signals.status.emit(f"Downloading {self.task_name}...")
            
            # Create a temporary file
            fd, tmp_path = tempfile.mkstemp(suffix=self.suffix)
            os.close(fd)
            
            # Convert backslashes to forward slashes for urllib on Windows
            if sys.platform == "win32":
                tmp_path = tmp_path.replace("\\", "/")
            
            # Download with progress and custom user-agent
            req = urllib.request.Request(self.url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open(tmp_path, 'wb') as out_file:
                total_size = int(response.getheader('Content-Length', 0))
                block_size = 8192
                count = 0
                while True:
                    data = response.read(block_size)
                    if not data:
                        break
                    out_file.write(data)
                    count += 1
                    bytes_read = count * block_size
                    self.signals.progress.emit(self.task_name, bytes_read, total_size)
            
            self.signals.status.emit(f"Extracting {self.task_name}...")
            self.signals.progress.emit(self.task_name, 0, 0) # Indeterminate progress
            
            # Extract
            os.makedirs(self.extract_dir, exist_ok=True)
            if self.suffix == ".zip":
                with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                    zip_ref.extractall(self.extract_dir)
            elif self.suffix == ".tar.xz":
                import tarfile
                with tarfile.open(tmp_path, "r:xz") as tar_ref:
                    tar_ref.extractall(self.extract_dir)
            elif self.suffix == ".dmg":
                import subprocess
                # Mount DMG
                mount_cmd = ["hdiutil", "attach", tmp_path, "-nobrowse"]
                res = subprocess.run(mount_cmd, capture_output=True, text=True)
                if res.returncode != 0:
                    raise Exception(f"Failed to mount DMG: {res.stderr}")
                
                # Find mount point
                mount_point = None
                for line in res.stdout.splitlines():
                    if "/Volumes/" in line:
                        mount_point = line[line.find("/Volumes/"):].strip()
                        break
                
                if mount_point:
                    try:
                        # Copy VLC.app
                        subprocess.run(["cp", "-R", f"{mount_point}/VLC.app", self.extract_dir], check=True)
                    finally:
                        # Detach DMG
                        subprocess.run(["hdiutil", "detach", mount_point], check=True)
                else:
                    raise Exception("Could not find DMG mount point")
                
            # Cleanup temp file
            os.unlink(tmp_path)
            
            self.signals.status.emit(f"{self.task_name} ready.")
            self.signals.finished.emit(True, "")
            
        except Exception as e:
            self.signals.finished.emit(False, str(e))


class DependencyDownloader(QObject):
    """Manages the download process for required dependencies."""
    
    all_finished = Signal()
    progress_update = Signal(str, int, int)
    status_update = Signal(str)
    error_occurred = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.thread_pool = QThreadPool()
        self.active_downloads = 0
        self.has_errors = False
        
    def start_downloads(self, needs_vlc: bool, needs_ffmpeg: bool):
        self.active_downloads = 0
        self.has_errors = False
        deps_dir = get_deps_dir()
        
        if needs_vlc:
            vlc_dir = os.path.join(deps_dir, "vlc")
            if sys.platform == "win32":
                self._start_worker("VLC Player", VLC_WIN64_URL, vlc_dir, ".zip")
            elif sys.platform == "darwin":
                self._start_worker("VLC Player", VLC_MAC_URL, vlc_dir, ".dmg")
            # Linux VLC downloaded via package manager (not dynamically handled here)
            
        if needs_ffmpeg:
            ffmpeg_dir = os.path.join(deps_dir, "ffmpeg")
            if sys.platform == "win32":
                self._start_worker("FFmpeg", FFMPEG_WIN64_URL, ffmpeg_dir, ".zip")
            elif sys.platform == "darwin":
                self._start_worker("FFmpeg", FFMPEG_MAC_URL, ffmpeg_dir, ".zip")
                self._start_worker("FFprobe", FFPROBE_MAC_URL, ffmpeg_dir, ".zip")
            else:
                self._start_worker("FFmpeg", FFMPEG_LINUX64_URL, ffmpeg_dir, ".tar.xz")
            
        if self.active_downloads == 0:
            self.all_finished.emit()

    def _start_worker(self, name: str, url: str, extract_dir: str, suffix: str = ".zip"):
        self.active_downloads += 1
        worker = DownloadWorker(name, url, extract_dir, suffix)
        worker.signals.progress.connect(self.progress_update)
        worker.signals.status.connect(self.status_update)
        worker.signals.finished.connect(self._on_worker_finished)
        self.thread_pool.start(worker)

    def _on_worker_finished(self, success: bool, error_msg: str):
        self.active_downloads -= 1
        if not success:
            self.has_errors = True
            self.error_occurred.emit(error_msg)
            
        if self.active_downloads <= 0:
            self.all_finished.emit()
