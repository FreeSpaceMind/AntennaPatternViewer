"""
Control panel widget containing all user controls.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from PyQt6.QtCore import pyqtSignal

# Import existing tab widgets (to be migrated from antenna_pattern/gui)
from antenna_pattern_viewer.widgets.view_tab import ViewTab
from antenna_pattern_viewer.widgets.processing_tab import ProcessingTab
from antenna_pattern_viewer.widgets.analysis_tab import AnalysisTab

import logging
logger = logging.getLogger(__name__)

class ControlPanelWidget(QWidget):
    """Control panel with tabbed interface for pattern controls."""

    nearfield_calculated = pyqtSignal(dict)  # Emits nearfield data
    
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
        self.processing_tab.shift_theta_origin_signal.connect(self.on_shift_theta_origin)
        self.processing_tab.shift_phi_origin_signal.connect(self.on_shift_phi_origin)
        self.processing_tab.normalize_amplitude_signal.connect(self.on_normalize_amplitude)
        
        # Connect analysis signals
        self.analysis_tab.calculate_swe_signal.connect(self.on_calculate_swe)
        self.analysis_tab.calculate_nearfield_signal.connect(self.on_calculate_nearfield)

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
        self.analysis_tab.update_pattern(pattern)
        
        # Reset processing state
        self.processing_tab.reset_processing_state()
    
    def on_pattern_modified(self, pattern):
        """Update tabs when pattern is modified."""
        self.view_tab.update_pattern(pattern)
        self.processing_tab.update_pattern(pattern)
        self.analysis_tab.update_pattern(pattern)
    
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

    def on_calculate_swe(self):
        """Handle SWE calculation request."""
        if self.data_model.pattern is None:
            return
        
        # Prevent multiple simultaneous calculations
        if hasattr(self, 'swe_worker') and self.swe_worker.isRunning():
            return
        
        try:
            from antenna_pattern_viewer.workers.swe_worker import SWEWorker
            
            # Get parameters from analysis tab
            frequency = self.analysis_tab.get_swe_frequency()
            
            # Update button state
            self.analysis_tab.calculate_swe_btn.setEnabled(False)
            self.analysis_tab.calculate_swe_btn.setText("Calculating...")
            
            # Create and configure worker thread
            self.swe_worker = SWEWorker(
                self.data_model.pattern,
                frequency
            )
            
            # Connect signals
            self.swe_worker.finished.connect(self.on_swe_finished)
            self.swe_worker.error.connect(self.on_swe_error)
            self.swe_worker.progress.connect(self.on_swe_progress)
            
            # Start the calculation in background
            self.swe_worker.start()
            
        except Exception as e:
            self.analysis_tab.swe_results.setText(f"Error: {str(e)}")
            self.analysis_tab.calculate_swe_btn.setEnabled(True)
            self.analysis_tab.calculate_swe_btn.setText("Calculate SWE Coefficients")

    def on_swe_finished(self, swe_obj):
        """Handle successful SWE calculation."""
        # Store SWE data in pattern
        pattern = self.data_model.pattern
        if not hasattr(pattern, 'swe'):
            pattern.swe = {}
        pattern.swe[swe_obj.frequency] = swe_obj
        
        # Display results
        self.analysis_tab.display_swe_results(swe_obj)
        
        # Re-enable button
        self.analysis_tab.calculate_swe_btn.setEnabled(True)
        self.analysis_tab.calculate_swe_btn.setText("Calculate SWE Coefficients")

    def on_swe_error(self, error_msg):
        """Handle SWE calculation error."""
        self.analysis_tab.swe_results.setText(f"Error: {error_msg}")
        
        # Re-enable button
        self.analysis_tab.calculate_swe_btn.setEnabled(True)
        self.analysis_tab.calculate_swe_btn.setText("Calculate SWE Coefficients")

    def on_swe_progress(self, message):
        """Handle SWE calculation progress updates."""
        pass

    def on_calculate_nearfield(self):
        """Handle near field calculation request."""
        if self.data_model.pattern is None or not self.analysis_tab.swe_calculated:
            return
        
        try:
            import numpy as np
            from swe import cartesian_to_spherical
            
            surface_type = self.analysis_tab.get_nf_surface_type()
            
            # Get the SWE object from the pattern
            pattern = self.data_model.pattern
            
            # Get the SWE object for the first (or selected) frequency
            freq = list(pattern.swe.keys())[0]
            swe = pattern.swe[freq]
            
            if surface_type == "spherical":
                # Get spherical parameters
                params = self.analysis_tab.get_nf_sphere_params()
                
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
                params = self.analysis_tab.get_nf_plane_params()
                
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
            
            # Store in analysis tab
            self.analysis_tab.nearfield_data = nf_data
            
            # Display results
            self.analysis_tab.display_nearfield_results(nf_data)
            
            # Emit signal so plot widget can display it
            self.nearfield_calculated.emit(nf_data)

        except Exception as e:
            import traceback
            error_msg = f"Error: {str(e)}\n{traceback.format_exc()}"
            self.analysis_tab.nf_results.setText(error_msg)

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