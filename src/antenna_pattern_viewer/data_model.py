"""
Shared data model for antenna pattern viewer GUI.
"""
from PyQt6.QtCore import QObject, pyqtSignal
from typing import Optional, Dict, Any, List, Set
from antenna_pattern_viewer.pattern_instance import PatternInstance

import logging
logger = logging.getLogger(__name__)

class PatternDataModel(QObject):
    """
    Central data model that holds antenna pattern state and emits signals on changes.
    
    This model serves as the single source of truth for the pattern data and view
    parameters. All widgets connect to this model to stay synchronized.
    """
    
    # Signals emitted when data changes
    pattern_loaded = pyqtSignal(object)  # Emits FarFieldSpherical pattern
    pattern_modified = pyqtSignal(object)  # Emits FarFieldSpherical pattern after modification
    view_parameters_changed = pyqtSignal(dict)  # Emits view params dict
    processing_applied = pyqtSignal(str)  # Emits processing type name
    instances_changed = pyqtSignal()  # Emitted when instance list changes
    active_instance_changed = pyqtSignal(object)  # Emits PatternInstance
    comparison_set_changed = pyqtSignal(list)  # Emits list of instance IDs
    
    def __init__(self):
        super().__init__()
        self._pattern: Optional[Any] = None  # Current (possibly processed) pattern
        self._original_pattern: Optional[Any] = None  # Original unprocessed pattern
        self._file_path: Optional[str] = None
        
        # Processing state flags
        self._processing_state = {
            'phase_center_translation': None,  # [x, y, z] or None
            'mars_max_extent': None,  # float or None
            'coordinate_format': None,  # 'central', 'sided', or None (original)
            'theta_origin_shift': None,
            'phi_origin_shift': None,
            'amplitude_normalization': None,
            'boresight_normalization': False,
        }
        
        # View parameters
        self._view_params = {
            'selected_frequencies': [],
            'selected_phi': [],
            'selected_theta': [],
            'plot_type': '1d_cut',
            'component': 'e_co',
            'value_type': 'gain',
            'normalize': False,
            'unwrap_phase': True,
            'statistics_enabled': False,
            'statistic_type': 'mean',
        }

        # Multi-pattern management
        self._instances: Dict[str, PatternInstance] = {}
        self._active_instance_id: Optional[str] = None
        self._comparison_instance_ids: Set[str] = set()
    
    @property
    def pattern(self) -> Optional[Any]:
        """Get current pattern."""
        return self._pattern
    
    @property
    def original_pattern(self) -> Optional[Any]:
        """Get original unprocessed pattern."""
        return self._original_pattern
    
    def set_pattern(self, pattern: Any, file_path: Optional[str] = None):
        """
        Set new pattern and emit signal.
        
        Args:
            pattern: FarFieldSpherical object
            file_path: Optional path to the source file
        """
        self._original_pattern = pattern
        self._pattern = pattern
        self._file_path = file_path
        
        # Reset processing state
        self._processing_state = {
            'phase_center_translation': None,
            'mars_max_extent': None,
            'coordinate_format': None,
            'theta_origin_shift': None,
            'phi_origin_shift': None,
            'amplitude_normalization': None,
            'boresight_normalization': False,
        }
        
        # Reset view parameters when loading new pattern
        if pattern is not None:
            self._view_params['selected_frequencies'] = []
            self._view_params['selected_phi'] = []
            self._view_params['selected_theta'] = []
        
        self.pattern_loaded.emit(pattern)

    def apply_processing(self):
        """
        Apply all enabled processing operations to the original pattern.
        This always starts from the original pattern to avoid stacking errors.
        """
        if self._original_pattern is None:
            return
        
        # Start with a copy of the original
        processed = self._original_pattern.copy()
        
        # Apply coordinate transformation first (if any)
        if self._processing_state['coordinate_format'] is not None:
            processed.transform_coordinates(self._processing_state['coordinate_format'])

        # Apply amplitude normalization (if any)
        if self._processing_state['amplitude_normalization'] is not None:
            processed.normalize_amplitude(self._processing_state['amplitude_normalization'])

        # Apply boresight normalization (if enabled)
        if self._processing_state['boresight_normalization']:
            processed.normalize_at_boresight()

        # Apply origin shifts (if any)
        if self._processing_state['theta_origin_shift'] is not None:
            processed.shift_theta_origin(self._processing_state['theta_origin_shift'])
        
        if self._processing_state['phi_origin_shift'] is not None:
            processed.shift_phi_origin(self._processing_state['phi_origin_shift'])
        
        # Apply phase center translation (if any)
        if self._processing_state['phase_center_translation'] is not None:
            import numpy as np
            translation = np.array(self._processing_state['phase_center_translation'])
            processed.translate(translation)
        
        # Apply MARS (if any)
        if self._processing_state['mars_max_extent'] is not None:
            processed.apply_mars(self._processing_state['mars_max_extent'])
        
        # Update current pattern
        self._pattern = processed
        logger.info("Processing applied to pattern")
        self.pattern_modified.emit(processed)
    
    def set_phase_center_translation(self, translation: Optional[list]):
        """
        Enable or disable phase center translation.
        
        Args:
            translation: [x, y, z] in meters, or None to disable
        """
        self._processing_state['phase_center_translation'] = translation
        self.apply_processing()
        self.processing_applied.emit("phase_center_translation")
    
    def set_mars(self, max_extent: Optional[float]):
        """
        Enable or disable MARS.
        
        Args:
            max_extent: Maximum radial extent in meters, or None to disable
        """
        self._processing_state['mars_max_extent'] = max_extent
        self.apply_processing()
        self.processing_applied.emit("mars")
    
    def set_coordinate_format(self, format: Optional[str]):
        """
        Set coordinate format transformation.
        
        Args:
            format: 'central', 'sided', or None for original format
        """
        self._processing_state['coordinate_format'] = format
        self.apply_processing()
        self.processing_applied.emit("coordinate_format")
    
    def modify_pattern(self, pattern: Any):
        """
        Update pattern after modification and emit signal.
        
        Args:
            pattern: Modified FarFieldSpherical object
        """
        self._pattern = pattern
        self.pattern_modified.emit(pattern)
    
    @property
    def file_path(self) -> Optional[str]:
        """Get the file path of current pattern."""
        return self._file_path
    
    def get_view_param(self, key: str) -> Any:
        """
        Get a view parameter.
        
        Args:
            key: Parameter name
            
        Returns:
            Parameter value or None if not found
        """
        return self._view_params.get(key)
    
    def set_view_param(self, key: str, value: Any):
        """
        Set a view parameter and emit signal.
        
        Args:
            key: Parameter name
            value: Parameter value
        """
        self._view_params[key] = value
        self.view_parameters_changed.emit(self._view_params)
    
    def update_view_params(self, params: Dict[str, Any]):
        """
        Update multiple view parameters at once.
        
        Args:
            params: Dictionary of parameter updates
        """
        self._view_params.update(params)
        self.view_parameters_changed.emit(self._view_params)
    
    def get_all_view_params(self) -> Dict[str, Any]:
        """
        Get all view parameters.
        
        Returns:
            Dictionary of all view parameters
        """
        return self._view_params.copy()
    
    def add_instance(self, instance: PatternInstance):
        """Add a new pattern instance."""
        self._instances[instance.instance_id] = instance
        self.instances_changed.emit()
        
        # Set as active if it's the first instance
        if len(self._instances) == 1:
            self.set_active_instance(instance.instance_id)
    
    def remove_instance(self, instance_id: str):
        """Remove a pattern instance."""
        if instance_id in self._instances:
            instance = self._instances[instance_id]
            
            # Remove from comparison set if present
            self._comparison_instance_ids.discard(instance_id)
            
            # Clear active if this was active
            if self._active_instance_id == instance_id:
                self._active_instance_id = None
                remaining = list(self._instances.keys())
                if remaining:
                    # Set first remaining as active
                    new_active = [k for k in remaining if k != instance_id][0] if len(remaining) > 1 else remaining[0]
                    self.set_active_instance(new_active)
                else:
                    self.active_instance_changed.emit(None)
                    self.pattern_loaded.emit(None)
            
            del self._instances[instance_id]
            self.instances_changed.emit()
    
    def get_instance(self, instance_id: str) -> Optional[PatternInstance]:
        """Get a pattern instance by ID."""
        return self._instances.get(instance_id)
    
    def get_all_instances(self) -> List[PatternInstance]:
        """Get all pattern instances."""
        return list(self._instances.values())
    
    def set_active_instance(self, instance_id: str):
        """Set the active pattern instance."""
        
        # Save current view params to old active instance
        if self._active_instance_id:
            old_instance = self._instances.get(self._active_instance_id)
            if old_instance:
                old_instance.view_params = self._view_params.copy()
        
        # Set new active
        self._active_instance_id = instance_id
        instance = self._instances[instance_id]
        
        # Restore view params from instance
        if instance.view_params:
            self._view_params.update(instance.view_params)
            self.view_parameters_changed.emit(self._view_params)
        
        # Update pattern
        file_path = str(instance.source_file) if instance.source_file else None
        self.set_pattern(instance.pattern, file_path=file_path)
        
        self.active_instance_changed.emit(instance)
        self.pattern_loaded.emit(instance.pattern)
    
    def get_active_instance(self) -> Optional[PatternInstance]:
        """Get the currently active pattern instance."""
        if self._active_instance_id:
            return self._instances.get(self._active_instance_id)
        return None
    
    def rename_instance(self, instance_id: str, new_name: str):
        """Rename a pattern instance."""
        if instance_id in self._instances:
            self._instances[instance_id].display_name = new_name
            self.instances_changed.emit()
    
    def add_to_comparison(self, instance_id: str):
        """Add an instance to the comparison set."""
        if instance_id in self._instances:
            self._comparison_instance_ids.add(instance_id)
            self.comparison_set_changed.emit(list(self._comparison_instance_ids))
    
    def remove_from_comparison(self, instance_id: str):
        """Remove an instance from the comparison set."""
        self._comparison_instance_ids.discard(instance_id)
        self.comparison_set_changed.emit(list(self._comparison_instance_ids))
    
    def get_comparison_instances(self) -> List[PatternInstance]:
        """Get all instances in the comparison set."""
        return [self._instances[iid] for iid in self._comparison_instance_ids
                if iid in self._instances]

    def get_comparison_compatibility(self) -> dict:
        """
        Check dimension compatibility between active and comparison patterns.

        Returns:
            dict with keys:
                'compatible': bool - True if all patterns have identical dimensions
                'common_frequencies': list - Frequencies present in all patterns
                'common_phi': list - Phi angles present in all patterns
                'num_comparison': int - Number of patterns in comparison set
        """
        active = self.get_active_instance()
        comparison = self.get_comparison_instances()

        if not active or not comparison:
            return {
                'compatible': False,
                'common_frequencies': [],
                'common_phi': [],
                'num_comparison': len(comparison) if comparison else 0
            }

        # Get all patterns (active + comparison)
        all_patterns = [active.pattern] + [c.pattern for c in comparison]

        # Find common frequencies
        freq_sets = [set(p.frequencies.tolist()) for p in all_patterns]
        common_freqs = sorted(set.intersection(*freq_sets))

        # Find common phi angles
        phi_sets = [set(p.phi_angles.tolist()) for p in all_patterns]
        common_phi = sorted(set.intersection(*phi_sets))

        # Fully compatible if all dimensions match exactly
        compatible = (
            len(common_freqs) == len(all_patterns[0].frequencies) and
            len(common_phi) == len(all_patterns[0].phi_angles) and
            all(len(common_freqs) == len(p.frequencies) for p in all_patterns) and
            all(len(common_phi) == len(p.phi_angles) for p in all_patterns)
        )

        return {
            'compatible': compatible,
            'common_frequencies': common_freqs,
            'common_phi': common_phi,
            'num_comparison': len(comparison)
        }

    def update_view_params(self, params: Dict[str, Any]):
        """
        Update view parameters and emit signal.
        
        Args:
            params: Dictionary of view parameters to update
        """
        self._view_params.update(params)
        self.view_parameters_changed.emit(self._view_params)

    def set_theta_origin_shift(self, theta_offset: Optional[float]):
        """
        Enable or disable theta origin shift.
        
        Args:
            theta_offset: Offset in degrees, or None to disable
        """
        self._processing_state['theta_origin_shift'] = theta_offset
        self.apply_processing()
        self.processing_applied.emit("theta_origin_shift")

    def set_phi_origin_shift(self, phi_offset: Optional[float]):
        """
        Enable or disable phi origin shift.
        
        Args:
            phi_offset: Offset in degrees, or None to disable
        """
        self._processing_state['phi_origin_shift'] = phi_offset
        self.apply_processing()
        self.processing_applied.emit("phi_origin_shift")

    def set_amplitude_normalization(self, norm_type: Optional[str]):
        """
        Enable or disable amplitude normalization.

        Args:
            norm_type: 'peak', 'boresight', 'mean', or None to disable
        """
        self._processing_state['amplitude_normalization'] = norm_type
        self.apply_processing()
        self.processing_applied.emit("amplitude_normalization")

    def set_boresight_normalization(self, enabled: bool):
        """
        Enable or disable boresight normalization.

        When enabled, each phi cut is scaled so all cuts cross at the same
        amplitude and phase at boresight (theta=0), using the median value.
        """
        self._processing_state['boresight_normalization'] = enabled
        self.apply_processing()
        self.processing_applied.emit("boresight_normalization")