"""Сохранение настроек между запусками."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .core.formats import DEFAULT_FORMAT, format_by_key

APP_NAME = "convertly"
KINDS = ("video", "audio", "image")
MIN_WINDOW_WIDTH = 1000
MIN_WINDOW_HEIGHT = 680


def default_output_dir() -> Path:
    if sys.platform == "win32":
        return Path.home() / "Videos" / "Convertly"
    if sys.platform == "darwin":
        return Path.home() / "Movies" / "Convertly"
    return Path.home() / "Videos" / "Convertly"


def config_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA")
        root = Path(base) if base else Path.home() / "AppData" / "Roaming"
        return root / "Convertly"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Convertly"

    base = os.environ.get("XDG_CONFIG_HOME")
    root = Path(base) if base else Path.home() / ".config"
    return root / APP_NAME


def config_path() -> Path:
    return config_dir() / "config.json"


@dataclass
class KindConfig:
    """Настройки вывода для одного типа файлов."""

    format_key: str
    video_codec: str | None = None
    quality: int = 75
    resolution: str = "original"
    fps: str = "original"
    copy_metadata: bool = True
    drop_audio: bool = False

    @classmethod
    def default_for(cls, kind: str) -> KindConfig:
        defaults = {
            "video": cls(
                format_key=DEFAULT_FORMAT["video"], video_codec="libx264", quality=75
            ),
            "audio": cls(
                format_key=DEFAULT_FORMAT["audio"], video_codec=None, quality=90
            ),
            "image": cls(
                format_key=DEFAULT_FORMAT["image"], video_codec=None, quality=85
            ),
        }
        return defaults.get(kind, defaults["video"])

    @classmethod
    def from_dict(cls, kind: str, raw: object) -> KindConfig:
        base = cls.default_for(kind)
        if not isinstance(raw, dict):
            return base

        format_key = base.format_key
        raw_format = raw.get("format_key")
        if isinstance(raw_format, str):
            try:
                spec = format_by_key(raw_format)
            except KeyError:
                spec = None
            if spec is not None and spec.kind == kind:
                format_key = spec.key

        raw_codec = raw.get("video_codec")
        if isinstance(raw_codec, str) and raw_codec:
            video_codec: str | None = raw_codec
        elif raw_codec is None or kind != "video":
            video_codec = None
        else:
            video_codec = base.video_codec

        quality = raw.get("quality")
        if (
            not isinstance(quality, int)
            or isinstance(quality, bool)
            or not 0 <= quality <= 100
        ):
            quality = base.quality

        resolution = raw.get("resolution")
        if not isinstance(resolution, str) or not resolution:
            resolution = base.resolution

        fps = raw.get("fps")
        if not isinstance(fps, str) or not fps:
            fps = base.fps

        copy_metadata = raw.get("copy_metadata")
        if not isinstance(copy_metadata, bool):
            copy_metadata = base.copy_metadata

        drop_audio = raw.get("drop_audio")
        if not isinstance(drop_audio, bool):
            drop_audio = base.drop_audio

        return cls(
            format_key=format_key,
            video_codec=video_codec,
            quality=quality,
            resolution=resolution,
            fps=fps,
            copy_metadata=copy_metadata,
            drop_audio=drop_audio,
        )


@dataclass
class AppConfig:
    """Все сохраняемые настройки приложения."""

    output_dir: Path = field(default_factory=default_output_dir)
    active_kind: str = "video"
    kinds: dict[str, KindConfig] = field(default_factory=dict)
    theme: str = "system"
    window_width: int = 1140
    window_height: int = 760

    def __post_init__(self) -> None:
        for kind in KINDS:
            self.kinds.setdefault(kind, KindConfig.default_for(kind))

    @classmethod
    def load(cls, path: Path | None = None) -> AppConfig:
        target = path or config_path()
        try:
            raw = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls()

        if not isinstance(raw, dict):
            return cls()

        config = cls()

        output_dir = raw.get("output_dir")
        if isinstance(output_dir, str) and output_dir.strip():
            config.output_dir = Path(output_dir).expanduser()

        active_kind = raw.get("active_kind")
        if active_kind in KINDS:
            config.active_kind = active_kind

        theme = raw.get("theme")
        if theme in {"light", "dark", "system"}:
            config.theme = theme

        kinds = raw.get("kinds")
        if isinstance(kinds, dict):
            for kind in KINDS:
                config.kinds[kind] = KindConfig.from_dict(kind, kinds.get(kind))

        width = raw.get("window_width")
        if isinstance(width, int) and not isinstance(width, bool):
            config.window_width = max(MIN_WINDOW_WIDTH, width)

        height = raw.get("window_height")
        if isinstance(height, int) and not isinstance(height, bool):
            config.window_height = max(MIN_WINDOW_HEIGHT, height)

        return config

    def to_dict(self) -> dict:
        return {
            "output_dir": str(self.output_dir),
            "active_kind": self.active_kind,
            "theme": self.theme,
            "window_width": self.window_width,
            "window_height": self.window_height,
            "kinds": {
                kind: {
                    "format_key": state.format_key,
                    "video_codec": state.video_codec,
                    "quality": state.quality,
                    "resolution": state.resolution,
                    "fps": state.fps,
                    "copy_metadata": state.copy_metadata,
                    "drop_audio": state.drop_audio,
                }
                for kind, state in self.kinds.items()
            },
        }

    def save(self, path: Path | None = None) -> None:
        target = path or config_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + ".tmp")
        temporary.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(target)
