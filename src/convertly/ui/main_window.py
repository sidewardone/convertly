"""Главное окно Convertly: шапка, очередь, настройки, запуск конвертации."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThreadPool, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStatusBar,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from .. import __version__
from ..config import AppConfig
from ..core.capabilities import ffmpeg_available, ffmpeg_version, install_hint
from ..core.command import unique_output_path
from ..core.formats import format_by_key
from ..core.probe import SUPPORTED_EXTENSIONS
from ..core.prober import ProbeTask, ProbeWorker
from ..core.reveal import reveal_file
from ..core.runner import ConversionRunner, Job, JobRequest, JobStatus
from .help_dialog import HelpDialog
from .theme import app_icon_pixmap, apply_theme
from .widgets.drop_zone import DropZone
from .widgets.queue_view import QueueView
from .widgets.segmented import SegmentedControl
from .widgets.settings_panel import SettingsPanel

MAX_DROPPED_FILES = 500

THEME_OPTIONS = (
    ("light", "Светлая"),
    ("dark", "Тёмная"),
    ("system", "Авто"),
)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Convertly")
        self.setAcceptDrops(True)

        self._app = QApplication.instance()
        self._config = AppConfig.load()
        self._resolved_theme = "light"
        if self._app is not None:
            self._resolved_theme = apply_theme(self._app, self._config.theme)

        self._jobs: list[Job] = []
        self._job_seq = 0
        self._output_dir = self._config.output_dir
        self._ffmpeg_ok = ffmpeg_available()
        self._probe_busy = False
        self._probe_worker: ProbeWorker | None = None

        self.resize(
            max(self._config.window_width, 1000),
            max(self._config.window_height, 680),
        )
        self.setMinimumSize(1000, 680)

        self._runner = ConversionRunner(self)
        self._runner.jobStarted.connect(self._on_job_started)
        self._runner.jobProgress.connect(self._on_job_progress)
        self._runner.jobFinished.connect(self._on_job_finished)
        self._runner.allFinished.connect(self._on_all_finished)

        root = QWidget(self)
        root.setObjectName("root")
        self.setCentralWidget(root)

        column = QVBoxLayout(root)
        column.setContentsMargins(20, 16, 20, 14)
        column.setSpacing(14)

        column.addLayout(self._build_header())

        body = QHBoxLayout()
        body.setSpacing(20)

        self._drop_zone = DropZone(root)
        self._drop_zone.clicked.connect(self._choose_files)
        self._add_shadow(self._drop_zone)

        self._queue = QueueView(root)
        self._queue.removeRequested.connect(self.remove_job)
        self._queue.revealRequested.connect(self.reveal_job)
        self._queue.kindSelected.connect(self._on_kind_clicked)

        self._panel = SettingsPanel(root)
        self._panel.import_kinds(self._config.kinds, self._config.active_kind)
        self._panel.outputDirRequested.connect(self._choose_output_dir)
        self._panel.settingsChanged.connect(self._on_settings_changed)
        self._panel.set_output_dir(self._output_dir)

        left = QVBoxLayout()
        left.setSpacing(12)
        left.addWidget(self._drop_zone)
        left.addWidget(self._queue, 1)
        body.addLayout(left, 1)
        body.addWidget(self._panel)

        column.addLayout(body, 1)
        column.addWidget(self._build_footer(root))

        self._build_status_bar()
        self._tray: QSystemTrayIcon | None = None
        self._setup_tray()

        if self._app is not None:
            self._app.styleHints().colorSchemeChanged.connect(
                self._on_system_scheme_changed
            )

        self._install_shortcuts()
        self._queue.set_jobs([], {})
        self._refresh_ui()

    @staticmethod
    def _add_shadow(widget: QWidget) -> None:
        effect = QGraphicsDropShadowEffect(widget)
        effect.setBlurRadius(22)
        effect.setOffset(0, 4)
        effect.setColor(QColor(0, 0, 0, 18))
        widget.setGraphicsEffect(effect)

    # шапка
    def _build_header(self) -> QHBoxLayout:
        header = QHBoxLayout()
        header.setSpacing(12)

        icon_pixmap = app_icon_pixmap(40)
        if icon_pixmap.isNull():
            mark = QLabel("C")
            mark.setObjectName("logoMark")
            mark.setAlignment(Qt.AlignCenter)
        else:
            mark = QLabel()
            mark.setPixmap(icon_pixmap)
        mark.setFixedSize(40, 40)

        titles = QVBoxLayout()
        titles.setSpacing(0)
        title = QLabel("Convertly")
        title.setObjectName("appTitle")
        subtitle = QLabel("Конвертер видео, аудио и изображений")
        subtitle.setObjectName("appSubtitle")
        titles.addWidget(title)
        titles.addWidget(subtitle)

        self._theme_selector = SegmentedControl(list(THEME_OPTIONS))
        self._theme_selector.set_value(self._config.theme)
        self._theme_selector.changed.connect(self._on_theme_changed)

        help_button = QPushButton("?")
        help_button.setObjectName("helpButton")
        help_button.setCursor(Qt.PointingHandCursor)
        help_button.setToolTip("Справка и горячие клавиши (F1)")
        help_button.clicked.connect(self._show_help)

        header.addWidget(mark)
        header.addLayout(titles)
        header.addStretch(1)
        header.addWidget(help_button, 0, Qt.AlignVCenter)
        header.addSpacing(2)
        header.addWidget(self._theme_selector, 0, Qt.AlignVCenter)
        return header

    # футер
    def _build_footer(self, parent: QWidget) -> QWidget:
        footer = QFrame(parent)

        row = QHBoxLayout(footer)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(14)

        status = QVBoxLayout()
        status.setSpacing(5)

        self._footer_hint = QLabel("")
        self._footer_hint.setObjectName("footerHint")

        self._overall = QProgressBar(footer)
        self._overall.setObjectName("overallProgress")
        self._overall.setRange(0, 100)
        self._overall.setValue(0)
        self._overall.setTextVisible(False)
        self._overall.setFixedHeight(6)
        self._overall.setMinimumWidth(300)

        status.addWidget(self._footer_hint)
        status.addWidget(self._overall)

        self._clear_button = QPushButton("Очистить", footer)
        self._add_button = QPushButton("Добавить файлы", footer)
        self._start_button = QPushButton("Конвертировать", footer)
        self._start_button.setObjectName("primary")

        self._open_folder_button = QPushButton("Открыть папку", footer)
        self._open_folder_button.clicked.connect(self._open_output_folder)
        self._open_folder_button.setVisible(False)

        for button in (
            self._clear_button,
            self._add_button,
            self._start_button,
            self._open_folder_button,
        ):
            button.setCursor(Qt.PointingHandCursor)

        self._clear_button.clicked.connect(self._clear_jobs)
        self._add_button.clicked.connect(self._choose_files)
        self._start_button.clicked.connect(self._on_primary_clicked)

        row.addLayout(status)
        row.addStretch(1)
        row.addWidget(self._open_folder_button, 0, Qt.AlignVCenter)
        row.addWidget(self._clear_button, 0, Qt.AlignVCenter)
        row.addWidget(self._add_button, 0, Qt.AlignVCenter)
        row.addWidget(self._start_button, 0, Qt.AlignVCenter)
        return footer

    # статус-бар
    def _build_status_bar(self) -> None:
        bar = QStatusBar(self)
        bar.setSizeGripEnabled(False)

        if self._ffmpeg_ok:
            text = "Готов к работе · ffmpeg найден"
        else:
            text = f"ffmpeg не найден: {install_hint()}"
        self._status_left = QLabel(text)

        engine = QLabel("●  ffmpeg не найден")
        engine.setObjectName("engineOff")
        if self._ffmpeg_ok:
            version = ffmpeg_version()
            engine.setText(f"●  ffmpeg {version}".rstrip())
            engine.setObjectName("engineOk")

        version_label = QLabel(f"v{__version__}")
        version_label.setContentsMargins(0, 0, 8, 0)

        bar.addWidget(self._status_left)
        bar.addPermanentWidget(engine)
        bar.addPermanentWidget(version_label)
        self.setStatusBar(bar)

    # темы
    def _on_theme_changed(self, mode: str) -> None:
        self._config.theme = mode
        self._apply_current_theme()
        self._save_config()

    def _on_system_scheme_changed(self, _scheme=None) -> None:
        if self._config.theme == "system":
            self._apply_current_theme()

    def _apply_current_theme(self) -> None:
        if self._app is None:
            return
        self._resolved_theme = apply_theme(self._app, self._config.theme)
        self._theme_selector.set_value(self._config.theme)
        self._queue.set_jobs(self._jobs, self._targets())
        self._drop_zone.refresh_theme()
        self.update()
        self._refresh_ui()

    # добавление
    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        paths = [
            Path(url.toLocalFile())
            for url in event.mimeData().urls()
            if url.isLocalFile() and url.toLocalFile()
        ]
        if paths:
            self.add_paths(paths)
            event.acceptProposedAction()

    def _choose_files(self) -> None:
        patterns = " ".join(f"*{ext}" for ext in sorted(SUPPORTED_EXTENSIONS))
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Выберите файлы",
            str(Path.home()),
            f"Медиафайлы ({patterns});;Все файлы (*)",
        )
        if files:
            self.add_paths([Path(name) for name in files])

    def add_paths(self, paths: list[Path]) -> None:
        if self._probe_busy:
            self._status_left.setText("Дождитесь окончания проверки файлов")
            return

        expanded = self._expand_paths(paths)
        if not expanded:
            return

        known = {job.info.path.resolve() for job in self._jobs}
        fresh: list[Path] = []
        for path in expanded:
            resolved = path.resolve()
            if resolved in known:
                continue
            known.add(resolved)
            fresh.append(path)

        if not fresh:
            self._status_left.setText("Все выбранные файлы уже в очереди")
            return

        self._probe_busy = True
        self._probe_worker = ProbeWorker()
        self._probe_worker.finished.connect(self._on_probe_finished)
        self._status_left.setText(f"Проверяю файлы: {len(fresh)}…")
        self._refresh_ui()

        QThreadPool.globalInstance().start(ProbeTask(fresh, self._probe_worker))

    def _on_probe_finished(self, infos: list, errors: list) -> None:
        self._probe_busy = False
        self._probe_worker = None

        for info in infos:
            self._jobs.append(Job(id=self._next_id(), info=info))

        if infos:
            self._panel.set_active_kind(infos[-1].kind)
            self._queue.set_jobs(self._jobs, self._targets())
            self._status_left.setText(f"Добавлено файлов: {len(infos)}")
        else:
            self._status_left.setText("Файлы не добавлены")

        self._refresh_ui()

        if errors:
            lines = [
                f"{Path(raw_path).name}: {message}" for raw_path, message in errors[:10]
            ]
            if len(errors) > 10:
                lines.append(f"…и ещё {len(errors) - 10}")
            QMessageBox.warning(self, "Не удалось прочитать файлы", "\n".join(lines))

    def _expand_paths(self, paths: list[Path]) -> list[Path]:
        result: list[Path] = []
        for path in paths:
            if len(result) >= MAX_DROPPED_FILES:
                break
            if path.is_dir():
                for child in sorted(path.rglob("*")):
                    if len(result) >= MAX_DROPPED_FILES:
                        break
                    if child.is_file() and child.suffix.lower() in SUPPORTED_EXTENSIONS:
                        result.append(child)
            elif path.is_file():
                result.append(path)
        return result

    # управление
    def _clear_jobs(self) -> None:
        if self._runner.is_running() or self._probe_busy:
            return
        self._jobs.clear()
        self._queue.set_jobs([], {})
        self._open_folder_button.setVisible(False)
        self._refresh_ui()
        self._status_left.setText("Очередь очищена")

    def _choose_output_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, "Папка вывода", str(self._output_dir)
        )
        if directory:
            self._output_dir = Path(directory)
            self._panel.set_output_dir(self._output_dir)

    def _open_output_folder(self) -> None:
        if self._output_dir.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._output_dir)))
        else:
            self._status_left.setText("Папка вывода ещё не создана")

    def remove_job(self, job_id: int) -> None:
        if self._runner.is_running() or self._probe_busy:
            self._status_left.setText("Дождитесь завершения конвертации")
            return

        before = len(self._jobs)
        self._jobs = [job for job in self._jobs if job.id != job_id]
        if len(self._jobs) == before:
            return

        self._queue.set_jobs(self._jobs, self._targets())
        self._open_folder_button.setVisible(
            any(job.status is JobStatus.DONE for job in self._jobs)
        )
        self._refresh_ui()
        self._status_left.setText("Файл убран из очереди")

    def reveal_job(self, job_id: int) -> None:
        job = next((item for item in self._jobs if item.id == job_id), None)
        if job is None or job.output is None:
            return

        if not job.output.exists():
            self._status_left.setText("Файл результата не найден")
            return

        if reveal_file(job.output):
            return

        # запасной вариант: просто открыть папку
        parent = job.output.parent
        if parent.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(parent)))
        else:
            self._status_left.setText("Папка с результатом не найдена")

    def _setup_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        app = QApplication.instance()
        icon = app.windowIcon() if app is not None else self.windowIcon()

        tray = QSystemTrayIcon(icon, self)
        menu = QMenu(self)
        open_action = menu.addAction("Открыть Convertly")
        open_action.triggered.connect(self._show_from_tray)
        menu.addSeparator()
        quit_action = menu.addAction("Выход")
        quit_action.triggered.connect(QApplication.quit)

        tray.setContextMenu(menu)
        tray.setToolTip("Convertly")
        tray.show()
        self._tray = tray

    def _install_shortcuts(self) -> None:
        self._shortcuts: list[QShortcut] = []
        bindings = (
            ("Ctrl+O", self._choose_files),
            ("Ctrl+Return", self._on_primary_clicked),
            ("Ctrl+Enter", self._on_primary_clicked),
            ("Ctrl+L", self._open_output_folder),
            ("F1", self._show_help),
            ("Ctrl+Q", self.close),
        )
        for keys, handler in bindings:
            shortcut = QShortcut(QKeySequence(keys), self)
            shortcut.activated.connect(handler)
            self._shortcuts.append(shortcut)

    def _show_help(self) -> None:
        HelpDialog(self).exec()

    def _on_kind_clicked(self, kind: str) -> None:
        self._panel.set_active_kind(kind)

    def _show_from_tray(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _save_config(self) -> None:
        self._config.output_dir = self._output_dir
        self._config.active_kind = self._panel.active_kind
        self._config.kinds = self._panel.export_kinds()
        self._config.window_width = self.width()
        self._config.window_height = self.height()
        try:
            self._config.save()
        except OSError:
            pass

    def closeEvent(self, event) -> None:
        self._save_config()
        super().closeEvent(event)

    def _next_id(self) -> int:
        self._job_seq += 1
        return self._job_seq

    def _targets(self) -> dict[str, str]:
        return {
            kind: self._panel.target_label(kind) for kind in ("video", "audio", "image")
        }

    def _on_settings_changed(self, kind: str) -> None:
        # изменились параметры для этого типа — готовые файлы снова в очередь
        for job in self._jobs:
            if job.info.kind == kind and job.status == JobStatus.DONE:
                job.status = JobStatus.QUEUED
                job.progress = 0
                self._queue.update_job(job, self._panel.target_label(kind))
        self._queue.update_targets(kind, self._panel.target_label(kind))
        self._refresh_ui()

    # конвертация
    def _on_primary_clicked(self) -> None:
        if self._runner.is_running():
            self._runner.cancel_all()
            return

        if not self._ffmpeg_ok:
            QMessageBox.critical(
                self,
                "ffmpeg не найден",
                "Convertly использует ffmpeg для конвертации.\n"
                f"Установите его: {install_hint()}",
            )
            return

        pending = [job for job in self._jobs if job.status != JobStatus.DONE]
        if not pending:
            return

        try:
            self._output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            QMessageBox.critical(self, "Не удалось создать папку", str(exc))
            return

        requests: list[JobRequest] = []
        taken: set[Path] = set()
        for job in pending:
            settings = self._panel.settings_for(job.info.kind)
            spec = format_by_key(settings.format_key)
            output = unique_output_path(
                self._output_dir, job.info.path.stem, spec.extension, taken
            )
            taken.add(output)

            job.status = JobStatus.QUEUED
            job.progress = 0
            job.error = ""
            requests.append(JobRequest(job=job, settings=settings, output=output))

        self._queue.set_jobs(self._jobs, self._targets())
        self._runner.start(requests)
        self._open_folder_button.setVisible(False)
        self._status_left.setText(f"Запущено задач: {len(requests)}")
        self._refresh_ui()

    def _on_job_started(self, job_id: int) -> None:
        self._refresh_job(job_id)
        self._refresh_ui()

    def _on_job_progress(self, job_id: int, _percent: int, _speed: str) -> None:
        self._refresh_job(job_id)
        self._refresh_ui()

    def _on_job_finished(self, job_id: int, _ok: bool, _message: str) -> None:
        self._refresh_job(job_id)
        self._refresh_ui()

    def _on_all_finished(self) -> None:
        done = sum(job.status == JobStatus.DONE for job in self._jobs)
        failed = sum(job.status == JobStatus.FAILED for job in self._jobs)
        cancelled = sum(job.status == JobStatus.CANCELLED for job in self._jobs)
        parts = [f"Готово: {done}"]
        if failed:
            parts.append(f"ошибок: {failed}")
        if cancelled:
            parts.append(f"отменено: {cancelled}")
        self._status_left.setText(" · ".join(parts))
        self._open_folder_button.setVisible(done > 0)

        if not self.isActiveWindow() or self.isMinimized():
            QApplication.alert(self)
            if self._tray is not None:
                self._tray.showMessage(
                    "Convertly", " · ".join(parts), QSystemTrayIcon.Information, 5000
                )

        self._refresh_ui()

    def _refresh_job(self, job_id: int) -> None:
        job = next((item for item in self._jobs if item.id == job_id), None)
        if job is not None:
            self._queue.update_job(job, self._panel.target_label(job.info.kind))

    # сводка
    def _refresh_ui(self) -> None:
        total = len(self._jobs)
        running = self._runner.is_running()
        done = sum(job.status == JobStatus.DONE for job in self._jobs)

        if total:
            values = [
                100 if job.status == JobStatus.DONE else job.progress
                for job in self._jobs
            ]
            self._overall.setValue(round(sum(values) / total))
        else:
            self._overall.setValue(0)

        if running:
            active = sum(job.status == JobStatus.RUNNING for job in self._jobs)
            self._footer_hint.setText(f"В работе: {active} · готово {done} из {total}")
        elif total:
            self._footer_hint.setText(f"Готово {done} из {total}")
        else:
            self._footer_hint.setText("Перетащите файлы, чтобы начать")

        self._start_button.setText("Остановить" if running else "Конвертировать")
        self._start_button.setEnabled(
            not self._probe_busy
            and (running or (total > 0 and done < total and self._ffmpeg_ok))
        )
        self._clear_button.setEnabled(
            total > 0 and not running and not self._probe_busy
        )
        self._add_button.setEnabled(not running and not self._probe_busy)
        self._drop_zone.setEnabled(not running and not self._probe_busy)
        self._queue.set_locked(running or self._probe_busy)
