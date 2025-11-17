"""
Data display widget showing numerical information and statistics.
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QTableWidget, QGroupBox)
from PyQt6.QtCore import Qt

class DataDisplayWidget(QWidget):
    """Widget for displaying numerical data and statistics."""
    
    def __init__(self, data_model, parent=None):
        super().__init__(parent)
        self.data_model = data_model
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        """Setup data display UI."""
        layout = QVBoxLayout(self)
        
        # Pattern info group
        info_group = QGroupBox("Pattern Information")
        info_layout = QVBoxLayout()
        
        self.info_label = QLabel("No pattern loaded")
        self.info_label.setStyleSheet("padding: 10px;")
        info_layout.addWidget(self.info_label)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Statistics group (placeholder)
        stats_group = QGroupBox("Statistics")
        stats_layout = QVBoxLayout()
        
        stats_label = QLabel("Statistics display coming soon")
        stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stats_label.setStyleSheet("color: #666; padding: 10px;")
        stats_layout.addWidget(stats_label)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # Add stretch to push everything to top
        layout.addStretch()
    
    def connect_signals(self):
        """Connect to data model signals."""
        self.data_model.pattern_loaded.connect(self.on_pattern_changed)
        self.data_model.pattern_modified.connect(self.on_pattern_changed)
    
    def on_pattern_changed(self, pattern):
        """Update display when pattern changes."""
        if pattern is None:
            self.info_label.setText("No pattern loaded")
            return
        
        # Display pattern info
        info_text = (
            f"<b>Frequencies:</b> {len(pattern.frequencies)}<br>"
            f"<b>Frequency Range:</b> {pattern.frequencies.min()/1e9:.3f} - "
            f"{pattern.frequencies.max()/1e9:.3f} GHz<br>"
            f"<b>Theta Points:</b> {len(pattern.theta_angles)}<br>"
            f"<b>Theta Range:</b> {pattern.theta_angles.min():.1f}° - "
            f"{pattern.theta_angles.max():.1f}°<br>"
            f"<b>Phi Points:</b> {len(pattern.phi_angles)}<br>"
            f"<b>Phi Range:</b> {pattern.phi_angles.min():.1f}° - "
            f"{pattern.phi_angles.max():.1f}°<br>"
            f"<b>Polarization:</b> {pattern.polarization}"
        )
        
        self.info_label.setText(info_text)