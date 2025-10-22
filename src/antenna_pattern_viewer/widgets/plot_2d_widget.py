"""
2D plot widget for antenna patterns.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QFileDialog, QMessageBox
from PyQt6.QtCore import pyqtSignal
import logging

from antenna_pattern_viewer.widgets.plot_widget import PlotWidget

logger = logging.getLogger(__name__)


class Plot2DWidget(QWidget):
    """Widget for 2D pattern visualization."""
    
    # Signals
    plot_updated = pyqtSignal()
    
    def __init__(self, data_model, parent=None):
        super().__init__(parent)
        self.data_model = data_model
        self.setup_ui()
        self.connect_signals()
        
        logger.debug("Plot2DWidget initialized")
    
    def setup_ui(self):
        """Setup 2D plot UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Reuse existing PlotWidget
        self.plot_widget = PlotWidget()
        layout.addWidget(self.plot_widget)
    
    def connect_signals(self):
        """Connect to data model signals."""
        self.data_model.pattern_loaded.connect(self.on_pattern_changed)
        self.data_model.pattern_modified.connect(self.on_pattern_changed)
        self.data_model.view_parameters_changed.connect(self.on_view_params_changed)
    
    def on_pattern_changed(self, pattern):
        """Update plot when pattern changes."""
        self.plot_widget.current_pattern = pattern
        
        if pattern is None:
            self.plot_widget.clear_plot()
            self.plot_updated.emit()
            logger.debug("Plot cleared - no pattern")
            return
        
        # Trigger plot update with current view parameters
        self.update_plot_from_model()
        
        logger.debug("Pattern updated in plot widget")
    
    def on_view_params_changed(self, params):
        """Update plot when view parameters change."""
        if self.plot_widget.current_pattern is None:
            return
        
        # Trigger plot update
        self.update_plot_from_model()
        
        logger.debug("Plot updated from view parameters")
    
    def update_plot_from_model(self):
        """Update the plot using current pattern and view parameters."""
        pattern = self.data_model.pattern
        if pattern is None:
            return
        
        # Get view parameters from model
        params = self.data_model._view_params
        
        # Extract parameters
        frequencies = params.get('selected_frequencies', [])
        phi_angles = params.get('selected_phi', [])
        
        # If no selection, use defaults
        if not frequencies:
            frequencies = [pattern.frequencies[0]] if len(pattern.frequencies) > 0 else []
        if not phi_angles:
            phi_angles = [0]  # Default phi cut
        
        plot_type = params.get('plot_type', '1d_cut')
        component = params.get('component', 'e_co')
        value_type = params.get('value_type', 'gain')
        show_cross_pol = params.get('show_cross_pol', False)
        unwrap_phase = params.get('unwrap_phase', True)
        statistics_enabled = params.get('statistics_enabled', False)
        show_range = params.get('show_range', True)
        statistic_type = params.get('statistic_type', 'mean')
        percentile_range = params.get('percentile_range', (25, 75))
        
        # Call plot widget's update_plot method
        try:
            self.plot_widget.update_plot(
                pattern=pattern,
                frequencies=frequencies,
                phi_angles=phi_angles,
                value_type=value_type,
                show_cross_pol=show_cross_pol,
                unwrap_phase=unwrap_phase,
                plot_format=plot_type,
                component=component,
                statistics_enabled=statistics_enabled,
                show_range=show_range,
                statistic_type=statistic_type,
                percentile_range=percentile_range
            )
            self.plot_updated.emit()
        except Exception as e:
            logger.error(f"Failed to update plot: {e}")
    
    def export_plot(self):
        """Export current plot to image file."""
        if self.plot_widget.current_pattern is None:
            QMessageBox.warning(
                self,
                "No Plot",
                "No pattern loaded to export"
            )
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Plot",
            "",
            "PNG Files (*.png);;PDF Files (*.pdf);;SVG Files (*.svg);;All Files (*.*)"
        )
        
        if file_path:
            try:
                self.plot_widget.figure.savefig(file_path, dpi=300, bbox_inches='tight')
                logger.info(f"Plot exported to: {file_path}")
            except Exception as e:
                logger.error(f"Failed to export plot: {e}")
                QMessageBox.critical(
                    self,
                    "Export Error",
                    f"Failed to export plot:\n{str(e)}"
                )