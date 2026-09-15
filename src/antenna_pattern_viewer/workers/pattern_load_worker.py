"""
Worker thread for reading pattern files without blocking the GUI.

The readers take seconds on a large file, and the file manager loads them on
the event loop, so the window is unresponsive (and marked "not responding" by
the desktop) for the whole read. Any format-specific options are collected on
the GUI thread first, then the reads run here.
"""
import logging
import traceback
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class PatternLoadWorker(QThread):
    """Reads a list of pattern files in the background."""

    # path, pattern
    loaded = pyqtSignal(object, object)
    # path, message, traceback
    failed = pyqtSignal(object, str, str)
    # path, index (1-based), total
    progress = pyqtSignal(object, int, int)

    def __init__(self, jobs, parent=None):
        """
        Args:
            jobs: sequence of (Path, callable) pairs. The callable takes no
                arguments and returns a FarFieldSpherical; it carries whatever
                options the GUI thread already collected.
        """
        super().__init__(parent)
        self._jobs = list(jobs)
        self._cancelled = False

    def cancel(self):
        """Ask the worker to stop after the file it is currently reading."""
        self._cancelled = True

    def run(self):
        total = len(self._jobs)
        for index, (file_path, read) in enumerate(self._jobs, start=1):
            if self._cancelled:
                return
            self.progress.emit(Path(file_path), index, total)
            try:
                pattern = read()
            except Exception as e:
                logger.exception("Failed to load %s", file_path)
                self.failed.emit(Path(file_path), str(e), traceback.format_exc())
            else:
                self.loaded.emit(Path(file_path), pattern)
