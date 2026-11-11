"""Поиск ffmpeg/ffprobe рядом с приложением и в PATH."""

from __future__ import annotations

from pathlib import Path

from convertly.core import binaries


def test_prefers_bundled_binary(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "ffmpeg"
    target.write_bytes(b"")

    monkeypatch.setattr(binaries, "_is_windows", lambda: False)
    monkeypatch.setattr(binaries, "candidate_dirs", lambda: [tmp_path])
    monkeypatch.setattr(binaries.shutil, "which", lambda name: f"/usr/bin/{name}")

    assert binaries.find_binary("ffmpeg") == str(target)


def test_falls_back_to_path(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(binaries, "_is_windows", lambda: False)
    monkeypatch.setattr(binaries, "candidate_dirs", lambda: [tmp_path])
    monkeypatch.setattr(binaries.shutil, "which", lambda name: f"/usr/bin/{name}")

    assert binaries.find_binary("ffmpeg") == "/usr/bin/ffmpeg"


def test_uses_exe_suffix_on_windows(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "ffmpeg.exe"
    target.write_bytes(b"")

    monkeypatch.setattr(binaries, "_is_windows", lambda: True)
    monkeypatch.setattr(binaries, "candidate_dirs", lambda: [tmp_path])
    monkeypatch.setattr(binaries.shutil, "which", lambda name: None)

    assert binaries.find_binary("ffmpeg") == str(target)


def test_returns_none_when_missing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(binaries, "_is_windows", lambda: False)
    monkeypatch.setattr(binaries, "candidate_dirs", lambda: [tmp_path])
    monkeypatch.setattr(binaries.shutil, "which", lambda name: None)

    assert binaries.find_binary("ffmpeg") is None


def test_finds_binary_in_pyinstaller_bundle(tmp_path: Path, monkeypatch) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    target = bin_dir / "ffmpeg"
    target.write_bytes(b"")

    monkeypatch.setattr(binaries, "_is_windows", lambda: False)
    monkeypatch.setattr(binaries.sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.setattr(binaries.shutil, "which", lambda name: None)

    assert binaries.find_binary("ffmpeg") == str(target)


def test_install_hint_depends_on_platform(monkeypatch) -> None:
    from convertly.core import capabilities

    monkeypatch.setattr(capabilities.sys, "platform", "win32")
    assert "winget" in capabilities.install_hint()

    monkeypatch.setattr(capabilities.sys, "platform", "darwin")
    assert "brew" in capabilities.install_hint()

    monkeypatch.setattr(capabilities.sys, "platform", "linux")
    assert "pacman" in capabilities.install_hint()
