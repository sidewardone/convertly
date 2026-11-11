"""Общие фикстуры: тестовые медиафайлы и Qt в offscreen-режиме."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

FFMPEG = shutil.which("ffmpeg")
requires_ffmpeg = pytest.mark.skipif(
    FFMPEG is None, reason="ffmpeg не установлен в системе"
)


@pytest.fixture(scope="session")
def media_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Небольшие видео, аудио и картинка, созданные ffmpeg."""
    if FFMPEG is None:
        pytest.skip("ffmpeg не установлен в системе")

    directory = tmp_path_factory.mktemp("media")

    subprocess.run(
        [
            FFMPEG,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=320x240:rate=25",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440",
            "-t",
            "1.2",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(directory / "sample.mp4"),
        ],
        check=True,
    )
    subprocess.run(
        [
            FFMPEG,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440",
            "-t",
            "1",
            str(directory / "sample.wav"),
        ],
        check=True,
    )
    subprocess.run(
        [
            FFMPEG,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=400x300",
            "-frames:v",
            "1",
            str(directory / "sample.png"),
        ],
        check=True,
    )
    return directory


@pytest.fixture
def sample_video(media_dir: Path) -> Path:
    return media_dir / "sample.mp4"


@pytest.fixture
def sample_audio(media_dir: Path) -> Path:
    return media_dir / "sample.wav"


@pytest.fixture
def sample_image(media_dir: Path) -> Path:
    return media_dir / "sample.png"
