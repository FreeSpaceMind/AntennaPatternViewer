"""
Top-level embeddable antenna pattern widget with dockable interface.
"""
from PyQt6.QtWidgets import (QMainWindow, QDockWidget, QFileDialog, 
                              QMessageBox, QStatusBar, QInputDialog)
from PyQt6.QtCore import Qt, pyqtSignal, QSettings
from PyQt6.QtGui import QAction
from pathlib import Path
import logging

from farfield_spherical import (
    FarFieldSpherical, 
    read_cut, 
    read_ffd, 
    load_pattern_npz,
    save_pattern_npz
)

from antenna_pattern_viewer.data_model import PatternDataModel
from antenna_pattern_viewer.widgets.control_panel_widget import ControlPanelWidget
from antenna_pattern_viewer.widgets.plot_2d_widget import Plot2DWidget
from antenna_pattern_viewer.widgets.plot_3d_widget import Plot3DWidget
from antenna_pattern_viewer.widgets.data_display_widget import DataDisplayWidget

logger = logging.getLogger(__name__)


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
        
        # Load saved window state if available
        self.load_settings()
        
        logger.info("AntennaPatternWidget initialized")
    
    def setup_docks(self):
        """Create and arrange dock widgets."""
        
        # Control Panel Dock (left side)
        self.control_dock = QDockWidget("Control Panel", self)
        self.control_dock.setObjectName("ControlDock")  # For state saving
        self.control_panel = ControlPanelWidget(self.data_model)
        self.control_dock.setWidget(self.control_panel)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.control_dock)
        
        # 2D Plot Dock (center-top)
        self.plot_2d_dock = QDockWidget("2D View", self)
        self.plot_2d_dock.setObjectName("Plot2DDock")
        self.plot_2d = Plot2DWidget(self.data_model)
        self.plot_2d_dock.setWidget(self.plot_2d)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.plot_2d_dock)
        
        # 3D Plot Dock (center-bottom)
        self.plot_3d_dock = QDockWidget("3D View", self)
        self.plot_3d_dock.setObjectName("Plot3DDock")
        self.plot_3d = Plot3DWidget(self.data_model)
        self.plot_3d_dock.setWidget(self.plot_3d)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.plot_3d_dock)
        
        # Data Display Dock (bottom)
        self.data_dock = QDockWidget("Data Display", self)
        self.data_dock.setObjectName("DataDock")
        self.data_display = DataDisplayWidget(self.data_model)
        self.data_dock.setWidget(self.data_display)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.data_dock)
        
        # Set initial layout - split 2D and 3D vertically
        self.splitDockWidget(self.plot_2d_dock, self.plot_3d_dock, Qt.Orientation.Vertical)
        
        # Set initial sizes
        self.control_dock.setMinimumWidth(350)
        self.control_dock.setMaximumWidth(500)
        self.data_dock.setMinimumHeight(150)
        
        # Initially hide 3D view
        self.plot_3d_dock.setVisible(False)
    
    def setup_menus(self):
        """Create menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        open_action = QAction("&Open Pattern...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_pattern)
        file_menu.addAction(open_action)
        
        save_action = QAction("&Save Pattern...", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_pattern)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        export_action = QAction("&Export Plot...", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self.export_plot)
        file_menu.addAction(export_action)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        view_menu.addAction(self.control_dock.toggleViewAction())
        view_menu.addAction(self.plot_2d_dock.toggleViewAction())
        view_menu.addAction(self.plot_3d_dock.toggleViewAction())
        view_menu.addAction(self.data_dock.toggleViewAction())
        
        view_menu.addSeparator()
        
        reset_action = QAction("&Reset Layout", self)
        reset_action.triggered.connect(self.reset_layout)
        view_menu.addAction(reset_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
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
    
    def open_pattern(self):
        """Open a pattern file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Pattern File",
            "",
            "Pattern Files (*.cut *.ffd *.npz *.sph);;All Files (*.*)"
        )
        
        if not file_path:
            return
        
        try:
            file_path = Path(file_path)
            suffix = file_path.suffix.lower()
            
            if suffix == '.cut':
                pattern = read_cut(str(file_path))
            elif suffix == '.ffd':
                pattern = read_ffd(str(file_path))
            elif suffix == '.npz':
                pattern, _ = load_pattern_npz(str(file_path))
            elif suffix == '.sph':
                # Need frequency dialog
                freq, ok = QInputDialog.getDouble(
                    self,
                    "Enter Frequency",
                    "Frequency (GHz):",
                    value=10.0,
                    min=0.1,
                    max=1000.0,
                    decimals=3
                )
                if not ok:
                    return
                freq_hz = freq * 1e9
                pattern = FarFieldSpherical.from_ticra_sph(str(file_path), freq_hz)
            else:
                raise ValueError(f"Unsupported file format: {suffix}")
            
            self.data_model.set_pattern(pattern, str(file_path))
            self.status_message.emit(f"Loaded: {file_path.name}")
            
        except Exception as e:
            logger.error(f"Failed to load pattern: {e}", exc_info=True)
            QMessageBox.critical(
                self, 
                "Error", 
                f"Failed to load pattern:\n{str(e)}"
            )
    
    def save_pattern(self):
        """Save current pattern."""
        if self.data_model.pattern is None:
            QMessageBox.warning(self, "Warning", "No pattern to save")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Pattern File",
            "",
            "NPZ Files (*.npz);;CUT Files (*.cut);;FFD Files (*.ffd)"
        )
        
        if not file_path:
            return
        
        try:
            file_path = Path(file_path)
            suffix = file_path.suffix.lower()
            
            if suffix == '.npz':
                save_pattern_npz(self.data_model.pattern, str(file_path))
            elif suffix == '.cut':
                self.data_model.pattern.write_cut(str(file_path))
            elif suffix == '.ffd':
                self.data_model.pattern.write_ffd(str(file_path))
            else:
                raise ValueError(f"Unsupported file format: {suffix}")
            
            self.status_message.emit(f"Saved: {file_path.name}")
            
        except Exception as e:
            logger.error(f"Failed to save pattern: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save pattern:\n{str(e)}"
            )
    
    def export_plot(self):
        """Export current plot to image file."""
        # Delegate to the active plot widget
        if self.plot_2d_dock.isVisible():
            self.plot_2d.export_plot()
        else:
            QMessageBox.information(
                self,
                "Export Plot",
                "No plot visible to export"
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
    
    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About Antenna Pattern Viewer",
            "<h3>Antenna Pattern Viewer</h3>"
            "<p>Version 1.0.0</p>"
            "<p>A GUI application for visualizing antenna far-field patterns.</p>"
            "<p>Built with PyQt6 and FarFieldSpherical library.</p>"
            "<p>Copyright © 2024 Justin Long</p>"
        )
    
    def on_pattern_loaded(self, pattern):
        """Handle pattern loaded event."""
        if pattern is not None:
            n_freq = len(pattern.frequencies)
            n_theta = len(pattern.theta_angles)
            n_phi = len(pattern.phi_angles)
            pol = pattern.polarization
            
            msg = f"Pattern loaded: {n_freq} freq, {n_theta}×{n_phi} points, {pol} pol"
            self.status_message.emit(msg)
            logger.info(msg)
    
    def save_settings(self):
        """Save window geometry and dock states."""
        settings = QSettings("AntennaPatternViewer", "MainWindow")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        logger.debug("Settings saved")
    
    def load_settings(self):
        """Load window geometry and dock states."""
        settings = QSettings("AntennaPatternViewer", "MainWindow")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        window_state = settings.value("windowState")
        if window_state:
            self.restoreState(window_state)
        logger.debug("Settings loaded")
    
    def closeEvent(self, event):
        """Handle window close event."""
        self.save_settings()
        event.accept()