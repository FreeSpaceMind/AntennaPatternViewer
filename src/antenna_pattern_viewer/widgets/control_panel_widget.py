"""
Control panel widget containing all user controls.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from PyQt6.QtCore import pyqtSignal
import logging

# Import existing tab widgets (to be migrated from antenna_pattern/gui)
from antenna_pattern_viewer.widgets.view_tab import ViewTab
from antenna_pattern_viewer.widgets.processing_tab import ProcessingTab
from antenna_pattern_viewer.widgets.analysis_tab import AnalysisTab

logger = logging.getLogger(__name__)


class ControlPanelWidget(QWidget):
    """Control panel with tabbed interface for pattern controls."""
    
    def __init__(self, data_model, parent=None):
        super().__init__(parent)
        self.data_model = data_model
        self.setup_ui()
        self.connect_signals()
        
        logger.debug("ControlPanelWidget initialized")
    
    def setup_ui(self):
        """Setup the control panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Create tabs (reuse existing tab widgets)
        self.view_tab = ViewTab()
        self.processing_tab = ProcessingTab()
        self.analysis_tab = AnalysisTab()
        
        # Add tabs
        self.tab_widget.addTab(self.view_tab, "View")
        self.tab_widget.addTab(self.processing_tab, "Processing")
        self.tab_widget.addTab(self.analysis_tab, "Analysis")
        
        layout.addWidget(self.tab_widget)
    
    def connect_signals(self):
        """Connect signals between tabs and data model."""
        # When view parameters change, update data model
        self.view_tab.parameters_changed.connect(self.on_view_params_changed)
        
        # When pattern is loaded/modified, update tabs
        self.data_model.pattern_loaded.connect(self.on_pattern_loaded)
        self.data_model.pattern_modified.connect(self.on_pattern_modified)
        
        # Connect processing signals
        self.processing_tab.apply_phase_center_signal.connect(self.on_apply_phase_center)
        self.processing_tab.apply_mars_signal.connect(self.on_apply_mars)
        self.processing_tab.polarization_changed.connect(self.on_polarization_changed)
        
        # Connect analysis signals
        self.analysis_tab.calculate_swe_signal.connect(self.on_calculate_swe)
        self.analysis_tab.calculate_nearfield_signal.connect(self.on_calculate_nearfield)
    
    def on_view_params_changed(self):
        """Handle view parameter changes from view tab."""
        # Extract parameters from view tab and update model
        params = self.view_tab.get_current_parameters()
        self.data_model.update_view_params(params)
        logger.debug("View parameters updated from view tab")
    
    def on_pattern_loaded(self, pattern):
        """Update all tabs when new pattern is loaded."""
        self.view_tab.update_pattern(pattern)
        self.processing_tab.update_pattern(pattern)
        self.analysis_tab.update_pattern(pattern)
        
        # Reset processing state
        self.processing_tab.reset_processing_state()
        
        logger.debug("All tabs updated with new pattern")
    
    def on_pattern_modified(self, pattern):
        """Update tabs when pattern is modified."""
        self.view_tab.update_pattern(pattern)
        self.processing_tab.update_pattern(pattern)
        self.analysis_tab.update_pattern(pattern)
        
        logger.debug("All tabs updated with modified pattern")
    
    def on_apply_phase_center(self, x, y, z, frequency):
        """Handle phase center translation request."""
        if self.data_model.pattern is None:
            return
        
        import numpy as np
        
        try:
            # Apply translation
            translation = np.array([x, y, z])
            pattern = self.data_model.pattern.copy()
            pattern.translate(translation, normalize=True)
            
            # Update model
            self.data_model.modify_pattern(pattern)
            self.data_model.processing_applied.emit("phase_center_translation")
            
            logger.info(f"Phase center translation applied: [{x}, {y}, {z}]")
            
        except Exception as e:
            logger.error(f"Failed to apply phase center translation: {e}")
    
    def on_apply_mars(self, angle):
        """Handle MARS rotation request."""
        if self.data_model.pattern is None:
            return
        
        try:
            # Apply MARS rotation
            pattern = self.data_model.pattern.copy()
            pattern.rotate(alpha=0, beta=angle, gamma=0)
            
            # Update model
            self.data_model.modify_pattern(pattern)
            self.data_model.processing_applied.emit("mars_rotation")
            
            logger.info(f"MARS rotation applied: {angle}°")
            
        except Exception as e:
            logger.error(f"Failed to apply MARS rotation: {e}")
    
    def on_polarization_changed(self, new_polarization):
        """Handle polarization change request."""
        if self.data_model.pattern is None:
            return
        
        try:
            # Change polarization
            pattern = self.data_model.pattern.copy()
            pattern.change_polarization(new_polarization)
            
            # Update model
            self.data_model.modify_pattern(pattern)
            self.data_model.processing_applied.emit("polarization_change")
            
            logger.info(f"Polarization changed to: {new_polarization}")
            
        except Exception as e:
            logger.error(f"Failed to change polarization: {e}")
    
    def on_calculate_swe(self):
        """Handle SWE calculation request."""
        if self.data_model.pattern is None:
            return
        
        logger.info("SWE calculation requested (not yet implemented)")
        # TODO: Implement SWE calculation
    
    def on_calculate_nearfield(self):
        """Handle near-field calculation request."""
        if self.data_model.pattern is None:
            return
        
        logger.info("Near-field calculation requested (not yet implemented)")
        # TODO: Implement near-field calculation