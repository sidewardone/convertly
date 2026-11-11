"""Реестр выходных форматов и доступных для них кодеков."""

from __future__ import annotations

from dataclasses import dataclass

from .capabilities import has_encoder

CODEC_LABELS = {
    "libx264": "H.264",
    "libx265": "H.265 (HEVC)",
    "libvpx-vp9": "VP9",
    "libsvtav1": "AV1 (SVT)",
    "libaom-av1": "AV1 (aom)",
    "libmp3lame": "MP3",
    "flac": "FLAC",
    "pcm_s16le": "PCM 16-bit",
    "libvorbis": "Vorbis",
    "aac": "AAC",
    "libopus": "Opus",
    "mjpeg": "JPEG",
    "png": "PNG",
    "libwebp": "WebP",
}


@dataclass(frozen=True)
class FormatSpec:
    key: str
    label: str
    kind: str  # "video" | "audio" | "image"
    extension: str
    video_codecs: tuple[str, ...] = ()
    audio_codec: str | None = None
    audio_bitrate: str = "192k"
    quality_mode: str = "crf"  # crf | audio | lossless | pcm | image
    default_quality: int = 75

    @property
    def lossless(self) -> bool:
        return self.quality_mode in {"lossless", "pcm"}

    @property
    def audio_encoder(self) -> str:
        """Энкодер для аудио-форматов (у них в video_codecs лежит аудио-кодек)."""
        return self.video_codecs[0] if self.video_codecs else "aac"


FORMATS: tuple[FormatSpec, ...] = (
    # видео
    FormatSpec(
        key="mp4",
        label="MP4",
        kind="video",
        extension=".mp4",
        video_codecs=("libx264", "libx265", "libsvtav1", "libaom-av1"),
        audio_codec="aac",
        audio_bitrate="192k",
        default_quality=75,
    ),
    FormatSpec(
        key="mkv",
        label="MKV",
        kind="video",
        extension=".mkv",
        video_codecs=("libx264", "libx265", "libvpx-vp9", "libsvtav1", "libaom-av1"),
        audio_codec="aac",
        audio_bitrate="192k",
        default_quality=75,
    ),
    FormatSpec(
        key="webm",
        label="WebM",
        kind="video",
        extension=".webm",
        video_codecs=("libvpx-vp9", "libsvtav1", "libaom-av1"),
        audio_codec="libopus",
        audio_bitrate="128k",
        default_quality=70,
    ),
    FormatSpec(
        key="mov",
        label="MOV",
        kind="video",
        extension=".mov",
        video_codecs=("libx264", "libx265"),
        audio_codec="aac",
        audio_bitrate="192k",
        default_quality=75,
    ),
    # аудио
    FormatSpec(
        key="mp3",
        label="MP3",
        kind="audio",
        extension=".mp3",
        video_codecs=("libmp3lame",),
        quality_mode="audio",
        default_quality=90,
    ),
    FormatSpec(
        key="flac",
        label="FLAC",
        kind="audio",
        extension=".flac",
        video_codecs=("flac",),
        quality_mode="lossless",
        default_quality=100,
    ),
    FormatSpec(
        key="wav",
        label="WAV",
        kind="audio",
        extension=".wav",
        video_codecs=("pcm_s16le",),
        quality_mode="pcm",
        default_quality=100,
    ),
    FormatSpec(
        key="ogg",
        label="OGG",
        kind="audio",
        extension=".ogg",
        video_codecs=("libvorbis",),
        quality_mode="audio",
        default_quality=80,
    ),
    # изображения
    FormatSpec(
        key="jpg",
        label="JPEG",
        kind="image",
        extension=".jpg",
        quality_mode="image",
        default_quality=85,
    ),
    FormatSpec(
        key="png",
        label="PNG",
        kind="image",
        extension=".png",
        quality_mode="lossless",
        default_quality=100,
    ),
    FormatSpec(
        key="webp",
        label="WebP",
        kind="image",
        extension=".webp",
        quality_mode="image",
        default_quality=85,
    ),
)

KINDS = ("video", "audio", "image")

DEFAULT_FORMAT = {"video": "mp4", "audio": "mp3", "image": "webp"}


def formats_for_kind(kind: str) -> list[FormatSpec]:
    return [spec for spec in FORMATS if spec.kind == kind]


def format_by_key(key: str) -> FormatSpec:
    for spec in FORMATS:
        if spec.key == key:
            return spec
    raise KeyError(f"неизвестный формат: {key}")


def codec_label(encoder: str) -> str:
    return CODEC_LABELS.get(encoder, encoder)


def available_video_codecs(spec: FormatSpec) -> list[tuple[str, str]]:
    """Список (энкодер, подпись), отфильтрованный по возможностям ffmpeg."""
    found = [
        (name, codec_label(name)) for name in spec.video_codecs if has_encoder(name)
    ]
    if found:
        return found
    # ffmpeg не ответил или энкодеры не распознаны — не оставляем список пустым
    return [(name, codec_label(name)) for name in spec.video_codecs]


def audio_encoder(spec: FormatSpec) -> str | None:
    return spec.audio_codec
