"""
Left panel widget combining icon sidebar, pattern strip, and stacked panels.

This widget serves as the main container for the left side of the application,
providing navigation between panels. It is designed to be reusable across
different applications by allowing customization of the first panel.

Usage:
    # Default (AntennaPatternViewer with file manager)
    left_panel = LeftPanelWidget(data_model, plot_widget=plot_widget)

    # Custom first panel (e.g., pattern generator)
    generator_widget = MyPatternGeneratorWidget(data_model)
    left_panel = LeftPanelWidget(
        data_model,
        first_panel_widget=generator_widget,
        first_panel_config={"icon": "🔧", "tooltip": "Generator - Create patterns", "name": "generator"},
        show_pattern_strip=False,  # Optional: hide pattern strip
    )
"""
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget, QSizePolicy, QFileDialog
)
from PyQt6.QtCore import pyqtSignal
from typing import Optional, Dict

from .icon_sidebar import IconSidebar
from .pattern_list_widget import PatternListWidget
from .view_panel import ViewPanel
from .processing_panel import ProcessingPanel
from .export_widget import ExportWidget

import logging
logger = logging.getLogger(__name__)


class LeftPanelWidget(QWidget):
    """
    Container widget for the left panel with icon navigation.

    Layout:
    +----------+----------------------+
    |          | PatternStrip         |
    | Icon     +----------------------+
    | Sidebar  | QStackedWidget       |
    |  Custom  |  [0] CustomPanel     |
    |  View    |  [1] ViewPanel       |
    |  Proc    |  [2] ProcessingPanel |
    |  Anlys   |  [3] AnalysisPanel   |
    |  Export  |  [4] ExportPanel     |
    +----------+----------------------+

    Args:
        data_model: The pattern data model
        plot_widget: Optional plot widget for export functionality
        first_panel_widget: Optional custom widget for the first panel.
            If None, uses FileManagerWidget.
        first_panel_config: Optional dict with icon/tooltip for first panel.
            Keys: "icon", "tooltip", "name"
        show_pattern_strip: Whether to show the pattern strip (default True)
        parent: Parent widget
    """

    # Forward signals from child widgets
    nearfield_calculated = pyqtSignal(dict)

    # File filter for pattern files
    FILE_FILTER = "Pattern Files (*.cut *.ffd *.npz *.sph);;All Files (*)"

    def __init__(
        self,
        data_model,
        plot_widget=None,
        first_panel_widget: Optional[QWidget] = None,
        first_panel_config: Optional[Dict[str, str]] = None,
        show_pattern_strip: bool = True,
        parent=None
    ):
        super().__init__(parent)
        self.data_model = data_model
        self.plot_widget = plot_widget
        self._first_panel_widget = first_panel_widget
        self._first_panel_config = first_panel_config
        self._show_pattern_strip = show_pattern_strip

        # Will be set during setup_panels
        self.first_panel = None  # The first panel widget (custom or FileManager)
        self.file_manager = None  # Only set if using default FileManager

        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        """Setup the left panel UI."""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Icon sidebar (left edge) - pass custom first panel config if provided
        self.icon_sidebar = IconSidebar(first_panel=self._first_panel_config)
        main_layout.addWidget(self.icon_sidebar)

        # Right side container (pattern strip + stacked panels)
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Pattern list (optionally visible at top)
        self.pattern_list = None
        if self._show_pattern_strip:
            self.pattern_list = PatternListWidget(self.data_model)
            right_layout.addWidget(self.pattern_list)

        # Stacked widget for panels
        self.panel_stack = QStackedWidget()
        self.setup_panels()
        right_layout.addWidget(self.panel_stack)

        main_layout.addWidget(right_container)

        # Set size policy - expand horizontally based on content
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

    def setup_panels(self):
        """Create and add all panels to the stack."""
        # Panel 0: First panel (custom or FileManager)
        if self._first_panel_widget is not None:
            self.first_panel = self._first_panel_widget
        else:
            # Import here to avoid circular imports and make FileManager optional
            from .file_manager_widget import FileManagerWidget
            self.first_panel = FileManagerWidget(self.data_model)
            self.file_manager = self.first_panel  # Alias for backwards compatibility
        self.panel_stack.addWidget(self.first_panel)

        # Panel 1: View Panel
        self.view_panel = ViewPanel(self.data_model)
        self.panel_stack.addWidget(self.view_panel)

        # Panel 2: Processing Panel
        self.processing_panel = ProcessingPanel(self.data_model)
        self.panel_stack.addWidget(self.processing_panel)

        # Panel 3: Analysis Panel
        from .analysis_panel import AnalysisPanel
        self.analysis_panel = AnalysisPanel(self.data_model)
        self.panel_stack.addWidget(self.analysis_panel)

        # Panel 4: Export Panel
        self.export_panel = ExportWidget(self.data_model, plot_widget=self.plot_widget)
        self.panel_stack.addWidget(self.export_panel)

    def connect_signals(self):
        """Connect signals between components."""
        # Icon sidebar -> panel stack
        self.icon_sidebar.panel_changed.connect(self.panel_stack.setCurrentIndex)

        # Pattern list -> file dialog (only if pattern list exists)
        if self.pattern_list is not None:
            self.pattern_list.add_pattern_requested.connect(self.open_file_dialog)

        # View panel -> data model
        self.view_panel.parameters_changed.connect(self.on_view_params_changed)

        # Processing panel signals -> data model operations
        self.processing_panel.apply_phase_center_signal.connect(self.on_apply_phase_center)
        self.processing_panel.apply_mars_signal.connect(self.on_apply_mars)
        self.processing_panel.polarization_changed.connect(self.on_polarization_changed)
        self.processing_panel.coordinate_format_changed.connect(self.on_coordinate_format_changed)
        self.processing_panel.shift_theta_origin_signal.connect(self.on_shift_theta_origin)
        self.processing_panel.shift_phi_origin_signal.connect(self.on_shift_phi_origin)
        self.processing_panel.normalize_amplitude_signal.connect(self.on_normalize_amplitude)

        # Analysis panel -> forward nearfield signal
        self.analysis_panel.nearfield_calculated.connect(self.nearfield_calculated.emit)

        # Comparison set changes -> update view panel status
        self.data_model.comparison_set_changed.connect(self.on_comparison_set_changed)

    # === VIEW PANEL HANDLERS ===

    def on_view_params_changed(self):
        """Handle view parameter changes from view panel."""
        params = self.view_panel.get_current_parameters()
        self.data_model.update_view_params(params)
        self.data_model.view_parameters_changed.emit(params)

    def on_comparison_set_changed(self, comparison_ids):
        """Handle comparison set changes - update view panel status."""
        compatibility = self.data_model.get_comparison_compatibility()
        num_patterns = len(comparison_ids)
        self.view_panel.update_comparison_status(num_patterns, compatibility)

    # === PROCESSING PANEL HANDLERS ===

    def on_apply_phase_center(self, x, y, z, frequency):
        """Handle phase center translation toggle."""
        if self.data_model.original_pattern is None:
            return

        try:
            is_checked = self.processing_panel.apply_phase_center_check.isChecked()

            if is_checked:
                phase_center = [x, y, z]
                self.data_model.set_phase_center_translation(phase_center)
                logger.info(f"Phase center shift enabled: {phase_center}")
            else:
                self.data_model.set_phase_center_translation(None)
                logger.info("Phase center shift disabled")

            self.processing_panel.on_pattern_loaded(self.data_model.pattern)
            self.data_model.view_parameters_changed.emit(self.data_model._view_params)

        except Exception as e:
            logger.error(f"Failed to toggle phase center: {e}", exc_info=True)

    def on_apply_mars(self, max_radial_extent):
        """Handle MARS toggle."""
        if self.data_model.original_pattern is None:
            return

        try:
            is_checked = self.processing_panel.apply_mars_check.isChecked()

            if is_checked:
                self.data_model.set_mars_processing(max_radial_extent)
                logger.info(f"MARS enabled: max_extent={max_radial_extent}")
            else:
                self.data_model.set_mars_processing(None)
                logger.info("MARS disabled")

            self.processing_panel.on_pattern_loaded(self.data_model.pattern)
            self.data_model.view_parameters_changed.emit(self.data_model._view_params)

        except Exception as e:
            logger.error(f"Failed to toggle MARS: {e}", exc_info=True)

    def on_polarization_changed(self, polarization):
        """Handle polarization change."""
        if self.data_model.pattern is None:
            return

        # Skip if already at this polarization
        if polarization == self.data_model.pattern.polarization:
            return

        try:
            pattern = self.data_model.pattern.copy()
            pattern.assign_polarization(polarization)
            self.data_model._pattern = pattern
            self.data_model.pattern_modified.emit(pattern)
            self.data_model.processing_applied.emit("polarization_conversion")
            self.processing_panel.on_pattern_loaded(pattern)
            self.data_model.view_parameters_changed.emit(self.data_model._view_params)

        except Exception as e:
            logger.error(f"Failed to convert polarization: {e}")

    def on_coordinate_format_changed(self, format_type):
        """Handle coordinate format change."""
        if self.data_model.pattern is None:
            return

        try:
            if format_type == 'central':
                pattern = self.data_model.pattern.to_central_coordinates()
            else:
                pattern = self.data_model.pattern.to_sided_coordinates()

            self.data_model._pattern = pattern
            self.data_model.pattern_modified.emit(pattern)
            self.data_model.processing_applied.emit("coordinate_conversion")
            self.processing_panel.on_pattern_loaded(pattern)
            self.data_model.view_parameters_changed.emit(self.data_model._view_params)

        except Exception as e:
            logger.error(f"Failed to convert coordinates: {e}")

    def on_shift_theta_origin(self, theta_offset):
        """Handle theta origin shift toggle."""
        if self.data_model.original_pattern is None:
            return

        try:
            is_checked = self.processing_panel.apply_theta_shift_check.isChecked()

            if is_checked:
                self.data_model.set_theta_origin_shift(theta_offset)
                logger.info(f"Theta origin shift enabled: {theta_offset} deg")
            else:
                self.data_model.set_theta_origin_shift(None)
                logger.info("Theta origin shift disabled")

            self.processing_panel.on_pattern_loaded(self.data_model.pattern)
            self.data_model.view_parameters_changed.emit(self.data_model._view_params)

        except Exception as e:
            logger.error(f"Failed to toggle theta origin shift: {e}", exc_info=True)

    def on_shift_phi_origin(self, phi_offset):
        """Handle phi origin shift toggle."""
        if self.data_model.original_pattern is None:
            return

        try:
            is_checked = self.processing_panel.apply_phi_shift_check.isChecked()

            if is_checked:
                self.data_model.set_phi_origin_shift(phi_offset)
                logger.info(f"Phi origin shift enabled: {phi_offset} deg")
            else:
                self.data_model.set_phi_origin_shift(None)
                logger.info("Phi origin shift disabled")

            self.processing_panel.on_pattern_loaded(self.data_model.pattern)
            self.data_model.view_parameters_changed.emit(self.data_model._view_params)

        except Exception as e:
            logger.error(f"Failed to toggle phi origin shift: {e}", exc_info=True)

    def on_normalize_amplitude(self, norm_type):
        """Handle amplitude normalization toggle."""
        if self.data_model.original_pattern is None:
            return

        try:
            is_checked = self.processing_panel.apply_normalization_check.isChecked()

            if is_checked and norm_type:
                self.data_model.set_amplitude_normalization(norm_type)
                logger.info(f"Amplitude normalization enabled: {norm_type}")
            else:
                self.data_model.set_amplitude_normalization(None)
                logger.info("Amplitude normalization disabled")

            self.processing_panel.on_pattern_loaded(self.data_model.pattern)
            self.data_model.view_parameters_changed.emit(self.data_model._view_params)

        except Exception as e:
            logger.error(f"Failed to toggle amplitude normalization: {e}", exc_info=True)

    # === FILE OPERATIONS ===

    def open_file_dialog(self):
        """Open file dialog to load patterns."""
        # Only works if file_manager exists (default configuration)
        if self.file_manager is None:
            logger.warning("open_file_dialog called but file_manager is not available")
            return

        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Open Pattern Files",
            "",
            self.FILE_FILTER
        )

        if files:
            from pathlib import Path
            for file_path in files:
                self.file_manager.load_pattern_file(Path(file_path))

    # === PANEL NAVIGATION ===

    # Panel indices (match IconSidebar)
    PANEL_FIRST = 0
    PANEL_VIEW = 1
    PANEL_PROCESSING = 2
    PANEL_ANALYSIS = 3
    PANEL_EXPORT = 4

    def set_current_panel(self, index: int):
        """Set the current panel by index."""
        self.icon_sidebar.set_current_panel(index)
        self.panel_stack.setCurrentIndex(index)

    def show_first_panel(self):
        """Show the first panel (custom or Files)."""
        self.set_current_panel(self.PANEL_FIRST)

    def show_files_panel(self):
        """Show the Files panel (alias for show_first_panel for backwards compatibility)."""
        self.show_first_panel()

    def show_view_panel(self):
        """Show the View panel."""
        self.set_current_panel(self.PANEL_VIEW)

    def show_processing_panel(self):
        """Show the Processing panel."""
        self.set_current_panel(self.PANEL_PROCESSING)

    def show_analysis_panel(self):
        """Show the Analysis panel."""
        self.set_current_panel(self.PANEL_ANALYSIS)

    def show_export_panel(self):
        """Show the Export panel."""
        self.set_current_panel(self.PANEL_EXPORT)

    @property
    def export_completed(self):
        """Forward export_completed signal from export panel."""
        return self.export_panel.export_completed
