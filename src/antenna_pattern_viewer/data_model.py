"""
Shared data model for antenna pattern viewer GUI.
"""
from PyQt6.QtCore import QObject, pyqtSignal
from typing import Optional, Dict, Any, List, Set
from antenna_pattern_viewer.pattern_instance import PatternInstance

import logging
logger = logging.getLogger(__name__)

def _common_values(arrays: List[Any], atol: float) -> List[float]:
    """
    Values of the first array that appear in every array, within `atol`.

    Used for frequency and phi matching, where exact float equality is too
    strict for data that came from different file formats.
    """
    import numpy as np

    if not arrays:
        return []
    candidates = np.asarray(arrays[0], dtype=float)
    for other in arrays[1:]:
        other = np.asarray(other, dtype=float)
        if other.size == 0:
            return []
        keep = [np.any(np.isclose(other, v, atol=atol, rtol=0.0)) for v in candidates]
        candidates = candidates[np.asarray(keep, dtype=bool)]
    return sorted(float(v) for v in candidates)


def default_processing_state() -> Dict[str, Any]:
    """The processing pipeline's settings with everything switched off."""
    return {
        'coordinate_format': None,      # 'central', 'sided', or None (as loaded)
        'polarization': None,           # e.g. 'x', 'rhcp', or None (as loaded)
        'amplitude_normalization': None,
        'boresight_normalization': False,
        'theta_origin_shift': None,     # measurement correction, degrees
        'phi_origin_shift': None,       # measurement correction, degrees
        'phase_center_translation': None,   # [x, y, z] in metres
        'mars_max_extent': None,
        'rotation': None,               # (alpha, beta, gamma, method)
    }


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
    processing_failed = pyqtSignal(str)  # Emits a message when the pipeline raises
    instances_changed = pyqtSignal()  # Emitted when instance list changes
    active_instance_changed = pyqtSignal(object)  # Emits PatternInstance
    comparison_set_changed = pyqtSignal(list)  # Emits list of instance IDs
    
    def __init__(self):
        super().__init__()
        self._pattern: Optional[Any] = None  # Current (possibly processed) pattern
        self._original_pattern: Optional[Any] = None  # Original unprocessed pattern
        self._file_path: Optional[str] = None
        
        # Processing state (mirrors the active instance's; see set_active_instance)
        self._processing_state = default_processing_state()

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
        # An ordered set: plot colours are assigned by position, so an
        # unordered container would reshuffle them on every redraw.
        self._comparison_instance_ids: Dict[str, None] = {}
    
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
        
        # Reset processing state: this is a different pattern
        self._processing_state = default_processing_state()

        # Reset view parameters when loading new pattern
        if pattern is not None:
            self._view_params['selected_frequencies'] = []
            self._view_params['selected_phi'] = []
            self._view_params['selected_theta'] = []
        
        self.pattern_loaded.emit(pattern)

    def apply_processing(self, _failed_key: Optional[str] = None):
        """
        Apply all enabled processing operations to the original pattern.

        The pipeline always restarts from the original pattern so that steps do
        not stack. Measurement corrections run in the frame the data was
        measured in; the rigid rotation runs last, after the phase centre has
        been moved to the origin.

        If a step raises, ``_failed_key`` (the setting that was just changed) is
        rolled back to its default, the pipeline is re-run without it, and
        ``processing_failed`` carries the message so the UI can show it. Without
        the rollback one bad value would make every later toggle raise too.
        """
        if self._original_pattern is None:
            return

        try:
            processed = self._run_pipeline(self._original_pattern, self._processing_state)
        except Exception as e:
            logger.error("Processing failed: %s", e, exc_info=True)
            if _failed_key is not None:
                self._processing_state[_failed_key] = default_processing_state()[_failed_key]
                self.apply_processing()
            # Emitted last: the rollback re-run above succeeds and emits
            # pattern_modified, which is what clears the message in the UI.
            self.processing_failed.emit(str(e))
            return

        self._pattern = processed
        instance = self.get_active_instance()
        if instance is not None:
            instance.processing_state = dict(self._processing_state)
            instance.processed_pattern = processed
        logger.info("Processing applied to pattern")
        self.pattern_modified.emit(processed)

    @staticmethod
    def _run_pipeline(original: Any, state: Dict[str, Any]) -> Any:
        """Apply `state` to a copy of `original` and return the result."""
        import numpy as np

        processed = original.copy()

        # Coordinate transformation first: later steps depend on the format
        if state.get('coordinate_format') is not None:
            processed.transform_coordinates(state['coordinate_format'])

        # Polarization is part of the pipeline so that it survives every other
        # toggle. Applied in place elsewhere it would be undone by the next
        # rebuild from the original.
        if state.get('polarization') is not None:
            processed.assign_polarization(state['polarization'])

        if state.get('amplitude_normalization') is not None:
            processed.normalize_amplitude(state['amplitude_normalization'])

        if state.get('boresight_normalization'):
            processed.normalize_at_boresight()

        # Measurement corrections
        if state.get('theta_origin_shift') is not None:
            processed.shift_theta_origin(state['theta_origin_shift'])

        if state.get('phi_origin_shift') is not None:
            processed.shift_phi_origin(state['phi_origin_shift'])

        if state.get('phase_center_translation') is not None:
            processed.translate(np.array(state['phase_center_translation']))

        if state.get('mars_max_extent') is not None:
            processed.apply_mars(state['mars_max_extent'])

        # Antenna orientation, last
        if state.get('rotation') is not None:
            alpha, beta, gamma, method = state['rotation']
            processed.rotate(alpha, beta, gamma, method=method)

        return processed

    def set_phase_center_translation(self, translation: Optional[list]):
        """
        Enable or disable phase center translation.
        
        Args:
            translation: [x, y, z] in meters, or None to disable
        """
        self._processing_state['phase_center_translation'] = translation
        self.apply_processing(_failed_key='phase_center_translation')
        self.processing_applied.emit("phase_center_translation")
    
    def set_mars(self, max_extent: Optional[float]):
        """
        Enable or disable MARS.
        
        Args:
            max_extent: Maximum radial extent in meters, or None to disable
        """
        self._processing_state['mars_max_extent'] = max_extent
        self.apply_processing(_failed_key='mars_max_extent')
        self.processing_applied.emit("mars")
    
    def set_coordinate_format(self, format: Optional[str]):
        """
        Set coordinate format transformation.
        
        Args:
            format: 'central', 'sided', or None for original format
        """
        self._processing_state['coordinate_format'] = format
        self.apply_processing(_failed_key='coordinate_format')
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
        """Remove a pattern instance and activate another, or clear the model."""
        if instance_id not in self._instances:
            return

        self._comparison_instance_ids.pop(instance_id, None)
        was_active = self._active_instance_id == instance_id

        # Delete first: the remaining set must not still contain this instance,
        # or removing the last pattern re-activates the one being deleted and
        # leaves the model pointing at it.
        del self._instances[instance_id]

        if was_active:
            self._active_instance_id = None
            remaining = list(self._instances.keys())
            if remaining:
                self.set_active_instance(remaining[0])
            else:
                self._pattern = None
                self._original_pattern = None
                self._file_path = None
                self._processing_state = default_processing_state()
                self.active_instance_changed.emit(None)
                self.pattern_loaded.emit(None)

        self.instances_changed.emit()

    def get_instance(self, instance_id: str) -> Optional[PatternInstance]:
        """Get a pattern instance by ID."""
        return self._instances.get(instance_id)
    
    def get_all_instances(self) -> List[PatternInstance]:
        """Get all pattern instances."""
        return list(self._instances.values())
    
    def set_active_instance(self, instance_id: str):
        """
        Make an instance active, carrying its view and processing settings.

        set_pattern() resets the view selections and the processing state for
        what it treats as a newly loaded pattern, so the instance's saved
        settings are restored afterwards, not before.
        """
        instance = self._instances.get(instance_id)
        if instance is None:
            logger.warning("set_active_instance: no instance %s", instance_id)
            return

        # Save the outgoing instance's settings
        if self._active_instance_id:
            old_instance = self._instances.get(self._active_instance_id)
            if old_instance:
                old_instance.view_params = self._view_params.copy()
                old_instance.processing_state = dict(self._processing_state)

        self._active_instance_id = instance_id

        # set_pattern emits pattern_loaded and clears the selections
        file_path = str(instance.source_file) if instance.source_file else None
        self.set_pattern(instance.pattern, file_path=file_path)

        # Restore this instance's saved settings on top of that reset
        if instance.view_params:
            self._view_params.update(instance.view_params)
            self.view_parameters_changed.emit(self._view_params)

        if instance.processing_state:
            self._processing_state = dict(instance.processing_state)
            if any(v not in (None, False) for v in self._processing_state.values()):
                self.apply_processing()

        self.active_instance_changed.emit(instance)

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
            self._comparison_instance_ids[instance_id] = None
            self.comparison_set_changed.emit(list(self._comparison_instance_ids))
    
    def remove_from_comparison(self, instance_id: str):
        """Remove an instance from the comparison set."""
        self._comparison_instance_ids.pop(instance_id, None)
        self.comparison_set_changed.emit(list(self._comparison_instance_ids))
    
    def get_comparison_instances(self) -> List[PatternInstance]:
        """Get all instances in the comparison set."""
        return [self._instances[iid] for iid in self._comparison_instance_ids
                if iid in self._instances]

    def get_instance_pattern(self, instance: PatternInstance) -> Any:
        """
        The pattern an instance should be plotted with.

        The active instance's processed pattern lives on the model, and every
        other instance keeps its own processed result, so a comparison plot
        shows each pattern with its own processing rather than raw.
        """
        if instance is None:
            return None
        if instance.instance_id == self._active_instance_id and self._pattern is not None:
            return self._pattern
        return instance.processed_pattern if instance.processed_pattern is not None else instance.pattern

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

        # Get all patterns (active + comparison), as they will be plotted
        all_patterns = [self.get_instance_pattern(active)]
        all_patterns += [self.get_instance_pattern(c) for c in comparison]

        # Match with a tolerance rather than on exact floats: frequencies from
        # a .cut file are generated from a start/stop pair while those from a
        # .ffd are parsed from text, so two physically identical patterns
        # essentially never produce bit-identical values.
        common_freqs = _common_values([p.frequencies for p in all_patterns], atol=1.0)
        common_phi = _common_values([p.phi_angles for p in all_patterns], atol=1e-6)

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

    def set_theta_origin_shift(self, theta_offset: Optional[float]):
        """
        Enable or disable theta origin shift.
        
        Args:
            theta_offset: Offset in degrees, or None to disable
        """
        self._processing_state['theta_origin_shift'] = theta_offset
        self.apply_processing(_failed_key='theta_origin_shift')
        self.processing_applied.emit("theta_origin_shift")

    def set_phi_origin_shift(self, phi_offset: Optional[float]):
        """
        Enable or disable phi origin shift.
        
        Args:
            phi_offset: Offset in degrees, or None to disable
        """
        self._processing_state['phi_origin_shift'] = phi_offset
        self.apply_processing(_failed_key='phi_origin_shift')
        self.processing_applied.emit("phi_origin_shift")

    def set_rotation(self, rotation: Optional[tuple]):
        """
        Enable or disable a rigid rotation of the antenna.

        Args:
            rotation: (alpha, beta, gamma, method) with angles in degrees and
                method an interpolation name ('linear' or 'cubic'), or None
                to disable
        """
        self._processing_state['rotation'] = rotation
        self.apply_processing(_failed_key='rotation')
        self.processing_applied.emit("rotation")

    def set_polarization(self, polarization: Optional[str]):
        """
        Set the polarization the pattern is expressed in.

        This is part of the processing pipeline rather than a one-off edit, so
        the choice survives every other processing toggle (each of which
        rebuilds the pattern from the original).

        Args:
            polarization: 'x', 'y', 'rhcp', 'lhcp', 'theta', 'phi', or None to
                keep the polarization the file was loaded with
        """
        self._processing_state['polarization'] = polarization
        self.apply_processing(_failed_key='polarization')
        self.processing_applied.emit("polarization")

    def set_amplitude_normalization(self, norm_type: Optional[str]):
        """
        Enable or disable amplitude normalization.

        Args:
            norm_type: 'peak', 'boresight', 'mean', or None to disable
        """
        self._processing_state['amplitude_normalization'] = norm_type
        self.apply_processing(_failed_key='amplitude_normalization')
        self.processing_applied.emit("amplitude_normalization")

    def set_boresight_normalization(self, enabled: bool):
        """
        Enable or disable boresight normalization.

        When enabled, each phi cut is scaled so all cuts cross at the same
        amplitude and phase at boresight (theta=0), using the median value.
        """
        self._processing_state['boresight_normalization'] = enabled
        self.apply_processing(_failed_key='boresight_normalization')
        self.processing_applied.emit("boresight_normalization")