"""FFmpeg Service — Transcoding, conversion, and media processing via subprocess."""

import os
import re
import subprocess
import signal
from dataclasses import dataclass, field
from typing import Callable, Optional

from src.core.utils import find_ffmpeg


@dataclass
class TranscodeJob:
    """Represents a transcoding/conversion job."""
    id: str
    input_path: str
    output_path: str
    options: dict = field(default_factory=dict)
    progress: float = 0.0
    status: str = "pending"  # pending, running, completed, failed, cancelled
    error: str = ""
    process: Optional[subprocess.Popen] = field(default=None, repr=False)


# ─── Preset Profiles ────────────────────────────────────────

PRESETS = {
    # ─── General (Very Fast) ──────────────────────────────
    "gen_very_fast_4k_av1": {
        "name": "General: Very Fast 2160p60 4K AV1",
        "ext": ".mkv",
        "args": ["-c:v", "libsvtav1", "-preset", "8", "-crf", "30",
                 "-vf", "scale=-2:2160", "-r", "60", "-c:a", "aac", "-b:a", "160k"],
    },
    "gen_very_fast_4k_hevc": {
        "name": "General: Very Fast 2160p60 4K HEVC",
        "ext": ".mp4",
        "args": ["-c:v", "libx265", "-preset", "veryfast", "-crf", "28", "-tag:v", "hvc1",
                 "-vf", "scale=-2:2160", "-r", "60", "-c:a", "aac", "-b:a", "160k"],
    },
    "gen_very_fast_1080p": {
        "name": "General: Very Fast 1080p30",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
                 "-vf", "scale=-2:1080", "-r", "30", "-c:a", "aac", "-b:a", "128k"],
    },
    "gen_very_fast_720p": {
        "name": "General: Very Fast 720p30",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
                 "-vf", "scale=-2:720", "-r", "30", "-c:a", "aac", "-b:a", "128k"],
    },
    "gen_very_fast_576p": {
        "name": "General: Very Fast 576p25",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
                 "-vf", "scale=-2:576", "-r", "25", "-c:a", "aac", "-b:a", "112k"],
    },
    "gen_very_fast_480p": {
        "name": "General: Very Fast 480p30",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
                 "-vf", "scale=-2:480", "-r", "30", "-c:a", "aac", "-b:a", "96k"],
    },

    # ─── General (Fast) ───────────────────────────────────
    "gen_fast_4k_av1": {
        "name": "General: Fast 2160p60 4K AV1",
        "ext": ".mkv",
        "args": ["-c:v", "libsvtav1", "-preset", "6", "-crf", "28",
                 "-vf", "scale=-2:2160", "-r", "60", "-c:a", "aac", "-b:a", "192k"],
    },
    "gen_fast_4k_hevc": {
        "name": "General: Fast 2160p60 4K HEVC",
        "ext": ".mp4",
        "args": ["-c:v", "libx265", "-preset", "fast", "-crf", "26", "-tag:v", "hvc1",
                 "-vf", "scale=-2:2160", "-r", "60", "-c:a", "aac", "-b:a", "192k"],
    },
    "gen_fast_1080p": {
        "name": "General: Fast 1080p30 (Default)",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "fast", "-crf", "22",
                 "-vf", "scale=-2:1080", "-r", "30", "-c:a", "aac", "-b:a", "160k"],
    },
    "gen_fast_720p": {
        "name": "General: Fast 720p30",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "fast", "-crf", "22",
                 "-vf", "scale=-2:720", "-r", "30", "-c:a", "aac", "-b:a", "128k"],
    },
    "gen_fast_576p": {
        "name": "General: Fast 576p25",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "fast", "-crf", "22",
                 "-vf", "scale=-2:576", "-r", "25", "-c:a", "aac", "-b:a", "112k"],
    },
    "gen_fast_480p": {
        "name": "General: Fast 480p30",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "fast", "-crf", "22",
                 "-vf", "scale=-2:480", "-r", "30", "-c:a", "aac", "-b:a", "96k"],
    },

    # ─── General (HQ) ─────────────────────────────────────
    "gen_hq_4k_av1": {
        "name": "General: HQ 2160p60 4K AV1 Surround",
        "ext": ".mkv",
        "args": ["-c:v", "libsvtav1", "-preset", "5", "-crf", "24",
                 "-vf", "scale=-2:2160", "-r", "60", "-c:a", "aac", "-b:a", "448k", "-ac", "6"],
    },
    "gen_hq_4k_hevc": {
        "name": "General: HQ 2160p60 4K HEVC Surround",
        "ext": ".mp4",
        "args": ["-c:v", "libx265", "-preset", "slow", "-crf", "24", "-tag:v", "hvc1",
                 "-vf", "scale=-2:2160", "-r", "60", "-c:a", "aac", "-b:a", "448k", "-ac", "6"],
    },
    "gen_hq_1080p": {
        "name": "General: HQ 1080p30 Surround",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "slow", "-crf", "20",
                 "-vf", "scale=-2:1080", "-r", "30", "-c:a", "aac", "-b:a", "384k", "-ac", "6"],
    },
    "gen_hq_720p": {
        "name": "General: HQ 720p30 Surround",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "slow", "-crf", "20",
                 "-vf", "scale=-2:720", "-r", "30", "-c:a", "aac", "-b:a", "320k", "-ac", "6"],
    },
    "gen_hq_576p": {
        "name": "General: HQ 576p25 Surround",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "slow", "-crf", "20",
                 "-vf", "scale=-2:576", "-r", "25", "-c:a", "aac", "-b:a", "256k", "-ac", "6"],
    },
    "gen_hq_480p": {
        "name": "General: HQ 480p30 Surround",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "slow", "-crf", "20",
                 "-vf", "scale=-2:480", "-r", "30", "-c:a", "aac", "-b:a", "224k", "-ac", "6"],
    },

    # ─── General (Super HQ) ───────────────────────────────
    "gen_super_hq_4k_av1": {
        "name": "General: Super HQ 2160p60 4K AV1 Surround",
        "ext": ".mkv",
        "args": ["-c:v", "libsvtav1", "-preset", "4", "-crf", "20",
                 "-vf", "scale=-2:2160", "-r", "60", "-c:a", "aac", "-b:a", "640k", "-ac", "6"],
    },
    "gen_super_hq_4k_hevc": {
        "name": "General: Super HQ 2160p60 4K HEVC Surround",
        "ext": ".mp4",
        "args": ["-c:v", "libx265", "-preset", "slower", "-crf", "20", "-tag:v", "hvc1",
                 "-vf", "scale=-2:2160", "-r", "60", "-c:a", "aac", "-b:a", "640k", "-ac", "6"],
    },
    "gen_super_hq_1080p": {
        "name": "General: Super HQ 1080p30 Surround",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "veryslow", "-crf", "18",
                 "-vf", "scale=-2:1080", "-r", "30", "-c:a", "aac", "-b:a", "448k", "-ac", "6"],
    },
    "gen_super_hq_720p": {
        "name": "General: Super HQ 720p30 Surround",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "veryslow", "-crf", "18",
                 "-vf", "scale=-2:720", "-r", "30", "-c:a", "aac", "-b:a", "448k", "-ac", "6"],
    },
    "gen_super_hq_576p": {
        "name": "General: Super HQ 576p25 Surround",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "veryslow", "-crf", "18",
                 "-vf", "scale=-2:576", "-r", "25", "-c:a", "aac", "-b:a", "384k", "-ac", "6"],
    },
    "gen_super_hq_480p": {
        "name": "General: Super HQ 480p30 Surround",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "veryslow", "-crf", "18",
                 "-vf", "scale=-2:480", "-r", "30", "-c:a", "aac", "-b:a", "320k", "-ac", "6"],
    },

    # ─── Web (Creator) ────────────────────────────────────
    "web_creator_4k": {
        "name": "Web: Creator 2160p60 4K",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "medium", "-crf", "18",
                 "-vf", "scale=-2:2160", "-r", "60", "-c:a", "aac", "-b:a", "320k"],
    },
    "web_creator_1440p": {
        "name": "Web: Creator 1440p60 2.5K",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "medium", "-crf", "18",
                 "-vf", "scale=-2:1440", "-r", "60", "-c:a", "aac", "-b:a", "320k"],
    },
    "web_creator_1080p": {
        "name": "Web: Creator 1080p60",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "medium", "-crf", "18",
                 "-vf", "scale=-2:1080", "-r", "60", "-c:a", "aac", "-b:a", "256k"],
    },
    "web_creator_720p": {
        "name": "Web: Creator 720p60",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "medium", "-crf", "18",
                 "-vf", "scale=-2:720", "-r", "60", "-c:a", "aac", "-b:a", "192k"],
    },

    # ─── Web (Social - File Size Targets) ─────────────────
    # 25MB Target
    "web_social_25mb_30s_1080p": {
        "name": "Web: Social 25MB 30s 1080p60",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "slow", "-b:v", "6500k", "-maxrate", "6500k", "-bufsize", "13000k",
                 "-vf", "scale=-2:1080", "-r", "60", "-c:a", "aac", "-b:a", "192k"],
    },
    "web_social_25mb_1m_720p": {
        "name": "Web: Social 25MB 1m 720p60",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "slow", "-b:v", "3200k", "-maxrate", "3200k", "-bufsize", "6400k",
                 "-vf", "scale=-2:720", "-r", "60", "-c:a", "aac", "-b:a", "160k"],
    },
    "web_social_25mb_2m_540p": {
        "name": "Web: Social 25MB 2m 540p60",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "slow", "-b:v", "1500k", "-maxrate", "1500k", "-bufsize", "3000k",
                 "-vf", "scale=-2:540", "-r", "60", "-c:a", "aac", "-b:a", "128k"],
    },
    "web_social_25mb_5m_360p": {
        "name": "Web: Social 25MB 5m 360p60",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "slow", "-b:v", "550k", "-maxrate", "550k", "-bufsize", "1100k",
                 "-vf", "scale=-2:360", "-r", "60", "-c:a", "aac", "-b:a", "96k"],
    },

    # 10MB Target
    "web_social_10mb_30s_720p": {
        "name": "Web: Social 10MB 30s 720p60",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "slow", "-b:v", "2500k", "-maxrate", "2500k", "-bufsize", "5000k",
                 "-vf", "scale=-2:720", "-r", "60", "-c:a", "aac", "-b:a", "128k"],
    },
    "web_social_10mb_1m_540p": {
        "name": "Web: Social 10MB 1m 540p60",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "slow", "-b:v", "1200k", "-maxrate", "1200k", "-bufsize", "2400k",
                 "-vf", "scale=-2:540", "-r", "60", "-c:a", "aac", "-b:a", "128k"],
    },
    "web_social_10mb_2m_360p": {
        "name": "Web: Social 10MB 2m 360p60",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "slow", "-b:v", "600k", "-maxrate", "600k", "-bufsize", "1200k",
                 "-vf", "scale=-2:360", "-r", "60", "-c:a", "aac", "-b:a", "96k"],
    },

    # ─── Devices ──────────────────────────────────────────
    # Amazon Fire
    "dev_fire_4k_hevc": {
        "name": "Device: Amazon Fire 2160p60 4K HEVC Surround",
        "ext": ".mp4",
        "args": ["-c:v", "libx265", "-preset", "medium", "-crf", "24", "-tag:v", "hvc1",
                 "-vf", "scale=-2:2160", "-r", "60", "-c:a", "aac", "-b:a", "320k", "-ac", "6"],
    },
    "dev_fire_1080p": {
        "name": "Device: Amazon Fire 1080p30 Surround",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "fast", "-crf", "22",
                 "-vf", "scale=-2:1080", "-r", "30", "-c:a", "aac", "-b:a", "192k", "-ac", "6"],
    },
    "dev_fire_720p": {
        "name": "Device: Amazon Fire 720p30",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "fast", "-crf", "22",
                 "-vf", "scale=-2:720", "-r", "30", "-c:a", "aac", "-b:a", "128k"],
    },

    # Android
    "dev_android_1080p": {
        "name": "Device: Android 1080p30",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "fast", "-crf", "22",
                 "-vf", "scale=-2:1080", "-r", "30", "-c:a", "aac", "-b:a", "128k"],
    },
    "dev_android_720p": {
        "name": "Device: Android 720p30",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "fast", "-crf", "22",
                 "-vf", "scale=-2:720", "-r", "30", "-c:a", "aac", "-b:a", "128k"],
    },
    "dev_android_576p": {
        "name": "Device: Android 576p25",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "fast", "-crf", "22",
                 "-vf", "scale=-2:576", "-r", "25", "-c:a", "aac", "-b:a", "112k"],
    },
    "dev_android_480p": {
        "name": "Device: Android 480p30",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "fast", "-crf", "22",
                 "-vf", "scale=-2:480", "-r", "30", "-c:a", "aac", "-b:a", "96k"],
    },

    # Apple
    "dev_apple_4k_hevc": {
        "name": "Device: Apple 2160p60 4K HEVC Surround",
        "ext": ".m4v",
        "args": ["-c:v", "libx265", "-preset", "medium", "-crf", "24", "-tag:v", "hvc1",
                 "-vf", "scale=-2:2160", "-r", "60", "-c:a", "aac", "-b:a", "320k", "-ac", "6", "-movflags", "+faststart"],
    },
    "dev_apple_1080p60": {
        "name": "Device: Apple 1080p60 Surround",
        "ext": ".m4v",
        "args": ["-c:v", "libx264", "-preset", "fast", "-crf", "22",
                 "-vf", "scale=-2:1080", "-r", "60", "-c:a", "aac", "-b:a", "192k", "-ac", "6", "-movflags", "+faststart"],
    },
    "dev_apple_1080p30": {
        "name": "Device: Apple 1080p30 Surround",
        "ext": ".m4v",
        "args": ["-c:v", "libx264", "-preset", "fast", "-crf", "22",
                 "-vf", "scale=-2:1080", "-r", "30", "-c:a", "aac", "-b:a", "192k", "-ac", "6", "-movflags", "+faststart"],
    },
    "dev_apple_720p": {
        "name": "Device: Apple 720p30 Surround",
        "ext": ".m4v",
        "args": ["-c:v", "libx264", "-preset", "fast", "-crf", "22",
                 "-vf", "scale=-2:720", "-r", "30", "-c:a", "aac", "-b:a", "160k", "-ac", "6", "-movflags", "+faststart"],
    },
    "dev_apple_540p": {
        "name": "Device: Apple 540p30 Surround",
        "ext": ".m4v",
        "args": ["-c:v", "libx264", "-preset", "fast", "-crf", "22",
                 "-vf", "scale=-2:540", "-r", "30", "-c:a", "aac", "-b:a", "128k", "-ac", "6", "-movflags", "+faststart"],
    },

    # Chromecast
    "dev_chromecast_4k_hevc": {
        "name": "Device: Chromecast 2160p60 4K HEVC Surround",
        "ext": ".mp4",
        "args": ["-c:v", "libx265", "-preset", "medium", "-crf", "24", "-tag:v", "hvc1",
                 "-vf", "scale=-2:2160", "-r", "60", "-c:a", "aac", "-b:a", "320k", "-ac", "6"],
    },
    "dev_chromecast_1080p60": {
        "name": "Device: Chromecast 1080p60 Surround",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "fast", "-crf", "22",
                 "-vf", "scale=-2:1080", "-r", "60", "-c:a", "aac", "-b:a", "192k", "-ac", "6"],
    },
    "dev_chromecast_1080p30": {
        "name": "Device: Chromecast 1080p30 Surround",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "fast", "-crf", "22",
                 "-vf", "scale=-2:1080", "-r", "30", "-c:a", "aac", "-b:a", "192k", "-ac", "6"],
    },

    # Playstation
    "dev_ps_4k": {
        "name": "Device: Playstation 2160p60 4K Surround",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "fast", "-crf", "22",
                 "-vf", "scale=-2:2160", "-r", "60", "-c:a", "aac", "-b:a", "320k", "-ac", "6"],
    },
    "dev_ps_1080p": {
        "name": "Device: Playstation 1080p30 Surround",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "fast", "-crf", "22",
                 "-vf", "scale=-2:1080", "-r", "30", "-c:a", "aac", "-b:a", "192k", "-ac", "6"],
    },
    "dev_ps_720p": {
        "name": "Device: Playstation 720p30",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "fast", "-crf", "22",
                 "-vf", "scale=-2:720", "-r", "30", "-c:a", "aac", "-b:a", "128k"],
    },
    "dev_ps_540p": {
        "name": "Device: Playstation 540p30",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "fast", "-crf", "22",
                 "-vf", "scale=-2:540", "-r", "30", "-c:a", "aac", "-b:a", "112k"],
    },

    # Roku
    "dev_roku_4k_hevc": {
        "name": "Device: Roku 2160p60 4K HEVC Surround",
        "ext": ".mp4",
        "args": ["-c:v", "libx265", "-preset", "medium", "-crf", "24", "-tag:v", "hvc1",
                 "-vf", "scale=-2:2160", "-r", "60", "-c:a", "aac", "-b:a", "320k", "-ac", "6"],
    },
    "dev_roku_1080p": {
        "name": "Device: Roku 1080p30 Surround",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "fast", "-crf", "22",
                 "-vf", "scale=-2:1080", "-r", "30", "-c:a", "aac", "-b:a", "192k", "-ac", "6"],
    },
    "dev_roku_720p": {
        "name": "Device: Roku 720p30 Surround",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "fast", "-crf", "22",
                 "-vf", "scale=-2:720", "-r", "30", "-c:a", "aac", "-b:a", "128k", "-ac", "6"],
    },
    "dev_roku_576p": {
        "name": "Device: Roku 576p25",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "fast", "-crf", "22",
                 "-vf", "scale=-2:576", "-r", "25", "-c:a", "aac", "-b:a", "112k"],
    },
    "dev_roku_480p": {
        "name": "Device: Roku 480p30",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "fast", "-crf", "22",
                 "-vf", "scale=-2:480", "-r", "30", "-c:a", "aac", "-b:a", "96k"],
    },

    # Xbox
    "dev_xbox_1080p": {
        "name": "Device: Xbox 1080p30 Surround",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "fast", "-crf", "22",
                 "-vf", "scale=-2:1080", "-r", "30", "-c:a", "aac", "-b:a", "192k", "-ac", "6"],
    },

    # ─── Matroska (MKV) ───────────────────────────────────
    # AV1
    "mkv_av1_4k": {
        "name": "Matroska: AV1 MKV 2160p60 4K",
        "ext": ".mkv",
        "args": ["-c:v", "libsvtav1", "-preset", "6", "-crf", "28",
                 "-vf", "scale=-2:2160", "-r", "60", "-c:a", "aac", "-b:a", "192k"],
    },
    
    # H.265 (HEVC)
    "mkv_h265_4k": {
        "name": "Matroska: H.265 MKV 2160p60 4K",
        "ext": ".mkv",
        "args": ["-c:v", "libx265", "-preset", "medium", "-crf", "22", "-tag:v", "hvc1",
                 "-vf", "scale=-2:2160", "-r", "60", "-c:a", "aac", "-b:a", "320k"],
    },
    "mkv_h265_1080p": {
        "name": "Matroska: H.265 MKV 1080p30",
        "ext": ".mkv",
        "args": ["-c:v", "libx265", "-preset", "medium", "-crf", "24", "-tag:v", "hvc1",
                 "-vf", "scale=-2:1080", "-r", "30", "-c:a", "aac", "-b:a", "192k"],
    },
    "mkv_h265_720p": {
        "name": "Matroska: H.265 MKV 720p30",
        "ext": ".mkv",
        "args": ["-c:v", "libx265", "-preset", "medium", "-crf", "24", "-tag:v", "hvc1",
                 "-vf", "scale=-2:720", "-r", "30", "-c:a", "aac", "-b:a", "160k"],
    },
    "mkv_h265_576p": {
        "name": "Matroska: H.265 MKV 576p25",
        "ext": ".mkv",
        "args": ["-c:v", "libx265", "-preset", "medium", "-crf", "24", "-tag:v", "hvc1",
                 "-vf", "scale=-2:576", "-r", "25", "-c:a", "aac", "-b:a", "128k"],
    },
    "mkv_h265_480p": {
        "name": "Matroska: H.265 MKV 480p30",
        "ext": ".mkv",
        "args": ["-c:v", "libx265", "-preset", "medium", "-crf", "24", "-tag:v", "hvc1",
                 "-vf", "scale=-2:480", "-r", "30", "-c:a", "aac", "-b:a", "112k"],
    },

    # H.264 (AVC)
    "mkv_h264_4k": {
        "name": "Matroska: H.264 MKV 2160p60 4K",
        "ext": ".mkv",
        "args": ["-c:v", "libx264", "-preset", "medium", "-crf", "20",
                 "-vf", "scale=-2:2160", "-r", "60", "-c:a", "aac", "-b:a", "320k"],
    },
    "mkv_h264_1080p": {
        "name": "Matroska: H.264 MKV 1080p30",
        "ext": ".mkv",
        "args": ["-c:v", "libx264", "-preset", "medium", "-crf", "22",
                 "-vf", "scale=-2:1080", "-r", "30", "-c:a", "aac", "-b:a", "192k"],
    },
    "mkv_h264_720p": {
        "name": "Matroska: H.264 MKV 720p30",
        "ext": ".mkv",
        "args": ["-c:v", "libx264", "-preset", "medium", "-crf", "22",
                 "-vf", "scale=-2:720", "-r", "30", "-c:a", "aac", "-b:a", "160k"],
    },
    "mkv_h264_576p": {
        "name": "Matroska: H.264 MKV 576p25",
        "ext": ".mkv",
        "args": ["-c:v", "libx264", "-preset", "medium", "-crf", "22",
                 "-vf", "scale=-2:576", "-r", "25", "-c:a", "aac", "-b:a", "128k"],
    },
    "mkv_h264_480p": {
        "name": "Matroska: H.264 MKV 480p30",
        "ext": ".mkv",
        "args": ["-c:v", "libx264", "-preset", "medium", "-crf", "22",
                 "-vf", "scale=-2:480", "-r", "30", "-c:a", "aac", "-b:a", "112k"],
    },

    # VP9
    "mkv_vp9_4k": {
        "name": "Matroska: VP9 MKV 2160p60 4K",
        "ext": ".mkv",
        "args": ["-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "30",
                 "-vf", "scale=-2:2160", "-r", "60", "-c:a", "libopus", "-b:a", "192k"],
    },
    "mkv_vp9_1080p": {
        "name": "Matroska: VP9 MKV 1080p30",
        "ext": ".mkv",
        "args": ["-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "30",
                 "-vf", "scale=-2:1080", "-r", "30", "-c:a", "libopus", "-b:a", "128k"],
    },
    "mkv_vp9_720p": {
        "name": "Matroska: VP9 MKV 720p30",
        "ext": ".mkv",
        "args": ["-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "30",
                 "-vf", "scale=-2:720", "-r", "30", "-c:a", "libopus", "-b:a", "96k"],
    },
    "mkv_vp9_576p": {
        "name": "Matroska: VP9 MKV 576p25",
        "ext": ".mkv",
        "args": ["-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "30",
                 "-vf", "scale=-2:576", "-r", "25", "-c:a", "libopus", "-b:a", "96k"],
    },
    "mkv_vp9_480p": {
        "name": "Matroska: VP9 MKV 480p30",
        "ext": ".mkv",
        "args": ["-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "30",
                 "-vf", "scale=-2:480", "-r", "30", "-c:a", "libopus", "-b:a", "96k"],
    },

    # ─── Hardware (NVIDIA/Intel/AMD/Apple) ────────────────
    # Intel QSV
    "hw_qsv_av1_4k": {
        "name": "Hardware: AV1 QSV 2160p 4K (Intel)",
        "ext": ".mp4",
        "args": ["-c:v", "av1_qsv", "-preset", "medium", "-global_quality", "25",
                 "-vf", "scale=-2:2160", "-c:a", "aac", "-b:a", "320k"],
    },
    "hw_qsv_h265_4k": {
        "name": "Hardware: H.265 QSV 2160p 4K (Intel)",
        "ext": ".mp4",
        "args": ["-c:v", "hevc_qsv", "-preset", "medium", "-global_quality", "25",
                 "-vf", "scale=-2:2160", "-c:a", "aac", "-b:a", "320k"],
    },
    "hw_qsv_h265_1080p": {
        "name": "Hardware: H.265 QSV 1080p (Intel)",
        "ext": ".mp4",
        "args": ["-c:v", "hevc_qsv", "-preset", "medium", "-global_quality", "25",
                 "-vf", "scale=-2:1080", "-c:a", "aac", "-b:a", "192k"],
    },

    # NVIDIA NVENC
    "hw_nvenc_h265_4k": {
        "name": "Hardware: H.265 NVENC 2160p 4K (NVIDIA)",
        "ext": ".mp4",
        "args": ["-c:v", "hevc_nvenc", "-preset", "p4", "-cq", "25",
                 "-vf", "scale=-2:2160", "-c:a", "aac", "-b:a", "320k"],
    },
    "hw_nvenc_h265_1080p": {
        "name": "Hardware: H.265 NVENC 1080p (NVIDIA)",
        "ext": ".mp4",
        "args": ["-c:v", "hevc_nvenc", "-preset", "p4", "-cq", "25",
                 "-vf", "scale=-2:1080", "-c:a", "aac", "-b:a", "192k"],
    },

    # AMD AMF (VCN)
    "hw_amf_h265_4k": {
        "name": "Hardware: H.265 VCN 2160p 4K (AMD)",
        "ext": ".mp4",
        "args": ["-c:v", "hevc_amf", "-usage", "transcoding", "-quality", "balanced",
                 "-vf", "scale=-2:2160", "-c:a", "aac", "-b:a", "320k"],
    },
    "hw_amf_h265_1080p": {
        "name": "Hardware: H.265 VCN 1080p (AMD)",
        "ext": ".mp4",
        "args": ["-c:v", "hevc_amf", "-usage", "transcoding", "-quality", "balanced",
                 "-vf", "scale=-2:1080", "-c:a", "aac", "-b:a", "192k"],
    },

    # Media Foundation (Windows)
    "hw_mf_h265_4k": {
        "name": "Hardware: H.265 MF 2160p 4K (Windows)",
        "ext": ".mp4",
        "args": ["-c:v", "hevc_mf", "-vf", "scale=-2:2160", "-c:a", "aac", "-b:a", "320k"],
    },
    "hw_mf_h265_1080p": {
        "name": "Hardware: H.265 MF 1080p (Windows)",
        "ext": ".mp4",
        "args": ["-c:v", "hevc_mf", "-vf", "scale=-2:1080", "-c:a", "aac", "-b:a", "192k"],
    },

    # Apple VideoToolbox
    "hw_vt_h265_4k": {
        "name": "Hardware: H.265 Apple VideoToolbox 2160p 4K",
        "ext": ".mp4",
        "args": ["-c:v", "hevc_videotoolbox", "-q:v", "50",
                 "-vf", "scale=-2:2160", "-c:a", "aac", "-b:a", "320k"],
    },
    "hw_vt_h265_1080p": {
        "name": "Hardware: H.265 Apple VideoToolbox 1080p",
        "ext": ".mp4",
        "args": ["-c:v", "hevc_videotoolbox", "-q:v", "50",
                 "-vf", "scale=-2:1080", "-c:a", "aac", "-b:a", "192k"],
    },

    # ─── Professional (Production) ────────────────────────
    "pro_proxy_1080p": {
        "name": "Professional: Production Proxy 1080p (All-Intra)",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "superfast", "-crf", "18", "-profile:v", "high",
                 "-vf", "scale=-2:1080", "-c:a", "aac", "-b:a", "128k",
                 # Editing optimizations: All-Intra (GOP=1), No B-frames via x264-params
                 "-x264-params", "keyint=1:min-keyint=1:ref=1:bframes=0:qcomp=0.8:aq-strength=0.5"],
    },
    "pro_standard": {
        "name": "Professional: Production Standard",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "medium", "-crf", "10", "-profile:v", "high",
                 "-c:a", "aac", "-b:a", "320k", "-movflags", "+faststart"],
    },
    "pro_max": {
        "name": "Professional: Production Max (Near Lossless)",
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "slow", "-crf", "2", "-profile:v", "high",
                 "-c:a", "aac", "-b:a", "320k", "-movflags", "+faststart"],
    },

    # ─── Audio Extract/Remux ──────────────────────────────
    "audio_mp3": {
        "name": "Audio: MP3 320k",
        "ext": ".mp3",
        "args": ["-vn", "-c:a", "libmp3lame", "-b:a", "320k"],
    },
    "audio_flac": {
        "name": "Audio: FLAC Lossless",
        "ext": ".flac",
        "args": ["-vn", "-c:a", "flac"],
    },
    "remux_copy": {
        "name": "Passthrough: Remux (Copy Streams)",
        "ext": ".mp4",
        "args": ["-c", "copy", "-movflags", "+faststart"],
    },
}


