"""Какие энкодеры реально доступны в установленном ffmpeg."""

from __future__ import annotations

import functools
import re
import subprocess
import sys

from .binaries import find_binary

_ENCODER_LINE = re.compile(r"^\s[VASFXBD.]{6}\s+(\S+)")


def ffmpeg_path() -> str | None:
    return find_binary("ffmpeg")


def install_hint() -> str:
    if sys.platform == "win32":
        return "winget install Gyan.FFmpeg"
    if sys.platform == "darwin":
        return "brew install ffmpeg"
    return "sudo pacman -S ffmpeg"


def ffmpeg_available() -> bool:
    return ffmpeg_path() is not None


@functools.lru_cache(maxsize=1)
def available_encoders() -> frozenset[str]:
    executable = ffmpeg_path()
    if not executable:
        return frozenset()
    try:
        result = subprocess.run(
            [executable, "-hide_banner", "-encoders"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return frozenset()

    names = set()
    for line in result.stdout.splitlines():
        match = _ENCODER_LINE.match(line)
        if match:
            names.add(match.group(1))
    return frozenset(names)


def has_encoder(name: str) -> bool:
    return name in available_encoders()


@functools.lru_cache(maxsize=1)
def ffmpeg_version() -> str:
    executable = ffmpeg_path()
    if not executable:
        return ""
    try:
        result = subprocess.run(
            [executable, "-version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    first_line = (result.stdout or "").splitlines()[0] if result.stdout else ""
    match = re.search(r"ffmpeg version (\S+)", first_line)
    return match.group(1) if match else ""
