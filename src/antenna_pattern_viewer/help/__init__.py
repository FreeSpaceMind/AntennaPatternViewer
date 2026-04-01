"""
Help system for AntennaPatternViewer.

Provides in-app documentation with navigation, search, and LaTeX equation rendering.
Documentation files are loaded from multiple packages (APV, FarFieldSpherical, SWE).
"""

from .help_dialog import HelpDialog, show_help_dialog

__all__ = ['HelpDialog', 'show_help_dialog']
