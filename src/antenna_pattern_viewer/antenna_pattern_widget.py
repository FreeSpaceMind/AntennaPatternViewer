"""
Top-level embeddable antenna pattern widget with dockable interface.
"""
from PyQt6.QtWidgets import (
    QMainWindow, QDockWidget, QStatusBar
    )
from PyQt6.QtCore import Qt, pyqtSignal, QSettings
from pathlib import Path

from antenna_pattern_viewer.data_model import PatternDataModel
from antenna_pattern_viewer.widgets.control_panel_widget import ControlPanelWidget
from antenna_pattern_viewer.widgets.plot_2d_widget import Plot2DWidget
from antenna_pattern_viewer.widgets.plot_3d_widget import Plot3DWidget
from antenna_pattern_viewer.widgets.data_display_widget import DataDisplayWidget
from antenna_pattern_viewer.widgets.file_manager_widget import FileManagerWidget
from antenna_pattern_viewer.widgets.plot_nearfield_widget import PlotNearFieldWidget
from antenna_pattern_viewer.widgets.export_widget import ExportWidget


class AntennaPatternWidget(QMainWindow):
    """
    Embeddable antenna pattern widget with dockable interface.
    
    This widget provides a complete antenna pattern visualization interface that can be
    used standalone or embedded in larger applications. All sub-panels are dockable,
    allowing users to customize the layout.
    """
    
    # Signals for external communication
    pattern_loaded = pyqtSignal(object)  # Emits FarFieldSpherical when pattern loaded
    status_message = pyqtSignal(str)  # Emits status messages
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create shared data model
        self.data_model = PatternDataModel()
        
        # Setup UI
        self.setWindowTitle("Antenna Pattern Viewer")
        self.resize(1600, 900)
        
        self.setup_docks()
        self.setup_menus()
        self.setup_status_bar()
        self.connect_signals()
        
        # TEMPORARY: Clear saved layout for testing
        settings = QSettings("AntPy", "AntennaPatternViewer")
        settings.clear()
        
    def setup_docks(self):
        """Create and arrange dock widgets in a two-column layout with tabbed center."""
        
        # Create all dock widgets
        self.file_manager_dock = QDockWidget("File Manager", self)
        self.file_manager_dock.setObjectName("FileManagerDock")
        self.file_manager = FileManagerWidget(self.data_model)
        self.file_manager_dock.setWidget(self.file_manager)
        
        self.control_dock = QDockWidget("Control Panel", self)
        self.control_dock.setObjectName("ControlDock")
        self.control_panel = ControlPanelWidget(self.data_model)
        self.control_dock.setWidget(self.control_panel)
        
        self.plot_2d_dock = QDockWidget("2D View", self)
        self.plot_2d_dock.setObjectName("Plot2DDock")
        self.plot_2d = Plot2DWidget(self.data_model)
        self.plot_2d_dock.setWidget(self.plot_2d)
        
        self.plot_3d_dock = QDockWidget("3D View", self)
        self.plot_3d_dock.setObjectName("Plot3DDock")
        self.plot_3d = Plot3DWidget(self.data_model)
        self.plot_3d_dock.setWidget(self.plot_3d)

        self.plot_nearfield_dock = QDockWidget("Near Field", self)
        self.plot_nearfield_dock.setObjectName("PlotNearFieldDock")
        self.plot_nearfield = PlotNearFieldWidget(self.data_model)
        self.plot_nearfield_dock.setWidget(self.plot_nearfield)
        
        self.data_dock = QDockWidget("Data Display", self)
        self.data_dock.setObjectName("DataDock")
        self.data_display = DataDisplayWidget(self.data_model)
        self.data_dock.setWidget(self.data_display)

        self.export_dock = QDockWidget("Export", self)
        self.export_dock.setObjectName("ExportDock")
        self.export_widget = ExportWidget(self.data_model)
        self.export_dock.setWidget(self.export_widget)

        
        # Build layout: LEFT COLUMN | TABBED CENTER
        
        # Left Column: File Manager + Control Panel stacked vertically
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.file_manager_dock)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.control_dock)
        self.splitDockWidget(self.file_manager_dock, self.control_dock, Qt.Orientation.Vertical)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.export_dock)
        self.splitDockWidget(self.control_dock, self.export_dock, Qt.Orientation.Vertical)
        
        # Center: Tabbed plots and data display
        # Add first dock to the right
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.plot_2d_dock)
        
        # Tabify the others on top of it
        self.tabifyDockWidget(self.plot_2d_dock, self.plot_3d_dock)
        self.tabifyDockWidget(self.plot_2d_dock, self.data_dock)
        self.tabifyDockWidget(self.plot_2d_dock, self.plot_nearfield_dock)
        
        # Make 2D plot the active tab
        self.plot_2d_dock.raise_()
        
        # Size constraints
        self.file_manager_dock.setMinimumHeight(200)
        self.control_dock.setMinimumWidth(350)
        self.control_dock.setMaximumWidth(500)
        
        # Set vertical split in left column (file manager smaller, control panel larger)
        self.resizeDocks(
            [self.file_manager_dock, self.control_dock],
            [250, 450],
            Qt.Orientation.Vertical
        )
        
    
    def setup_menus(self):
        """Create menu bar - disabled for embedded mode."""
        # Menu bar removed since this widget is designed to be embedded
        # File operations can be done programmatically through the data model
        # or through a parent application's menu system
        pass
    
    def setup_status_bar(self):
        """Create status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def connect_signals(self):
        """Connect internal signals."""
        # Relay pattern loaded signal
        self.data_model.pattern_loaded.connect(self.on_pattern_loaded)
        self.data_model.pattern_loaded.connect(self.pattern_loaded.emit)
        
        # Status messages
        self.status_message.connect(self.status_bar.showMessage)

        # Connect near field calculation signal to plot widget
        self.control_panel.nearfield_calculated.connect(self.on_nearfield_calculated)

        self.export_widget.export_completed.connect(
            lambda path: self.status_message.emit(f"Exported: {Path(path).name}")
        )
    
    def reset_layout(self):
        """Reset dock layout to default."""
        # Remove all docks
        self.removeDockWidget(self.control_dock)
        self.removeDockWidget(self.plot_2d_dock)
        self.removeDockWidget(self.plot_3d_dock)
        self.removeDockWidget(self.data_dock)
        
        # Re-add in default configuration
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.control_dock)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.plot_2d_dock)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.plot_3d_dock)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.data_dock)
        
        self.splitDockWidget(self.plot_2d_dock, self.plot_3d_dock, Qt.Orientation.Vertical)
        
        # Show/hide docks
        self.control_dock.setVisible(True)
        self.plot_2d_dock.setVisible(True)
        self.plot_3d_dock.setVisible(False)
        self.data_dock.setVisible(True)
        
        self.status_message.emit("Layout reset to default")
    
    def on_pattern_loaded(self, pattern):
        """Handle pattern loaded event."""
        if pattern is not None:
            n_freq = len(pattern.frequencies)
            n_theta = len(pattern.theta_angles)
            n_phi = len(pattern.phi_angles)
            pol = pattern.polarization
            
            msg = f"Pattern loaded: {n_freq} freq, {n_theta}×{n_phi} points, {pol} pol"
            self.status_message.emit(msg)

    def on_nearfield_calculated(self, near_field_data):
        """Handle near field calculation completion."""
        self.plot_nearfield.plot_near_field(near_field_data)
        self.plot_nearfield_dock.raise_()
    
    def save_settings(self):
        """Save window geometry and dock states."""
        settings = QSettings("AntennaPatternViewer", "MainWindow")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
    
    def load_settings(self):
        """Load window geometry and dock states."""
        settings = QSettings("AntennaPatternViewer", "MainWindow")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        window_state = settings.value("windowState")
        if window_state:
            self.restoreState(window_state)
    
    def closeEvent(self, event):
        """Handle window close event."""
        self.save_settings()
        event.accept()

    def reset_to_default_layout(self):
        """Reset dock layout to default configuration."""
        # Clear saved state
        settings = QSettings("AntPy", "AntennaPatternViewer")
        settings.remove("geometry")
        settings.remove("windowState")
        
        # Reapply default layout
        self.setup_docks()