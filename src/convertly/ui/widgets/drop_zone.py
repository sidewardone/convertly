"""Зона перетаскивания файлов: drag&drop и клик для выбора."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from ..theme import current, svg_pixmap


class DropZone(QFrame):
    """Карточка «перетащите файлы сюда»."""

    clicked = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("dropZone")
        self.setMinimumHeight(180)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 18, 24, 18)
        layout.setSpacing(8)

        self._icon = QLabel(self)
        self._icon.setObjectName("dropIcon")
        self._icon.setAlignment(Qt.AlignCenter)
        self._icon.setFixedSize(56, 56)

        title = QLabel("Перетащите файлы сюда", self)
        title.setObjectName("dropTitle")
        title.setAlignment(Qt.AlignCenter)

        hint = QLabel("видео, аудио и изображения · или нажмите, чтобы выбрать", self)
        hint.setObjectName("dropHint")
        hint.setAlignment(Qt.AlignCenter)

        layout.addStretch(1)
        layout.addWidget(self._icon, 0, Qt.AlignHCenter)
        layout.addWidget(title, 0, Qt.AlignHCenter)
        layout.addWidget(hint, 0, Qt.AlignHCenter)
        layout.addStretch(1)

        self.setToolTip("Поддерживаются файлы видео, аудио и изображений")
        self.refresh_theme()

    def refresh_theme(self) -> None:
        self._icon.setPixmap(
            svg_pixmap("arrow-down-to-line.svg", 30, current()["ACCENT"])
        )

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self.rect().contains(
            event.position().toPoint()
        ):
            self.clicked.emit()
        super().mouseReleaseEvent(event)
