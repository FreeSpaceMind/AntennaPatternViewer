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
        # DON'T connect to pattern_modified here - we update tabs ourselves after our own modifications
        # self.data_model.pattern_modified.connect(self.on_pattern_modified)  # REMOVE THIS
        
        # Connect processing signals
        self.processing_tab.apply_phase_center_signal.connect(self.on_apply_phase_center)
        self.processing_tab.apply_mars_signal.connect(self.on_apply_mars)
        self.processing_tab.polarization_changed.connect(self.on_polarization_changed)
        self.processing_tab.coordinate_format_changed.connect(self.on_coordinate_format_changed)
        
        # Connect analysis signals
        self.analysis_tab.calculate_swe_signal.connect(self.on_calculate_swe)
        self.analysis_tab.calculate_nearfield_signal.connect(self.on_calculate_nearfield)

    def on_view_params_changed(self):
        """Handle view parameter changes from view tab."""
        # Extract parameters from view tab and update model
        params = self.view_tab.get_current_parameters()
        self.data_model.update_view_params(params)
        logger.debug("View parameters updated from view tab")
        
        # Trigger plot update through data model
        self.data_model.view_parameters_changed.emit(params)
    
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
        """Handle phase center translation toggle."""
        if self.data_model.original_pattern is None:
            return
        
        try:
            # Get checkbox state from processing tab
            is_checked = self.processing_tab.apply_phase_center_check.isChecked()
            
            if is_checked:
                # Enable translation
                self.data_model.set_phase_center_translation([x, y, z])
                logger.info(f"Phase center translation enabled: [{x}, {y}, {z}]")
            else:
                # Disable translation
                self.data_model.set_phase_center_translation(None)
                logger.info("Phase center translation disabled")
            
            # Update our tabs
            self.processing_tab.update_pattern(self.data_model.pattern)
            
            # Trigger plot update
            self.data_model.view_parameters_changed.emit(self.data_model._view_params)
            
        except Exception as e:
            logger.error(f"Failed to toggle phase center translation: {e}", exc_info=True)

    def on_apply_mars(self, max_extent):
        """Handle MARS toggle."""
        if self.data_model.original_pattern is None:
            return
        
        try:
            # Get checkbox state from processing tab
            is_checked = self.processing_tab.apply_mars_check.isChecked()
            
            if is_checked:
                # Enable MARS
                self.data_model.set_mars(max_extent)
                logger.info(f"MARS enabled with max extent: {max_extent:.3f} m")
            else:
                # Disable MARS
                self.data_model.set_mars(None)
                logger.info("MARS disabled")
            
            # Update our tabs
            self.processing_tab.update_pattern(self.data_model.pattern)
            
            # Trigger plot update
            self.data_model.view_parameters_changed.emit(self.data_model._view_params)
            
        except Exception as e:
            logger.error(f"Failed to toggle MARS: {e}", exc_info=True)

    def on_coordinate_format_changed(self, new_format):
        """Handle coordinate format change request."""
        if self.data_model.original_pattern is None:
            return
        
        try:
            # Detect original format
            from antenna_pattern_viewer.plotting import detect_coordinate_format
            original_format = detect_coordinate_format(self.data_model.original_pattern)
            
            # Map combo text to format string
            format_map = {"Central": "central", "Sided": "sided", "central": "central", "sided": "sided"}
            target_format = format_map.get(new_format)
            
            # Only transform if different from original
            if target_format != original_format:
                self.data_model.set_coordinate_format(target_format)
            else:
                # Revert to original format (no transformation)
                self.data_model.set_coordinate_format(None)
            
            # Update our tabs
            self.processing_tab.update_pattern(self.data_model.pattern)
            
            # Trigger plot update
            self.data_model.view_parameters_changed.emit(self.data_model._view_params)
            
            logger.info(f"Coordinate format changed to: {new_format}")
            
        except Exception as e:
            logger.error(f"Failed to change coordinate format: {e}", exc_info=True)

    def on_polarization_changed(self, new_polarization):
        """Handle polarization change request."""
        if self.data_model.pattern is None:
            return
        
        if new_polarization == self.data_model.pattern.polarization:
            return
        
        try:
            # Polarization change modifies the current pattern directly
            # (It doesn't stack, so we can modify in place)
            pattern = self.data_model.pattern.copy()
            pattern.assign_polarization(new_polarization)
            
            self.data_model._pattern = pattern
            self.data_model.pattern_modified.emit(pattern)
            self.data_model.processing_applied.emit("polarization_conversion")
            
            # Update our tabs
            self.processing_tab.update_pattern(pattern)
            
            # Trigger plot update
            self.data_model.view_parameters_changed.emit(self.data_model._view_params)
            
            logger.info(f"Polarization converted to: {new_polarization}")
            
        except Exception as e:
            logger.error(f"Failed to convert polarization: {e}")

    def on_calculate_swe(self):
        """Handle SWE calculation request."""
        if self.data_model.pattern is None:
            return
        
        # Prevent multiple simultaneous calculations
        if hasattr(self, 'swe_worker') and self.swe_worker.isRunning():
            return
        
        try:
            from antenna_pattern_viewer.widgets.swe_worker import SWEWorker
            
            # Get parameters from analysis tab
            adaptive = self.analysis_tab.get_swe_adaptive()
            radius = None if adaptive else self.analysis_tab.get_swe_radius()
            frequency = self.analysis_tab.get_swe_frequency()
            
            # Update button state
            self.analysis_tab.calculate_swe_btn.setEnabled(False)
            self.analysis_tab.calculate_swe_btn.setText("Calculating...")
            
            # Create and configure worker thread
            self.swe_worker = SWEWorker(
                self.data_model.pattern,
                radius,
                frequency,
                adaptive
            )
            
            # Connect signals
            self.swe_worker.finished.connect(self.on_swe_finished)
            self.swe_worker.error.connect(self.on_swe_error)
            self.swe_worker.progress.connect(self.on_swe_progress)
            
            # Start the calculation in background
            self.swe_worker.start()
            
        except Exception as e:
            logger.error(f"Error starting SWE calculation: {e}", exc_info=True)
            self.analysis_tab.swe_results.setText(f"Error: {str(e)}")
            self.analysis_tab.calculate_swe_btn.setEnabled(True)
            self.analysis_tab.calculate_swe_btn.setText("Calculate SWE Coefficients")

    def on_swe_finished(self, swe_data):
        """Handle successful SWE calculation."""
        # Store SWE data in pattern
        pattern = self.data_model.pattern
        if hasattr(pattern, 'swe'):
            pattern.swe = swe_data
        
        # Display results
        self.analysis_tab.display_swe_results(swe_data)
        
        # Re-enable button
        self.analysis_tab.calculate_swe_btn.setEnabled(True)
        self.analysis_tab.calculate_swe_btn.setText("Calculate SWE Coefficients")
        
        logger.info("SWE calculation completed successfully")

    def on_swe_error(self, error_msg):
        """Handle SWE calculation error."""
        self.analysis_tab.swe_results.setText(f"Error: {error_msg}")
        
        # Re-enable button
        self.analysis_tab.calculate_swe_btn.setEnabled(True)
        self.analysis_tab.calculate_swe_btn.setText("Calculate SWE Coefficients")
        
        logger.error(f"SWE calculation failed: {error_msg}")

    def on_swe_progress(self, message):
        """Handle SWE calculation progress updates."""
        logger.debug(f"SWE progress: {message}")

    def on_calculate_nearfield(self):
        """Handle near field calculation request."""
        if self.data_model.pattern is None or not self.analysis_tab.swe_calculated:
            return
        
        try:
            # Get near field parameters
            surface_type = self.analysis_tab.get_nf_surface_type()
            
            # This would need implementation based on your nearfield calculation logic
            # For now, just log that it was requested
            logger.info(f"Near field calculation requested for {surface_type} surface")
            
        except Exception as e:
            logger.error(f"Failed to calculate near field: {e}")