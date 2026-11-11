"""Поиск внешних исполняемых файлов ffmpeg и ffprobe."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


def _is_windows() -> bool:
    return sys.platform == "win32"


def candidate_dirs() -> list[Path]:
    """Где искать бинарники: рядом с приложением, во встроенной папке, в проекте."""
    directories: list[Path] = []

    bundle_dir = getattr(sys, "_MEIPASS", None)
    if bundle_dir:
        bundle = Path(bundle_dir)
        directories += [bundle / "bin", bundle]

    executable_dir = Path(sys.executable).resolve().parent
    directories += [executable_dir, executable_dir / "bin"]

    project_dir = Path(__file__).resolve().parents[3]
    directories += [project_dir, project_dir / "bin", project_dir / "vendor"]

    return directories


def find_binary(name: str) -> str | None:
    """Возвращает путь к бинарнику или None, если его нет."""
    filename = f"{name}.exe" if _is_windows() else name
    for directory in candidate_dirs():
        candidate = directory / filename
        if candidate.is_file():
            return str(candidate)
    return shutil.which(name)
