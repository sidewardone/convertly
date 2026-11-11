"""Панель настроек в стиле macOS System Settings: группы строк и тумблеры."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ...config import KindConfig
from ...core.command import ConversionSettings, audio_bitrate_for_quality
from ...core.formats import (
    DEFAULT_FORMAT,
    available_video_codecs,
    codec_label,
    format_by_key,
    formats_for_kind,
)

RESOLUTIONS = (
    ("Оригинал", "original"),
    ("2160p (4K)", "2160"),
    ("1440p", "1440"),
    ("1080p", "1080"),
    ("720p", "720"),
    ("480p", "480"),
)

FPS_VALUES = (
    ("Оригинал", "original"),
    ("60", "60"),
    ("50", "50"),
    ("30", "30"),
    ("25", "25"),
    ("24", "24"),
)

KIND_TITLES = {"video": "Видео", "audio": "Аудио", "image": "Картинки"}

PRESETS: dict[str, list[tuple[str, dict]]] = {
    "video": [
        ("Пользовательский", {}),
        ("Telegram 1080p", {"format": "mp4", "quality": 70, "resolution": "1080"}),
        ("WebM 720p", {"format": "webm", "quality": 60, "resolution": "720"}),
    ],
    "audio": [
        ("Пользовательский", {}),
        ("MP3 320", {"format": "mp3", "quality": 100}),
        ("FLAC без потерь", {"format": "flac"}),
    ],
    "image": [
        ("Пользовательский", {}),
        ("WebP 80%", {"format": "webp", "quality": 80}),
        ("JPEG 90%", {"format": "jpg", "quality": 90}),
    ],
}


@dataclass
class KindState:
    format_key: str
    video_codec: str | None
    quality: int
    resolution: str = "original"
    fps: str = "original"
    copy_metadata: bool = True
    drop_audio: bool = False


class SettingsPanel(QFrame):
    settingsChanged = Signal(str)
    outputDirRequested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(330)

        self._kind = "video"
        self._syncing = True
        self._states: dict[str, KindState] = {
            "video": KindState(
                format_key=DEFAULT_FORMAT["video"], video_codec="libx264", quality=75
            ),
            "audio": KindState(
                format_key=DEFAULT_FORMAT["audio"], video_codec=None, quality=90
            ),
            "image": KindState(
                format_key=DEFAULT_FORMAT["image"], video_codec=None, quality=85
            ),
        }

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget(scroll)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 6, 0)
        layout.setSpacing(12)

        self._title = QLabel("Настройки вывода", content)
        self._title.setObjectName("panelTitle")
        layout.addWidget(self._title)

        # группа параметров
        group, group_layout = self._make_group(content)

        self._preset_combo = QComboBox(group)
        self._preset_combo.currentIndexChanged.connect(self._on_preset_changed)

        self._format_combo = QComboBox(group)
        self._format_combo.currentIndexChanged.connect(self._on_format_changed)

        self._codec_combo = QComboBox(group)
        self._codec_combo.currentIndexChanged.connect(self._on_codec_changed)

        self._quality_slider = QSlider(Qt.Horizontal, group)
        self._quality_slider.setRange(0, 100)
        self._quality_slider.setSingleStep(5)
        self._quality_slider.valueChanged.connect(self._on_quality_changed)

        self._quality_value = QLabel("", group)
        self._quality_value.setObjectName("qualityValue")
        self._quality_value.setMinimumWidth(58)
        self._quality_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self._resolution_combo = QComboBox(group)
        for label, value in RESOLUTIONS:
            self._resolution_combo.addItem(label, value)
        self._resolution_combo.currentIndexChanged.connect(self._on_resolution_changed)

        self._fps_combo = QComboBox(group)
        for label, value in FPS_VALUES:
            self._fps_combo.addItem(label, value)
        self._fps_combo.currentIndexChanged.connect(self._on_fps_changed)

        for combo in (
            self._preset_combo,
            self._format_combo,
            self._codec_combo,
            self._resolution_combo,
            self._fps_combo,
        ):
            combo.setFixedWidth(176)

        self._add_row(group, group_layout, "Пресет", self._preset_combo)
        self._add_row(group, group_layout, "Формат", self._format_combo)
        self._add_row(group, group_layout, "Кодек", self._codec_combo)
        self._add_row(group, group_layout, "Качество", self._quality_control(group))
        self._add_row(group, group_layout, "Разрешение", self._resolution_combo)
        self._add_row(group, group_layout, "Частота кадров", self._fps_combo, last=True)
        layout.addWidget(group)

        # папка вывода
        folder_group, folder_layout = self._make_group(content)
        header = QWidget(folder_group)
        header.setFixedHeight(40)
        header_row = QHBoxLayout(header)
        header_row.setContentsMargins(12, 4, 12, 4)
        header_row.setSpacing(8)
        folder_title = QLabel("Папка вывода", header)
        folder_title.setObjectName("fieldLabel")
        change = QPushButton("Изменить", header)
        change.setObjectName("linkButton")
        change.setCursor(Qt.PointingHandCursor)
        change.clicked.connect(self.outputDirRequested)
        header_row.addWidget(folder_title, 1)
        header_row.addWidget(change, 0, Qt.AlignRight | Qt.AlignVCenter)
        folder_layout.addWidget(header)

        self._path_label = QLabel(folder_group)
        self._path_label.setObjectName("pathField")
        path_holder = QWidget(folder_group)
        path_row = QHBoxLayout(path_holder)
        path_row.setContentsMargins(12, 0, 12, 12)
        path_row.setSpacing(0)
        path_row.addWidget(self._path_label)
        folder_layout.addWidget(path_holder)
        layout.addWidget(folder_group)

        # переключатели
        switch_group, switch_layout = self._make_group(content)
        self._meta_check = QCheckBox(switch_group)
        self._meta_check.setCursor(Qt.PointingHandCursor)
        self._meta_check.toggled.connect(self._on_option_changed)
        self._audio_check = QCheckBox(switch_group)
        self._audio_check.setCursor(Qt.PointingHandCursor)
        self._audio_check.toggled.connect(self._on_option_changed)

        self._meta_row, self._meta_sep = self._add_row(
            switch_group, switch_layout, "Сохранять метаданные", self._meta_check
        )
        self._audio_row, _ = self._add_row(
            switch_group, switch_layout, "Удалить звук", self._audio_check, last=True
        )
        layout.addWidget(switch_group)

        layout.addStretch(1)

        hint = QLabel("Параметры применяются к выбранному типу файлов", content)
        hint.setObjectName("panelHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        scroll.setWidget(content)
        outer.addWidget(scroll)

        self._syncing = False
        self._load_kind("video")

    # API
    @property
    def active_kind(self) -> str:
        return self._kind

    def export_kinds(self) -> dict[str, KindConfig]:
        return {
            kind: KindConfig(
                format_key=state.format_key,
                video_codec=state.video_codec,
                quality=state.quality,
                resolution=state.resolution,
                fps=state.fps,
                copy_metadata=state.copy_metadata,
                drop_audio=state.drop_audio,
            )
            for kind, state in self._states.items()
        }

    def import_kinds(
        self, kinds: dict[str, KindConfig], active_kind: str = "video"
    ) -> None:
        for kind, config in kinds.items():
            if kind not in self._states:
                continue
            state = self._states[kind]
            state.format_key = config.format_key
            state.video_codec = config.video_codec
            state.quality = config.quality
            state.resolution = config.resolution
            state.fps = config.fps
            state.copy_metadata = config.copy_metadata
            state.drop_audio = config.drop_audio

        self._load_kind(active_kind if active_kind in self._states else "video")

    def set_active_kind(self, kind: str) -> None:
        if kind in self._states and kind != self._kind:
            self._load_kind(kind)

    def settings_for(self, kind: str) -> ConversionSettings:
        state = self._states[kind]
        spec = format_by_key(state.format_key)
        return ConversionSettings(
            format_key=state.format_key,
            video_codec=state.video_codec if spec.kind == "video" else None,
            quality=100 if spec.lossless else state.quality,
            resolution=state.resolution,
            fps=state.fps,
            copy_metadata=state.copy_metadata,
            drop_audio=state.drop_audio,
        )

    def target_label(self, kind: str) -> str:
        state = self._states[kind]
        spec = format_by_key(state.format_key)

        if spec.kind == "video":
            codecs = dict(available_video_codecs(spec))
            codec = codecs.get(state.video_codec or "", "")
            return f"{spec.label} · {codec}" if codec else spec.label
        if spec.kind == "audio":
            if spec.quality_mode == "audio":
                return f"{spec.label} · {audio_bitrate_for_quality(state.quality)}"
            return spec.label
        if spec.lossless:
            return spec.label
        return f"{spec.label} · {state.quality}%"

    def set_output_dir(self, path: Path) -> None:
        self._output_dir = path
        try:
            shown = "~/" + str(path.relative_to(Path.home()))
        except ValueError:
            shown = str(path)
        self._path_label.setText(shown)
        self._path_label.setToolTip(str(path))

    # внутреннее
    def _current_spec(self):
        return format_by_key(self._states[self._kind].format_key)

    def _load_kind(self, kind: str, preset_index: int = 0) -> None:
        self._kind = kind
        state = self._states[kind]
        self._syncing = True
        try:
            self._title.setText(f"Настройки · {KIND_TITLES[kind]}")

            self._preset_combo.clear()
            for name, _ in PRESETS[kind]:
                self._preset_combo.addItem(name)
            self._preset_combo.setCurrentIndex(preset_index)

            self._format_combo.clear()
            for spec in formats_for_kind(kind):
                self._format_combo.addItem(spec.label, spec.key)
            format_index = self._format_combo.findData(state.format_key)
            self._format_combo.setCurrentIndex(max(0, format_index))

            self._reload_codecs(state)
            self._quality_slider.setValue(state.quality)
            self._update_quality_label()

            self._set_combo_data(self._resolution_combo, state.resolution)
            self._set_combo_data(self._fps_combo, state.fps)

            self._meta_check.setChecked(state.copy_metadata)
            self._audio_check.setChecked(state.drop_audio)
        finally:
            self._syncing = False

        self._update_enabled()

    def _reload_codecs(self, state: KindState) -> None:
        spec = self._current_spec()
        self._codec_combo.clear()

        if spec.kind == "video":
            for encoder, label in available_video_codecs(spec):
                self._codec_combo.addItem(label, encoder)
            index = self._codec_combo.findData(state.video_codec)
            index = max(index, 0)
            self._codec_combo.setCurrentIndex(index)
            state.video_codec = self._codec_combo.currentData()
        elif spec.kind == "audio":
            encoder = spec.audio_encoder
            self._codec_combo.addItem(codec_label(encoder), encoder)
        else:
            self._codec_combo.addItem("—", None)

    @staticmethod
    def _set_combo_data(combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        combo.setCurrentIndex(max(0, index))

    def _update_enabled(self) -> None:
        spec = self._current_spec()
        is_video = spec.kind == "video"

        self._codec_combo.setEnabled(is_video)
        self._resolution_combo.setEnabled(spec.kind in {"video", "image"})
        self._fps_combo.setEnabled(is_video)
        self._quality_slider.setEnabled(not spec.lossless)
        self._audio_check.setEnabled(is_video)
        self._audio_row.setVisible(is_video)
        self._meta_sep.setVisible(is_video)

    def _update_quality_label(self) -> None:
        spec = self._current_spec()
        value = self._quality_slider.value()
        if spec.lossless:
            self._quality_value.setText("без потерь")
        elif spec.kind == "audio":
            self._quality_value.setText(audio_bitrate_for_quality(value))
        else:
            self._quality_value.setText(f"{value}%")

    # слоты
    def _on_format_changed(self, _index: int) -> None:
        if self._syncing:
            return
        state = self._states[self._kind]
        key = self._format_combo.currentData()
        if not key:
            return
        state.format_key = key
        state.quality = format_by_key(key).default_quality

        self._syncing = True
        try:
            self._reload_codecs(state)
            self._quality_slider.setValue(state.quality)
            self._update_quality_label()
            self._preset_combo.setCurrentIndex(0)
        finally:
            self._syncing = False

        self._update_enabled()
        self.settingsChanged.emit(self._kind)

    def _on_codec_changed(self, _index: int) -> None:
        if self._syncing:
            return
        self._states[self._kind].video_codec = self._codec_combo.currentData()
        self.settingsChanged.emit(self._kind)

    def _on_quality_changed(self, value: int) -> None:
        if self._syncing:
            return
        self._states[self._kind].quality = value
        self._update_quality_label()
        self.settingsChanged.emit(self._kind)

    def _on_resolution_changed(self, _index: int) -> None:
        if self._syncing:
            return
        self._states[self._kind].resolution = self._resolution_combo.currentData()
        self.settingsChanged.emit(self._kind)

    def _on_fps_changed(self, _index: int) -> None:
        if self._syncing:
            return
        self._states[self._kind].fps = self._fps_combo.currentData()
        self.settingsChanged.emit(self._kind)

    def _on_option_changed(self, _checked: bool) -> None:
        if self._syncing:
            return
        state = self._states[self._kind]
        state.copy_metadata = self._meta_check.isChecked()
        state.drop_audio = self._audio_check.isChecked()
        self.settingsChanged.emit(self._kind)

    def _on_preset_changed(self, index: int) -> None:
        if self._syncing or index <= 0:
            return
        _, overrides = PRESETS[self._kind][index]
        if not overrides:
            return

        state = self._states[self._kind]
        if "format" in overrides:
            state.format_key = overrides["format"]
        if "quality" in overrides:
            state.quality = overrides["quality"]
        if "resolution" in overrides:
            state.resolution = overrides["resolution"]

        self._load_kind(self._kind, preset_index=index)
        self.settingsChanged.emit(self._kind)

    # вид
    def _make_group(self, parent: QWidget) -> tuple[QFrame, QVBoxLayout]:
        group = QFrame(parent)
        group.setObjectName("settingsGroup")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        return group, layout

    def _add_row(
        self,
        group: QWidget,
        layout: QVBoxLayout,
        label_text: str,
        control: QWidget,
        *,
        last: bool = False,
    ) -> tuple[QWidget, QWidget | None]:
        row = QWidget(group)
        row.setFixedHeight(40)
        h = QHBoxLayout(row)
        h.setContentsMargins(12, 4, 12, 4)
        h.setSpacing(8)

        label = QLabel(label_text, row)
        label.setObjectName("fieldLabel")
        h.addWidget(label, 1)
        h.addWidget(control, 0, Qt.AlignRight | Qt.AlignVCenter)

        layout.addWidget(row)
        separator = None
        if not last:
            separator = self._separator(group)
            layout.addWidget(separator)
        return row, separator

    def _separator(self, parent: QWidget) -> QWidget:
        holder = QWidget(parent)
        layout = QHBoxLayout(holder)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(0)
        line = QFrame(holder)
        line.setObjectName("rowSeparator")
        line.setFixedHeight(1)
        layout.addWidget(line)
        return holder

    def _quality_control(self, parent: QWidget) -> QWidget:
        box = QWidget(parent)
        box.setFixedWidth(176)
        row = QHBoxLayout(box)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        row.addWidget(self._quality_slider, 1)
        row.addWidget(self._quality_value, 0, Qt.AlignRight | Qt.AlignVCenter)
        return box
