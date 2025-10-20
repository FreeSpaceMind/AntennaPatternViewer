"""Widget submodules for antenna pattern viewer."""

from .control_panel_widget import ControlPanelWidget
from .plot_2d_widget import Plot2DWidget
from .plot_3d_widget import Plot3DWidget
from .data_display_widget import DataDisplayWidget
from .file_manager_widget import FileManagerWidget
from .plot_nearfield_widget import PlotNearFieldWidget

__all__ = [
    'ControlPanelWidget',
    'Plot2DWidget',
    'Plot3DWidget',
    'PlotNearFieldWidget',
    'DataDisplayWidget',
    'FileManagerWidget'
]