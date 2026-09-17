"""
Top-level embeddable antenna pattern widget with dockable interface.
"""
from PyQt6.QtWidgets import (
    QMainWindow, QDockWidget, QStatusBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QSettings
from PyQt6.QtGui import QKeySequence, QAction
from pathlib import Path

from antenna_pattern_viewer.data_model import PatternDataModel
from antenna_pattern_viewer.widgets.left_panel_widget import LeftPanelWidget
from antenna_pattern_viewer.widgets.plot_2d_widget import Plot2DWidget
from antenna_pattern_viewer.widgets.plot_3d_widget import Plot3DWidget
from antenna_pattern_viewer.widgets.data_display_widget import DataDisplayWidget
from antenna_pattern_viewer.widgets.plot_nearfield_widget import PlotNearFieldWidget


class AntennaPatternWidget(QMainWindow):
    """
    Embeddable antenna pattern widget with dockable interface.

    This widget provides a complete antenna pattern visualization interface that can be
    used standalone or embedded in larger applications. The left panel uses an icon
    sidebar for navigation between Files, Controls, Analysis, and Export panels.
    """

    # Signals for external communication
    pattern_loaded = pyqtSignal(object)  # Emits FarFieldSpherical when pattern loaded
    status_message = pyqtSignal(str)  # Emits status messages

    SETTINGS_ORG = "AntennaPatternViewer"
    SETTINGS_APP = "MainWindow"

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

        # Restore the window geometry and dock arrangement saved on last exit
        self.load_settings()

        # After the restore, because restoreState() brings back whatever was
        # visible last time. The 3D view is still a "Coming Soon" placeholder,
        # so it is not offered as a tab.
        self.plot_3d_dock.setVisible(False)

    def setup_docks(self):
        """Create and arrange dock widgets with icon sidebar navigation."""

        # Create plot widgets first (needed for export panel)
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

        # Create left panel with icon sidebar navigation
        # Pass plot_widget for export functionality
        self.left_panel_dock = QDockWidget("Controls", self)
        self.left_panel_dock.setObjectName("LeftPanelDock")
        self.left_panel = LeftPanelWidget(
            self.data_model,
            plot_widget=self.plot_2d.plot_widget
        )
        self.left_panel_dock.setWidget(self.left_panel)

        # Build layout: LEFT PANEL | TABBED CENTER

        # Left: Single dock with icon sidebar
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.left_panel_dock)

        # Center: Tabbed plots and data display
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.plot_2d_dock)

        # Tabify the others on top of it
        self.tabifyDockWidget(self.plot_2d_dock, self.plot_3d_dock)
        # The 3D view is a placeholder ("Coming Soon"), so it is not offered as
        # a tab until it is implemented.
        self.plot_3d_dock.setVisible(False)
        self.tabifyDockWidget(self.plot_2d_dock, self.data_dock)
        self.tabifyDockWidget(self.plot_2d_dock, self.plot_nearfield_dock)

        # Make 2D plot the active tab
        self.plot_2d_dock.raise_()

        # Size constraints - minimum only, no max (auto-sizing)
        self.left_panel_dock.setMinimumWidth(350)

    def setup_menus(self):
        """Create menu bar with Help menu."""
        menubar = self.menuBar()

        # Help menu
        file_menu = menubar.addMenu("&File")
        save_session_action = QAction("&Save Session…", self)
        save_session_action.setShortcut("Ctrl+Shift+S")
        save_session_action.setStatusTip("Save the loaded files, processing, view, styles and masks")
        save_session_action.triggered.connect(self.save_session)
        file_menu.addAction(save_session_action)
        load_session_action = QAction("&Open Session…", self)
        load_session_action.setShortcut("Ctrl+Shift+O")
        load_session_action.setStatusTip("Replace the workspace with a saved session")
        load_session_action.triggered.connect(self.load_session)
        file_menu.addAction(load_session_action)

        help_menu = menubar.addMenu("&Help")

        doc_action = QAction("&Documentation", self)
        doc_action.setShortcut(QKeySequence("F1"))
        doc_action.setStatusTip("Open documentation")
        doc_action.triggered.connect(self.show_help)
        help_menu.addAction(doc_action)

        context_help_action = QAction("&Context Help", self)
        context_help_action.setShortcut(QKeySequence("Shift+F1"))
        context_help_action.setStatusTip("Show help for current panel")
        context_help_action.triggered.connect(self.show_context_help)
        help_menu.addAction(context_help_action)

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
        self.left_panel.nearfield_calculated.connect(self.on_nearfield_calculated)

        # Export completed status
        self.left_panel.export_completed.connect(
            lambda path: self.status_message.emit(f"Exported: {Path(path).name}")
        )

    def reset_layout(self):
        """Reset dock layout to default."""
        # Remove all docks
        self.removeDockWidget(self.left_panel_dock)
        self.removeDockWidget(self.plot_2d_dock)
        self.removeDockWidget(self.plot_3d_dock)
        self.removeDockWidget(self.data_dock)
        self.removeDockWidget(self.plot_nearfield_dock)

        # Re-add in default configuration
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.left_panel_dock)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.plot_2d_dock)
        self.tabifyDockWidget(self.plot_2d_dock, self.plot_3d_dock)
        self.tabifyDockWidget(self.plot_2d_dock, self.data_dock)
        self.tabifyDockWidget(self.plot_2d_dock, self.plot_nearfield_dock)

        # Make 2D plot active tab
        self.plot_2d_dock.raise_()

        # Show/hide docks
        self.left_panel_dock.setVisible(True)
        self.plot_2d_dock.setVisible(True)
        # The 3D view is not implemented yet, so it is not offered as a tab.
        self.plot_3d_dock.setVisible(False)
        self.data_dock.setVisible(True)
        self.plot_nearfield_dock.setVisible(True)

        self.status_message.emit("Layout reset to default")

    def on_pattern_loaded(self, pattern):
        """Handle pattern loaded event."""
        if pattern is not None:
            n_freq = len(pattern.frequencies)
            # Handle both uniform and non-uniform theta patterns
            if pattern.has_uniform_theta:
                n_theta = len(pattern.theta_angles)
                theta_info = f"{n_theta}"
            else:
                n_theta = pattern.theta_grid.shape[0]
                theta_info = f"{n_theta} (per-phi)"
            n_phi = len(pattern.phi_angles)
            pol = pattern.polarization

            msg = f"Pattern loaded: {n_freq} freq, {theta_info}x{n_phi} points, {pol} pol"
            self.status_message.emit(msg)

    def on_nearfield_calculated(self, near_field_data):
        """Handle near field calculation completion."""
        self.plot_nearfield.plot_near_field(near_field_data)
        self.plot_nearfield_dock.raise_()

    def save_settings(self):
        """Save window geometry and dock states."""
        settings = QSettings(self.SETTINGS_ORG, self.SETTINGS_APP)
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())

    def load_settings(self):
        """Load window geometry and dock states."""
        settings = QSettings(self.SETTINGS_ORG, self.SETTINGS_APP)
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        window_state = settings.value("windowState")
        if window_state:
            self.restoreState(window_state)

    def closeEvent(self, event):
        """Handle window close event."""
        self.save_settings()
        self._stop_background_workers()
        event.accept()

    def _stop_background_workers(self):
        """
        Wait for background threads before the window goes away.

        A running QThread whose owner is destroyed aborts the process with
        "QThread: Destroyed while thread is still running".
        """
        analysis = getattr(self.left_panel, 'analysis_panel', None)
        worker = getattr(analysis, 'swe_worker', None)
        if worker is not None and worker.isRunning():
            worker.wait(5000)

        file_panel = getattr(self.left_panel, 'file_manager', None)
        for loader in list(getattr(file_panel, '_load_workers', [])):
            loader.cancel()
            loader.wait(5000)

    def reset_to_default_layout(self):
        """
        Clear the saved window state and restore the default dock layout.

        Calling setup_docks() a second time would build a second set of plot
        widgets, each connected to the same data model, so the rearrangement is
        delegated to reset_layout(), which moves the existing docks.
        """
        settings = QSettings(self.SETTINGS_ORG, self.SETTINGS_APP)
        settings.remove("geometry")
        settings.remove("windowState")
        self.reset_layout()

    # Session files
    def save_session(self):
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from antenna_pattern_viewer.session import SESSION_SUFFIX, collect_session, write_session

        path, _ = QFileDialog.getSaveFileName(
            self, "Save Session", f"session{SESSION_SUFFIX}",
            f"Antenna Pattern Viewer session (*{SESSION_SUFFIX});;All files (*)")
        if not path:
            return
        try:
            written = write_session(path, collect_session(self))
        except (OSError, TypeError, ValueError) as e:
            QMessageBox.critical(self, "Save Failed", f"Could not save the session:\n{e}")
            return
        self.statusBar().showMessage(f"Session saved to {written}", 5000)

    def load_session(self):
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from antenna_pattern_viewer.session import SESSION_SUFFIX, read_session, restore_session

        path, _ = QFileDialog.getOpenFileName(
            self, "Open Session", "",
            f"Antenna Pattern Viewer session (*{SESSION_SUFFIX});;All files (*)")
        if not path:
            return
        try:
            data = read_session(path)
        except (OSError, ValueError) as e:
            QMessageBox.critical(self, "Open Failed", f"Could not read the session:\n{e}")
            return

        def done(missing):
            if missing:
                QMessageBox.warning(self, "Files Missing",
                                    "These files from the session were not found and were "
                                    "skipped:\n" + "\n".join(missing))
            self.statusBar().showMessage(f"Session restored from {path}", 5000)

        try:
            restore_session(self, data, on_done=done)
        except Exception as e:
            QMessageBox.critical(self, "Open Failed", f"Could not restore the session:\n{e}")

    # Help methods
    def show_help(self):
        """Show the help documentation dialog."""
        from antenna_pattern_viewer.help import HelpDialog
        dialog = HelpDialog(self)
        dialog.exec()

    def show_context_help(self):
        """Show context-sensitive help for the current panel."""
        from antenna_pattern_viewer.help import HelpDialog
        panel_index = self.left_panel.panel_stack.currentIndex()
        HelpDialog.show_context_help(self, panel_index)

    # Convenience methods to access panels
    def show_files_panel(self):
        """Show the Files panel in the left sidebar."""
        self.left_panel.show_files_panel()

    def show_view_panel(self):
        """Show the View panel in the left sidebar."""
        self.left_panel.show_view_panel()

    def show_processing_panel(self):
        """Show the Processing panel in the left sidebar."""
        self.left_panel.show_processing_panel()

    def show_analysis_panel(self):
        """Show the Analysis panel in the left sidebar."""
        self.left_panel.show_analysis_panel()

    def show_export_panel(self):
        """Show the Export panel in the left sidebar."""
        self.left_panel.show_export_panel()
