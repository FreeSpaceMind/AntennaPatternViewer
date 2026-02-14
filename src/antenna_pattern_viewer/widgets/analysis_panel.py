"""
Analysis panel widget for SWE and near field calculations.

This is a standalone panel (not a tab) that provides analysis capabilities
including Spherical Wave Expansion and Near Field evaluation.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QComboBox, QPushButton, QDoubleSpinBox, QCheckBox,
    QScrollArea, QSpinBox, QTextEdit, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, Qt

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
import logging

logger = logging.getLogger(__name__)


class AnalysisPanel(QWidget):
    """
    Standalone panel for analysis operations.

    Contains:
    - Spherical Wave Expansion (SWE) calculation
    - Near Field evaluation from SWE coefficients

    This panel was extracted from the AnalysisTab to be a standalone
    panel in the new icon sidebar navigation.
    """

    # Signals
    nearfield_calculated = pyqtSignal(dict)  # Emits near field data

    def __init__(self, data_model, parent=None):
        super().__init__(parent)
        self.data_model = data_model
        self.current_pattern = None
        self.swe_calculated = False
        self.nearfield_data = None
        self.swe_worker = None

        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        """Setup the analysis panel UI."""
        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Create scrollable widget
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        layout.setSpacing(10)

        # === SPHERICAL WAVE EXPANSION ===
        swe_group = QGroupBox("Spherical Wave Expansion")
        swe_layout = QVBoxLayout(swe_group)

        swe_layout.addWidget(QLabel("Calculate spherical mode coefficients:"))

        # Frequency selection for SWE
        swe_freq_row = QHBoxLayout()
        swe_freq_row.addWidget(QLabel("Frequency:"))
        self.swe_freq_combo = QComboBox()
        swe_freq_row.addWidget(self.swe_freq_combo)
        swe_freq_row.addStretch()
        swe_layout.addLayout(swe_freq_row)

        # NMAX controls
        nmax_row = QHBoxLayout()
        nmax_row.addWidget(QLabel("NMAX:"))
        self.nmax_auto_check = QCheckBox("Auto")
        self.nmax_auto_check.setChecked(True)
        self.nmax_auto_check.toggled.connect(
            lambda checked: self.nmax_spin.setEnabled(not checked))
        nmax_row.addWidget(self.nmax_auto_check)
        self.nmax_spin = QSpinBox()
        self.nmax_spin.setRange(1, 500)
        self.nmax_spin.setValue(100)
        self.nmax_spin.setEnabled(False)
        self.nmax_spin.setToolTip("Maximum polar mode index (degree)")
        nmax_row.addWidget(self.nmax_spin)
        nmax_row.addStretch()
        swe_layout.addLayout(nmax_row)

        # MMAX controls
        mmax_row = QHBoxLayout()
        mmax_row.addWidget(QLabel("MMAX:"))
        self.mmax_auto_check = QCheckBox("Auto")
        self.mmax_auto_check.setChecked(True)
        self.mmax_auto_check.toggled.connect(
            lambda checked: self.mmax_spin.setEnabled(not checked))
        mmax_row.addWidget(self.mmax_auto_check)
        self.mmax_spin = QSpinBox()
        self.mmax_spin.setRange(0, 500)
        self.mmax_spin.setValue(50)
        self.mmax_spin.setEnabled(False)
        self.mmax_spin.setToolTip("Maximum azimuthal mode index (order)")
        mmax_row.addWidget(self.mmax_spin)
        mmax_row.addStretch()
        swe_layout.addLayout(mmax_row)

        # Calculate button
        self.calculate_swe_btn = QPushButton("Calculate SWE Coefficients")
        self.calculate_swe_btn.clicked.connect(self.on_calculate_swe)
        swe_layout.addWidget(self.calculate_swe_btn)

        # Results display
        self.swe_results = QTextEdit()
        self.swe_results.setReadOnly(True)
        self.swe_results.setMaximumHeight(150)
        self.swe_results.setPlaceholderText("SWE results will appear here...")
        swe_layout.addWidget(self.swe_results)

        # Power per mode plot
        self.power_figure = Figure(figsize=(4, 3))
        self.power_canvas = FigureCanvas(self.power_figure)
        self.power_canvas.setMinimumHeight(280)
        self.power_canvas.setVisible(False)
        swe_layout.addWidget(self.power_canvas)

        layout.addWidget(swe_group)

        # === NEAR FIELD EVALUATION ===
        nf_group = QGroupBox("Near Field Evaluation")
        nf_layout = QVBoxLayout(nf_group)

        nf_layout.addWidget(QLabel("Evaluate near field from SWE coefficients:"))

        # Surface type selection
        surface_row = QHBoxLayout()
        surface_row.addWidget(QLabel("Surface Type:"))
        self.nf_surface_combo = QComboBox()
        self.nf_surface_combo.addItems(["Spherical Surface", "Planar Surface"])
        self.nf_surface_combo.currentTextChanged.connect(self.on_surface_type_changed)
        surface_row.addWidget(self.nf_surface_combo)
        surface_row.addStretch()
        nf_layout.addLayout(surface_row)

        # Spherical surface controls
        self.sphere_controls_widget = QWidget()
        sphere_layout = QVBoxLayout(self.sphere_controls_widget)
        sphere_layout.setContentsMargins(0, 0, 0, 0)

        radius_row = QHBoxLayout()
        radius_row.addWidget(QLabel("Radius:"))
        self.nf_sphere_radius_spin = QDoubleSpinBox()
        self.nf_sphere_radius_spin.setRange(0.001, 10.0)
        self.nf_sphere_radius_spin.setValue(0.05)
        self.nf_sphere_radius_spin.setSuffix(" m")
        self.nf_sphere_radius_spin.setDecimals(4)
        radius_row.addWidget(self.nf_sphere_radius_spin)
        radius_row.addStretch()
        sphere_layout.addLayout(radius_row)

        theta_pts_row = QHBoxLayout()
        theta_pts_row.addWidget(QLabel("Theta Points:"))
        self.nf_theta_points_spin = QSpinBox()
        self.nf_theta_points_spin.setRange(10, 361)
        self.nf_theta_points_spin.setValue(91)
        theta_pts_row.addWidget(self.nf_theta_points_spin)
        theta_pts_row.addStretch()
        sphere_layout.addLayout(theta_pts_row)

        phi_pts_row = QHBoxLayout()
        phi_pts_row.addWidget(QLabel("Phi Points:"))
        self.nf_phi_points_spin = QSpinBox()
        self.nf_phi_points_spin.setRange(10, 361)
        self.nf_phi_points_spin.setValue(91)
        phi_pts_row.addWidget(self.nf_phi_points_spin)
        phi_pts_row.addStretch()
        sphere_layout.addLayout(phi_pts_row)

        nf_layout.addWidget(self.sphere_controls_widget)

        # Planar surface controls
        self.plane_controls_widget = QWidget()
        plane_layout = QVBoxLayout(self.plane_controls_widget)
        plane_layout.setContentsMargins(0, 0, 0, 0)

        x_extent_row = QHBoxLayout()
        x_extent_row.addWidget(QLabel("X Extent:"))
        self.nf_x_extent_spin = QDoubleSpinBox()
        self.nf_x_extent_spin.setRange(0.01, 10.0)
        self.nf_x_extent_spin.setValue(0.5)
        self.nf_x_extent_spin.setSuffix(" m")
        self.nf_x_extent_spin.setDecimals(3)
        x_extent_row.addWidget(self.nf_x_extent_spin)
        x_extent_row.addStretch()
        plane_layout.addLayout(x_extent_row)

        y_extent_row = QHBoxLayout()
        y_extent_row.addWidget(QLabel("Y Extent:"))
        self.nf_y_extent_spin = QDoubleSpinBox()
        self.nf_y_extent_spin.setRange(0.01, 10.0)
        self.nf_y_extent_spin.setValue(0.5)
        self.nf_y_extent_spin.setSuffix(" m")
        self.nf_y_extent_spin.setDecimals(3)
        y_extent_row.addWidget(self.nf_y_extent_spin)
        y_extent_row.addStretch()
        plane_layout.addLayout(y_extent_row)

        z_dist_row = QHBoxLayout()
        z_dist_row.addWidget(QLabel("Z Distance:"))
        self.nf_z_distance_spin = QDoubleSpinBox()
        self.nf_z_distance_spin.setRange(0.001, 10.0)
        self.nf_z_distance_spin.setValue(0.1)
        self.nf_z_distance_spin.setSuffix(" m")
        self.nf_z_distance_spin.setDecimals(4)
        z_dist_row.addWidget(self.nf_z_distance_spin)
        z_dist_row.addStretch()
        plane_layout.addLayout(z_dist_row)

        x_pts_row = QHBoxLayout()
        x_pts_row.addWidget(QLabel("X Points:"))
        self.nf_x_points_spin = QSpinBox()
        self.nf_x_points_spin.setRange(10, 501)
        self.nf_x_points_spin.setValue(51)
        x_pts_row.addWidget(self.nf_x_points_spin)
        x_pts_row.addStretch()
        plane_layout.addLayout(x_pts_row)

        y_pts_row = QHBoxLayout()
        y_pts_row.addWidget(QLabel("Y Points:"))
        self.nf_y_points_spin = QSpinBox()
        self.nf_y_points_spin.setRange(10, 501)
        self.nf_y_points_spin.setValue(51)
        y_pts_row.addWidget(self.nf_y_points_spin)
        y_pts_row.addStretch()
        plane_layout.addLayout(y_pts_row)

        nf_layout.addWidget(self.plane_controls_widget)

        # Initially hide plane controls
        self.plane_controls_widget.setVisible(False)

        # Calculate button
        self.calculate_nf_btn = QPushButton("Calculate Near Field")
        self.calculate_nf_btn.clicked.connect(self.on_calculate_nearfield)
        self.calculate_nf_btn.setEnabled(False)
        nf_layout.addWidget(self.calculate_nf_btn)

        # Results display
        self.nf_results = QTextEdit()
        self.nf_results.setReadOnly(True)
        self.nf_results.setMaximumHeight(120)
        self.nf_results.setPlaceholderText("Near field results will appear here...")
        nf_layout.addWidget(self.nf_results)

        layout.addWidget(nf_group)

        # Add stretch
        layout.addStretch()

        # Set scroll widget
        scroll_area.setWidget(scroll_widget)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.addWidget(scroll_area)

        # Set size policy
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

    def connect_signals(self):
        """Connect to data model signals."""
        self.data_model.pattern_loaded.connect(self.on_pattern_loaded)

    def on_pattern_loaded(self, pattern):
        """Handle pattern loaded event."""
        if pattern is None:
            self.current_pattern = None
            self.swe_calculated = False
            self.nearfield_data = None
            self.swe_freq_combo.clear()
            self.swe_results.clear()
            self.nf_results.clear()
            self.power_canvas.setVisible(False)
            self.calculate_swe_btn.setEnabled(False)
            self.calculate_nf_btn.setEnabled(False)
            return

        self.current_pattern = pattern
        self.nearfield_data = None

        # Update frequency combo for SWE
        self.swe_freq_combo.clear()
        for freq in pattern.frequencies:
            self.swe_freq_combo.addItem(f"{freq/1e6:.2f} MHz")

        # Check if pattern has loaded SWE data
        if hasattr(pattern, 'swe') and pattern.swe:
            self.swe_calculated = True
            self._display_loaded_swe_data()
            self.calculate_nf_btn.setEnabled(True)
            self.calculate_swe_btn.setEnabled(True)
        else:
            self.swe_calculated = False
            self.calculate_swe_btn.setEnabled(True)
            self.calculate_nf_btn.setEnabled(False)
            self.swe_results.clear()

        self.nf_results.clear()

    def on_surface_type_changed(self, surface_type):
        """Handle surface type change."""
        is_spherical = "Spherical" in surface_type
        self.sphere_controls_widget.setVisible(is_spherical)
        self.plane_controls_widget.setVisible(not is_spherical)

    def on_calculate_swe(self):
        """Handle SWE calculation request."""
        if self.current_pattern is None:
            return

        # Prevent multiple simultaneous calculations
        if self.swe_worker is not None and self.swe_worker.isRunning():
            return

        try:
            from antenna_pattern_viewer.workers.swe_worker import SWEWorker

            # Get frequency
            frequency = self.get_swe_frequency()
            if frequency is None:
                return

            # Read NMAX/MMAX settings
            nmax = None if self.nmax_auto_check.isChecked() else self.nmax_spin.value()
            mmax = None if self.mmax_auto_check.isChecked() else self.mmax_spin.value()

            # Update button state
            self.calculate_swe_btn.setEnabled(False)
            self.calculate_swe_btn.setText("Calculating...")

            # Create and configure worker thread
            self.swe_worker = SWEWorker(self.current_pattern, frequency,
                                        nmax=nmax, mmax=mmax)

            # Connect signals
            self.swe_worker.finished.connect(self.on_swe_finished)
            self.swe_worker.error.connect(self.on_swe_error)
            self.swe_worker.progress.connect(self.on_swe_progress)

            # Start the calculation in background
            self.swe_worker.start()

        except Exception as e:
            self.swe_results.setText(f"Error: {str(e)}")
            self.calculate_swe_btn.setEnabled(True)
            self.calculate_swe_btn.setText("Calculate SWE Coefficients")

    def on_swe_finished(self, swe_obj):
        """Handle successful SWE calculation."""
        # Store SWE data in pattern
        pattern = self.current_pattern
        if not hasattr(pattern, 'swe'):
            pattern.swe = {}
        pattern.swe[swe_obj.frequency] = swe_obj

        # Display results
        self.display_swe_results(swe_obj)

        # Re-enable button
        self.calculate_swe_btn.setEnabled(True)
        self.calculate_swe_btn.setText("Calculate SWE Coefficients")

    def on_swe_error(self, error_msg):
        """Handle SWE calculation error."""
        self.swe_results.setText(f"Error: {error_msg}")
        self.calculate_swe_btn.setEnabled(True)
        self.calculate_swe_btn.setText("Calculate SWE Coefficients")

    def on_swe_progress(self, message):
        """Handle SWE calculation progress updates."""
        pass

    def on_calculate_nearfield(self):
        """Handle near field calculation request."""
        if self.current_pattern is None or not self.swe_calculated:
            return

        try:
            from swe import cartesian_to_spherical

            surface_type = self.get_nf_surface_type()

            # Get the SWE object from the pattern
            pattern = self.current_pattern

            # Get the SWE object for the first (or selected) frequency
            freq = list(pattern.swe.keys())[0]
            swe = pattern.swe[freq]

            if surface_type == "spherical":
                # Get spherical parameters
                params = self.get_nf_sphere_params()

                # Create theta and phi arrays (in degrees)
                theta_deg = np.linspace(0, 180, params['theta_points'])
                phi_deg = np.linspace(0, 360, params['phi_points'])

                # Convert to radians
                theta_rad = np.radians(theta_deg)
                phi_rad = np.radians(phi_deg)

                # Create meshgrid
                THETA, PHI = np.meshgrid(theta_rad, phi_rad, indexing='ij')
                R = np.full_like(THETA, params['radius'])

                # Evaluate near field
                (E_r, E_theta, E_phi), (H_r, H_theta, H_phi) = swe.near_field(
                    R.ravel(), THETA.ravel(), PHI.ravel()
                )

                # Reshape to grid
                shape = THETA.shape
                nf_data = {
                    'E_r': E_r.reshape(shape),
                    'E_theta': E_theta.reshape(shape),
                    'E_phi': E_phi.reshape(shape),
                    'H_r': H_r.reshape(shape),
                    'H_theta': H_theta.reshape(shape),
                    'H_phi': H_phi.reshape(shape),
                    'theta': theta_deg,
                    'phi': phi_deg,
                    'radius': params['radius'],
                    'is_spherical': True
                }

            else:  # planar
                # Get planar parameters
                params = self.get_nf_plane_params()

                # Create x and y arrays
                x = np.linspace(-params['x_extent'], params['x_extent'], params['x_points'])
                y = np.linspace(-params['y_extent'], params['y_extent'], params['y_points'])

                # Create meshgrid
                X, Y = np.meshgrid(x, y, indexing='ij')
                Z = np.full_like(X, params['z_distance'])

                # Convert to spherical coordinates
                r, theta, phi = cartesian_to_spherical(X.ravel(), Y.ravel(), Z.ravel())

                # Evaluate near field in spherical coordinates
                (E_r, E_theta, E_phi), (H_r, H_theta, H_phi) = swe.near_field(r, theta, phi)

                # Reshape to grid
                shape = X.shape
                nf_data = {
                    'E_r': E_r.reshape(shape),
                    'E_theta': E_theta.reshape(shape),
                    'E_phi': E_phi.reshape(shape),
                    'H_r': H_r.reshape(shape),
                    'H_theta': H_theta.reshape(shape),
                    'H_phi': H_phi.reshape(shape),
                    'x': x,
                    'y': y,
                    'x_extent': params['x_extent'],
                    'y_extent': params['y_extent'],
                    'z_distance': params['z_distance'],
                    'is_spherical': False
                }

            # Store data
            self.nearfield_data = nf_data

            # Display results
            self.display_nearfield_results(nf_data)

            # Emit signal
            self.nearfield_calculated.emit(nf_data)

        except Exception as e:
            import traceback
            error_msg = f"Error: {str(e)}\n{traceback.format_exc()}"
            self.nf_results.setText(error_msg)
            logger.error(f"Near field calculation failed: {e}", exc_info=True)

    def display_swe_results(self, swe):
        """Display SWE calculation results with power-per-mode analysis."""
        self.swe_calculated = True
        self.calculate_nf_btn.setEnabled(True)

        result_text = "SWE Coefficients calculated:\n"
        result_text += f"Frequency: {swe.frequency/1e9:.3f} GHz\n"
        result_text += f"Mode indices: MMAX={swe.MMAX}, NMAX={swe.NMAX}\n"

        # Calculate total modes
        total_modes = len(swe.Q1_coeffs) + len(swe.Q2_coeffs)
        result_text += f"Total coefficients: {total_modes}\n"

        # Calculate total power
        total_power = sum(abs(q)**2 for q in swe.Q1_coeffs.values())
        total_power += sum(abs(q)**2 for q in swe.Q2_coeffs.values())
        result_text += f"Total power: {total_power:.6e} W\n"

        self.swe_results.setText(result_text)

        # Compute and plot power distributions
        power_per_n, power_per_m = self._compute_power_distributions(swe)
        self._plot_power_distributions(power_per_n, power_per_m)

    def _compute_power_distributions(self, swe):
        """Compute power aggregated by n and by |m|."""
        all_modes = set(swe.Q1_coeffs.keys()) | set(swe.Q2_coeffs.keys())

        power_per_n = {}
        power_per_m = {}
        for (n, m) in all_modes:
            q1 = swe.Q1_coeffs.get((n, m), 0)
            q2 = swe.Q2_coeffs.get((n, m), 0)
            mode_power = abs(q1)**2 + abs(q2)**2
            power_per_n[n] = power_per_n.get(n, 0) + mode_power
            power_per_m[abs(m)] = power_per_m.get(abs(m), 0) + mode_power

        return power_per_n, power_per_m

    def _plot_power_distributions(self, power_per_n, power_per_m):
        """Plot cumulative power vs n and power per |m|."""
        self.power_figure.clear()

        # Top subplot: Cumulative power vs n
        ax1 = self.power_figure.add_subplot(2, 1, 1)
        n_values = sorted(power_per_n.keys())
        powers_n = np.array([power_per_n[n] for n in n_values])
        total_power = powers_n.sum()
        if total_power > 0:
            cumulative = np.cumsum(powers_n) / total_power * 100.0
        else:
            cumulative = np.zeros_like(powers_n)

        ax1.plot(n_values, cumulative, 'b-', linewidth=1.5)
        ax1.axhline(y=99.9, color='r', linestyle='--', alpha=0.7, label='99.9%')
        ax1.set_xlabel('Mode order n')
        ax1.set_ylabel('Cumulative power (%)')
        ax1.set_title('Power convergence', fontsize=9)
        ax1.legend(fontsize=7)
        ax1.grid(True, alpha=0.3)
        if len(cumulative) > 0:
            ax1.set_ylim([max(0, cumulative[0] - 5), 100.5])

        # Bottom subplot: Power per |m|
        ax2 = self.power_figure.add_subplot(2, 1, 2)
        m_values = sorted(power_per_m.keys())
        powers_m = np.array([power_per_m[m] for m in m_values])
        if total_power > 0:
            powers_m_db = 10 * np.log10(np.maximum(powers_m / total_power, 1e-15))
        else:
            powers_m_db = np.full_like(powers_m, -150.0)

        ax2.bar(m_values, powers_m_db, color='steelblue', alpha=0.8)
        ax2.set_xlabel('Azimuthal index |m|')
        ax2.set_ylabel('Relative power (dB)')
        ax2.set_title('Power per azimuthal mode', fontsize=9)
        ax2.grid(True, alpha=0.3, axis='y')

        self.power_figure.tight_layout()
        self.power_canvas.setVisible(True)
        self.power_canvas.draw()

    def display_nearfield_results(self, nf_data):
        """Display near field calculation results."""
        surface_type = "spherical" if nf_data.get('is_spherical', True) else "planar"
        result_text = f"Near Field Calculated ({surface_type}):\n"

        if surface_type == "spherical":
            result_text += f"Radius: {nf_data['radius']:.4f} m\n"
            result_text += f"Theta points: {len(nf_data['theta'])}\n"
            result_text += f"Phi points: {len(nf_data['phi'])}\n"
        else:
            result_text += f"X extent: +/-{nf_data['x_extent']:.3f} m\n"
            result_text += f"Y extent: +/-{nf_data['y_extent']:.3f} m\n"
            result_text += f"Z distance: {nf_data['z_distance']:.4f} m\n"
            result_text += f"Grid: {len(nf_data['x'])} x {len(nf_data['y'])} points\n"

        self.nf_results.setText(result_text)

    def _display_loaded_swe_data(self):
        """Display SWE data that was loaded from file."""
        if not hasattr(self.current_pattern, 'swe') or not self.current_pattern.swe:
            return

        num_frequencies = len(self.current_pattern.swe)
        swe_for_plot = None

        if num_frequencies == 1:
            # Single frequency - display detailed info
            freq = list(self.current_pattern.swe.keys())[0]
            swe = self.current_pattern.swe[freq]
            swe_for_plot = swe

            result_text = "SWE Coefficients (loaded from file):\n"
            result_text += f"Frequency: {swe.frequency/1e9:.3f} GHz\n"

            # Calculate wavelength
            wavelength = 299792458.0 / swe.frequency if swe.frequency else 0
            if hasattr(swe, 'radius'):
                result_text += f"Radius: {swe.radius:.4f} m ({swe.radius/wavelength:.2f} lambda)\n"

            result_text += f"Mode indices: MMAX={swe.MMAX}, NMAX={swe.NMAX}\n"

            # Calculate total modes
            total_modes = len(swe.Q1_coeffs) + len(swe.Q2_coeffs)
            result_text += f"Total coefficients: {total_modes}\n"

            # Calculate total power if possible
            total_power = sum(abs(q)**2 for q in swe.Q1_coeffs.values())
            total_power += sum(abs(q)**2 for q in swe.Q2_coeffs.values())
            result_text += f"Total power: {total_power:.6e} W\n"

        else:
            # Multiple frequencies - display summary, use first for plot
            swe_for_plot = list(self.current_pattern.swe.values())[0]

            result_text = f"SWE Coefficients (loaded from file):\n"
            result_text += f"{num_frequencies} frequencies with SWE data:\n\n"

            for freq, swe in self.current_pattern.swe.items():
                result_text += f"  - {swe.frequency/1e9:.3f} GHz: "
                result_text += f"MMAX={swe.MMAX}, NMAX={swe.NMAX}"

                if hasattr(swe, 'radius'):
                    wavelength = 299792458.0 / swe.frequency
                    result_text += f", R={swe.radius:.4f} m ({swe.radius/wavelength:.2f} lambda)"
                result_text += "\n"

        self.swe_results.setText(result_text)

        # Plot power distributions
        if swe_for_plot is not None:
            power_per_n, power_per_m = self._compute_power_distributions(swe_for_plot)
            self._plot_power_distributions(power_per_n, power_per_m)

    # Getter methods
    def get_swe_frequency(self):
        """Get selected frequency for SWE."""
        if self.current_pattern is None or self.swe_freq_combo.currentIndex() < 0:
            return None
        freq_index = self.swe_freq_combo.currentIndex()
        return self.current_pattern.frequencies[freq_index]

    def get_nf_surface_type(self):
        """Get near field surface type."""
        text = self.nf_surface_combo.currentText()
        return "spherical" if "Spherical" in text else "planar"

    def get_nf_sphere_params(self):
        """Get spherical surface parameters."""
        return {
            'radius': self.nf_sphere_radius_spin.value(),
            'theta_points': self.nf_theta_points_spin.value(),
            'phi_points': self.nf_phi_points_spin.value()
        }

    def get_nf_plane_params(self):
        """Get planar surface parameters."""
        return {
            'x_extent': self.nf_x_extent_spin.value(),
            'y_extent': self.nf_y_extent_spin.value(),
            'z_distance': self.nf_z_distance_spin.value(),
            'x_points': self.nf_x_points_spin.value(),
            'y_points': self.nf_y_points_spin.value()
        }
