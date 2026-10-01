"""
Worker thread for SWE calculations to prevent GUI freezing.
"""

import logging
import traceback

from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class SWEWorker(QThread):
    """Worker thread for calculating one or more spherical wave expansions."""
    
    # Signals
    finished = pyqtSignal(object)  # Emits SWE object when done
    error = pyqtSignal(str)  # Emits error message (the traceback goes to the log)
    progress = pyqtSignal(str)  # Emits progress messages
    
    def __init__(self, pattern, frequency, r, nmax=None, mmax=None):
        super().__init__()
        self.pattern = pattern
        try:
            self.frequencies = [float(value) for value in frequency]
        except TypeError:
            self.frequencies = [float(frequency)]
        self.r = float(r)
        self.nmax = nmax
        self.mmax = mmax

    def _calculate_expansion(self, frequency):
        """Extract one expansion; the library forwards the source radius to SWE."""
        return self.pattern.calculate_spherical_modes(
            frequency=frequency, nmax=self.nmax, mmax=self.mmax, r0=self.r)

    def run(self):
        """Run the calculation in background thread."""
        try:
            expansions = []
            total = len(self.frequencies)
            for index, frequency in enumerate(self.frequencies, start=1):
                self.progress.emit(
                    f"Calculating spherical modes {index}/{total} "
                    f"({frequency / 1e9:.3f} GHz)..."
                )
                expansions.append(self._calculate_expansion(frequency))

            if len(expansions) == 1:
                combined = expansions[0]
            else:
                from swe import SphericalWaveExpansion

                q1_by_frequency = {}
                q2_by_frequency = {}
                nmax_by_frequency = {}
                mmax_by_frequency = {}
                for frequency, expansion in zip(self.frequencies, expansions):
                    q1_by_frequency[frequency] = expansion.Q1_coeffs(frequency)
                    q2_by_frequency[frequency] = expansion.Q2_coeffs(frequency)
                    nmax_by_frequency[frequency] = expansion.NMAX(frequency)
                    mmax_by_frequency[frequency] = expansion.MMAX(frequency)

                combined = SphericalWaveExpansion(
                    Q1_coeffs=q1_by_frequency,
                    Q2_coeffs=q2_by_frequency,
                    NMAX=nmax_by_frequency,
                    MMAX=mmax_by_frequency,
                )

            self.finished.emit(combined)
            
        except Exception as e:
            # str(e) alone is often unactionable (a bare LinAlgError, say), so
            # the full traceback is logged even though only the message is
            # shown in the panel.
            logger.error("SWE calculation failed:\n%s", traceback.format_exc())
            self.error.emit(str(e))
