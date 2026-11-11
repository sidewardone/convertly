"""Интеграционные тесты запуска ffmpeg через ConversionRunner."""

from __future__ import annotations

from pathlib import Path

import convertly.core.runner as runner_module
from convertly.core.command import ConversionSettings
from convertly.core.probe import MediaInfo, probe
from convertly.core.runner import ConversionRunner, Job, JobRequest, JobStatus


def test_successful_conversion(qtbot, sample_video: Path, tmp_path: Path) -> None:
    job = Job(id=1, info=probe(sample_video))
    runner = ConversionRunner(parallel=1)
    request = JobRequest(
        job,
        ConversionSettings(format_key="mp4", video_codec="libx264", quality=70),
        tmp_path / "out.mp4",
    )

    with qtbot.waitSignal(runner.allFinished, timeout=30000):
        runner.start([request])

    assert job.status is JobStatus.DONE
    assert job.progress == 100
    assert job.output_size == (tmp_path / "out.mp4").stat().st_size
    assert job.output_size > 0


def test_audio_conversion(qtbot, sample_audio: Path, tmp_path: Path) -> None:
    job = Job(id=1, info=probe(sample_audio))
    runner = ConversionRunner(parallel=1)
    request = JobRequest(
        job, ConversionSettings(format_key="mp3", quality=90), tmp_path / "out.mp3"
    )

    with qtbot.waitSignal(runner.allFinished, timeout=30000):
        runner.start([request])

    assert job.status is JobStatus.DONE
    assert (tmp_path / "out.mp3").stat().st_size > 0


def test_failure_reports_message(
    qtbot, sample_video: Path, tmp_path: Path, monkeypatch
) -> None:
    def broken_command(*_args, **_kwargs):
        raise RuntimeError("Тестовая ошибка сборки команды")

    monkeypatch.setattr(runner_module, "build_command", broken_command)

    job = Job(id=1, info=probe(sample_video))
    runner = ConversionRunner(parallel=1)

    with qtbot.waitSignal(runner.allFinished, timeout=10000):
        runner.start([JobRequest(job, ConversionSettings(), tmp_path / "out.mp4")])

    assert job.status is JobStatus.FAILED
    assert "Тестовая ошибка" in job.error


def test_cancel_stops_running_jobs(
    qtbot, sample_video: Path, tmp_path: Path, monkeypatch
) -> None:
    def slow_command(*_args, **_kwargs):
        return ["sleep", "5"]

    monkeypatch.setattr(runner_module, "build_command", slow_command)

    jobs = [Job(id=index, info=probe(sample_video)) for index in (1, 2)]
    requests = [
        JobRequest(
            job, ConversionSettings(format_key="mp4"), tmp_path / f"out{job.id}.mp4"
        )
        for job in jobs
    ]

    runner = ConversionRunner(parallel=2)
    runner.start(requests)
    qtbot.waitUntil(
        lambda: all(job.status is JobStatus.RUNNING for job in jobs), timeout=5000
    )

    with qtbot.waitSignal(runner.allFinished, timeout=10000):
        runner.cancel_all()

    assert all(job.status is JobStatus.CANCELLED for job in jobs)
    assert not runner.is_running()


def test_missing_ffmpeg_is_reported(monkeypatch, tmp_path: Path) -> None:
    info = MediaInfo(
        path=tmp_path / "in.mp4", kind="video", duration=1.0, has_audio=False
    )
    job = Job(id=1, info=info)

    monkeypatch.setattr("convertly.core.command.ffmpeg_path", lambda: None)
    runner = ConversionRunner(parallel=1)

    finished: list[tuple[int, bool, str]] = []
    runner.jobFinished.connect(lambda jid, ok, msg: finished.append((jid, ok, msg)))
    runner.start([JobRequest(job, ConversionSettings(), tmp_path / "out.mp4")])

    assert job.status is JobStatus.FAILED
    assert finished and finished[0][1] is False
    assert "ffmpeg" in finished[0][2]
