"""Темы Convertly: светлая и тёмная в стиле macOS, плюс режим «системная»."""

from __future__ import annotations

from pathlib import Path
from string import Template

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPalette, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

MODES = ("light", "dark", "system")

LIGHT = {
    "BG": "#f5f5f7",
    "SURFACE": "#ffffff",
    "ROW_HOVER": "#f5f5f7",
    "BORDER": "#e3e3e8",
    "BORDER_HOVER": "#cdcdd2",
    "SEPARATOR": "#ededf0",
    "TRACK": "#e9e9ee",
    "TEXT": "#1d1d1f",
    "MUTED": "#86868b",
    "ACCENT": "#007aff",
    "ACCENT_HOVER": "#2f95ff",
    "ACCENT_PRESSED": "#0066d6",
    "ACCENT_SOFT": "#e9f1ff",
    "SUCCESS": "#34c759",
    "SUCCESS_SOFT": "#e9f9ee",
    "WARN": "#ff9500",
    "DANGER": "#ff3b30",
    "DARK_TEXT": "#ffffff",
    "SEGMENT_BG": "#e9e9ee",
    "SEGMENT_ACTIVE": "#ffffff",
    "SEGMENT_ACTIVE_BORDER": "#d9d9de",
    "BADGE_VIDEO_BG": "#e9f1ff",
    "BADGE_VIDEO_FG": "#007aff",
    "BADGE_AUDIO_BG": "#f7ecff",
    "BADGE_AUDIO_FG": "#af52de",
    "BADGE_IMAGE_BG": "#e9f9ee",
    "BADGE_IMAGE_FG": "#248a3d",
}

DARK = {
    "BG": "#1c1c1e",
    "SURFACE": "#2c2c2e",
    "ROW_HOVER": "#323234",
    "BORDER": "#3a3a3c",
    "BORDER_HOVER": "#48484a",
    "SEPARATOR": "#3a3a3c",
    "TRACK": "#3a3a3c",
    "TEXT": "#f5f5f7",
    "MUTED": "#98989d",
    "ACCENT": "#0a84ff",
    "ACCENT_HOVER": "#3395ff",
    "ACCENT_PRESSED": "#0066d6",
    "ACCENT_SOFT": "#0f2a45",
    "SUCCESS": "#30d158",
    "SUCCESS_SOFT": "#12331f",
    "WARN": "#ff9f0a",
    "DANGER": "#ff453a",
    "DARK_TEXT": "#ffffff",
    "SEGMENT_BG": "#2c2c2e",
    "SEGMENT_ACTIVE": "#48484a",
    "SEGMENT_ACTIVE_BORDER": "#5a5a5e",
    "BADGE_VIDEO_BG": "#0f2a45",
    "BADGE_VIDEO_FG": "#64a8ff",
    "BADGE_AUDIO_BG": "#2c1b38",
    "BADGE_AUDIO_FG": "#d0a1ff",
    "BADGE_IMAGE_BG": "#12331f",
    "BADGE_IMAGE_FG": "#4cd964",
}

PALETTES = {"light": LIGHT, "dark": DARK}
_current = LIGHT
_current_mode = "light"

FONT_SIZE = 10
FONT_FAMILIES = (
    "SF Pro Text",
    "SF Pro Display",
    "Segoe UI",
    "Inter",
    "Helvetica Neue",
    "Noto Sans",
    "DejaVu Sans",
    "Arial",
)

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
CHEVRON_ICON = (ASSETS_DIR / "chevron-down.svg").as_posix()
CHECK_ICON = (ASSETS_DIR / "check.svg").as_posix()
APP_ICON = ASSETS_DIR / "icon.svg"

