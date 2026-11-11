"""Сегментированный переключатель в стиле macOS."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QPushButton, QWidget


class SegmentedControl(QFrame):
    """Ряд связанных кнопок с одним выбранным значением."""

    changed = Signal(str)

    def __init__(
        self,
        options: list[tuple[str, str]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("segmented")
        self._options = list(options)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: dict[str, QPushButton] = {}

        for index, (key, label) in enumerate(self._options):
            button = QPushButton(label, self)
            button.setObjectName("segment")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            self._group.addButton(button, index)
            layout.addWidget(button)
            self._buttons[key] = button

        self._group.idClicked.connect(self._on_clicked)

    def value(self) -> str:
        for key, button in self._buttons.items():
            if button.isChecked():
                return key
        return self._options[0][0]

    def set_value(self, key: str) -> None:
        button = self._buttons.get(key)
        if button is not None and not button.isChecked():
            button.setChecked(True)

    def _on_clicked(self, index: int) -> None:
        if 0 <= index < len(self._options):
            self.changed.emit(self._options[index][0])
