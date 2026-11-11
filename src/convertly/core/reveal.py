"""Показ файла в системном файловом менеджере."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def reveal_file(path: Path) -> bool:
    """Открывает папку с выделенным файлом. False — если не получилось."""
    path = path.resolve()
    if not path.exists():
        return False

    if sys.platform.startswith("linux"):
        return _reveal_linux(path)
    if sys.platform == "darwin":
        return _run(["open", "-R", str(path)])
    if sys.platform == "win32":
        return _run(["explorer", f"/select,{path}"])
    return False


def _reveal_linux(path: Path) -> bool:
    """Стандартный DBus-интерфейс, его поддерживают Dolphin, Nautilus, Thunar."""
    if shutil.which("dbus-send") and _run(
        [
            "dbus-send",
            "--session",
            "--dest=org.freedesktop.FileManager1",
            "--type=method_call",
            "/org/freedesktop/FileManager1",
            "org.freedesktop.FileManager1.ShowItems",
            f"array:string:{path.as_uri()}",
            "string:",
        ]
    ):
        return True

    # файловый менеджер не зарегистрировал сервис — пробуем напрямую
    for program in ("dolphin", "nautilus"):
        if shutil.which(program) and _run([program, "--select", str(path)]):
            return True
    return False


def _run(command: list[str]) -> bool:
    try:
        result = subprocess.run(command, capture_output=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0
