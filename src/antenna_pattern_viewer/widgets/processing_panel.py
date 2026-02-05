"""
Processing panel - Controls for modifying pattern data.

Standalone panel for the icon sidebar navigation (no collapsible groups).
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QComboBox, QCheckBox, QPushButton, QDoubleSpinBox,
    QScrollArea, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, Qt

import logging
logger = logging.getLogger(__name__)


class ProcessingPanel(QWidget):
    """Panel containing pattern processing controls."""

    # Signals for processing operations
    apply_phase_center_signal = pyqtSignal(float, float, float, float)  # x, y, z, frequency
    apply_mars_signal = pyqtSignal(float)  # max_radial_extent
    polarization_changed = pyqtSignal(str)
    coordinate_format_changed = pyqtSignal(str)  # 'central' or 'sided'
    shift_theta_origin_signal = pyqtSignal(float)  # theta_offset in degrees
    shift_phi_origin_signal = pyqtSignal(float)  # phi_offset in degrees
    normalize_amplitude_signal = pyqtSignal(str)  # normalization type

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
        layout.setSpacing(10)

        # === POLARIZATION ===
        pol_group = QGroupBox("Polarization")
        pol_layout = QHBoxLayout(pol_group)
        pol_layout.addWidget(QLabel("Polarization:"))
        self.polarization_combo = QComboBox()
        self.polarization_combo.addItems([
            "Theta", "Phi", "X (Ludwig-3)", "Y (Ludwig-3)", "RHCP", "LHCP"
        ])
        self.polarization_combo.currentTextChanged.connect(self.on_polarization_combo_changed)
        pol_layout.addWidget(self.polarization_combo)
        pol_layout.addStretch()
        layout.addWidget(pol_group)

        # === COORDINATE FORMAT ===
        coord_group = QGroupBox("Coordinate Format")
        coord_layout = QVBoxLayout(coord_group)

        coord_row = QHBoxLayout()
        coord_row.addWidget(QLabel("Format:"))
        self.coord_format_combo = QComboBox()
        self.coord_format_combo.addItems(["Central", "Sided"])
        self.coord_format_combo.currentTextChanged.connect(self.on_coordinate_format_changed)
        coord_row.addWidget(self.coord_format_combo)
        coord_row.addStretch()
        coord_layout.addLayout(coord_row)

        desc_label = QLabel("Central: theta +/-180, phi 0-180  |  Sided: theta 0-180, phi 0-360")
        desc_label.setStyleSheet("font-size: 9pt; color: #666;")
        coord_layout.addWidget(desc_label)

        layout.addWidget(coord_group)

        # === AMPLITUDE NORMALIZATION ===
        norm_group = QGroupBox("Amplitude Normalization")
        norm_layout = QVBoxLayout(norm_group)

        norm_row = QHBoxLayout()
        norm_row.addWidget(QLabel("Reference:"))
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

        self.apply_normalization_check = QCheckBox("Apply Amplitude Normalization")
        self.apply_normalization_check.toggled.connect(self.on_apply_normalization_toggled)
        norm_layout.addWidget(self.apply_normalization_check)

        layout.addWidget(norm_group)

        # === ORIGIN SHIFT ===
        origin_group = QGroupBox("Origin Shift")
        origin_layout = QVBoxLayout(origin_group)

        # Theta shift
        theta_row = QHBoxLayout()
        theta_row.addWidget(QLabel("Theta Offset:"))
        self.theta_shift_spin = QDoubleSpinBox()
        self.theta_shift_spin.setRange(-180.0, 180.0)
        self.theta_shift_spin.setValue(0.0)
        self.theta_shift_spin.setSuffix(" deg")
        self.theta_shift_spin.setDecimals(1)
        theta_row.addWidget(self.theta_shift_spin)

        self.apply_theta_shift_check = QCheckBox("Apply")
        self.apply_theta_shift_check.toggled.connect(self.on_apply_theta_shift_toggled)
        self.theta_shift_spin.valueChanged.connect(self.on_theta_shift_value_changed)
        theta_row.addWidget(self.apply_theta_shift_check)
        origin_layout.addLayout(theta_row)

        # Phi shift
        phi_row = QHBoxLayout()
        phi_row.addWidget(QLabel("Phi Offset:"))
        self.phi_shift_spin = QDoubleSpinBox()
        self.phi_shift_spin.setRange(-180.0, 180.0)
        self.phi_shift_spin.setValue(0.0)
        self.phi_shift_spin.setSuffix(" deg")
        self.phi_shift_spin.setDecimals(1)
        phi_row.addWidget(self.phi_shift_spin)

        self.apply_phi_shift_check = QCheckBox("Apply")
        self.apply_phi_shift_check.toggled.connect(self.on_apply_phi_shift_toggled)
        self.phi_shift_spin.valueChanged.connect(self.on_phi_shift_value_changed)
        phi_row.addWidget(self.apply_phi_shift_check)
        origin_layout.addLayout(phi_row)

        layout.addWidget(origin_group)

        # === PHASE CENTER ===
        pc_group = QGroupBox("Phase Center")
        pc_layout = QVBoxLayout(pc_group)

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

        self.phase_center_result = QLabel("Phase center: Not calculated")
        self.phase_center_result.setStyleSheet("font-size: 9pt; color: #666;")
        pc_layout.addWidget(self.phase_center_result)

        layout.addWidget(pc_group)

        # === MARS ALGORITHM ===
        mars_group = QGroupBox("MARS Algorithm")
        mars_layout = QVBoxLayout(mars_group)

        mars_row = QHBoxLayout()
        mars_row.addWidget(QLabel("Max Radial Extent:"))
        self.max_radial_extent_spin = QDoubleSpinBox()
        self.max_radial_extent_spin.setRange(0.001, 10.0)
        self.max_radial_extent_spin.setValue(0.5)
        self.max_radial_extent_spin.setSuffix(" m")
        self.max_radial_extent_spin.setDecimals(3)
        mars_row.addWidget(self.max_radial_extent_spin)
        mars_row.addStretch()
        mars_layout.addLayout(mars_row)

        self.apply_mars_check = QCheckBox("Apply MARS")
        self.apply_mars_check.toggled.connect(self.on_apply_mars_toggled)
        mars_layout.addWidget(self.apply_mars_check)

        layout.addWidget(mars_group)

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

    def connect_signals(self):
        """Connect to data model signals."""
        self.data_model.pattern_loaded.connect(self.on_pattern_loaded)

    def on_pattern_loaded(self, pattern):
        """Handle pattern loaded event."""
        if pattern is None:
            self.current_pattern = None
            self.pc_freq_combo.clear()
            self.update_processing_controls_state()
            return

        self.current_pattern = pattern

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

        self.update_processing_controls_state()

    def update_processing_controls_state(self):
        """Enable/disable processing controls based on pattern availability."""
        has_pattern = self.current_pattern is not None
        self.find_phase_center_btn.setEnabled(has_pattern)
        self.apply_phase_center_check.setEnabled(has_pattern)
        self.apply_mars_check.setEnabled(has_pattern)
        self.apply_theta_shift_check.setEnabled(has_pattern)
        self.apply_phi_shift_check.setEnabled(has_pattern)
        self.apply_normalization_check.setEnabled(has_pattern)

    def reset_processing_state(self):
        """Reset checkboxes when loading new pattern."""
        self.apply_phase_center_check.setChecked(False)
        self.apply_mars_check.setChecked(False)
        self.apply_theta_shift_check.setChecked(False)
        self.apply_phi_shift_check.setChecked(False)
        self.apply_normalization_check.setChecked(False)

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
        max_radial_extent = self.max_radial_extent_spin.value()
        self.apply_mars_signal.emit(max_radial_extent)

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
