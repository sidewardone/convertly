"""Фоновое чтение файлов через ffprobe, чтобы не блокировать интерфейс."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Signal

from .probe import MediaInfo, ProbeError, probe


class ProbeWorker(QObject):
    """Сигналы готового результата (испускаются из фонового потока)."""

    finished = Signal(list, list)  # list[MediaInfo], list[tuple[str, str]]


class ProbeTask(QRunnable):
    def __init__(self, paths: list[Path], worker: ProbeWorker) -> None:
        super().__init__()
        self._paths = paths
        self._worker = worker

    def run(self) -> None:
        infos: list[MediaInfo] = []
        errors: list[tuple[str, str]] = []
        for path in self._paths:
            try:
                infos.append(probe(path))
            except ProbeError as exc:
                errors.append((str(path), str(exc)))
        self._worker.finished.emit(infos, errors)
