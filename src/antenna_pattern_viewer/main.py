"""
Entry point for standalone Antenna Pattern Viewer application.
"""
import logging
import sys
import traceback

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt

logger = logging.getLogger(__name__)


def install_exception_hook():
    """
    Report unhandled exceptions instead of letting Qt abort the process.

    PyQt6 terminates the application when a slot raises, so without this a
    single bug in a signal handler closes the window with no message and no
    chance to save anything.
    """
    def hook(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        detail = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        logger.error("Unhandled exception:\n%s", detail)
        if QApplication.instance() is not None:
            box = QMessageBox(QMessageBox.Icon.Critical, "Unexpected Error",
                              f"{exc_type.__name__}: {exc_value}")
            box.setInformativeText("The application may be in an inconsistent state.")
            box.setDetailedText(detail)
            box.exec()

    sys.excepthook = hook


def main():
    """Launch the Antenna Pattern Viewer application."""
    
    # Enable high DPI display support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    # Report errors in slots rather than aborting the process
    install_exception_hook()

    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("Antenna Pattern Viewer")
    app.setOrganizationName("AntennaPatternViewer")
    
    # Import here to avoid issues with relative imports
    from antenna_pattern_viewer.antenna_pattern_widget import AntennaPatternWidget
    
    # Create and show main window
    main_window = AntennaPatternWidget()
    main_window.show()
    
    # Start event loop
    sys.exit(app.exec())


if __name__ == '__main__':
    main()