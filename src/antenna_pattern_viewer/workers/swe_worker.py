"""
Worker thread for SWE calculations to prevent GUI freezing.
"""

import logging
import traceback

from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class SWEWorker(QThread):
    """Worker thread for calculating spherical wave expansion."""
    
    # Signals
    finished = pyqtSignal(object)  # Emits SWE object when done
    error = pyqtSignal(str)  # Emits error message (the traceback goes to the log)
    progress = pyqtSignal(str)  # Emits progress messages
    
    def __init__(self, pattern, frequency, nmax=None, mmax=None):
        super().__init__()
        self.pattern = pattern
        self.frequency = frequency
        self.nmax = nmax
        self.mmax = mmax

    def run(self):
        """Run the calculation in background thread."""
        try:
            self.progress.emit("Calculating spherical modes...")
            swe = self.pattern.calculate_spherical_modes(
                frequency=self.frequency,
                nmax=self.nmax,
                mmax=self.mmax
            )
            self.finished.emit(swe)
            
        except Exception as e:
            # str(e) alone is often unactionable (a bare LinAlgError, say), so
            # the full traceback is logged even though only the message is
            # shown in the panel.
            logger.error("SWE calculation failed:\n%s", traceback.format_exc())
            self.error.emit(str(e))