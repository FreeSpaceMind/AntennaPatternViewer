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
        """Calculate one expansion, supporting old and new FarField APIs."""
        calculate = self.pattern.calculate_spherical_modes
        parameters = inspect.signature(calculate).parameters
        kwargs = {
            'frequency': frequency,
            'nmax': self.nmax,
            'mmax': self.mmax,
        }

        # Newer farfield-spherical versions forward the enclosing-source
        # radius to SWE.  Accept either spelling while the package API settles.
        if 'r' in parameters:
            kwargs['r'] = self.r
            return calculate(**kwargs)
        if 'r0' in parameters:
            kwargs['r0'] = self.r
            return calculate(**kwargs)

        # Compatibility path for older FarField wrappers: perform the same
        # extraction here so r0 still reaches SWE's from_far_field method.
        return self._calculate_with_swe(frequency)

    def _calculate_with_swe(self, frequency):
        """Extract coefficients directly when FarField cannot forward r0."""
        from swe import SphericalWaveExpansion

        with self.pattern.at_frequency(frequency) as single_freq_pattern:
            single_freq_pattern.transform_coordinates('sided')
            theta_1d = np.radians(single_freq_pattern.theta_angles)
            phi_1d = np.radians(single_freq_pattern.phi_angles)
            e_theta = single_freq_pattern.data.e_theta.values[0, :, :]
            e_phi = single_freq_pattern.data.e_phi.values[0, :, :]
            theta, phi = np.meshgrid(theta_1d, phi_1d, indexing='ij')

            expansion = SphericalWaveExpansion.from_far_field(
                theta=theta.ravel(),
                phi=phi.ravel(),
                E_theta=e_theta.ravel(),
                E_phi=e_phi.ravel(),
                frequency=frequency,
                r0=self.r,
            )

        if self.nmax is None and self.mmax is None:
            return expansion

        n_limit = self.nmax if self.nmax is not None else expansion.NMAX(frequency)
        m_limit = self.mmax if self.mmax is not None else expansion.MMAX(frequency)
        q1 = {
            (n, m): value
            for (n, m), value in expansion.Q1_coeffs(frequency).items()
            if n <= n_limit and abs(m) <= m_limit
        }
        q2 = {
            (n, m): value
            for (n, m), value in expansion.Q2_coeffs(frequency).items()
            if n <= n_limit and abs(m) <= m_limit
        }
        return SphericalWaveExpansion(
            Q1_coeffs={frequency: q1},
            Q2_coeffs={frequency: q2},
            NMAX={frequency: n_limit},
            MMAX={frequency: m_limit},
        )

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