_QSS = Template(
    r"""
QWidget {
    color: $TEXT;
    font-size: 13px;
}

QMainWindow, QWidget#root {
    background: $BG;
}

QToolTip {
    background: $SURFACE;
    color: $TEXT;
    border: 1px solid $BORDER;
    border-radius: 6px;
    padding: 4px 8px;
}

/* --- заголовки ---------------------------------------------------------- */
QLabel#appTitle {
    font-size: 24px;
    font-weight: 700;
}

QLabel#appSubtitle {
    color: $MUTED;
    font-size: 12px;
}

QPushButton#helpButton {
    background: $SURFACE;
    border: 1px solid $BORDER;
    border-radius: 14px;
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    padding: 0;
    color: $MUTED;
    font-size: 14px;
    font-weight: 700;
}

QPushButton#helpButton:hover {
    background: $ROW_HOVER;
    color: $TEXT;
}

QLabel#dialogTitle {
    font-size: 20px;
    font-weight: 700;
}

QDialog {
    background: $BG;
}

QTextBrowser {
    background: $SURFACE;
    border: 1px solid $BORDER;
    border-radius: 12px;
    padding: 10px;
}

QLabel#panelTitle {
    font-size: 15px;
    font-weight: 600;
}

QLabel#sectionTitle {
    color: $MUTED;
    font-size: 11px;
    font-weight: 700;
}

QLabel#countBadge {
    background: $TRACK;
    color: $MUTED;
    border-radius: 9px;
    padding: 2px 9px;
    font-size: 11px;
    font-weight: 600;
}

QLabel#rowName {
    font-weight: 600;
    font-size: 13px;
}

QLabel#rowMeta, QLabel#targetLabel {
    color: $MUTED;
    font-size: 11px;
}

QLabel#rowStatus {
    color: $MUTED;
    font-size: 11px;
}

QLabel#rowStatus[state="done"] {
    color: $SUCCESS;
    font-weight: 600;
}

QLabel#rowStatus[state="failed"] {
    color: $DANGER;
    font-weight: 600;
}

/* --- зона перетаскивания ------------------------------------------------ */
QFrame#dropZone {
    background: $SURFACE;
    border: 1px solid $BORDER;
    border-radius: 14px;
}

QLabel#dropIcon {
    background: $ACCENT_SOFT;
    border-radius: 28px;
}

QFrame#dropZone:hover {
    border-color: $ACCENT;
    background: $ROW_HOVER;
}

QLabel#dropTitle {
    font-size: 15px;
    font-weight: 600;
}

QLabel#dropHint {
    color: $MUTED;
    font-size: 12px;
}

QLabel#emptyState {
    color: $MUTED;
    font-size: 12px;
}

/* --- групповые списки --------------------------------------------------- */
QFrame#queueGroup, QFrame#settingsGroup {
    background: $SURFACE;
    border: 1px solid $BORDER;
    border-radius: 12px;
}

QFrame#queueRow {
    background: transparent;
    border: none;
}

QFrame#queueRow:hover {
    background: $ROW_HOVER;
}

QFrame#queueRow[pos="first"] {
    border-top-left-radius: 12px;
    border-top-right-radius: 12px;
}

QFrame#queueRow[pos="last"] {
    border-bottom-left-radius: 12px;
    border-bottom-right-radius: 12px;
}

QFrame#queueRow[pos="single"] {
    border-radius: 12px;
}

QFrame#rowSeparator {
    background: $SEPARATOR;
    border: none;
    max-height: 1px;
}

QFrame#separator {
    background: $SEPARATOR;
    border: none;
    max-height: 1px;
}

/* --- значки типов файлов ------------------------------------------------ */
QLabel#kindBadge {
    border-radius: 9px;
    font-size: 15px;
    font-weight: 700;
}

QLabel#kindBadge[kind="video"] {
    background: $BADGE_VIDEO_BG;
    color: $BADGE_VIDEO_FG;
}

QLabel#kindBadge[kind="audio"] {
    background: $BADGE_AUDIO_BG;
    color: $BADGE_AUDIO_FG;
}

QLabel#kindBadge[kind="image"] {
    background: $BADGE_IMAGE_BG;
    color: $BADGE_IMAGE_FG;
}

/* --- поля ввода --------------------------------------------------------- */
QLabel#fieldLabel {
    color: $TEXT;
    font-size: 13px;
}

QLabel#pathField {
    background: $TRACK;
    border: none;
    border-radius: 7px;
    padding: 6px 9px;
    font-size: 11px;
    color: $TEXT;
}

QLabel#qualityValue {
    color: $MUTED;
    font-size: 11px;
}

QLabel#footerHint {
    color: $MUTED;
    font-size: 11px;
}

QLabel#panelHint {
    color: $MUTED;
    font-size: 11px;
}

QLabel#engineOk {
    color: $SUCCESS;
    font-size: 11px;
}

QLabel#engineOff {
    color: $DANGER;
    font-size: 11px;
}

QComboBox {
    background: $SURFACE;
    border: 1px solid $BORDER_HOVER;
    border-radius: 7px;
    padding: 5px 9px;
    min-height: 18px;
    font-size: 12px;
}

QComboBox:hover {
    border-color: #a8a8ad;
}

QComboBox:focus {
    border-color: $ACCENT;
}

QComboBox:disabled {
    color: $MUTED;
    background: $TRACK;
    border-color: transparent;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox::down-arrow {
    image: url("$CHEVRON");
    width: 11px;
    height: 11px;
    margin-right: 6px;
}

QComboBox QAbstractItemView {
    background: $SURFACE;
    border: 1px solid $BORDER;
    border-radius: 8px;
    selection-background-color: $ACCENT_SOFT;
    selection-color: $ACCENT;
    outline: none;
    padding: 4px;
}

/* --- сегментированные переключатели ------------------------------------ */
QFrame#segmented {
    background: $SEGMENT_BG;
    border-radius: 8px;
}

QPushButton#segment {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 4px 10px;
    color: $MUTED;
    font-size: 11px;
    font-weight: 600;
}

QPushButton#segment:hover {
    color: $TEXT;
}

QPushButton#segment:checked {
    background: $SEGMENT_ACTIVE;
    border-color: $SEGMENT_ACTIVE_BORDER;
    color: $TEXT;
}

/* --- слайдер ------------------------------------------------------------ */
QSlider::groove:horizontal {
    height: 4px;
    background: $TRACK;
    border-radius: 2px;
}

QSlider::sub-page:horizontal {
    background: $ACCENT;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    width: 14px;
    height: 14px;
    margin: -6px 0;
    border-radius: 8px;
    background: #ffffff;
    border: 1px solid $BORDER_HOVER;
}

QSlider::sub-page:horizontal:disabled {
    background: $BORDER_HOVER;
}

QSlider::handle:horizontal:disabled {
    background: $SURFACE;
    border-color: $BORDER;
}

/* --- прогресс ----------------------------------------------------------- */
QProgressBar#rowProgress {
    background: $TRACK;
    border: none;
    border-radius: 4px;
}

QProgressBar#rowProgress::chunk {
    background: $ACCENT;
    border-radius: 4px;
}

QProgressBar#rowProgress[state="done"]::chunk {
    background: $SUCCESS;
}

QProgressBar#rowProgress[state="failed"]::chunk {
    background: $DANGER;
}

QProgressBar#rowProgress[state="queued"]::chunk {
    background: $BORDER_HOVER;
}

QProgressBar#overallProgress {
    background: $TRACK;
    border: none;
    border-radius: 3px;
}

QProgressBar#overallProgress::chunk {
    background: $ACCENT;
    border-radius: 3px;
}

/* --- кнопки ------------------------------------------------------------- */
QPushButton {
    background: $SURFACE;
    border: 1px solid $BORDER_HOVER;
    border-radius: 8px;
    padding: 7px 14px;
    font-weight: 500;
    font-size: 12px;
}

QPushButton:hover {
    background: $ROW_HOVER;
}

QPushButton:pressed {
    background: $TRACK;
}

QPushButton:disabled {
    background: $TRACK;
    color: $MUTED;
    border-color: transparent;
}

QPushButton#primary {
    background: $ACCENT;
    border: 1px solid $ACCENT;
    color: $DARK_TEXT;
    padding: 7px 18px;
    font-weight: 600;
}

QPushButton#primary:hover {
    background: $ACCENT_HOVER;
    border-color: $ACCENT_HOVER;
}

QPushButton#primary:pressed {
    background: $ACCENT_PRESSED;
    border-color: $ACCENT_PRESSED;
}

QPushButton#primary:disabled {
    background: $TRACK;
    border-color: transparent;
    color: $MUTED;
}

QPushButton#rowRemove {
    background: transparent;
    border: none;
    color: $MUTED;
    font-size: 15px;
    font-weight: 600;
    padding: 0;
}

QPushButton#rowRemove:hover {
    color: $DANGER;
    background: $ACCENT_SOFT;
    border-radius: 7px;
}

QPushButton#rowRemove:disabled {
    color: $BORDER_HOVER;
    background: transparent;
}

QPushButton#linkButton {
    background: transparent;
    border: none;
    color: $ACCENT;
    font-size: 12px;
    padding: 2px 4px;
}

QPushButton#linkButton:hover {
    background: transparent;
    color: $ACCENT_HOVER;
}

/* --- переключатели (switch) -------------------------------------------- */
QCheckBox {
    spacing: 0;
    background: transparent;
}

QCheckBox::indicator {
    width: 40px;
    height: 24px;
    image: url("$SWITCH_OFF");
}

QCheckBox::indicator:checked {
    image: url("$SWITCH_ON");
}

QCheckBox::indicator:disabled {
    opacity: 0.5;
}

/* --- прокрутка ---------------------------------------------------------- */
QScrollArea, QScrollArea > QWidget > QWidget {
    background: transparent;
    border: none;
}

QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 2px;
}

QScrollBar::handle:vertical {
    background: $BORDER_HOVER;
    border-radius: 4px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: $MUTED;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
    border: none;
    height: 0;
}

/* --- меню --------------------------------------------------------------- */
QMenu {
    background: $SURFACE;
    border: 1px solid $BORDER;
    border-radius: 10px;
    padding: 5px;
}

QMenu::item {
    padding: 6px 18px;
    border-radius: 6px;
}

QMenu::item:selected {
    background: $ACCENT;
    color: $DARK_TEXT;
}

QMenu::separator {
    height: 1px;
    background: $SEPARATOR;
    margin: 4px 8px;
}

/* --- статус-бар --------------------------------------------------------- */
QStatusBar {
    background: $BG;
    border-top: 1px solid $BORDER;
}

QStatusBar::item {
    border: none;
}

QStatusBar QLabel {
    color: $MUTED;
    font-size: 11px;
}
"""
)


