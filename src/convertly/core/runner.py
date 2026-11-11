"""Запуск ffmpeg через QProcess: параллельные задачи, прогресс, отмена."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, Signal

from .command import ConversionSettings, build_command
from .probe import MediaInfo


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Job:
    id: int
    info: MediaInfo
    status: JobStatus = JobStatus.QUEUED
    progress: int = 0
    speed: str = ""
    error: str = ""
    output: Path | None = None
    output_size: int = 0


@dataclass
class JobRequest:
    job: Job
    settings: ConversionSettings
    output: Path


class ConversionRunner(QObject):
    """Держит очередь задач и не больше N процессов ffmpeg одновременно."""

    jobStarted = Signal(int)
    jobProgress = Signal(int, int, str)
    jobFinished = Signal(int, bool, str)
    allFinished = Signal()

    def __init__(self, parent: QObject | None = None, parallel: int = 2) -> None:
        super().__init__(parent)
        self.parallel = max(1, parallel)
        self._queue: deque[JobRequest] = deque()
        self._active: dict[int, tuple[QProcess, JobRequest]] = {}
        self._stdout: dict[int, str] = {}
        self._stderr: dict[int, str] = {}
        self._cancelled = False
        self._busy = False

    # API
    def is_running(self) -> bool:
        return self._busy

    def start(self, requests: list[JobRequest]) -> None:
        if not requests or self._busy:
            return
        self._queue = deque(requests)
        self._cancelled = False
        self._busy = True
        self._pump()

    def cancel_all(self) -> None:
        if not self._busy:
            return
        self._cancelled = True

        while self._queue:
            request = self._queue.popleft()
            job = request.job
            job.status = JobStatus.CANCELLED
            job.progress = 0
            self.jobFinished.emit(job.id, False, "Отменено")

        for process, _ in list(self._active.values()):
            process.kill()

        if not self._active:
            self._finish_all()

    # внутреннее
    def _pump(self) -> None:
        while not self._cancelled and self._queue and len(self._active) < self.parallel:
            self._launch(self._queue.popleft())

        if self._busy and not self._active and not self._queue:
            self._finish_all()

    def _finish_all(self) -> None:
        if not self._busy:
            return
        self._busy = False
        self._cancelled = False
        self.allFinished.emit()

    def _launch(self, request: JobRequest) -> None:
        job = request.job
        job.status = JobStatus.RUNNING
        job.progress = 0
        job.speed = ""
        job.error = ""

        try:
            command = build_command(job.info, request.settings, request.output)
        except (KeyError, OSError, RuntimeError) as exc:
            job.status = JobStatus.FAILED
            job.error = str(exc)
            self.jobFinished.emit(job.id, False, job.error)
            return

        try:
            request.output.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            job.status = JobStatus.FAILED
            job.error = f"Не удалось создать папку: {exc}"
            self.jobFinished.emit(job.id, False, job.error)
            return

        process = QProcess(self)
        process.setProgram(command[0])
        process.setArguments(command[1:])
        process.setWorkingDirectory(str(request.output.parent))

        self._active[job.id] = (process, request)
        self._stdout[job.id] = ""
        self._stderr[job.id] = ""

        process.readyReadStandardOutput.connect(
            lambda jid=job.id: self._read_stdout(jid)
        )
        process.readyReadStandardError.connect(
            lambda jid=job.id: self._read_stderr(jid)
        )
        process.finished.connect(
            lambda exit_code, status, jid=job.id: self._on_finished(
                jid, exit_code, status
            )
        )
        process.errorOccurred.connect(
            lambda error, jid=job.id: self._on_error(jid, error)
        )

        self.jobStarted.emit(job.id)
        process.start()

    def _read_stdout(self, job_id: int) -> None:
        entry = self._active.get(job_id)
        if entry is None:
            return
        process, _ = entry
        chunk = bytes(process.readAllStandardOutput()).decode("utf-8", "replace")
        buffer = self._stdout.get(job_id, "") + chunk
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            self._parse_progress(job_id, line.strip())
        self._stdout[job_id] = buffer

    def _read_stderr(self, job_id: int) -> None:
        entry = self._active.get(job_id)
        if entry is None:
            return
        process, _ = entry
        chunk = bytes(process.readAllStandardError()).decode("utf-8", "replace")
        buffer = (self._stderr.get(job_id, "") + chunk)[-4000:]
        self._stderr[job_id] = buffer

    def _parse_progress(self, job_id: int, line: str) -> None:
        entry = self._active.get(job_id)
        if entry is None:
            return
        _, request = entry
        job = request.job

        key, separator, value = line.partition("=")
        if not separator:
            return

        if key in {"out_time_us", "out_time_ms"} and value.isdigit():
            if not job.info.duration:
                return
            seconds = int(value) / 1_000_000
            percent = min(99, int(seconds * 100 / job.info.duration))
            if percent != job.progress:
                job.progress = percent
                self.jobProgress.emit(job_id, percent, job.speed)
        elif key == "speed":
            job.speed = value.strip()

    def _on_finished(self, job_id: int, exit_code: int, status) -> None:
        entry = self._active.pop(job_id, None)
        if entry is None:
            return
        _, request = entry
        job = request.job

        stderr_text = self._stderr.pop(job_id, "")
        self._stdout.pop(job_id, None)

        if self._cancelled:
            job.status = JobStatus.CANCELLED
            job.progress = 0
            self.jobFinished.emit(job_id, False, "Отменено")
        elif (
            exit_code == 0
            and request.output.exists()
            and request.output.stat().st_size > 0
        ):
            job.status = JobStatus.DONE
            job.progress = 100
            job.speed = ""
            job.output = request.output
            job.output_size = request.output.stat().st_size
            self.jobFinished.emit(job_id, True, "")
        else:
            job.status = JobStatus.FAILED
            job.error = _error_message(stderr_text, exit_code)
            self.jobFinished.emit(job_id, False, job.error)

        self._pump()

    def _on_error(self, job_id: int, error) -> None:
        if error != QProcess.ProcessError.FailedToStart:
            return
        entry = self._active.pop(job_id, None)
        if entry is None:
            return
        _, request = entry
        job = request.job
        job.status = JobStatus.FAILED
        job.error = "Не удалось запустить ffmpeg"
        self.jobFinished.emit(job_id, False, job.error)
        self._pump()


def _error_message(stderr_text: str, exit_code: int) -> str:
    lines = [line.strip() for line in stderr_text.splitlines() if line.strip()]
    if not lines:
        return f"ffmpeg завершился с кодом {exit_code}"

    message = _clean_ffmpeg_line(lines[-1])

    known = (
        ("No such file or directory", "Файл не найден или недоступен"),
        ("Permission denied", "Нет доступа к файлу или папке"),
        ("Invalid data found", "Повреждённый или неподдерживаемый файл"),
        ("Unknown encoder", "Выбранный кодек недоступен в установленном ffmpeg"),
        ("Nothing was written", "ffmpeg ничего не записал: проверьте формат и кодек"),
        ("Conversion failed", "Конвертация не удалась"),
    )
    for needle, friendly in known:
        if needle.lower() in message.lower():
            return friendly

    return message[:300]


def _clean_ffmpeg_line(line: str) -> str:
    """Убирает служебный префикс вида «[out#0/webm @ 0x55d1...] »."""
    if line.startswith("["):
        closing = line.find("]")
        if closing != -1:
            return line[closing + 1 :].strip() or line
    return line
