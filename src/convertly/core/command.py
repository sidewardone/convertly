"""Построение аргументов ffmpeg из настроек конвертации."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .capabilities import ffmpeg_path, has_encoder
from .formats import FormatSpec, format_by_key
from .probe import MediaInfo

RESOLUTION_HEIGHTS = {"2160": 2160, "1440": 1440, "1080": 1080, "720": 720, "480": 480}


@dataclass
class ConversionSettings:
    format_key: str = "mp4"
    video_codec: str | None = None
    quality: int = 75
    resolution: str = "original"
    fps: str = "original"
    copy_metadata: bool = True
    drop_audio: bool = False


def build_command(
    info: MediaInfo,
    settings: ConversionSettings,
    output_path: Path,
) -> list[str]:
    """Собирает полную команду ffmpeg с прогрессом в stdout."""
    executable = ffmpeg_path()
    if not executable:
        raise RuntimeError("ffmpeg не найден в PATH")

    spec = format_by_key(settings.format_key)
    quality = _clamp(settings.quality)

    args: list[str] = [
        executable,
        "-hide_banner",
        "-y",
        "-nostdin",
        "-loglevel",
        "error",
        "-progress",
        "pipe:1",
        "-nostats",
        "-i",
        str(info.path),
    ]

    if spec.kind == "video":
        args += _video_args(info, spec, settings, quality)
    elif spec.kind == "audio":
        args += _audio_args(info, spec, quality)
    else:
        args += _image_args(info, spec, settings, quality)

    args += (
        ["-map_metadata", "0"] if settings.copy_metadata else ["-map_metadata", "-1"]
    )
    args.append(str(output_path))
    return args


def unique_output_path(
    directory: Path, stem: str, extension: str, taken: set[Path] | None = None
) -> Path:
    """Свободное имя файла: name.mp4, name (1).mp4, name (2).mp4…"""
    taken = taken or set()
    candidate = directory / f"{stem}{extension}"
    index = 1
    while candidate.exists() or candidate in taken:
        candidate = directory / f"{stem} ({index}){extension}"
        index += 1
    return candidate


# Внутреннее
def _video_args(
    info: MediaInfo,
    spec: FormatSpec,
    settings: ConversionSettings,
    quality: int,
) -> list[str]:
    encoder = settings.video_codec
    if not encoder or not has_encoder(encoder):
        encoder = next(
            (codec for codec in spec.video_codecs if has_encoder(codec)),
            spec.video_codecs[0],
        )

    args: list[str] = ["-map", "0:v:0"]
    if not settings.drop_audio and info.has_audio:
        args += ["-map", "0:a:0"]

    args += ["-c:v", encoder]

    crf = _video_crf(encoder, quality)
    if encoder in {"libx264", "libx265"}:
        args += ["-preset", "medium", "-crf", str(crf)]
    elif encoder == "libvpx-vp9":
        args += ["-b:v", "0", "-crf", str(crf), "-row-mt", "1"]
    elif encoder == "libsvtav1":
        args += ["-crf", str(crf), "-preset", "6"]
    elif encoder == "libaom-av1":
        args += ["-b:v", "0", "-crf", str(crf), "-cpu-used", "6"]

    if spec.key in {"mp4", "mov"}:
        args += ["-pix_fmt", "yuv420p"]

    if not settings.drop_audio and info.has_audio and spec.audio_codec:
        args += ["-c:a", spec.audio_codec, "-b:a", spec.audio_bitrate]

    filters: list[str] = []
    height = _target_height(info, settings.resolution)
    if height:
        filters.append(f"scale=-2:{height}")
    if filters:
        args += ["-vf", ",".join(filters)]

    if settings.fps != "original":
        args += ["-r", settings.fps]

    if spec.key in {"mp4", "mov"}:
        args += ["-movflags", "+faststart"]

    return args


def _audio_args(info: MediaInfo, spec: FormatSpec, quality: int) -> list[str]:
    encoder = spec.audio_encoder
    if not has_encoder(encoder):
        encoder = "flac" if has_encoder("flac") else encoder

    args = ["-map", "0:a:0", "-vn", "-c:a", encoder]

    if spec.quality_mode == "audio":
        args += ["-b:a", audio_bitrate_for_quality(quality)]
    elif spec.quality_mode == "lossless":
        args += ["-compression_level", "8"]

    return args


def _image_args(
    info: MediaInfo,
    spec: FormatSpec,
    settings: ConversionSettings,
    quality: int,
) -> list[str]:
    args = ["-map", "0:v:0", "-frames:v", "1", "-update", "1"]

    filters: list[str] = []
    height = _target_height(info, settings.resolution)
    if height:
        filters.append(f"scale=-2:{height}")
    if filters:
        args += ["-vf", ",".join(filters)]

    if spec.key == "jpg":
        qscale = round(2 + (100 - quality) * 0.2)
        args += ["-q:v", str(_clamp(qscale, 2, 31))]
    elif spec.key == "png":
        args += ["-compression_level", "6"]
    elif spec.key == "webp":
        args += ["-quality", str(quality)]

    return args


def _target_height(info: MediaInfo, resolution: str) -> int | None:
    height = RESOLUTION_HEIGHTS.get(resolution)
    if not height:
        return None
    if info.height and info.height <= height:
        return None  # не растягиваем маленькие файлы
    return height


def _video_crf(encoder: str, quality: int) -> int:
    if encoder in {"libvpx-vp9", "libsvtav1", "libaom-av1"}:
        return _clamp(round(50 - quality * 0.30), 20, 50)
    return _clamp(round(35 - quality * 0.17), 18, 35)


def audio_bitrate_for_quality(quality: int) -> str:
    if quality >= 85:
        return "320k"
    if quality >= 60:
        return "256k"
    if quality >= 35:
        return "192k"
    return "128k"


def _clamp(value: int, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, value))
