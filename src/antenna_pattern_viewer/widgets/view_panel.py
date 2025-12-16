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
        self.plot_format_combo.addItems(["1D Cut", "2D Polar"])
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

    def on_pattern_loaded(self, pattern):
        """Handle pattern loaded event."""
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
            'enable_comparison': self.enable_comparison.isChecked()
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

    def get_plot_format(self):
        """Get selected plot format."""
        format_text = self.plot_format_combo.currentText()
        if "2D Polar" in format_text:
            return "2d_polar"
        else:
            return "1d_cut"

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
