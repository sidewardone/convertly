"""Тесты сохранения настроек."""

from __future__ import annotations

import json
from pathlib import Path

import convertly.config as config_module
from convertly.config import AppConfig, KindConfig


def test_defaults() -> None:
    config = AppConfig()
    assert config.active_kind == "video"
    assert config.kinds["video"].format_key == "mp4"
    assert config.kinds["audio"].format_key == "mp3"
    assert config.kinds["image"].format_key == "webp"
    assert str(config.output_dir)


def test_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    config = AppConfig(
        output_dir=tmp_path / "out",
        active_kind="audio",
        theme="dark",
        window_width=1234,
        window_height=777,
    )
    config.kinds["video"] = KindConfig(
        format_key="webm",
        video_codec="libvpx-vp9",
        quality=55,
        resolution="720",
        fps="30",
        copy_metadata=False,
        drop_audio=True,
    )
    config.save(path)

    loaded = AppConfig.load(path)
    assert loaded.output_dir == tmp_path / "out"
    assert loaded.active_kind == "audio"
    assert loaded.theme == "dark"
    assert loaded.window_width == 1234
    assert loaded.window_height == 777

    video = loaded.kinds["video"]
    assert video.format_key == "webm"
    assert video.video_codec == "libvpx-vp9"
    assert video.quality == 55
    assert video.resolution == "720"
    assert video.fps == "30"
    assert video.copy_metadata is False
    assert video.drop_audio is True


def test_broken_json_falls_back_to_defaults(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text("{ это не json", encoding="utf-8")
    config = AppConfig.load(path)
    assert config.kinds["video"].format_key == "mp4"
    assert config.active_kind == "video"


def test_invalid_values_are_ignored(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {
                "active_kind": "unknown",
                "theme": "neon",
                "window_width": "big",
                "window_height": -5,
                "kinds": {
                    "video": {
                        "format_key": "mp3",  # аудио-формат для видео не подходит
                        "quality": 500,
                        "resolution": 123,
                        "copy_metadata": "yes",
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    config = AppConfig.load(path)
    assert config.active_kind == "video"
    assert config.theme == "system"
    assert config.window_width == 1140
    assert config.window_height >= 680

    video = config.kinds["video"]
    assert video.format_key == "mp4"
    assert video.quality == 75
    assert video.resolution == "original"
    assert video.copy_metadata is True


def test_config_path_linux(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(config_module.sys, "platform", "linux")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert config_module.config_path() == tmp_path / "convertly" / "config.json"


def test_config_path_windows(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(config_module.sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert config_module.config_path() == tmp_path / "Convertly" / "config.json"


def test_config_path_macos(monkeypatch) -> None:
    monkeypatch.setattr(config_module.sys, "platform", "darwin")
    assert "Application Support/Convertly" in config_module.config_path().as_posix()
