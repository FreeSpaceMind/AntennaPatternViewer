"""
View panel - Controls for visualizing pattern data.

Standalone panel for the icon sidebar navigation (no collapsible groups).
"""
import numpy as np
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QListWidget, QComboBox, QCheckBox, QLabel,
    QAbstractItemView, QPushButton, QDoubleSpinBox,
    QScrollArea, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, Qt


class ViewPanel(QWidget):
    """Panel containing visualization controls."""

    # Signal emitted when any parameter changes
    parameters_changed = pyqtSignal()

    def __init__(self, data_model, parent=None):
        super().__init__(parent)
        self.data_model = data_model
        self.current_pattern = None
        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        """Setup the view panel UI."""
        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Create scrollable widget
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        layout.setSpacing(10)

        # === FREQUENCY SELECTION ===
        freq_group = QGroupBox("Frequency Selection")
        freq_layout = QVBoxLayout(freq_group)

        self.frequency_list = QListWidget()
        self.frequency_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.frequency_list.setMaximumHeight(100)
        self.frequency_list.itemSelectionChanged.connect(self.parameters_changed.emit)
        freq_layout.addWidget(self.frequency_list)

        freq_buttons = QHBoxLayout()
        self.freq_select_all = QPushButton("Select All")
        self.freq_select_all.clicked.connect(self.select_all_frequencies)
        self.freq_clear_all = QPushButton("Clear All")
        self.freq_clear_all.clicked.connect(self.clear_all_frequencies)
        freq_buttons.addWidget(self.freq_select_all)
        freq_buttons.addWidget(self.freq_clear_all)
        freq_layout.addLayout(freq_buttons)

        layout.addWidget(freq_group)

        # === PHI ANGLE SELECTION ===
        phi_group = QGroupBox("Phi Angle Selection")
        phi_layout = QVBoxLayout(phi_group)

        self.phi_list = QListWidget()
        self.phi_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.phi_list.setMaximumHeight(100)
        self.phi_list.itemSelectionChanged.connect(self.parameters_changed.emit)
        phi_layout.addWidget(self.phi_list)

        phi_buttons = QHBoxLayout()
        self.phi_select_all = QPushButton("Select All")
        self.phi_select_all.clicked.connect(self.select_all_phi)
        self.phi_clear_all = QPushButton("Clear All")
        self.phi_clear_all.clicked.connect(self.clear_all_phi)
        phi_buttons.addWidget(self.phi_select_all)
        phi_buttons.addWidget(self.phi_clear_all)
        phi_layout.addLayout(phi_buttons)

        layout.addWidget(phi_group)

        # === PLOT SETTINGS ===
        plot_group = QGroupBox("Plot Settings")
        plot_layout = QVBoxLayout(plot_group)

        # Plot format and value type in a row
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Format:"))
        self.plot_format_combo = QComboBox()
        self.plot_format_combo.addItems(list(self.PLOT_FORMATS))
        self.plot_format_combo.currentTextChanged.connect(self.on_plot_format_changed)
        row1.addWidget(self.plot_format_combo)
        row1.addWidget(QLabel("Value:"))
        self.value_type_combo = QComboBox()
        self.value_type_combo.addItems(["Gain", "Phase", "Axial Ratio"])
        self.value_type_combo.currentTextChanged.connect(self.parameters_changed.emit)
        row1.addWidget(self.value_type_combo)
        plot_layout.addLayout(row1)

        # Component selection
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Component:"))
        self.component_combo = QComboBox()
        self.component_combo.addItems(["Co-pol", "Cross-pol", "E-theta", "E-phi"])
        self.component_combo.currentTextChanged.connect(self.parameters_changed.emit)
        row2.addWidget(self.component_combo)
        row2.addStretch()
        plot_layout.addLayout(row2)

        # Checkboxes in a row
        row3 = QHBoxLayout()
        self.show_cross_pol = QCheckBox("Show Cross-Pol")
        self.show_cross_pol.setChecked(False)
        self.show_cross_pol.toggled.connect(self.parameters_changed.emit)
        row3.addWidget(self.show_cross_pol)

        self.unwrap_phase = QCheckBox("Unwrap Phase")
        self.unwrap_phase.setChecked(False)
        self.unwrap_phase.toggled.connect(self.parameters_changed.emit)
        row3.addWidget(self.unwrap_phase)
        row3.addStretch()
        plot_layout.addLayout(row3)

        # Sweep metric, shown only for the Frequency Sweep format
        self.sweep_row = QWidget()
        row4 = QHBoxLayout(self.sweep_row)
        row4.setContentsMargins(0, 0, 0, 0)
        row4.addWidget(QLabel("Sweep metric:"))
        self.sweep_metric_combo = QComboBox()
        from ..plot_layouts import SWEEP_METRICS
        for key, label in SWEEP_METRICS.items():
            self.sweep_metric_combo.addItem(label, key)
        self.sweep_metric_combo.currentIndexChanged.connect(self.parameters_changed.emit)
        row4.addWidget(self.sweep_metric_combo)
        row4.addStretch()
        self.sweep_row.setVisible(False)
        plot_layout.addWidget(self.sweep_row)

        layout.addWidget(plot_group)

        # === STATISTICS ===
        stats_group = QGroupBox("Statistics")
        stats_layout = QVBoxLayout(stats_group)

        # Enable and show range checkboxes
        check_row = QHBoxLayout()
        self.enable_statistics = QCheckBox("Enable Statistics Plot")
        self.enable_statistics.setChecked(False)
        self.enable_statistics.toggled.connect(self.parameters_changed.emit)
        check_row.addWidget(self.enable_statistics)

        self.show_range = QCheckBox("Show Min/Max Range")
        self.show_range.setChecked(True)
        self.show_range.toggled.connect(self.parameters_changed.emit)
        check_row.addWidget(self.show_range)
        check_row.addStretch()
        stats_layout.addLayout(check_row)

        # Statistic type
        stat_row = QHBoxLayout()
        stat_row.addWidget(QLabel("Statistic:"))
        self.statistic_combo = QComboBox()
        self.statistic_combo.addItems(["mean", "median", "rms", "percentile", "std"])
        self.statistic_combo.currentTextChanged.connect(self.parameters_changed.emit)
        self.statistic_combo.currentTextChanged.connect(self.on_statistic_changed)
        stat_row.addWidget(self.statistic_combo)
        stat_row.addStretch()
        stats_layout.addLayout(stat_row)

        # Percentile range (hidden by default)
        self.percentile_widget = QWidget()
        percentile_layout = QHBoxLayout(self.percentile_widget)
        percentile_layout.setContentsMargins(0, 0, 0, 0)
        percentile_layout.addWidget(QLabel("Range:"))
        self.percentile_lower_spin = QDoubleSpinBox()
        self.percentile_lower_spin.setRange(0.0, 100.0)
        self.percentile_lower_spin.setValue(25.0)
        self.percentile_lower_spin.setSuffix("%")
        self.percentile_lower_spin.valueChanged.connect(self.parameters_changed.emit)
        percentile_layout.addWidget(self.percentile_lower_spin)
        percentile_layout.addWidget(QLabel("to"))
        self.percentile_upper_spin = QDoubleSpinBox()
        self.percentile_upper_spin.setRange(0.0, 100.0)
        self.percentile_upper_spin.setValue(75.0)
        self.percentile_upper_spin.setSuffix("%")
        self.percentile_upper_spin.valueChanged.connect(self.parameters_changed.emit)
        percentile_layout.addWidget(self.percentile_upper_spin)
        percentile_layout.addStretch()
        self.percentile_widget.setVisible(False)
        stats_layout.addWidget(self.percentile_widget)

        layout.addWidget(stats_group)

        # === PATTERN COMPARISON ===
        comparison_group = QGroupBox("Pattern Comparison")
        comparison_layout = QVBoxLayout(comparison_group)

        # Enable comparison checkbox
        self.enable_comparison = QCheckBox("Enable Multi-Pattern Plot")
        self.enable_comparison.setChecked(True)
        self.enable_comparison.setToolTip("Plot comparison patterns on the same axes")
        self.enable_comparison.toggled.connect(self.parameters_changed.emit)
        comparison_layout.addWidget(self.enable_comparison)

        # Status label showing compatibility
        self.comparison_status = QLabel("No patterns in comparison set")
        self.comparison_status.setStyleSheet("color: gray; font-style: italic;")
        comparison_layout.addWidget(self.comparison_status)

        layout.addWidget(comparison_group)

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

    def connect_signals(self):
        """Connect to data model signals."""
        self.data_model.pattern_loaded.connect(self.on_pattern_loaded)
        # Processing can change the theta/phi grids (a coordinate-format change
        # moves phi from 0-180 to 0-360), so the selection lists must refresh
        # on pattern_modified too or they offer angles that no longer exist.
        self.data_model.pattern_modified.connect(self.on_pattern_modified)

    def on_pattern_modified(self, pattern):
        """
        Refresh the selection lists after processing changed the grids.

        The previous frequency and phi selections are re-applied by nearest
        value, so a coordinate-format change keeps the user looking at roughly
        the same cuts instead of resetting to the default.
        """
        if pattern is None:
            return
        previous_freqs = self.get_selected_frequencies()
        previous_phi = self.get_selected_phi_angles()

        # Repopulate without announcing it: on_pattern_loaded resets the lists
        # to their first row, and anything listening would replot that single
        # cut before the previous selection is restored below. The restore
        # itself is silent, so the one emit at the end is what redraws.
        self.on_pattern_loaded(pattern, _announce=False)

        self._reselect_nearest(self.frequency_list, pattern.frequencies, previous_freqs)
        try:
            phi_angles = pattern.phi_angles
        except Exception:
            phi_angles = None
        if phi_angles is not None:
            self._reselect_nearest(self.phi_list, phi_angles, previous_phi)

        self.parameters_changed.emit()

    @staticmethod
    def _reselect_nearest(list_widget, available, previous_values):
        """Select the rows of `available` nearest to each previously chosen value."""
        import numpy as np

        if list_widget is None or previous_values is None or len(previous_values) == 0:
            return
        available = np.asarray(available, dtype=float)
        if available.size == 0:
            return
        wanted = {int(np.argmin(np.abs(available - float(v)))) for v in previous_values}
        list_widget.blockSignals(True)
        try:
            for row in range(list_widget.count()):
                item = list_widget.item(row)
                if item is not None:
                    item.setSelected(row in wanted)
        finally:
            list_widget.blockSignals(False)

    def on_pattern_loaded(self, pattern, _announce=True):
        """
        Handle pattern loaded event.

        ``_announce`` is False when the caller will restore a selection and
        emit ``parameters_changed`` itself; see ``on_pattern_modified``.
        """
        if pattern is None:
            self.current_pattern = None
            self.frequency_list.clear()
            self.phi_list.clear()
            return

        # Block signals during update to prevent index mismatch errors
        self.frequency_list.blockSignals(True)
        self.phi_list.blockSignals(True)

        self.current_pattern = pattern

        # Update frequency list
        self.frequency_list.clear()
        for freq in pattern.frequencies:
            self.frequency_list.addItem(f"{freq/1e6:.2f} MHz")
        self.frequency_list.setCurrentRow(0)

        # Update phi list
        self.phi_list.clear()
        for phi in pattern.phi_angles:
            self.phi_list.addItem(f"{phi:.1f}")
        self.phi_list.setCurrentRow(0)

        # Re-enable signals and emit change
        self.frequency_list.blockSignals(False)
        self.phi_list.blockSignals(False)
        if _announce:
            self.parameters_changed.emit()

    def get_current_parameters(self):
        """Get current view parameters as a dictionary."""
        params = {
            'selected_frequencies': self.get_selected_frequencies(),
            'selected_phi': self.get_selected_phi_angles(),
            'plot_type': self.get_plot_format(),
            'component': self.get_component(),
            'value_type': self.get_value_type(),
            'show_cross_pol': self.get_show_cross_pol(),
            'unwrap_phase': self.unwrap_phase.isChecked(),
            'statistics_enabled': self.get_statistics_enabled(),
            'show_range': self.get_show_range(),
            'statistic_type': self.get_statistic_type(),
            'percentile_range': self.get_percentile_range(),
            'enable_comparison': self.enable_comparison.isChecked(),
            'sweep_metric': self.get_sweep_metric(),
        }
        return params

    def update_comparison_status(self, num_patterns: int, compatibility: dict):
        """
        Update comparison status display.

        Args:
            num_patterns: Number of patterns in comparison set
            compatibility: Dict from data_model.get_comparison_compatibility()
        """
        if num_patterns == 0:
            self.comparison_status.setText("No patterns in comparison set")
            self.comparison_status.setStyleSheet("color: gray; font-style: italic;")
        elif compatibility.get('compatible', False):
            self.comparison_status.setText(f"{num_patterns} compatible pattern(s)")
            self.comparison_status.setStyleSheet("color: green; font-style: normal;")
        else:
            common_freq = len(compatibility.get('common_frequencies', []))
            common_phi = len(compatibility.get('common_phi', []))
            self.comparison_status.setText(
                f"{num_patterns} pattern(s) ({common_freq} common freq, {common_phi} common phi)"
            )
            self.comparison_status.setStyleSheet("color: orange; font-style: normal;")

    def select_all_frequencies(self):
        """Select all frequencies."""
        self.frequency_list.selectAll()

    def clear_all_frequencies(self):
        """Clear frequency selection."""
        self.frequency_list.clearSelection()

    def select_all_phi(self):
        """Select all phi angles."""
        self.phi_list.selectAll()

    def clear_all_phi(self):
        """Clear phi selection."""
        self.phi_list.clearSelection()

    def on_plot_format_changed(self):
        """Handle plot format change."""
        self.sweep_row.setVisible(self.get_plot_format() == 'sweep')
        self.parameters_changed.emit()

    def on_statistic_changed(self, statistic):
        """Handle statistic type change."""
        self.percentile_widget.setVisible(statistic == "percentile")

    # Getter methods
    def get_selected_frequencies(self):
        """Get list of selected frequencies."""
        if self.current_pattern is None:
            return []
        selected_items = self.frequency_list.selectedItems()
        if not selected_items:
            return [self.current_pattern.frequencies[0]]
        indices = [self.frequency_list.row(item) for item in selected_items]
        return [self.current_pattern.frequencies[i] for i in indices]

    def get_selected_phi_angles(self):
        """Get list of selected phi angles."""
        if self.current_pattern is None:
            return []
        selected_items = self.phi_list.selectedItems()
        if not selected_items:
            return [self.current_pattern.phi_angles[0]]
        indices = [self.phi_list.row(item) for item in selected_items]
        return [self.current_pattern.phi_angles[i] for i in indices]

    # Display name -> plot format key handed to the plot widget
    PLOT_FORMATS = {
        "1D Cut": "1d_cut",
        "2D Polar": "2d_polar",
        "Polar Cut": "polar_cut",
        "Amplitude + Phase": "amp_phase",
        "Small Multiples": "small_multiples",
        "Frequency Sweep": "sweep",
    }

    def get_plot_format(self):
        """Get selected plot format."""
        return self.PLOT_FORMATS.get(self.plot_format_combo.currentText(), "1d_cut")

    def set_plot_format(self, key: str):
        for name, value in self.PLOT_FORMATS.items():
            if value == key:
                self.plot_format_combo.setCurrentText(name)
                return

    def get_sweep_metric(self):
        return self.sweep_metric_combo.currentData() or 'peak_gain'

    def apply_parameters(self, params: dict):
        """
        Restore the panel from a get_current_parameters() dictionary (a
        session). Selections are re-applied by nearest value; one
        parameters_changed is emitted at the end.
        """
        if not params:
            return
        widgets = [self.plot_format_combo, self.value_type_combo, self.component_combo,
                   self.show_cross_pol, self.unwrap_phase, self.enable_statistics,
                   self.show_range, self.statistic_combo, self.enable_comparison,
                   self.sweep_metric_combo, self.frequency_list, self.phi_list]
        for w in widgets:
            w.blockSignals(True)
        try:
            if 'plot_type' in params:
                self.set_plot_format(params['plot_type'])
            if 'value_type' in params:
                text = {'gain': 'Gain', 'phase': 'Phase', 'axial_ratio': 'Axial Ratio'}.get(
                    params['value_type'])
                if text:
                    self.value_type_combo.setCurrentText(text)
            if 'component' in params:
                names = {'e_co': 'Co-pol', 'e_cx': 'Cross-pol', 'e_theta': 'E-theta', 'e_phi': 'E-phi'}
                if params['component'] in names:
                    self.component_combo.setCurrentText(names[params['component']])
            if 'show_cross_pol' in params:
                self.show_cross_pol.setChecked(bool(params['show_cross_pol']))
            if 'unwrap_phase' in params:
                self.unwrap_phase.setChecked(bool(params['unwrap_phase']))
            if 'statistics_enabled' in params:
                self.enable_statistics.setChecked(bool(params['statistics_enabled']))
            if 'show_range' in params:
                self.show_range.setChecked(bool(params['show_range']))
            if 'statistic_type' in params:
                self.statistic_combo.setCurrentText(str(params['statistic_type']))
            if 'enable_comparison' in params:
                self.enable_comparison.setChecked(bool(params['enable_comparison']))
            if 'sweep_metric' in params:
                index = self.sweep_metric_combo.findData(params['sweep_metric'])
                if index >= 0:
                    self.sweep_metric_combo.setCurrentIndex(index)
            if self.current_pattern is not None:
                if params.get('selected_frequencies'):
                    self._reselect_nearest(self.frequency_list, self.current_pattern.frequencies,
                                           params['selected_frequencies'])
                if params.get('selected_phi'):
                    self._reselect_nearest(self.phi_list, self.current_pattern.phi_angles,
                                           params['selected_phi'])
        finally:
            for w in widgets:
                w.blockSignals(False)
        self.sweep_row.setVisible(self.get_plot_format() == 'sweep')
        self.parameters_changed.emit()

    def get_value_type(self):
        """Get selected value type."""
        return self.value_type_combo.currentText().lower().replace(" ", "_")

    def get_component(self):
        """Get selected component."""
        component_map = {
            "Co-pol": "e_co",
            "Cross-pol": "e_cx",
            "E-theta": "e_theta",
            "E-phi": "e_phi"
        }
        return component_map[self.component_combo.currentText()]

    def get_show_cross_pol(self):
        """Get show cross-pol state."""
        return self.show_cross_pol.isChecked()

    def get_statistics_enabled(self):
        """Get statistics enabled state."""
        return self.enable_statistics.isChecked()

    def get_show_range(self):
        """Get show range state."""
        return self.show_range.isChecked()

    def get_statistic_type(self):
        """Get selected statistic type."""
        return self.statistic_combo.currentText()

    def get_percentile_range(self):
        """Get percentile range."""
        return (self.percentile_lower_spin.value(), self.percentile_upper_spin.value())
