"""
Control panel widget containing View and Processing controls.

Note: Analysis functionality has been moved to a separate AnalysisPanel widget.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QSizePolicy

from antenna_pattern_viewer.widgets.view_tab import ViewTab
from antenna_pattern_viewer.widgets.processing_tab import ProcessingTab

import logging
logger = logging.getLogger(__name__)


class ControlPanelWidget(QWidget):
    """Control panel with tabbed interface for View and Processing controls."""

    def __init__(self, data_model, parent=None):
        super().__init__(parent)
        self.data_model = data_model
        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        """Setup the control panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Create tab widget
        self.tab_widget = QTabWidget()

        # Create tabs (View and Processing only - Analysis moved to separate panel)
        self.view_tab = ViewTab()
        self.processing_tab = ProcessingTab()

        # Add tabs
        self.tab_widget.addTab(self.view_tab, "View")
        self.tab_widget.addTab(self.processing_tab, "Processing")

        layout.addWidget(self.tab_widget)

        # Allow auto-sizing
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

    def connect_signals(self):
        """Connect signals between tabs and data model."""
        # When view parameters change, update data model
        self.view_tab.parameters_changed.connect(self.on_view_params_changed)

        # When pattern is loaded/modified, update tabs
        self.data_model.pattern_loaded.connect(self.on_pattern_loaded)

        # Connect processing signals
        self.processing_tab.apply_phase_center_signal.connect(self.on_apply_phase_center)
        self.processing_tab.apply_mars_signal.connect(self.on_apply_mars)
        self.processing_tab.polarization_changed.connect(self.on_polarization_changed)
        self.processing_tab.coordinate_format_changed.connect(self.on_coordinate_format_changed)
        self.processing_tab.shift_theta_origin_signal.connect(self.on_shift_theta_origin)
        self.processing_tab.shift_phi_origin_signal.connect(self.on_shift_phi_origin)
        self.processing_tab.normalize_amplitude_signal.connect(self.on_normalize_amplitude)

    def on_view_params_changed(self):
        """Handle view parameter changes from view tab."""
        # Extract parameters from view tab and update model
        params = self.view_tab.get_current_parameters()
        self.data_model.update_view_params(params)
        
        # Trigger plot update through data model
        self.data_model.view_parameters_changed.emit(params)
    
    def on_pattern_loaded(self, pattern):
        """Update all tabs when new pattern is loaded."""
        self.view_tab.update_pattern(pattern)
        self.processing_tab.update_pattern(pattern)

        # Reset processing state
        self.processing_tab.reset_processing_state()

    def on_pattern_modified(self, pattern):
        """Update tabs when pattern is modified."""
        self.view_tab.update_pattern(pattern)
        self.processing_tab.update_pattern(pattern)
    
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
            else:
                # Disable translation
                self.data_model.set_phase_center_translation(None)
            
            # Update our tabs
            self.processing_tab.update_pattern(self.data_model.pattern)
            
            # Trigger plot update
            self.data_model.view_parameters_changed.emit(self.data_model._view_params)
            
        except Exception as e:
            print(f"Failed to toggle phase center translation: {e}", exc_info=True)

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
            else:
                # Disable MARS
                self.data_model.set_mars(None)
            
            # Update our tabs
            self.processing_tab.update_pattern(self.data_model.pattern)
            
            # Trigger plot update
            self.data_model.view_parameters_changed.emit(self.data_model._view_params)
            
        except Exception as e:
            print(f"Failed to toggle MARS: {e}", exc_info=True)

    def on_coordinate_format_changed(self, new_format):
        """Handle coordinate format change request."""
        if self.data_model.original_pattern is None:
            return
        
        try:
            # Detect original format
            from farfield_spherical import detect_coordinate_format
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
            
        except Exception as e:
            print(f"Failed to change coordinate format: {e}", exc_info=True)

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
            
        except Exception as e:
            print(f"Failed to convert polarization: {e}")

    # Note: SWE and Near Field calculation methods moved to AnalysisPanel

    def on_shift_theta_origin(self, theta_offset):
        """Handle theta origin shift toggle."""
        if self.data_model.original_pattern is None:
            return
        
        try:
            is_checked = self.processing_tab.apply_theta_shift_check.isChecked()
            
            if is_checked:
                self.data_model.set_theta_origin_shift(theta_offset)
                logger.info(f"Theta origin shift enabled: {theta_offset}°")
            else:
                self.data_model.set_theta_origin_shift(None)
                logger.info("Theta origin shift disabled")
            
            self.processing_tab.update_pattern(self.data_model.pattern)
            self.data_model.view_parameters_changed.emit(self.data_model._view_params)
            
        except Exception as e:
            logger.error(f"Failed to toggle theta origin shift: {e}", exc_info=True)

    def on_shift_phi_origin(self, phi_offset):
        """Handle phi origin shift toggle."""
        if self.data_model.original_pattern is None:
            return
        
        try:
            is_checked = self.processing_tab.apply_phi_shift_check.isChecked()
            
            if is_checked:
                self.data_model.set_phi_origin_shift(phi_offset)
                logger.info(f"Phi origin shift enabled: {phi_offset}°")
            else:
                self.data_model.set_phi_origin_shift(None)
                logger.info("Phi origin shift disabled")
            
            self.processing_tab.update_pattern(self.data_model.pattern)
            self.data_model.view_parameters_changed.emit(self.data_model._view_params)
            
        except Exception as e:
            logger.error(f"Failed to toggle phi origin shift: {e}", exc_info=True)

    def on_normalize_amplitude(self, norm_type):
        """Handle amplitude normalization toggle."""
        if self.data_model.original_pattern is None:
            return
        
        try:
            # Get checkbox state from processing tab
            is_checked = self.processing_tab.apply_normalization_check.isChecked()
            
            if is_checked:
                # Enable normalization
                self.data_model.set_amplitude_normalization(norm_type)
                logger.info(f"Amplitude normalization enabled: {norm_type}")
            else:
                # Disable normalization
                self.data_model.set_amplitude_normalization(None)
                logger.info("Amplitude normalization disabled")
            
            # Update tabs
            self.processing_tab.update_pattern(self.data_model.pattern)
            
            # Trigger plot update
            self.data_model.view_parameters_changed.emit(self.data_model._view_params)
            
        except Exception as e:
            logger.error(f"Failed to toggle amplitude normalization: {e}", exc_info=True)