"""
2D plot widget for antenna patterns.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QFileDialog, QMessageBox
from PyQt6.QtCore import pyqtSignal
import logging

# Import existing plot widget (to be migrated from antenna_pattern/gui)
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
        # Just store the pattern - don't replot yet
        self.plot_widget.current_pattern = pattern
        
        # Clear the plot if no pattern
        if pattern is None:
            self.plot_widget.clear_plot()
        
        self.plot_updated.emit()
        logger.debug("Pattern updated in plot widget")
    
    def on_view_params_changed(self, params):
        """Update plot when view parameters change."""
        # Update plot widget settings based on params
        if 'normalize' in params:
            self.plot_widget.normalize_check.setChecked(params['normalize'])
        
        # The plot_widget will automatically replot when its controls change
        # through its internal signal connections
        
        logger.debug("Plot settings updated from view parameters")
    
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
        
        if not file_path:
            return
        
        try:
            # Save the matplotlib figure
            self.plot_widget.figure.savefig(
                file_path,
                dpi=300,
                bbox_inches='tight'
            )
            logger.info(f"Plot exported to: {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to export plot: {e}")
            QMessageBox.critical(
                self,
                "Export Error",
                f"Failed to export plot:\n{str(e)}"
            )