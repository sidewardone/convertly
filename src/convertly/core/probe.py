"""Определение параметров файла через ffprobe."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .binaries import find_binary

IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
    ".gif",
    ".heic",
    ".avif",
    ".ico",
    ".tga",
}

VIDEO_EXTENSIONS = {
    ".mp4",
    ".mkv",
    ".webm",
    ".mov",
    ".avi",
    ".m4v",
    ".ts",
    ".flv",
    ".wmv",
    ".mpg",
    ".mpeg",
    ".3gp",
    ".ogv",
}

AUDIO_EXTENSIONS = {
    ".mp3",
    ".flac",
    ".wav",
    ".ogg",
    ".opus",
    ".aac",
    ".m4a",
    ".wma",
    ".aiff",
    ".alac",
}

SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS | AUDIO_EXTENSIONS

_IMAGE_FORMAT_NAMES = {
    "png_pipe",
    "jpeg_pipe",
    "webp_pipe",
    "bmp_pipe",
    "tiff_pipe",
    "gif",
    "heic",
    "avif",
    "ico",
    "image2",
}


class ProbeError(RuntimeError):
    """ffprobe не смог прочитать файл."""


@dataclass
class MediaInfo:
    path: Path
    kind: str  # "video" | "audio" | "image"
    duration: float | None = None
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    video_codec: str | None = None
    audio_codec: str | None = None
    size: int = 0
    has_audio: bool = False

    @property
    def size_label(self) -> str:
        return human_size(self.size)

    @property
    def resolution_label(self) -> str:
        if not self.width or not self.height:
            return ""
        return f"{self.width}×{self.height}"

    @property
    def duration_label(self) -> str:
        if not self.duration:
            return ""
        total = round(self.duration)
        minutes, seconds = divmod(total, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"

    @property
    def meta_label(self) -> str:
        """Строка для очереди: «1.8 ГБ · 3840×2160 · 30 fps»."""
        parts = [self.size_label]
        if self.kind != "audio" and self.resolution_label:
            parts.append(self.resolution_label)
        if self.duration:
            parts.append(self.duration_label)
        elif self.video_codec and self.kind == "video":
            parts.append(self.video_codec.upper())
        if self.has_audio and self.kind == "audio":
            extension = self.path.suffix.lstrip(".").upper()
            if extension:
                parts.append(extension)
        return " · ".join(parts)


def human_size(num: float) -> str:
    units = ("Б", "КБ", "МБ", "ГБ", "ТБ")
    value = float(num)
    for unit in units:
        if abs(value) < 1024 or unit == units[-1]:
            if unit == "Б":
                return f"{value:.0f} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} {units[-1]}"


def ffprobe_path() -> str | None:
    return find_binary("ffprobe")


def probe(path: Path) -> MediaInfo:
    """Читает информацию о файле. Бросает ProbeError при проблемах."""
    executable = ffprobe_path()
    if not executable:
        raise ProbeError("ffprobe не найден в PATH")

    command = [
        executable,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=30, check=False
        )
    except subprocess.TimeoutExpired as exc:
        raise ProbeError("ffprobe не ответил за 30 секунд") from exc

    if result.returncode != 0:
        message = _last_line(result.stderr) or "неизвестный формат файла"
        raise ProbeError(message)

    try:
        data = json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise ProbeError("не удалось разобрать ответ ffprobe") from exc

    streams = data.get("streams") or []
    fmt = data.get("format") or {}

    video_stream = next(
        (
            stream
            for stream in streams
            if stream.get("codec_type") == "video"
            and not (stream.get("disposition") or {}).get("attached_pic")
        ),
        None,
    )
    audio_stream = next(
        (stream for stream in streams if stream.get("codec_type") == "audio"),
        None,
    )

    info = MediaInfo(
        path=path,
        kind=_detect_kind(path, fmt, video_stream, audio_stream),
        size=path.stat().st_size if path.exists() else 0,
        has_audio=audio_stream is not None,
        audio_codec=audio_stream.get("codec_name") if audio_stream else None,
    )

    duration = _as_float(fmt.get("duration"))
    if duration is None and video_stream is not None:
        duration = _as_float(video_stream.get("duration"))
    info.duration = duration

    if video_stream is not None:
        info.width = _as_int(video_stream.get("width"))
        info.height = _as_int(video_stream.get("height"))
        info.fps = _parse_fps(video_stream.get("r_frame_rate"))
        info.video_codec = video_stream.get("codec_name")

    return info


def _detect_kind(
    path: Path, fmt: dict, video_stream: dict | None, audio_stream: dict | None
) -> str:
    extension = path.suffix.lower()
    format_name = (fmt.get("format_name") or "").lower()

    if extension in IMAGE_EXTENSIONS:
        return "image"
    if format_name in _IMAGE_FORMAT_NAMES:
        return "image"

    if video_stream is not None:
        if audio_stream is None and not _as_float(fmt.get("duration")):
            return "image"
        return "video"
    if audio_stream is not None:
        return "audio"
    raise ProbeError("в файле нет ни видео, ни аудио")


def _parse_fps(raw: str | None) -> float | None:
    if not raw or raw in {"0/0", "N/A"}:
        return None
    try:
        if "/" in raw:
            numerator, denominator = raw.split("/", 1)
            value = float(numerator) / float(denominator)
        else:
            value = float(raw)
    except (ValueError, ZeroDivisionError):
        return None
    return round(value, 2) if value > 0 else None


def _as_float(raw) -> float | None:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _as_int(raw) -> int | None:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _last_line(text: str) -> str:
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    return lines[-1] if lines else ""
