"""
Export widget for saving antenna patterns.
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QRadioButton,
                            QComboBox, QPushButton, QLabel, QFileDialog, QMessageBox,
                            QHBoxLayout)
from PyQt6.QtCore import pyqtSignal
from pathlib import Path

import numpy as np
from farfield_spherical import FarFieldSpherical, write_cut, write_ffd, save_pattern_npz, write_ticra_sph


class ExportWidget(QWidget):
    """Widget for exporting antenna patterns with various options."""
    
    export_completed = pyqtSignal(str)  # Emits file path on successful export
    
    def __init__(self, data_model, parent=None):
        super().__init__(parent)
        self.data_model = data_model
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the export widget UI."""
        layout = QVBoxLayout()
        
        # Single export options group
        export_group = QGroupBox("Export Options")
        export_layout = QVBoxLayout()
        
        # File type selection
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("File Type:"))
        self.file_type_combo = QComboBox()
        self.file_type_combo.addItems([
            "NPZ (Numpy Archive)",
            "CUT (GRASP)",
            "FFD (HFSS)",
            "SPH (TICRA Spherical Modes)"
        ])
        type_layout.addWidget(self.file_type_combo)
        export_layout.addLayout(type_layout)
        
        # Frequency selection - side by side
        freq_layout = QHBoxLayout()
        self.freq_all = QRadioButton("All frequencies")
        self.freq_selected = QRadioButton("Selected only")
        self.freq_all.setChecked(True)
        freq_layout.addWidget(self.freq_all)
        freq_layout.addWidget(self.freq_selected)
        export_layout.addLayout(freq_layout)
        
        # Processing state selection - side by side
        processing_layout = QHBoxLayout()
        self.processing_with = QRadioButton("With processing")
        self.processing_raw = QRadioButton("Raw data")
        self.processing_with.setChecked(True)
        processing_layout.addWidget(self.processing_with)
        processing_layout.addWidget(self.processing_raw)
        export_layout.addLayout(processing_layout)
        
        export_group.setLayout(export_layout)
        layout.addWidget(export_group)
        
        # Status label
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)
        
        # Export button
        self.export_button = QPushButton("Export...")
        self.export_button.clicked.connect(self.on_export)
        layout.addWidget(self.export_button)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def get_file_extension(self):
        """Get file extension based on selected type."""
        type_text = self.file_type_combo.currentText()
        if "NPZ" in type_text:
            return ".npz"
        elif "CUT" in type_text:
            return ".cut"
        elif "FFD" in type_text:
            return ".ffd"
        elif "SPH" in type_text:
            return ".sph"
        return ".dat"
    
    def on_export(self):
        """Handle export button click."""
        if self.data_model.pattern is None:
            QMessageBox.warning(self, "No Data", "No pattern loaded to export.")
            return
        
        # Get file path from user
        extension = self.get_file_extension()
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Pattern",
            "",
            f"*{extension}"
        )
        
        if not file_path:
            return
        
        try:
            # Get pattern based on processing state selection
            if self.processing_raw.isChecked():
                pattern = self.data_model.original_pattern
            else:
                pattern = self.data_model.pattern
            
            if pattern is None:
                raise ValueError("No pattern available for export")
            
            # Handle frequency filtering for non-SPH formats
            type_text = self.file_type_combo.currentText()
            if "SPH" not in type_text and self.freq_selected.isChecked():
                selected_freqs = self.data_model.get_view_param('selected_frequencies')
                if not selected_freqs:
                    QMessageBox.warning(self, "No Selection", 
                                    "No frequency selected. Using first frequency.")
                    freq_idx = 0
                else:
                    freq_idx = selected_freqs[0]
                
                # Extract single frequency using data slicing
                freq_value = pattern.frequencies[freq_idx]
                pattern = FarFieldSpherical(
                    theta=pattern.theta_angles,
                    phi=pattern.phi_angles,
                    frequency=np.array([freq_value]),
                    e_theta=pattern.data.e_theta.values[freq_idx:freq_idx+1, :, :],
                    e_phi=pattern.data.e_phi.values[freq_idx:freq_idx+1, :, :],
                    polarization=pattern.polarization
                )
            
            self.write_pattern(pattern, file_path)
            
            self.status_label.setText(f"Exported: {Path(file_path).name}")
            self.export_completed.emit(file_path)

        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Failed to export:\n{str(e)}")
    
    def write_pattern(self, pattern, file_path):
        """Write pattern to file based on selected format."""
        type_text = self.file_type_combo.currentText()
        
        if "NPZ" in type_text:
            save_pattern_npz(pattern, file_path)
        elif "CUT" in type_text:
            write_cut(pattern, file_path)
        elif "FFD" in type_text:
            write_ffd(pattern, file_path)
        elif "SPH" in type_text:
            # Check if SWE has been pre-calculated
            if not hasattr(pattern, 'swe') or not pattern.swe:
                raise ValueError(
                    "Spherical wave expansion not calculated. "
                    "Please calculate SWE in the Analysis tab before exporting to SPH format."
                )
            
            # Export the first available SWE (user has already calculated the one they want)
            freq = list(pattern.swe.keys())[0]
            swe = pattern.swe[freq]
            write_ticra_sph(swe, file_path)