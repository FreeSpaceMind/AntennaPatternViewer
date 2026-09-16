"""
Processing panel - Controls for modifying pattern data.

Standalone panel for the icon sidebar navigation (no collapsible groups).
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QComboBox, QCheckBox, QPushButton, QDoubleSpinBox, QSpinBox,
    QScrollArea, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, Qt

import logging
logger = logging.getLogger(__name__)


class ProcessingPanel(QWidget):
    """Panel containing pattern processing controls."""

    # Signals for processing operations
    apply_phase_center_signal = pyqtSignal(float, float, float, float)  # x, y, z, frequency
    apply_mars_signal = pyqtSignal(float, int)  # max_radial_extent, taper
    polarization_changed = pyqtSignal(str)
    coordinate_format_changed = pyqtSignal(str)  # 'central' or 'sided'
    shift_theta_origin_signal = pyqtSignal(float)  # theta_offset in degrees
    shift_phi_origin_signal = pyqtSignal(float)  # phi_offset in degrees
    rotate_signal = pyqtSignal(float, float, float, str)  # alpha, beta, gamma (deg), interpolation
    normalize_amplitude_signal = pyqtSignal(str)  # normalization type
    normalize_boresight_signal = pyqtSignal(bool)  # enabled
    split_spheres_signal = pyqtSignal()
    average_spheres_signal = pyqtSignal()

    def __init__(self, data_model, parent=None):
        super().__init__(parent)
        self.data_model = data_model
        self.current_pattern = None
        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        """Setup the processing panel UI."""
        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Create scrollable widget
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        layout.setSpacing(6)

        # === POLARIZATION ===
        pol_group = QGroupBox("Polarization")
        pol_layout = QHBoxLayout(pol_group)
        self.polarization_combo = QComboBox()
        self.polarization_combo.addItems([
            "Theta", "Phi", "X (Ludwig-3)", "Y (Ludwig-3)", "RHCP", "LHCP"
        ])
        self.polarization_combo.currentTextChanged.connect(self.on_polarization_combo_changed)
        pol_layout.addWidget(self.polarization_combo)
        pol_layout.addStretch()
        layout.addWidget(pol_group)

        # === COORDINATE FORMAT & DUAL SPHERE (merged) ===
        coord_group = QGroupBox("Coordinate Format")
        coord_layout = QVBoxLayout(coord_group)
        coord_layout.setSpacing(4)

        coord_row = QHBoxLayout()
        coord_row.addWidget(QLabel("Format:"))
        self.coord_format_combo = QComboBox()
        self.coord_format_combo.addItems(["Central", "Sided"])
        self.coord_format_combo.currentTextChanged.connect(self.on_coordinate_format_changed)
        coord_row.addWidget(self.coord_format_combo)
        coord_row.addStretch()
        coord_layout.addLayout(coord_row)

        # Dual sphere status and buttons
        ds_row = QHBoxLayout()
        self.dual_sphere_status = QLabel("")
        self.dual_sphere_status.setStyleSheet("font-size: 9pt; color: #666;")
        ds_row.addWidget(self.dual_sphere_status, 1)

        self.split_spheres_btn = QPushButton("Split")
        self.split_spheres_btn.setToolTip("Split into two patterns: phi 0-180 and phi 180-360 remapped to 0-180")
        self.split_spheres_btn.setEnabled(False)
        self.split_spheres_btn.clicked.connect(self._on_split_spheres)
        ds_row.addWidget(self.split_spheres_btn)

        self.average_spheres_btn = QPushButton("Average")
        self.average_spheres_btn.setToolTip("Split and average the two spheres into a single pattern")
        self.average_spheres_btn.setEnabled(False)
        self.average_spheres_btn.clicked.connect(self._on_average_spheres)
        ds_row.addWidget(self.average_spheres_btn)

        coord_layout.addLayout(ds_row)
        layout.addWidget(coord_group)

        # === NORMALIZATION ===
        norm_group = QGroupBox("Normalization")
        norm_layout = QVBoxLayout(norm_group)
        norm_layout.setSpacing(4)

        norm_row = QHBoxLayout()
        self.apply_normalization_check = QCheckBox("Amplitude:")
        self.apply_normalization_check.toggled.connect(self.on_apply_normalization_toggled)
        norm_row.addWidget(self.apply_normalization_check)
        self.normalization_combo = QComboBox()
        self.normalization_combo.addItems(["Peak", "Boresight", "Mean"])
        self.normalization_combo.setToolTip(
            "Peak: Normalize to maximum gain\n"
            "Boresight: Normalize to boresight gain\n"
            "Mean: Normalize to mean gain"
        )
        norm_row.addWidget(self.normalization_combo)
        norm_row.addStretch()
        norm_layout.addLayout(norm_row)

        self.apply_boresight_norm_check = QCheckBox("Normalize at Boresight")
        self.apply_boresight_norm_check.setToolTip(
            "Force all phi cuts to cross at the same amplitude and phase at boresight"
        )
        self.apply_boresight_norm_check.toggled.connect(self.on_apply_boresight_norm_toggled)
        norm_layout.addWidget(self.apply_boresight_norm_check)

        layout.addWidget(norm_group)

        # === ORIGIN SHIFT ===
        origin_group = QGroupBox("Origin Shift (Measurement Correction)")
        origin_layout = QVBoxLayout(origin_group)
        origin_layout.setSpacing(4)

        origin_note = QLabel(
            "Re-zeroes the measured \u03b8/\u03c6 axes to correct a positioner or "
            "mounting offset. Each \u03c6 cut is shifted along its own axis. "
            "This does not rotate the antenna; use Rotation for that.")
        origin_note.setWordWrap(True)
        origin_note.setStyleSheet("font-size: 9pt; color: #666;")
        origin_layout.addWidget(origin_note)

        # Theta shift
        theta_row = QHBoxLayout()
        self.apply_theta_shift_check = QCheckBox("Theta:")
        self.apply_theta_shift_check.toggled.connect(self.on_apply_theta_shift_toggled)
        theta_row.addWidget(self.apply_theta_shift_check)
        self.theta_shift_spin = QDoubleSpinBox()
        self.theta_shift_spin.setRange(-180.0, 180.0)
        self.theta_shift_spin.setValue(0.0)
        self.theta_shift_spin.setSuffix(" deg")
        self.theta_shift_spin.setDecimals(1)
        self.theta_shift_spin.valueChanged.connect(self.on_theta_shift_value_changed)
        theta_row.addWidget(self.theta_shift_spin)
        theta_row.addStretch()
        origin_layout.addLayout(theta_row)

        # Phi shift
        phi_row = QHBoxLayout()
        self.apply_phi_shift_check = QCheckBox("Phi:")
        self.apply_phi_shift_check.toggled.connect(self.on_apply_phi_shift_toggled)
        phi_row.addWidget(self.apply_phi_shift_check)
        self.phi_shift_spin = QDoubleSpinBox()
        self.phi_shift_spin.setRange(-180.0, 180.0)
        self.phi_shift_spin.setValue(0.0)
        self.phi_shift_spin.setSuffix(" deg")
        self.phi_shift_spin.setDecimals(1)
        self.phi_shift_spin.valueChanged.connect(self.on_phi_shift_value_changed)
        phi_row.addWidget(self.phi_shift_spin)
        phi_row.addStretch()
        origin_layout.addLayout(phi_row)

        layout.addWidget(origin_group)

        # === ROTATION (ANTENNA ORIENTATION) ===
        rot_group = QGroupBox("Rotation (Antenna Orientation)")
        rot_layout = QVBoxLayout(rot_group)
        rot_layout.setSpacing(4)

        rot_note = QLabel(
            "Rigid 3D rotation of the antenna about the origin, field vectors "
            "included. Use this to change where the boresight points. "
            "+\u03b1 tilts the boresight toward +x, +\u03b2 toward +y, "
            "\u03b3 rolls about z from +x toward +y.")
        rot_note.setWordWrap(True)
        rot_note.setStyleSheet("font-size: 9pt; color: #666;")
        rot_layout.addWidget(rot_note)

        angles_row = QHBoxLayout()
        self.apply_rotation_check = QCheckBox("Apply")
        self.apply_rotation_check.toggled.connect(self.on_apply_rotation_toggled)
        angles_row.addWidget(self.apply_rotation_check)
        self.rot_alpha_spin = QDoubleSpinBox()
        self.rot_beta_spin = QDoubleSpinBox()
        self.rot_gamma_spin = QDoubleSpinBox()
        for label, spin, tip in (
                ("\u03b1:", self.rot_alpha_spin, "Azimuth about y: +\u03b1 tilts boresight toward +x"),
                ("\u03b2:", self.rot_beta_spin, "Elevation about x: +\u03b2 tilts boresight toward +y"),
                ("\u03b3:", self.rot_gamma_spin, "Roll about z, from +x toward +y")):
            angles_row.addWidget(QLabel(label))
            spin.setRange(-180.0, 180.0)
            spin.setValue(0.0)
            spin.setSuffix(" deg")
            spin.setDecimals(1)
            spin.setToolTip(tip)
            spin.valueChanged.connect(self.on_rotation_value_changed)
            angles_row.addWidget(spin)
        angles_row.addStretch()
        rot_layout.addLayout(angles_row)

        interp_row = QHBoxLayout()
        interp_row.addWidget(QLabel("Interpolation:"))
        self.rot_interp_combo = QComboBox()
        self.rot_interp_combo.addItems(["Linear", "Cubic"])
        self.rot_interp_combo.setToolTip(
            "Cubic is more accurate on coarse grids but slower")
        self.rot_interp_combo.currentTextChanged.connect(self.on_rotation_value_changed)
        interp_row.addWidget(self.rot_interp_combo)
        interp_row.addStretch()
        rot_layout.addLayout(interp_row)

        self.rotation_result = QLabel("")
        self.rotation_result.setStyleSheet("font-size: 9pt; color: #666;")
        rot_layout.addWidget(self.rotation_result)
        self._update_rotation_result()

        layout.addWidget(rot_group)

        # === PHASE CENTER ===
        pc_group = QGroupBox("Phase Center")
        pc_layout = QVBoxLayout(pc_group)
        pc_layout.setSpacing(4)

        # Find phase center controls
        find_row = QHBoxLayout()
        find_row.addWidget(QLabel("Theta:"))
        self.theta_angle_spin = QDoubleSpinBox()
        self.theta_angle_spin.setRange(0.0, 90.0)
        self.theta_angle_spin.setValue(45.0)
        self.theta_angle_spin.setSuffix(" deg")
        find_row.addWidget(self.theta_angle_spin)
        find_row.addWidget(QLabel("Freq:"))
        self.pc_freq_combo = QComboBox()
        find_row.addWidget(self.pc_freq_combo)
        self.find_phase_center_btn = QPushButton("Find")
        self.find_phase_center_btn.clicked.connect(self.on_find_phase_center)
        find_row.addWidget(self.find_phase_center_btn)
        pc_layout.addLayout(find_row)

        # Manual coordinates
        coords_row = QHBoxLayout()
        coords_row.addWidget(QLabel("X:"))
        self.pc_x_spin = QDoubleSpinBox()
        self.pc_x_spin.setRange(-1000.0, 1000.0)
        self.pc_x_spin.setSuffix(" mm")
        self.pc_x_spin.setDecimals(2)
        coords_row.addWidget(self.pc_x_spin)
        coords_row.addWidget(QLabel("Y:"))
        self.pc_y_spin = QDoubleSpinBox()
        self.pc_y_spin.setRange(-1000.0, 1000.0)
        self.pc_y_spin.setSuffix(" mm")
        self.pc_y_spin.setDecimals(2)
        coords_row.addWidget(self.pc_y_spin)
        coords_row.addWidget(QLabel("Z:"))
        self.pc_z_spin = QDoubleSpinBox()
        self.pc_z_spin.setRange(-1000.0, 1000.0)
        self.pc_z_spin.setSuffix(" mm")
        self.pc_z_spin.setDecimals(2)
        coords_row.addWidget(self.pc_z_spin)
        pc_layout.addLayout(coords_row)

        self.apply_phase_center_check = QCheckBox("Apply Phase Center Shift")
        self.apply_phase_center_check.toggled.connect(self.on_apply_phase_center_toggled)
        pc_layout.addWidget(self.apply_phase_center_check)

        self.phase_center_result = QLabel("")
        self.phase_center_result.setStyleSheet("font-size: 9pt; color: #666;")
        pc_layout.addWidget(self.phase_center_result)

        layout.addWidget(pc_group)

        # === MARS ALGORITHM ===
        mars_group = QGroupBox("MARS")
        mars_row = QHBoxLayout(mars_group)
        self.apply_mars_check = QCheckBox("Apply")
        self.apply_mars_check.toggled.connect(self.on_apply_mars_toggled)
        mars_row.addWidget(self.apply_mars_check)
        mars_row.addWidget(QLabel("Max Extent:"))
        self.max_radial_extent_spin = QDoubleSpinBox()
        self.max_radial_extent_spin.setRange(0.001, 10.0)
        self.max_radial_extent_spin.setValue(0.5)
        self.max_radial_extent_spin.setSuffix(" m")
        self.max_radial_extent_spin.setDecimals(3)
        self.max_radial_extent_spin.valueChanged.connect(self.on_mars_value_changed)
        mars_row.addWidget(self.max_radial_extent_spin)
        mars_row.addWidget(QLabel("Taper:"))
        self.mars_taper_spin = QSpinBox()
        self.mars_taper_spin.setRange(0, 100)
        self.mars_taper_spin.setValue(0)
        self.mars_taper_spin.setSuffix(" modes")
        self.mars_taper_spin.setToolTip(
            "Mode orders above k*D over which the filter rolls off with a raised cosine.\n"
            "0 is a brick wall. A taper reduces ringing of the removed reflection\n"
            "at the cost of keeping slightly more of it.")
        self.mars_taper_spin.valueChanged.connect(self.on_mars_value_changed)
        mars_row.addWidget(self.mars_taper_spin)
        mars_row.addStretch()
        layout.addWidget(mars_group)

        # Pipeline errors: a failing step rolls itself back, and the reason
        # belongs in front of the user rather than only in the log.
        self.processing_error = QLabel("")
        self.processing_error.setWordWrap(True)
        self.processing_error.setStyleSheet("color: #c00000; font-size: 9pt;")
        self.processing_error.setVisible(False)
        layout.addWidget(self.processing_error)

        # Add stretch
        layout.addStretch()

        # Set scroll widget
        scroll_area.setWidget(scroll_widget)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.addWidget(scroll_area)

        # Size policy
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        # Initially disable processing controls
        self.update_processing_controls_state()

    def show_processing_error(self, message):
        """Display a processing pipeline failure; the step has been rolled back."""
        self.processing_error.setText(
            f"Processing step failed and was switched off: {message}")
        self.processing_error.setVisible(True)

    def clear_processing_error(self):
        """Hide any previous processing failure message."""
        self.processing_error.clear()
        self.processing_error.setVisible(False)

    def connect_signals(self):
        """Connect to data model signals."""
        self.data_model.pattern_loaded.connect(self.on_pattern_loaded)
        self.data_model.processing_failed.connect(self.show_processing_error)
        # pattern_modified fires after the model has settled on a new state,
        # including when switching instances restores a saved one, so the
        # controls are mirrored from there rather than from pattern_loaded
        # alone (which runs before the restore).
        self.data_model.pattern_modified.connect(self.on_pattern_modified)

    def on_pattern_loaded(self, pattern):
        """Handle pattern loaded event."""
        if pattern is None:
            self.current_pattern = None
            self.pc_freq_combo.clear()
            # Clear the checkboxes too, or they keep claiming steps are applied
            # after the last pattern is unloaded.
            self.reset_processing_state()
            self.clear_processing_error()
            self.update_processing_controls_state()
            return

        self.current_pattern = pattern

        # Mirror the model's processing state, which is per pattern instance:
        # otherwise the checkboxes claim steps are applied to a pattern that
        # does not have them.
        self.sync_processing_controls()

        # Update frequency combo for phase center
        self.pc_freq_combo.clear()
        for freq in pattern.frequencies:
            self.pc_freq_combo.addItem(f"{freq/1e6:.2f} MHz")

        # Update polarization combo to match current pattern
        self.polarization_combo.blockSignals(True)
        pol_map = {
            'theta': 0, 'phi': 1,
            'x': 2, 'l3x': 2,
            'y': 3, 'l3y': 3,
            'rhcp': 4, 'rh': 4, 'r': 4,
            'lhcp': 5, 'lh': 5, 'l': 5
        }
        idx = pol_map.get(pattern.polarization.lower(), 0)
        self.polarization_combo.setCurrentIndex(idx)
        self.polarization_combo.blockSignals(False)

        # Update coordinate format
        try:
            from farfield_spherical import detect_coordinate_format
            current_format = detect_coordinate_format(pattern)
            format_idx = 0 if current_format == 'central' else 1
            self.coord_format_combo.blockSignals(True)
            self.coord_format_combo.setCurrentIndex(format_idx)
            self.coord_format_combo.blockSignals(False)
        except Exception:
            pass

        # Update dual sphere detection
        self._update_dual_sphere_status(pattern)

        self.update_processing_controls_state()

    def update_processing_controls_state(self):
        """Enable/disable processing controls based on pattern availability."""
        has_pattern = self.current_pattern is not None
        self.find_phase_center_btn.setEnabled(has_pattern)
        self.apply_phase_center_check.setEnabled(has_pattern)
        self.apply_mars_check.setEnabled(has_pattern)
        self.apply_theta_shift_check.setEnabled(has_pattern)
        self.apply_phi_shift_check.setEnabled(has_pattern)
        self.apply_rotation_check.setEnabled(has_pattern)
        self.apply_normalization_check.setEnabled(has_pattern)
        self.apply_boresight_norm_check.setEnabled(has_pattern)
        if not has_pattern:
            self.split_spheres_btn.setEnabled(False)
            self.average_spheres_btn.setEnabled(False)
            self.dual_sphere_status.setText("")

    def on_pattern_modified(self, pattern):
        """Mirror the model's settled processing state and clear any error."""
        self.current_pattern = pattern
        self.clear_processing_error()
        self.sync_processing_controls()

    def sync_processing_controls(self):
        """
        Set every processing control from the data model's current state.

        Signals are blocked throughout: these toggles are what drive the
        pipeline, so setting them here would re-apply what is already applied.
        """
        state = self.data_model._processing_state

        # Polarization combo follows the pattern itself, since the pipeline
        # may leave it at the value the file was loaded with.
        pattern = self.data_model.pattern
        if pattern is not None:
            pol_map = {
                'theta': 0, 'phi': 1,
                'x': 2, 'l3x': 2,
                'y': 3, 'l3y': 3,
                'rhcp': 4, 'rh': 4, 'r': 4,
                'lhcp': 5, 'lh': 5, 'l': 5
            }
            self.polarization_combo.blockSignals(True)
            self.polarization_combo.setCurrentIndex(
                pol_map.get(str(pattern.polarization).lower(), 0))
            self.polarization_combo.blockSignals(False)

        controls = {
            self.apply_phase_center_check: state.get('phase_center_translation') is not None,
            self.apply_mars_check: state.get('mars') is not None,
            self.apply_theta_shift_check: state.get('theta_origin_shift') is not None,
            self.apply_phi_shift_check: state.get('phi_origin_shift') is not None,
            self.apply_rotation_check: state.get('rotation') is not None,
            self.apply_normalization_check: state.get('amplitude_normalization') is not None,
            self.apply_boresight_norm_check: bool(state.get('boresight_normalization')),
        }
        for widget in controls:
            widget.blockSignals(True)
        try:
            for widget, checked in controls.items():
                widget.setChecked(checked)

            if state.get('theta_origin_shift') is not None:
                self.theta_shift_spin.blockSignals(True)
                self.theta_shift_spin.setValue(state['theta_origin_shift'])
                self.theta_shift_spin.blockSignals(False)
            if state.get('phi_origin_shift') is not None:
                self.phi_shift_spin.blockSignals(True)
                self.phi_shift_spin.setValue(state['phi_origin_shift'])
                self.phi_shift_spin.blockSignals(False)
            if state.get('mars') is not None:
                max_extent, taper = state['mars']
                for spin, value in ((self.max_radial_extent_spin, max_extent),
                                    (self.mars_taper_spin, taper)):
                    spin.blockSignals(True)
                    spin.setValue(value)
                    spin.blockSignals(False)
            if state.get('rotation') is not None:
                alpha, beta, gamma, method = state['rotation']
                for spin, value in ((self.rot_alpha_spin, alpha),
                                    (self.rot_beta_spin, beta),
                                    (self.rot_gamma_spin, gamma)):
                    spin.blockSignals(True)
                    spin.setValue(value)
                    spin.blockSignals(False)
                self.rot_interp_combo.blockSignals(True)
                self.rot_interp_combo.setCurrentText(method.capitalize())
                self.rot_interp_combo.blockSignals(False)
                self._update_rotation_result()
        finally:
            for widget in controls:
                widget.blockSignals(False)

    def reset_processing_state(self):
        """
        Clear every processing checkbox without re-triggering the pipeline.

        Signals are blocked because these toggles are what drive
        apply_processing; unblocked, resetting them would emit a disable for
        each step against a model that has already reset itself.
        """
        checks = [self.apply_phase_center_check, self.apply_mars_check,
                  self.apply_theta_shift_check, self.apply_phi_shift_check,
                  self.apply_rotation_check, self.apply_normalization_check,
                  self.apply_boresight_norm_check]
        for check in checks:
            check.blockSignals(True)
        try:
            for check in checks:
                check.setChecked(False)
        finally:
            for check in checks:
                check.blockSignals(False)

    # === EVENT HANDLERS ===

    def on_polarization_combo_changed(self, text):
        """Handle polarization combo box change."""
        pol_map = {
            "Theta": "theta", "Phi": "phi",
            "X (Ludwig-3)": "x", "Y (Ludwig-3)": "y",
            "RHCP": "rhcp", "LHCP": "lhcp"
        }
        new_pol = pol_map.get(text, "theta")
        self.polarization_changed.emit(new_pol)

    def on_coordinate_format_changed(self):
        """Handle coordinate format change."""
        format_map = {"Central": "central", "Sided": "sided"}
        format_type = format_map.get(self.coord_format_combo.currentText())
        if format_type:
            self.coordinate_format_changed.emit(format_type)

    def on_apply_normalization_toggled(self, checked):
        """Handle apply normalization checkbox toggle."""
        if not self.current_pattern:
            return
        norm_type = self.normalization_combo.currentText().lower()
        if checked:
            self.normalize_amplitude_signal.emit(norm_type)
        else:
            self.normalize_amplitude_signal.emit("")

    def on_apply_boresight_norm_toggled(self, checked):
        """Handle apply boresight normalization checkbox toggle."""
        if not self.current_pattern:
            return
        self.normalize_boresight_signal.emit(checked)

    def on_apply_theta_shift_toggled(self, checked):
        """Handle apply theta shift checkbox toggle."""
        if not self.current_pattern:
            return
        theta_offset = self.theta_shift_spin.value()
        self.shift_theta_origin_signal.emit(theta_offset)

    def on_theta_shift_value_changed(self, value):
        """Handle theta shift spinbox value change."""
        if not self.current_pattern:
            return
        if self.apply_theta_shift_check.isChecked():
            self.shift_theta_origin_signal.emit(value)

    def on_apply_phi_shift_toggled(self, checked):
        """Handle apply phi shift checkbox toggle."""
        if not self.current_pattern:
            return
        phi_offset = self.phi_shift_spin.value()
        self.shift_phi_origin_signal.emit(phi_offset)

    def on_phi_shift_value_changed(self, value):
        """Handle phi shift spinbox value change."""
        if not self.current_pattern:
            return
        if self.apply_phi_shift_check.isChecked():
            self.shift_phi_origin_signal.emit(value)

    def get_rotation(self):
        """(alpha, beta, gamma) in degrees and the interpolation method name."""
        return (self.rot_alpha_spin.value(), self.rot_beta_spin.value(),
                self.rot_gamma_spin.value(), self.rot_interp_combo.currentText().lower())

    def _update_rotation_result(self):
        """Show where the original boresight lands for the current angles."""
        import math
        alpha, beta, _, _ = self.get_rotation()
        a, b = math.radians(alpha), math.radians(beta)
        theta0 = math.degrees(math.acos(max(-1.0, min(1.0, math.cos(a) * math.cos(b)))))
        if theta0 < 1e-9:
            self.rotation_result.setText("Boresight stays at \u03b8 = 0\u00b0")
        else:
            phi0 = math.degrees(math.atan2(math.sin(b), math.sin(a) * math.cos(b))) % 360.0
            self.rotation_result.setText(
                f"Boresight \u2192 \u03b8 = {theta0:.1f}\u00b0, \u03c6 = {phi0:.1f}\u00b0")

    def on_apply_rotation_toggled(self, checked):
        """Handle apply rotation checkbox toggle."""
        if not self.current_pattern:
            return
        self.rotate_signal.emit(*self.get_rotation())

    def on_rotation_value_changed(self, _value=None):
        """Handle rotation angle or interpolation change."""
        self._update_rotation_result()
        if not self.current_pattern:
            return
        if self.apply_rotation_check.isChecked():
            self.rotate_signal.emit(*self.get_rotation())

    def on_find_phase_center(self):
        """Handle find phase center button click."""
        if not self.current_pattern:
            return

        theta_angle = self.theta_angle_spin.value()
        frequency = self.get_phase_center_frequency()

        if frequency is None:
            return

        try:
            phase_center = self.current_pattern.find_phase_center(theta_angle, frequency)
            self.set_manual_phase_center(phase_center)
            pc_text = f"[{phase_center[0]*1000:.2f}, {phase_center[1]*1000:.2f}, {phase_center[2]*1000:.2f}] mm"
            self.phase_center_result.setText(f"Phase center: {pc_text}")
        except Exception as e:
            self.phase_center_result.setText(f"Error: {str(e)}")

    def on_apply_phase_center_toggled(self, checked):
        """Handle apply phase center checkbox toggle."""
        if not self.current_pattern:
            return

        frequency = self.get_phase_center_frequency()
        if frequency is not None:
            phase_center = self.get_manual_phase_center()
            self.apply_phase_center_signal.emit(
                phase_center[0], phase_center[1], phase_center[2], frequency
            )

    def on_apply_mars_toggled(self, checked):
        """Handle apply MARS checkbox toggle."""
        if not self.current_pattern:
            return
        self.apply_mars_signal.emit(self.max_radial_extent_spin.value(),
                                    self.mars_taper_spin.value())

    def on_mars_value_changed(self, _value):
        """Re-apply MARS with the new extent or taper while it is enabled."""
        if not self.current_pattern:
            return
        if self.apply_mars_check.isChecked():
            self.apply_mars_signal.emit(self.max_radial_extent_spin.value(),
                                        self.mars_taper_spin.value())

    # === GETTERS/SETTERS ===

    def get_phase_center_frequency(self):
        """Get selected frequency for phase center calculation."""
        if self.current_pattern is None or self.pc_freq_combo.currentIndex() < 0:
            return None
        freq_index = self.pc_freq_combo.currentIndex()
        return self.current_pattern.frequencies[freq_index]

    def get_manual_phase_center(self):
        """Get manually entered phase center coordinates in meters."""
        x_mm = self.pc_x_spin.value()
        y_mm = self.pc_y_spin.value()
        z_mm = self.pc_z_spin.value()
        return [x_mm / 1000.0, y_mm / 1000.0, z_mm / 1000.0]

    def set_manual_phase_center(self, phase_center):
        """Set manual phase center coordinates from meters."""
        self.pc_x_spin.setValue(phase_center[0] * 1000.0)
        self.pc_y_spin.setValue(phase_center[1] * 1000.0)
        self.pc_z_spin.setValue(phase_center[2] * 1000.0)

    def get_polarization(self):
        """Get selected polarization type."""
        pol_map = {0: 'theta', 1: 'phi', 2: 'x', 3: 'y', 4: 'rhcp', 5: 'lhcp'}
        return pol_map.get(self.polarization_combo.currentIndex())

    # === DUAL SPHERE ===

    def _update_dual_sphere_status(self, pattern):
        """Detect dual sphere and update UI accordingly."""
        if pattern is None:
            self.dual_sphere_status.setText("")
            self.split_spheres_btn.setEnabled(False)
            self.average_spheres_btn.setEnabled(False)
            return

        try:
            from farfield_spherical import detect_dual_sphere
            result = detect_dual_sphere(pattern)
            if result['is_dual_sphere']:
                self.dual_sphere_status.setText(result['message'])
            else:
                self.dual_sphere_status.setText("")
            self.split_spheres_btn.setEnabled(result['is_dual_sphere'])
            self.average_spheres_btn.setEnabled(result['is_dual_sphere'])
        except Exception as e:
            self.dual_sphere_status.setText(f"Detection error: {e}")
            self.split_spheres_btn.setEnabled(False)
            self.average_spheres_btn.setEnabled(False)

    def _on_split_spheres(self):
        """Handle split spheres button click."""
        self.split_spheres_signal.emit()

    def _on_average_spheres(self):
        """Handle average spheres button click."""
        self.average_spheres_signal.emit()
