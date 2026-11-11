"""Тесты ffprobe на реальных файлах."""

from __future__ import annotations

from pathlib import Path

from convertly.core.probe import probe


def test_video(sample_video: Path) -> None:
    info = probe(sample_video)
    assert info.kind == "video"
    assert info.width == 320
    assert info.height == 240
    assert info.has_audio
    assert info.audio_codec == "aac"
    assert info.duration and 1.0 < info.duration < 1.5
    assert "КБ" in info.meta_label or "МБ" in info.meta_label


def test_audio(sample_audio: Path) -> None:
    info = probe(sample_audio)
    assert info.kind == "audio"
    assert info.has_audio
    assert not info.width
    assert info.duration and 0.5 < info.duration < 1.5
    assert "WAV" in info.meta_label


def test_image(sample_image: Path) -> None:
    info = probe(sample_image)
    assert info.kind == "image"
    assert info.width == 400
    assert info.height == 300
    assert not info.has_audio