def resolve_mode(mode: str) -> str:
    """Превращает light/dark/system в конкретную тему."""
    if mode in {"light", "dark"}:
        return mode
    return system_mode()


def system_mode() -> str:
    app = QApplication.instance()
    if app is None:
        return "light"
    scheme = app.styleHints().colorScheme()
    return "dark" if scheme == Qt.ColorScheme.Dark else "light"


def current() -> dict:
    """Текущая палитра — для виджетов с собственной отрисовкой."""
    return _current


def current_mode() -> str:
    return _current_mode


def stylesheet(palette: dict, resolved_mode: str) -> str:
    switch_off = ASSETS_DIR / f"switch-off-{resolved_mode}.svg"
    switch_on = ASSETS_DIR / f"switch-on-{resolved_mode}.svg"
    return _QSS.substitute(
        **palette,
        CHEVRON=CHEVRON_ICON,
        SWITCH_OFF=switch_off.as_posix(),
        SWITCH_ON=switch_on.as_posix(),
    )


def apply_theme(app: QApplication, mode: str = "system") -> str:
    """Применяет тему и возвращает фактическую (light/dark)."""
    global _current, _current_mode

    resolved = resolve_mode(mode)
    palette = PALETTES[resolved]
    _current = palette
    _current_mode = resolved

    app.setStyle("Fusion")
    app.setFont(app_font())

    qt_palette = QPalette()
    qt_palette.setColor(QPalette.Window, QColor(palette["BG"]))
    qt_palette.setColor(QPalette.WindowText, QColor(palette["TEXT"]))
    qt_palette.setColor(QPalette.Base, QColor(palette["SURFACE"]))
    qt_palette.setColor(QPalette.AlternateBase, QColor(palette["BG"]))
    qt_palette.setColor(QPalette.Text, QColor(palette["TEXT"]))
    qt_palette.setColor(QPalette.Button, QColor(palette["SURFACE"]))
    qt_palette.setColor(QPalette.ButtonText, QColor(palette["TEXT"]))
    qt_palette.setColor(QPalette.Highlight, QColor(palette["ACCENT"]))
    qt_palette.setColor(QPalette.HighlightedText, QColor(palette["DARK_TEXT"]))
    qt_palette.setColor(QPalette.ToolTipBase, QColor(palette["SURFACE"]))
    qt_palette.setColor(QPalette.ToolTipText, QColor(palette["TEXT"]))
    qt_palette.setColor(QPalette.PlaceholderText, QColor(palette["MUTED"]))
    qt_palette.setColor(QPalette.Disabled, QPalette.Text, QColor(palette["MUTED"]))
    qt_palette.setColor(
        QPalette.Disabled, QPalette.ButtonText, QColor(palette["MUTED"])
    )
    app.setPalette(qt_palette)

    app.setStyleSheet(stylesheet(palette, resolved))
    return resolved


