"""Widget submodules for antenna pattern viewer."""

from .control_panel_widget import ControlPanelWidget
from .plot_2d_widget import Plot2DWidget
from .plot_3d_widget import Plot3DWidget
from .data_display_widget import DataDisplayWidget
from .file_manager_widget import FileManagerWidget
from .plot_nearfield_widget import PlotNearFieldWidget

# New icon sidebar navigation widgets
from .icon_sidebar import IconSidebar
from .pattern_strip import PatternStrip
from .left_panel_widget import LeftPanelWidget
from .analysis_panel import AnalysisPanel

__all__ = [
    'ControlPanelWidget',
    'Plot2DWidget',
    'Plot3DWidget',
    'PlotNearFieldWidget',
    'DataDisplayWidget',
    'FileManagerWidget',
    # New widgets
    'IconSidebar',
    'PatternStrip',
    'LeftPanelWidget',
    'AnalysisPanel',
]