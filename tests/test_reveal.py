"""Тесты показа файла в файловом менеджере."""

from __future__ import annotations

import subprocess
from pathlib import Path

from convertly.core import reveal as reveal_module
from convertly.core.reveal import reveal_file


class _Result:
    def __init__(self, returncode: int = 0) -> None:
        self.returncode = returncode


def test_missing_file_returns_false(tmp_path: Path) -> None:
    assert reveal_file(tmp_path / "nope.mp4") is False


def test_linux_uses_file_manager1_showitems(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "clip.mp4"
    target.write_bytes(b"x")

    calls: list[list[str]] = []

    def fake_run(command, **_kwargs):
        calls.append(command)
        return _Result(0)

    monkeypatch.setattr(reveal_module.sys, "platform", "linux")
    monkeypatch.setattr(
        reveal_module.shutil, "which", lambda _name: "/usr/bin/dbus-send"
    )
    monkeypatch.setattr(reveal_module.subprocess, "run", fake_run)

    assert reveal_file(target) is True
    assert calls
    assert "org.freedesktop.FileManager1.ShowItems" in calls[0]
    assert any(target.resolve().as_uri() in arg for arg in calls[0])


def test_linux_reports_failure_when_dbus_fails(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "clip.mp4"
    target.write_bytes(b"x")

    monkeypatch.setattr(reveal_module.sys, "platform", "linux")
    monkeypatch.setattr(
        reveal_module.shutil, "which", lambda _name: "/usr/bin/dbus-send"
    )
    monkeypatch.setattr(
        reveal_module.subprocess, "run", lambda *_args, **_kwargs: _Result(1)
    )

    assert reveal_file(target) is False


def test_linux_without_dbus_send_returns_false(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "clip.mp4"
    target.write_bytes(b"x")

    monkeypatch.setattr(reveal_module.sys, "platform", "linux")
    monkeypatch.setattr(reveal_module.shutil, "which", lambda _name: None)

    assert reveal_file(target) is False


def test_macos_uses_open_reveal(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "clip.mp4"
    target.write_bytes(b"x")

    calls: list[list[str]] = []

    def fake_run(command, **_kwargs):
        calls.append(command)
        return _Result(0)

    monkeypatch.setattr(reveal_module.sys, "platform", "darwin")
    monkeypatch.setattr(reveal_module.subprocess, "run", fake_run)

    assert reveal_file(target) is True
    assert calls == [["open", "-R", str(target.resolve())]]


def test_subprocess_error_returns_false(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "clip.mp4"
    target.write_bytes(b"x")

    def broken_run(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd="dbus-send", timeout=10)

    monkeypatch.setattr(reveal_module.sys, "platform", "darwin")
    monkeypatch.setattr(reveal_module.subprocess, "run", broken_run)

    assert reveal_file(target) is False


def test_linux_falls_back_to_dolphin(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "clip.mp4"
    target.write_bytes(b"x")

    calls: list[list[str]] = []

    def fake_run(command, **_kwargs):
        calls.append(command)
        return _Result(0)

    monkeypatch.setattr(reveal_module.sys, "platform", "linux")
    monkeypatch.setattr(
        reveal_module.shutil,
        "which",
        lambda name: "/usr/bin/dolphin" if name == "dolphin" else None,
    )
    monkeypatch.setattr(reveal_module.subprocess, "run", fake_run)

    assert reveal_file(target) is True
    assert calls == [["dolphin", "--select", str(target.resolve())]]
