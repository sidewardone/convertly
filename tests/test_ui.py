"""Смоук-тесты главного окна: добавление файлов, конвертация, сохранение настроек."""

from __future__ import annotations

from pathlib import Path

import pytest

from convertly.config import AppConfig
from convertly.core.runner import JobStatus


@pytest.fixture
def isolated_config(tmp_path: Path, monkeypatch) -> Path:
    """Уводит XDG_CONFIG_HOME в tmp, чтобы не трогать настройки пользователя."""
    config_home = tmp_path / "config"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    monkeypatch.setenv("APPDATA", str(config_home))
    return config_home


def test_window_adds_files_and_converts(qtbot, isolated_config, sample_video, tmp_path):
    from convertly.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    window._output_dir = tmp_path / "out"
    window._panel.set_output_dir(window._output_dir)

    window.add_paths([sample_video])
    qtbot.waitUntil(lambda: not window._probe_busy, timeout=15000)

    assert len(window._jobs) == 1
    assert window._jobs[0].info.kind == "video"
    assert window._start_button.isEnabled()

    with qtbot.waitSignal(window._runner.allFinished, timeout=60000):
        window._on_primary_clicked()

    assert window._jobs[0].status is JobStatus.DONE
    assert (tmp_path / "out" / "sample.mp4").exists()
    assert not window._open_folder_button.isHidden()


def test_window_rejects_duplicates(qtbot, isolated_config, sample_video):
    from convertly.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)

    window.add_paths([sample_video])
    qtbot.waitUntil(lambda: not window._probe_busy, timeout=15000)
    window.add_paths([sample_video])
    qtbot.waitUntil(lambda: not window._probe_busy, timeout=15000)

    assert len(window._jobs) == 1


def test_window_saves_settings_on_close(qtbot, isolated_config, tmp_path):
    from convertly.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)

    window._output_dir = tmp_path / "my_output"
    window._panel.set_output_dir(window._output_dir)
    window._panel.set_active_kind("audio")
    window.close()

    from convertly.config import config_path

    config = AppConfig.load(config_path())
    assert config.output_dir == tmp_path / "my_output"
    assert config.active_kind == "audio"


def test_window_removes_single_file(qtbot, isolated_config, sample_video, sample_audio):
    from convertly.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)

    window.add_paths([sample_video, sample_audio])
    qtbot.waitUntil(lambda: not window._probe_busy, timeout=15000)
    assert len(window._jobs) == 2

    removed_id = window._jobs[0].id
    window.remove_job(removed_id)

    assert len(window._jobs) == 1
    assert window._jobs[0].id != removed_id


def test_reveal_job_falls_back_to_folder(
    qtbot, isolated_config, sample_video, tmp_path, monkeypatch
):
    from convertly.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    window.add_paths([sample_video])
    qtbot.waitUntil(lambda: not window._probe_busy, timeout=15000)

    job = window._jobs[0]
    assert window._queue._rows[job.id]._name._clickable is False
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    job.output = output_dir / "sample.mp4"
    job.output.write_bytes(b"x")
    job.output_size = 1
    job.status = JobStatus.DONE
    window._queue.update_job(job, window._panel.target_label("video"))

    row = window._queue._rows[job.id]
    assert row._name._clickable is True

    opened: list[str] = []

    class FakeDesktopServices:
        @staticmethod
        def openUrl(url) -> None:
            opened.append(url.toLocalFile())

    monkeypatch.setattr("convertly.ui.main_window.reveal_file", lambda _path: False)
    monkeypatch.setattr(
        "convertly.ui.main_window.QDesktopServices", FakeDesktopServices
    )

    window.reveal_job(job.id)
    assert [Path(item) for item in opened] == [output_dir]


def test_theme_switch_persists(qtbot, isolated_config):
    from convertly.config import AppConfig
    from convertly.ui.main_window import MainWindow
    from convertly.ui.theme import current

    window = MainWindow()
    qtbot.addWidget(window)

    window._on_theme_changed("dark")
    assert window._config.theme == "dark"
    assert current()["BG"] == "#1c1c1e"

    window._on_theme_changed("light")
    assert current()["BG"] == "#f5f5f7"

    from convertly.config import config_path

    loaded = AppConfig.load(config_path())
    assert loaded.theme == "light"


def test_settings_follow_added_file_kind(
    qtbot, isolated_config, sample_video, sample_audio
):
    from convertly.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)

    window.add_paths([sample_video])
    qtbot.waitUntil(lambda: not window._probe_busy, timeout=15000)
    assert window._panel.active_kind == "video"

    window.add_paths([sample_audio])
    qtbot.waitUntil(lambda: not window._probe_busy, timeout=15000)
    assert window._panel.active_kind == "audio"


def test_help_dialog_lists_hotkeys(qtbot, isolated_config):
    from convertly.ui.help_dialog import HelpDialog

    dialog = HelpDialog()
    qtbot.addWidget(dialog)

    text = dialog.browser.toPlainText()
    assert "Ctrl + O" in text
    assert "F1" in text
    assert "Горячие клавиши" in text


def test_shortcuts_installed(qtbot, isolated_config):
    from convertly.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    assert len(window._shortcuts) == 6
