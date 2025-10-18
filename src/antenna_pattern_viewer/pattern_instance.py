"""
Pattern instance with associated settings and state.
"""
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path
import uuid

@dataclass
class PatternInstance:
    """
    Represents a loaded pattern with its associated settings.
    
    This allows multiple instances of the same pattern file to be loaded
    with different processing/view settings for comparison.
    """
    
    # Unique identifier
    instance_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # Pattern data
    pattern: Any = None  # FarFieldSpherical object
    source_file: Optional[Path] = None
    display_name: str = ""
    
    # View settings (stored for recall when pattern becomes active)
    view_params: Dict[str, Any] = field(default_factory=dict)
    
    # Processing history/state
    processing_history: list = field(default_factory=list)
    
    # Additional metadata
    load_timestamp: Optional[float] = None
    notes: str = ""
    
    def __post_init__(self):
        """Set default display name if not provided."""
        if not self.display_name and self.source_file:
            self.display_name = self.source_file.name
        elif not self.display_name:
            self.display_name = f"Pattern_{self.instance_id[:8]}"
    
    def clone(self, new_name: Optional[str] = None) -> 'PatternInstance':
        """
        Create a copy of this instance with a new ID.
        Useful for loading the same pattern multiple times.
        """
        import copy
        new_instance = PatternInstance(
            pattern=self.pattern,  # Reference same pattern initially
            source_file=self.source_file,
            display_name=new_name or f"{self.display_name} (copy)",
            view_params=copy.deepcopy(self.view_params),
            processing_history=copy.deepcopy(self.processing_history),
            notes=self.notes
        )
        return new_instance