"""
Worker thread for SWE calculations to prevent GUI freezing.
"""

from PyQt6.QtCore import QThread, pyqtSignal


class SWEWorker(QThread):
    """Worker thread for calculating spherical wave expansion."""
    
    # Signals
    finished = pyqtSignal(object)  # Emits SWE object when done
    error = pyqtSignal(str)  # Emits error message
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
            self.error.emit(str(e))