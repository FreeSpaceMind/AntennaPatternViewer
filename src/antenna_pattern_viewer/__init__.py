"""
AntennaPatternViewer - GUI application for visualizing antenna far-field patterns.

This package provides a comprehensive GUI for viewing and analyzing antenna
patterns. The main widget (AntennaPatternWidget) can be used standalone or
embedded in larger applications.
"""

__version__ = '1.0.0'
__author__ = 'Justin Long'
__email__ = 'justinwlong1@gmail.com'

from .antenna_pattern_widget import AntennaPatternWidget
from .data_model import PatternDataModel

__all__ = [
    'AntennaPatternWidget',
    'PatternDataModel'
]