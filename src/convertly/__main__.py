"""Точка входа: python3 -m convertly."""

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication

from .ui.main_window import MainWindow
from .ui.theme import APP_ICON, LIGHT, app_icon_pixmap, apply_theme


def _app_icon() -> QIcon:
    """Иконка из SVG-файла, с запасным вариантом на случай проблем."""
    if APP_ICON.exists():
        pixmap = app_icon_pixmap(256)
        if not pixmap.isNull():
            return QIcon(pixmap)

    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(LIGHT["ACCENT"]))
    painter.drawRoundedRect(0, 0, 64, 64, 16, 16)

    font = QFont()
    font.setBold(True)
    font.setPointSize(28)
    painter.setFont(font)
    painter.setPen(QColor("#ffffff"))
    painter.drawText(pixmap.rect(), Qt.AlignCenter, "C")
    painter.end()

    return QIcon(pixmap)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Convertly")
    app.setApplicationDisplayName("Convertly")
    app.setOrganizationName("Convertly")
    app.setDesktopFileName("convertly")
    app.setWindowIcon(_app_icon())

    apply_theme(app)

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
