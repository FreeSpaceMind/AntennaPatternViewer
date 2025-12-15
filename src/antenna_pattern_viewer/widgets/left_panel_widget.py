"""
Left panel widget combining icon sidebar, pattern strip, and stacked panels.

This widget serves as the main container for the left side of the application,
providing navigation between Files, Controls, Analysis, and Export panels.
"""
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget, QSizePolicy, QFileDialog
)
from PyQt6.QtCore import pyqtSignal

from .icon_sidebar import IconSidebar
from .pattern_strip import PatternStrip
from .file_manager_widget import FileManagerWidget
from .control_panel_widget import ControlPanelWidget
from .export_widget import ExportWidget


class LeftPanelWidget(QWidget):
    """
    Container widget for the left panel with icon navigation.

    Layout:
    ┌─────────┬──────────────────────┐
    │         │ PatternStrip         │
    │ Icon    ├──────────────────────┤
    │ Sidebar │ QStackedWidget       │
    │  📁     │  [0] FileManager     │
    │  ⚙️     │  [1] ControlPanel    │
    │  📊     │  [2] AnalysisPanel   │
    │  📤     │  [3] ExportPanel     │
    └─────────┴──────────────────────┘
    """

    # Forward signals from child widgets
    nearfield_calculated = pyqtSignal(dict)

    # File filter for pattern files
    FILE_FILTER = "Pattern Files (*.cut *.ffd *.npz *.sph);;All Files (*)"

    def __init__(self, data_model, plot_widget=None, parent=None):
        super().__init__(parent)
        self.data_model = data_model
        self.plot_widget = plot_widget

        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        """Setup the left panel UI."""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Icon sidebar (left edge)
        self.icon_sidebar = IconSidebar()
        main_layout.addWidget(self.icon_sidebar)

        # Right side container (pattern strip + stacked panels)
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Pattern strip (always visible at top)
        self.pattern_strip = PatternStrip(self.data_model)
        right_layout.addWidget(self.pattern_strip)

        # Stacked widget for panels
        self.panel_stack = QStackedWidget()
        self.setup_panels()
        right_layout.addWidget(self.panel_stack)

        main_layout.addWidget(right_container)

        # Set size policy - expand horizontally based on content
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

    def setup_panels(self):
        """Create and add all panels to the stack."""
        # Panel 0: File Manager
        self.file_manager = FileManagerWidget(self.data_model)
        self.panel_stack.addWidget(self.file_manager)

        # Panel 1: Control Panel (View + Processing only)
        self.control_panel = ControlPanelWidget(self.data_model)
        self.panel_stack.addWidget(self.control_panel)

        # Panel 2: Analysis Panel
        from .analysis_panel import AnalysisPanel
        self.analysis_panel = AnalysisPanel(self.data_model)
        self.panel_stack.addWidget(self.analysis_panel)

        # Panel 3: Export Panel
        self.export_panel = ExportWidget(self.data_model, plot_widget=self.plot_widget)
        self.panel_stack.addWidget(self.export_panel)

    def connect_signals(self):
        """Connect signals between components."""
        # Icon sidebar -> panel stack
        self.icon_sidebar.panel_changed.connect(self.panel_stack.setCurrentIndex)

        # Pattern strip -> file dialog
        self.pattern_strip.add_pattern_requested.connect(self.open_file_dialog)

        # Analysis panel -> forward nearfield signal
        self.analysis_panel.nearfield_calculated.connect(self.nearfield_calculated.emit)

    def open_file_dialog(self):
        """Open file dialog to load patterns."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Open Pattern Files",
            "",
            self.FILE_FILTER
        )

        if files:
            # Use file manager to load files
            from pathlib import Path
            for file_path in files:
                self.file_manager.load_pattern_file(Path(file_path))

    def set_current_panel(self, index: int):
        """Set the current panel by index."""
        self.icon_sidebar.set_current_panel(index)
        self.panel_stack.setCurrentIndex(index)

    def show_files_panel(self):
        """Show the Files panel."""
        self.set_current_panel(IconSidebar.PANEL_FILES)

    def show_controls_panel(self):
        """Show the Controls panel."""
        self.set_current_panel(IconSidebar.PANEL_CONTROLS)

    def show_analysis_panel(self):
        """Show the Analysis panel."""
        self.set_current_panel(IconSidebar.PANEL_ANALYSIS)

    def show_export_panel(self):
        """Show the Export panel."""
        self.set_current_panel(IconSidebar.PANEL_EXPORT)

    @property
    def export_completed(self):
        """Forward export_completed signal from export panel."""
        return self.export_panel.export_completed