class FFmpegService:
    """Manages FFmpeg subprocess calls for transcoding and conversion."""

    def __init__(self):
        self._active_processes: dict[str, subprocess.Popen] = {}

    @property
    def ffmpeg_path(self):
        return find_ffmpeg() or "ffmpeg"

    def get_presets(self) -> dict:
        """Return available transcoding presets."""
        return {k: {"name": v["name"], "ext": v["ext"]} for k, v in PRESETS.items()}

    def transcode(
        self,
        job: TranscodeJob,
        on_progress: Callable[[float, str], None] = None,
    ) -> TranscodeJob:
        """
        Run a transcode/convert job synchronously (call from QThread).
        on_progress(percent, speed_str) called periodically.
        """
        preset_key = job.options.get("preset")
        custom_args = job.options.get("custom_args", [])

        if preset_key and preset_key in PRESETS:
            ffmpeg_args = PRESETS[preset_key]["args"]
        elif custom_args:
            ffmpeg_args = custom_args
        else:
            job.status = "failed"
            job.error = "No preset or custom args specified"
            return job

        cmd = [
            self.ffmpeg_path,
            "-y",                   # Overwrite output
            "-i", job.input_path,
            "-progress", "pipe:1",  # Progress to stdout
            "-nostats",
        ] + ffmpeg_args + [job.output_path]

        try:
            job.status = "running"
            creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr to avoid deadlock
                universal_newlines=True,
                creationflags=creation_flags,
            )
            job.process = proc
            self._active_processes[job.id] = proc

            # Get duration for progress calculation
            duration = job.options.get("duration", 0)

            # Parse progress output
            # Parse progress output
            current_time = 0.0
            speed = "0x"
            error_log = []

            for line in proc.stdout:
                line = line.strip()
                error_log.append(line)
                if len(error_log) > 50: # Keep last 50 lines
                    error_log.pop(0)

                if line.startswith("out_time_us="):
                    try:
                        us = int(line.split("=")[1])
                        current_time = us / 1_000_000.0
                        if duration > 0:
                            job.progress = min(100.0, (current_time / duration) * 100.0)
                    except ValueError:
                        pass
                elif line.startswith("speed="):
                    speed = line.split("=")[1]
                elif line.startswith("progress="):
                    status = line.split("=")[1]
                    if status == "end":
                        job.progress = 100.0

                if on_progress and duration > 0:
                    on_progress(job.progress, speed)


                if on_progress and duration > 0:
                    on_progress(job.progress, speed)

            proc.wait()

            if proc.returncode == 0:
                job.status = "completed"
                job.progress = 100.0
            else:
                job.status = "failed"
                # Join captured lines for error context
                job.error = "\n".join(error_log)

        except FileNotFoundError:
            job.status = "failed"
            job.error = "ffmpeg not found. Install FFmpeg and add to PATH."
        except Exception as e:
            job.status = "failed"
            job.error = str(e)
        finally:
            self._active_processes.pop(job.id, None)
            job.process = None

        return job

    def cancel(self, job_id: str):
        """Cancel a running job."""
        proc = self._active_processes.get(job_id)
        if proc:
            try:
                if os.name == "nt":
                    proc.terminate()
                else:
                    proc.send_signal(signal.SIGINT)
            except ProcessLookupError:
                pass

    def extract_audio(
        self,
        input_path: str,
        output_path: str,
        codec: str = "libmp3lame",
        bitrate: str = "320k",
        on_progress: Callable[[float, str], None] = None,
    ) -> dict:
        """Extract audio from a video file."""
        job = TranscodeJob(
            id=f"extract_{os.path.basename(input_path)}",
            input_path=input_path,
            output_path=output_path,
            options={"custom_args": ["-vn", "-c:a", codec, "-b:a", bitrate]},
        )
        result = self.transcode(job, on_progress)
        return {"status": result.status, "error": result.error, "output": output_path}

    def generate_thumbnail(
        self,
        input_path: str,
        output_path: str,
        timestamp: float = 0,
        width: int = 320,
    ) -> bool:
        """Generate a thumbnail at a specific timestamp."""
        cmd = [
            self.ffmpeg_path, "-y",
            "-ss", str(timestamp),
            "-i", input_path,
            "-frames:v", "1",
            "-vf", f"scale={width}:-1",
            output_path,
        ]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            return result.returncode == 0
        except Exception:
            return False
