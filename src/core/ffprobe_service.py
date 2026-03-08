"""FFprobe Service — Extract metadata from media files via subprocess."""

import json
import subprocess
import os

from src.core.utils import find_ffprobe, format_duration, format_size, format_bitrate


class FFprobeService:
    """Extracts structured metadata from media files using ffprobe."""

    def __init__(self):
        pass

    @property
    def ffprobe_path(self):
        return find_ffprobe() or "ffprobe"

    def get_metadata(self, file_path: str) -> dict:
        """
        Run ffprobe and return structured metadata.
        Returns dict with format, video streams, audio streams, subtitles, chapters.
        """
        if not os.path.isfile(file_path):
            return {"error": f"File not found: {file_path}"}

        try:
            cmd = [
                self.ffprobe_path,
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                "-show_chapters",
                file_path,
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )

            if result.returncode != 0:
                return {"error": f"ffprobe failed: {result.stderr.strip()}"}

            data = json.loads(result.stdout)
            return self._parse_metadata(file_path, data)

        except subprocess.TimeoutExpired:
            return {"error": "ffprobe timed out"}
        except FileNotFoundError:
            return {"error": "ffprobe not found. Install FFmpeg and add to PATH."}
        except json.JSONDecodeError as e:
            return {"error": f"Failed to parse ffprobe output: {e}"}

    def _parse_metadata(self, file_path: str, data: dict) -> dict:
        """Parse raw ffprobe JSON into structured format."""
        fmt = data.get("format", {})

        result = {
            "file_path": file_path,
            "file_name": os.path.basename(file_path),
            "format": {
                "name": fmt.get("format_name", "unknown"),
                "long_name": fmt.get("format_long_name", ""),
                "duration": float(fmt.get("duration", 0)),
                "duration_str": format_duration(float(fmt.get("duration", 0))),
                "size": int(fmt.get("size", 0)),
                "size_str": format_size(int(fmt.get("size", 0))),
                "bitrate": int(fmt.get("bit_rate", 0)),
                "bitrate_str": format_bitrate(int(fmt.get("bit_rate", 0))),
                "tags": fmt.get("tags", {}),
            },
            "video_streams": [],
            "audio_streams": [],
            "subtitle_streams": [],
            "chapters": [],
        }

        # Parse streams
        for stream in data.get("streams", []):
            codec_type = stream.get("codec_type")

            base = {
                "index": stream.get("index"),
                "codec": stream.get("codec_name", "unknown"),
                "codec_name": stream.get("codec_name", "unknown"),  # Alias for UI compatibility
                "codec_long": stream.get("codec_long_name", ""),
                "profile": stream.get("profile", ""),
                "bitrate": int(stream.get("bit_rate", 0)),
                "bitrate_str": format_bitrate(int(stream.get("bit_rate", 0))),
                "tags": stream.get("tags", {}),
                "disposition": stream.get("disposition", {}),
            }

            if codec_type == "video":
                result["video_streams"].append({
                    **base,
                    "width": stream.get("width", 0),
                    "height": stream.get("height", 0),
                    "resolution": f"{stream.get('width', 0)}x{stream.get('height', 0)}",
                    "fps": self._parse_fps(stream.get("r_frame_rate", "0/1")),
                    "pixel_format": stream.get("pix_fmt", ""),
                    "aspect_ratio": stream.get("display_aspect_ratio", ""),
                    "color_range": stream.get("color_range", ""),
                    "color_space": stream.get("color_space", ""),
                    "color_transfer": stream.get("color_transfer", ""),
                    "color_primaries": stream.get("color_primaries", ""),
                    "chroma_location": stream.get("chroma_location", ""),
                })
            elif codec_type == "audio":
                result["audio_streams"].append({
                    **base,
                    "channels": stream.get("channels", 0),
                    "channel_layout": stream.get("channel_layout", ""),
                    "sample_rate": int(stream.get("sample_rate", 0)),
                    "sample_fmt": stream.get("sample_fmt", ""),
                    "bits_per_sample": int(stream.get("bits_per_sample", 0)),
                    "bits_per_raw_sample": int(stream.get("bits_per_raw_sample", 0)),
                })
            elif codec_type == "subtitle":
                result["subtitle_streams"].append({
                    **base,
                    "language": stream.get("tags", {}).get("language", "und"),
                    "title": stream.get("tags", {}).get("title", ""),
                })

        # Parse chapters
        for chapter in data.get("chapters", []):
            result["chapters"].append({
                "id": chapter.get("id"),
                "start": float(chapter.get("start_time", 0)),
                "end": float(chapter.get("end_time", 0)),
                "title": chapter.get("tags", {}).get("title", ""),
            })

        return result

    @staticmethod
    def _parse_fps(rate_str: str) -> float:
        """Parse frame rate string like '30000/1001' to float."""
        try:
            if "/" in rate_str:
                num, den = rate_str.split("/")
                den = int(den)
                if den == 0:
                    return 0.0
                return round(int(num) / den, 2)
            return round(float(rate_str), 2)
        except (ValueError, ZeroDivisionError):
            return 0.0
