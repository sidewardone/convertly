"""Список задач в очереди."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...core.probe import human_size
from ...core.runner import Job, JobStatus
from ..theme import current

KIND_SYMBOLS = {
    "video": "▶",
    "audio": "♫",
    "image": "▣",
}


def plural_files(count: int) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return f"{count} файл"
    if 2 <= count % 10 <= 4 and not 12 <= count % 100 <= 14:
        return f"{count} файла"
    return f"{count} файлов"


def _repolish(widget: QWidget) -> None:
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)


class _ClickableName(QLabel):
    """Имя файла, открывающее папку с результатом после конвертации."""

    clicked = Signal()

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self._clickable = False

    def set_clickable(self, clickable: bool) -> None:
        if clickable == self._clickable:
            return
        self._clickable = clickable
        self.setCursor(Qt.PointingHandCursor if clickable else Qt.ArrowCursor)
        self._apply_hover(False)

    def _apply_hover(self, hovered: bool) -> None:
        active = self._clickable and hovered
        font = self.font()
        font.setUnderline(active)
        self.setFont(font)
        self.setStyleSheet(f"color: {current()['ACCENT']};" if active else "")

    def enterEvent(self, event) -> None:
        self._apply_hover(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._apply_hover(False)
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._clickable and event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class QueueRow(QFrame):
    """Строка сгруппированного списка задач."""

    removeRequested = Signal(int)
    revealRequested = Signal(int)
    kindSelected = Signal(str)

    def __init__(self, job: Job, target: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("queueRow")
        self.setFixedHeight(72)
        self.setAttribute(Qt.WA_Hover, True)
        self.job_id = job.id
        self.kind = job.info.kind

        row = QHBoxLayout(self)
        row.setContentsMargins(14, 10, 10, 10)
        row.setSpacing(12)

        badge = QLabel(KIND_SYMBOLS.get(self.kind, "•"), self)
        badge.setObjectName("kindBadge")
        badge.setProperty("kind", self.kind)
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedSize(38, 38)
        row.addWidget(badge)

        text_box = QVBoxLayout()
        text_box.setSpacing(3)
        text_box.setContentsMargins(0, 0, 0, 0)

        self._name = _ClickableName(job.info.path.name, self)
        self._name.setObjectName("rowName")
        self._name.clicked.connect(lambda: self.revealRequested.emit(self.job_id))

        self._base_meta = job.info.meta_label
        self._meta = QLabel(self._base_meta, self)
        self._meta.setObjectName("rowMeta")
        text_box.addWidget(self._name)
        text_box.addWidget(self._meta)
        row.addLayout(text_box, 1)

        self._target = QLabel(target, self)
        self._target.setObjectName("targetLabel")
        self._target.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._target.setFixedWidth(142)
        row.addWidget(self._target)

        status_box = QVBoxLayout()
        status_box.setSpacing(4)
        status_box.setContentsMargins(0, 0, 0, 0)

        self._status = QLabel("", self)
        self._status.setObjectName("rowStatus")
        self._status.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._status.setFixedHeight(16)
        self._status.setMinimumWidth(150)

        self._bar = QProgressBar(self)
        self._bar.setObjectName("rowProgress")
        self._bar.setRange(0, 100)
        self._bar.setTextVisible(False)
        self._bar.setFixedSize(150, 6)

        status_box.addWidget(self._status)
        status_box.addWidget(self._bar, 0, Qt.AlignRight)
        row.addLayout(status_box)

        self._remove = QPushButton("×", self)
        self._remove.setObjectName("rowRemove")
        self._remove.setFixedSize(24, 24)
        self._remove.setCursor(Qt.PointingHandCursor)
        self._remove.setToolTip("Убрать из очереди")
        self._remove.clicked.connect(lambda: self.removeRequested.emit(self.job_id))
        row.addWidget(self._remove)

        self.refresh(job, target)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.kindSelected.emit(self.kind)
        super().mouseReleaseEvent(event)

    def set_position(self, position: str) -> None:
        self.setProperty("pos", position)
        _repolish(self)

    def set_target(self, target: str) -> None:
        self._target.setText(target)

    def set_locked(self, locked: bool) -> None:
        self._remove.setEnabled(not locked)

    def refresh(self, job: Job, target: str) -> None:
        self.set_target(target)

        can_reveal = job.status is JobStatus.DONE and job.output is not None
        self._name.set_clickable(can_reveal)
        self._name.setToolTip(
            "Открыть папку с файлом" if can_reveal else str(job.info.path)
        )
        self._remove.setVisible(job.status is not JobStatus.RUNNING)

        if job.status == JobStatus.RUNNING:
            speed = f" · {job.speed}" if job.speed else ""
            self._status.setText(f"{job.progress}%{speed}")
            state = "running"
        elif job.status == JobStatus.DONE:
            self._status.setText("✓ Готово")
            state = "done"
            if job.output_size:
                self._meta.setText(f"{self._base_meta} → {human_size(job.output_size)}")
            else:
                self._meta.setText(self._base_meta)
        elif job.status == JobStatus.FAILED:
            self._status.setText("✗ Ошибка")
            state = "failed"
        elif job.status == JobStatus.CANCELLED:
            self._status.setText("Отменено")
            state = "queued"
        else:
            self._status.setText("В очереди")
            state = "queued"

        self._status.setProperty("state", state)
        _repolish(self._status)

        self._bar.setProperty("state", state)
        _repolish(self._bar)
        self._bar.setValue(100 if job.status is JobStatus.DONE else job.progress)

        self.setToolTip(self._tooltip(job))

    @staticmethod
    def _tooltip(job: Job) -> str:
        lines = [str(job.info.path)]

        if job.status is JobStatus.DONE and job.output is not None:
            lines.append(f"Результат: {job.output}")
            if job.output_size:
                line = f"{job.info.size_label} → {human_size(job.output_size)}"
                if job.info.size and job.output_size < job.info.size:
                    saved = round((1 - job.output_size / job.info.size) * 100)
                    line += f" (−{saved}%)"
                lines.append(line)

        if job.error:
            lines.append("")
            lines.append(job.error)

        return "\n".join(lines)


class QueueView(QWidget):
    """Заголовок, счётчик, пустое состояние и список задач в одной карточке."""

    removeRequested = Signal(int)
    revealRequested = Signal(int)
    kindSelected = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._rows: dict[int, QueueRow] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(8)

        title = QLabel("ОЧЕРЕДЬ", self)
        title.setObjectName("sectionTitle")
        self._count = QLabel("", self)
        self._count.setObjectName("countBadge")
        self._count.setVisible(False)

        header.addWidget(title)
        header.addWidget(self._count)
        header.addStretch(1)
        layout.addLayout(header)

        self._empty = QLabel(
            "Пока пусто\nПеретащите файлы сюда или нажмите «Добавить файлы»",
            self,
        )
        self._empty.setObjectName("emptyState")
        self._empty.setAlignment(Qt.AlignCenter)
        self._empty.setMinimumHeight(220)
        layout.addWidget(self._empty, 1)

        self._rows_host = QWidget(self)
        host_layout = QVBoxLayout(self._rows_host)
        host_layout.setContentsMargins(0, 0, 6, 0)
        host_layout.setSpacing(0)

        self._group = QFrame(self._rows_host)
        self._group.setObjectName("queueGroup")
        self._group_layout = QVBoxLayout(self._group)
        self._group_layout.setContentsMargins(0, 0, 0, 0)
        self._group_layout.setSpacing(0)

        host_layout.addWidget(self._group)
        host_layout.addStretch(1)

        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setWidget(self._rows_host)
        self._scroll.setVisible(False)
        layout.addWidget(self._scroll, 1)

    def set_jobs(self, jobs: list[Job], targets: dict[str, str]) -> None:
        while self._group_layout.count():
            item = self._group_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        self._rows.clear()
        total = len(jobs)
        for index, job in enumerate(jobs):
            row = QueueRow(job, targets.get(job.info.kind, ""), self._group)
            row.removeRequested.connect(self.removeRequested)
            row.revealRequested.connect(self.revealRequested)
            row.kindSelected.connect(self.kindSelected)

            if total == 1:
                position = "single"
            elif index == 0:
                position = "first"
            elif index == total - 1:
                position = "last"
            else:
                position = "middle"
            row.set_position(position)

            self._group_layout.addWidget(row)
            if index < total - 1:
                self._group_layout.addWidget(self._separator())

            self._rows[job.id] = row

        has_jobs = bool(jobs)
        self._scroll.setVisible(has_jobs)
        self._empty.setVisible(not has_jobs)
        self._count.setVisible(has_jobs)
        self._count.setText(plural_files(len(jobs)) if has_jobs else "")

    def _separator(self) -> QWidget:
        holder = QWidget(self._group)
        layout = QHBoxLayout(holder)
        layout.setContentsMargins(62, 0, 12, 0)
        layout.setSpacing(0)
        line = QFrame(holder)
        line.setObjectName("rowSeparator")
        line.setFixedHeight(1)
        layout.addWidget(line)
        return holder

    def update_job(self, job: Job, target: str) -> None:
        row = self._rows.get(job.id)
        if row is not None:
            row.refresh(job, target)

    def update_targets(self, kind: str, target: str) -> None:
        for row in self._rows.values():
            if row.kind == kind:
                row.set_target(target)

    def set_locked(self, locked: bool) -> None:
        for row in self._rows.values():
            row.set_locked(locked)
