"""
PDF Toolbox — Application Entry Point.

Usage:
    python -m src.main

Or run the built executable directly.
"""

import sys
import os

# Add alternative package install path (for systems with long path issues)
_ALT_PACKAGE_PATH = "C:/pylibs"
if os.path.isdir(_ALT_PACKAGE_PATH) and _ALT_PACKAGE_PATH not in sys.path:
    sys.path.insert(0, _ALT_PACKAGE_PATH)

# Ensure the project root is on the path so 'src' imports work
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from src import __app_name__, __version__
from src.utils.logger import logger
from src.ui.main_window import MainWindow


def load_stylesheet(app: QApplication) -> str:
    """Load and apply the dark theme QSS stylesheet."""
    style_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "ui", "styles", "dark_theme.qss"
    )

    if os.path.exists(style_path):
        with open(style_path, "r", encoding="utf-8") as f:
            qss = f.read()
        app.setStyleSheet(qss)
        logger.info("Dark theme loaded")
        return qss
    else:
        logger.warning(f"Stylesheet not found: {style_path}")
        return ""


def main():
    """Main entry point."""
    # Enable High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName(__app_name__)
    app.setApplicationVersion(__version__)
    app.setOrganizationName("PDFToolbox")

    # Load Qt Chinese translations for native dialogs
    from PySide6.QtCore import QTranslator, QLibraryInfo
    translator = QTranslator()
    qt_translations_path = QLibraryInfo.path(
        QLibraryInfo.TranslationsPath
    )
    if translator.load("qt_zh_CN", qt_translations_path):
        app.installTranslator(translator)
        logger.info("Chinese translation loaded")
    else:
        logger.debug("Qt Chinese translation not found, using defaults")

    # Apply dark theme
    load_stylesheet(app)

    # Create and show main window
    window = MainWindow()
    window.show()

    # Run the application
    exit_code = app.exec()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

