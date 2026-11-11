"""Тесты сборки команд ffmpeg и имён выходных файлов."""

from __future__ import annotations

from pathlib import Path

import pytest

from convertly.core.capabilities import ffmpeg_available
from convertly.core.command import (
    ConversionSettings,
    audio_bitrate_for_quality,
    build_command,
    unique_output_path,
)
from convertly.core.formats import available_video_codecs, format_by_key
from convertly.core.probe import MediaInfo

pytestmark = pytest.mark.skipif(
    not ffmpeg_available(), reason="ffmpeg не установлен"
)


def make_info(kind: str = "video", **overrides) -> MediaInfo:
    defaults = {
        "path": Path("input.mp4"),
        "kind": kind,
        "duration": 10.0,
        "width": 1280,
        "height": 720,
        "fps": 30.0,
        "video_codec": "h264",
        "audio_codec": "aac",
        "size": 1000,
        "has_audio": True,
    }
    defaults.update(overrides)
    return MediaInfo(**defaults)


def test_video_command_has_progress_and_encoder() -> None:
    encoder = available_video_codecs(format_by_key("mp4"))[0][0]
    command = build_command(
        make_info(),
        ConversionSettings(format_key="mp4", video_codec=encoder, quality=75),
        Path("out.mp4"),
    )
    assert "-progress" in command
    assert "pipe:1" in command
    assert command[command.index("-c:v") + 1] == encoder

    crf = int(command[command.index("-crf") + 1])
    assert 18 <= crf <= 35
    assert command[-1] == "out.mp4"


def test_drop_audio_removes_audio_stream() -> None:
    command = build_command(
        make_info(),
        ConversionSettings(format_key="mp4", drop_audio=True),
        Path("out.mp4"),
    )
    assert "0:a:0" not in command
    assert "-c:a" not in command


def test_audio_is_kept_by_default() -> None:
    command = build_command(
        make_info(), ConversionSettings(format_key="mp4"), Path("out.mp4")
    )
    assert "0:a:0" in command
    assert command[command.index("-c:a") + 1] == "aac"


def test_resolution_is_not_upscaled() -> None:
    command = build_command(
        make_info(height=480),
        ConversionSettings(format_key="mp4", resolution="1080"),
        Path("out.mp4"),
    )
    assert "-vf" not in command


def test_resolution_scales_big_video() -> None:
    command = build_command(
        make_info(height=2160),
        ConversionSettings(format_key="mp4", resolution="1080"),
        Path("out.mp4"),
    )
    assert command[command.index("-vf") + 1] == "scale=-2:1080"


def test_webm_uses_opus_audio() -> None:
    command = build_command(
        make_info(),
        ConversionSettings(format_key="webm", video_codec="libvpx-vp9"),
        Path("out.webm"),
    )
    assert command[command.index("-c:a") + 1] == "libopus"


def test_audio_bitrate_depends_on_quality() -> None:
    assert audio_bitrate_for_quality(100) == "320k"
    assert audio_bitrate_for_quality(70) == "256k"
    assert audio_bitrate_for_quality(40) == "192k"
    assert audio_bitrate_for_quality(10) == "128k"


def test_image_quality_stays_in_jpeg_range() -> None:
    info = MediaInfo(path=Path("in.png"), kind="image", width=400, height=300, size=10)
    for quality in (0, 50, 100):
        command = build_command(
            info, ConversionSettings(format_key="jpg", quality=quality), Path("o.jpg")
        )
        qscale = int(command[command.index("-q:v") + 1])
        assert 2 <= qscale <= 31


def test_metadata_flag() -> None:
    kept = build_command(
        make_info(), ConversionSettings(copy_metadata=True), Path("o.mp4")
    )
    dropped = build_command(
        make_info(), ConversionSettings(copy_metadata=False), Path("o.mp4")
    )
    assert kept[kept.index("-map_metadata") + 1] == "0"
    assert dropped[dropped.index("-map_metadata") + 1] == "-1"


def test_unique_output_path(tmp_path: Path) -> None:
    (tmp_path / "clip.mp4").write_bytes(b"x")

    first = unique_output_path(tmp_path, "clip", ".mp4")
    assert first.name == "clip (1).mp4"

    second = unique_output_path(tmp_path, "clip", ".mp4", {first})
    assert second.name == "clip (2).mp4"
