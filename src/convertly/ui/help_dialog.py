"""Окно справки: как пользоваться, горячие клавиши и частые вопросы."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from .theme import current

HOTKEYS = (
    ("Ctrl + O", "Добавить файлы"),
    ("Ctrl + Enter", "Запустить или остановить конвертацию"),
    ("Ctrl + L", "Открыть папку вывода"),
    ("F1", "Эта справка"),
    ("Ctrl + Q", "Закрыть приложение"),
)


def help_html() -> str:
    c = current()
    text = c["TEXT"]
    muted = c["MUTED"]
    accent = c["ACCENT"]
    border = c["BORDER"]

    rows = "".join(
        f"<tr>"
        f'<td style="padding:5px 8px; color:{accent}; font-weight:600; white-space:nowrap;">{keys}</td>'
        f'<td style="padding:5px 8px; color:{text};">{description}</td>'
        f"</tr>"
        for keys, description in HOTKEYS
    )

    return f"""
<html>
<body style="color:{text}; font-family:'Noto Sans'; font-size:13px;">

<h2 style="color:{text}; font-size:18px; margin-bottom:6px;">Как конвертировать</h2>
<ol style="margin-top:4px;">
  <li>Перетащите файлы или папки в окно либо нажмите «Добавить файлы».</li>
  <li>Справа выберите формат и качество. Панель сама показывает настройки
      для типа последнего добавленного файла.</li>
  <li>Нажмите «Конвертировать». Две задачи идут параллельно, прогресс виден в очереди.</li>
  <li>Готовый файл можно открыть в папке: кликните по его имени в очереди.</li>
</ol>

<h2 style="color:{text}; font-size:18px; margin-bottom:6px;">Горячие клавиши</h2>
<table width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;">
{rows}
</table>

<h2 style="color:{text}; font-size:18px; margin-bottom:6px;">Настройки для разных типов</h2>
<p style="color:{text};">
У видео, аудио и изображений свои параметры: формат, кодек, качество, разрешение.
Панель справа переключается автоматически: на тип последнего добавленного файла
или на тип строки, по которой вы кликнули в очереди.
</p>

<h2 style="color:{text}; font-size:18px; margin-bottom:6px;">Куда сохраняются файлы</h2>
<p style="color:{text};">
Результат попадает в папку, указанную в настройках (по умолчанию
<code style="color:{accent};">~/Videos/Convertly</code>).
Существующие файлы не перезаписываются: при совпадении имени добавляется
суффикс <code style="color:{accent};">(1)</code>, <code style="color:{accent};">(2)</code> и так далее.
</p>

<h2 style="color:{text}; font-size:18px; margin-bottom:6px;">Поддерживаемые форматы</h2>
<ul style="margin-top:4px; color:{text};">
  <li><b>Видео:</b> mp4, mkv, webm, mov, avi, m4v, ts, flv, wmv, mpg, 3gp, ogv → MP4, MKV, WebM, MOV</li>
  <li><b>Аудио:</b> mp3, flac, wav, ogg, opus, aac, m4a, wma, aiff → MP3, FLAC, WAV, OGG</li>
  <li><b>Изображения:</b> png, jpg, webp, bmp, tif, gif, heic, avif → JPEG, PNG, WebP</li>
</ul>

<h2 style="color:{text}; font-size:18px; margin-bottom:6px;">Частые вопросы</h2>

<p style="color:{text}; margin-bottom:2px;"><b>Файл не появился в очереди</b></p>
<p style="color:{muted}; margin-top:0;">Формат не поддерживается или файл повреждён.
При ошибке ffprobe приложение показывает предупреждение с причиной.</p>

<p style="color:{text}; margin-bottom:2px;"><b>Конвертация идёт медленно</b></p>
<p style="color:{muted}; margin-top:0;">AV1 и H.265 кодируются заметно дольше H.264.
Одновременно выполняется две задачи; на слабом CPU это может занимать время.</p>

<p style="color:{text}; margin-bottom:2px;"><b>Не работает уведомление</b></p>
<p style="color:{muted}; margin-top:0;">Уведомления показываются через системный трей,
только когда окно не в фокусе. Проверьте, что трей доступен в вашем окружении.</p>

<p style="color:{text}; margin-bottom:2px;"><b>Где хранятся настройки</b></p>
<p style="color:{muted}; margin-top:0;">
<code style="color:{accent};">~/.config/convertly/config.json</code> — папка вывода,
параметры каждого типа, тема и размер окна. Удалите файл, чтобы сбросить всё.
</p>

<p style="color:{text}; margin-bottom:2px;"><b>Темы</b></p>
<p style="color:{muted}; margin-top:0;">Переключатель в правом верхнем углу: светлая, тёмная
или «Авто» — следовать за системной темой. Выбор сохраняется между запусками.</p>

<p style="color:{muted}; margin-top:14px; border-top:1px solid {border}; padding-top:8px;">
Convertly · конвертация через ffmpeg · интерфейс на PySide6
</p>

</body>
</html>
"""


class HelpDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Справка Convertly")
        self.resize(680, 620)
        self.setMinimumSize(560, 480)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        title = QLabel("Справка", self)
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        self.browser = QTextBrowser(self)
        self.browser.setOpenExternalLinks(True)
        self.browser.setHtml(help_html())
        layout.addWidget(self.browser, 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        close_button = QPushButton("Понятно", self)
        close_button.setObjectName("primary")
        close_button.setCursor(Qt.PointingHandCursor)
        close_button.setDefault(True)
        close_button.clicked.connect(self.accept)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)