def _screen_ratio() -> float:
    screen = QGuiApplication.primaryScreen()
    return max(1.0, screen.devicePixelRatio()) if screen is not None else 1.0


def svg_pixmap(asset: str, size: int, color: str | None = None) -> QPixmap:
    """Рендерит SVG-иконку в цвете темы с учётом масштаба экрана."""
    ratio = _screen_ratio()
    physical = max(1, round(size * ratio))
    pixmap = QPixmap(physical, physical)
    pixmap.fill(Qt.transparent)

    path = ASSETS_DIR / asset
    if not path.exists():
        return pixmap

    markup = path.read_text(encoding="utf-8")
    if color:
        markup = markup.replace("currentColor", color)

    renderer = QSvgRenderer(QByteArray(markup.encode("utf-8")))
    if not renderer.isValid():
        return pixmap

    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    pixmap.setDevicePixelRatio(ratio)
    return pixmap


def app_icon_pixmap(size: int = 40) -> QPixmap:
    """Отрисовывает иконку приложения из SVG с учётом масштаба экрана."""
    ratio = _screen_ratio()
    physical = max(1, round(size * ratio))

    pixmap = QPixmap(physical, physical)
    pixmap.fill(Qt.transparent)
    if not APP_ICON.exists():
        return pixmap

    renderer = QSvgRenderer(str(APP_ICON))
    if not renderer.isValid():
        return pixmap

    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    pixmap.setDevicePixelRatio(ratio)
    return pixmap


def app_font(size: int = FONT_SIZE) -> QFont:
    font = QFont()
    font.setFamilies(list(FONT_FAMILIES))
    font.setPointSize(size)
    return font
