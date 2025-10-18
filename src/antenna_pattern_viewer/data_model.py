"""
Shared data model for antenna pattern viewer GUI.
"""
from PyQt6.QtCore import QObject, pyqtSignal
from typing import Optional, Dict, Any
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
    
    def __init__(self):
        super().__init__()
        self._pattern: Optional[Any] = None  # FarFieldSpherical object
        self._file_path: Optional[str] = None
        
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
    
    @property
    def pattern(self) -> Optional[Any]:
        """Get current pattern."""
        return self._pattern
    
    def set_pattern(self, pattern: Any, file_path: Optional[str] = None):
        """
        Set new pattern and emit signal.
        
        Args:
            pattern: FarFieldSpherical object
            file_path: Optional path to the source file
        """
        self._pattern = pattern
        self._file_path = file_path
        
        # Reset view parameters when loading new pattern
        if pattern is not None:
            self._view_params['selected_frequencies'] = []
            self._view_params['selected_phi'] = []
            self._view_params['selected_theta'] = []
        
        logger.info(f"Pattern loaded: {file_path if file_path else 'from memory'}")
        self.pattern_loaded.emit(pattern)
    
    def modify_pattern(self, pattern: Any):
        """
        Update pattern after modification and emit signal.
        
        Args:
            pattern: Modified FarFieldSpherical object
        """
        self._pattern = pattern
        logger.info("Pattern modified")
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
        logger.debug(f"View parameter updated: {key} = {value}")
        self.view_parameters_changed.emit(self._view_params)
    
    def update_view_params(self, params: Dict[str, Any]):
        """
        Update multiple view parameters at once.
        
        Args:
            params: Dictionary of parameter updates
        """
        self._view_params.update(params)
        logger.debug(f"View parameters updated: {list(params.keys())}")
        self.view_parameters_changed.emit(self._view_params)
    
    def get_all_view_params(self) -> Dict[str, Any]:
        """
        Get all view parameters.
        
        Returns:
            Dictionary of all view parameters
        """
        return self._view_params.copy()