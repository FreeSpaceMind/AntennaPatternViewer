"""
Matplotlib integration widget for PyQt6.
"""

import numpy as np
import matplotlib
matplotlib.use('QtAgg')  # Use Qt5Agg backend for PyQt6 compatibility

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from typing import Tuple, Optional, Any

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QCheckBox,
                             QLineEdit, QLabel, QFileDialog, QMessageBox)
from pathlib import Path
from PyQt6.QtCore import pyqtSignal

from ..plotting import plot_pattern_cut, plot_pattern_2d_polar, plot_multiple_patterns
from ..plot_style import PlotStyle, apply_style, cycle_colors, series_labels
from ..pattern_markers import analyze_cut, draw_markers
from ..plot_layouts import (plot_amplitude_phase, plot_frequency_sweep, plot_polar_cut,
                            plot_small_multiples)
from ..spec_mask import SpecMask, draw_masks, mask_report
from ..plot_cursors import CursorTracker
from PyQt6.QtCore import QSettings

import logging

logger = logging.getLogger(__name__)


class PlotWidget(QWidget):
    """Widget containing matplotlib canvas and plot formatting controls."""

    STYLE_FORMATS = ('1d_cut', '2d_polar', 'polar_cut', 'amp_phase', 'small_multiples',
                     'sweep', 'near_field')
    STYLE_FORMAT_NAMES = {'1d_cut': '1D cut', '2d_polar': '2D polar', 'polar_cut': 'Polar cut',
                          'amp_phase': 'Amplitude + phase', 'small_multiples': 'Small multiples',
                          'sweep': 'Frequency sweep', 'near_field': 'Near field'}
    POLAR_FORMATS = ('2d_polar', 'polar_cut')
    MULTI_AXES_FORMATS = ('amp_phase', 'small_multiples')
    MARKER_FORMATS = ('1d_cut', 'amp_phase', 'small_multiples')
    CURSOR_FORMATS = ('1d_cut', 'amp_phase', 'small_multiples', 'sweep')
    MASK_FORMATS = ('1d_cut', 'amp_phase', 'small_multiples')
    SETTINGS_ORG = 'AntennaPatternViewer'
    SETTINGS_APP = 'PlotStyle'
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_pattern = None
        self.current_frequencies = None
        self.current_phi_angles = None
        self.current_value_type = 'gain'
        self.current_show_cross_pol = False
        self.current_plot_format = '1d_cut'
        self.current_component = 'e_co'
        self.current_statistics_enabled = False
        self.current_show_range = True
        self.current_statistic_type = 'mean'
        self.current_percentile_range = (25, 75)
        # One style per plot format: a 1D cut and a 2D polar image want
        # different labels and ticks. Loaded from settings, edited live by
        # the Plot Style dialog, applied after every draw.
        self.styles = {key: PlotStyle() for key in self.STYLE_FORMATS}
        self.style_dialog = None
        self._cycle_colors = None
        self._comparison_args = None
        self.current_sweep_metric = 'peak_gain'
        self._data_axes = []          # the axes carrying data, in order
        self._marker_axes = []        # the subset markers and masks go on
        self.masks = []
        self.mask_dialog = None
        self._mask_artists = []
        self._mask_text = ""
        self._load_styles()
        self.current_colorbar = None

        # Remembered matplotlib limits and limit-field text, one entry per
        # plot format, created on demand by _limits() and _limit_fields().
        self.current_matplotlib_limits = {}
        self.axis_limits_memory = {}
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the plot widget UI."""
        layout = QVBoxLayout()
        
        # Create matplotlib figure and canvas
        # A layout engine re-runs on every draw, so titles and labels are
        # not clipped when a style makes them larger or a format adds panels.
        self.figure = Figure(figsize=(10, 6), layout='tight')
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        # Plot formatting controls
        format_layout = QHBoxLayout()
        
        # Grid checkbox
        self.grid_check = QCheckBox("Grid")
        self.grid_check.setChecked(True)
        self.grid_check.toggled.connect(self.update_plot_formatting)
        format_layout.addWidget(self.grid_check)
        
        # Legend/Colorbar checkbox
        self.legend_colorbar_check = QCheckBox("Legend")
        self.legend_colorbar_check.setChecked(True)
        self.legend_colorbar_check.toggled.connect(self.update_plot_formatting)
        format_layout.addWidget(self.legend_colorbar_check)

        # Normalize Checkbox
        self.normalize_check = QCheckBox("Normalize")
        self.normalize_check.setChecked(False)
        # toggled() passes the checkbox state, which would land in
        # preserve_limits. Normalizing changes the y scale, so the old limits
        # must not be kept.
        self.normalize_check.toggled.connect(
            lambda _checked: self.replot_current_data(preserve_limits=False))
        format_layout.addWidget(self.normalize_check)

        # Smooth checkbox (for 2D plots - bicubic interpolation)
        self.smooth_check = QCheckBox("Smooth")
        self.smooth_check.setChecked(False)
        self.smooth_check.toggled.connect(
            lambda _checked: self.replot_current_data(preserve_limits=True))
        self.smooth_check.setVisible(False)  # Initially hidden, shown only for 2D plots
        format_layout.addWidget(self.smooth_check)

        # Pattern markers (peak, HPBW, first sidelobe) and cursors, 1D cuts only
        self.markers_check = QCheckBox("Markers")
        self.markers_check.setToolTip("Mark the peak, the half-power beamwidth and the first "
                                      "sidelobe of each co-pol trace (gain cuts)")
        self.markers_check.toggled.connect(lambda _c: self.update_plot_formatting())
        format_layout.addWidget(self.markers_check)
        self.cursors_check = QCheckBox("Cursors")
        self.cursors_check.setToolTip("Hover for a data tip; click to pin cursor A, click again "
                                      "for B and the difference; right-click clears")
        self.cursors_check.toggled.connect(self._on_cursors_toggled)
        format_layout.addWidget(self.cursors_check)

        # X-axis/Phi limits
        self.x_phi_label = QLabel("X-axis:")
        format_layout.addWidget(self.x_phi_label)
        
        self.x_phi_min_edit = QLineEdit()
        self.x_phi_min_edit.setPlaceholderText("Auto")
        self.x_phi_min_edit.setMaximumWidth(60)
        self.x_phi_min_edit.editingFinished.connect(self.update_plot_formatting)
        format_layout.addWidget(self.x_phi_min_edit)
        
        format_layout.addWidget(QLabel("to"))
        
        self.x_phi_max_edit = QLineEdit()
        self.x_phi_max_edit.setPlaceholderText("Auto")
        self.x_phi_max_edit.setMaximumWidth(60)
        self.x_phi_max_edit.editingFinished.connect(self.update_plot_formatting)
        format_layout.addWidget(self.x_phi_max_edit)
        
        # Y-axis/Theta limits
        self.y_theta_label = QLabel("Y-axis:")
        format_layout.addWidget(self.y_theta_label)
        
        self.y_theta_min_edit = QLineEdit()
        self.y_theta_min_edit.setPlaceholderText("Auto")
        self.y_theta_min_edit.setMaximumWidth(60)
        self.y_theta_min_edit.editingFinished.connect(self.update_plot_formatting)
        format_layout.addWidget(self.y_theta_min_edit)
        
        format_layout.addWidget(QLabel("to"))
        
        self.y_theta_max_edit = QLineEdit()
        self.y_theta_max_edit.setPlaceholderText("Auto")
        self.y_theta_max_edit.setMaximumWidth(60)
        self.y_theta_max_edit.editingFinished.connect(self.update_plot_formatting)
        format_layout.addWidget(self.y_theta_max_edit)
        
        # Z-axis/Colorbar limits (for 2D plots only)
        self.z_label = QLabel("Z-axis:")
        self.z_label.setVisible(False)
        format_layout.addWidget(self.z_label)
        
        self.z_min_edit = QLineEdit()
        self.z_min_edit.setPlaceholderText("Auto")
        self.z_min_edit.setMaximumWidth(60)
        self.z_min_edit.editingFinished.connect(self.update_plot_formatting)
        self.z_min_edit.setVisible(False)
        format_layout.addWidget(self.z_min_edit)
        
        self.z_to_label = QLabel("to")
        self.z_to_label.setVisible(False)
        format_layout.addWidget(self.z_to_label)
        
        self.z_max_edit = QLineEdit()
        self.z_max_edit.setPlaceholderText("Auto")
        self.z_max_edit.setMaximumWidth(60)
        self.z_max_edit.editingFinished.connect(self.update_plot_formatting)
        self.z_max_edit.setVisible(False)
        format_layout.addWidget(self.z_max_edit)

        # Reset Scale button
        self.reset_scale_btn = QPushButton("Reset Scale")
        self.reset_scale_btn.clicked.connect(self.reset_scale)
        format_layout.addWidget(self.reset_scale_btn)

        # Export what is on screen, which is the common ask after looking at a
        # cut. The Export panel writes whole patterns, not the plotted curves.
        self.export_curves_btn = QPushButton("Export Plot Data")
        self.export_curves_btn.setToolTip(
            "Write the plotted curves to CSV: one column of x values and one "
            "column per trace, exactly as displayed")
        self.export_curves_btn.clicked.connect(self.export_plotted_data)
        format_layout.addWidget(self.export_curves_btn)

        # Everything about the plot's appearance lives in a floating dialog so
        # the strip stays as it is.
        self.style_btn = QPushButton("Style…")
        self.style_btn.setToolTip("Titles, labels, fonts, legend, grid, ticks, line styles, "
                                  "per-trace colours and presets")
        self.style_btn.clicked.connect(self.open_style_dialog)
        format_layout.addWidget(self.style_btn)
        self.masks_btn = QPushButton("Masks…")
        self.masks_btn.setToolTip("Specification masks: import from CSV or define points; "
                                  "violations are reported under the plot")
        self.masks_btn.clicked.connect(self.open_mask_dialog)
        format_layout.addWidget(self.masks_btn)

        format_layout.addStretch()
        
        # Readouts for markers and cursors; hidden until there is something to say
        self.readout_label = QLabel("")
        self.readout_label.setStyleSheet("font-size: 9pt; color: #444;")
        self.readout_label.setWordWrap(True)
        self.readout_label.setVisible(False)
        self._marker_artists = []
        self._marker_text = ""
        self._cursor_text = ""
        self.cursors = CursorTracker(self.canvas, lambda: self._data_axes or list(self.figure.axes),
                                     toolbar=self.toolbar)
        self.cursors.on_readout = self._on_cursor_readout

        # Add to main layout
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        layout.addLayout(format_layout)
        layout.addWidget(self.readout_label)
        
        self.setLayout(layout)
        
        # Store current plot format for control updates
        self.current_plot_format = '1d_cut'
        self.current_colorbar = None

    
    def update_plot(self, pattern, frequencies, phi_angles, value_type,
                    show_cross_pol, unwrap_phase, plot_format, component,
                    statistics_enabled=False, show_range=True,
                    statistic_type='mean', percentile_range=(25, 75),
                    preserve_limits=True, pattern_key=None, sweep_metric='peak_gain'
    ):
        """
        Update the plot with new data and parameters.
        
        Args:
            pattern: FarFieldSpherical object
            frequencies: Frequency or list of frequencies to plot
            phi_angles: Phi angle or list of phi angles to plot
            value_type: Type of value to plot ('gain', 'phase', 'axial_ratio')
            show_cross_pol: Whether to show cross-polarization
            plot_format: Plot format ('1d_cut', '2d_polar', 'near_field')
            component: Component to plot ('e_co', 'e_cx', 'e_theta', 'e_phi')
            statistics_enabled: Whether to plot statistics instead of individual cuts
            show_range: Whether to show min/max range for statistics
            statistic_type: Type of statistic ('mean', 'median', 'rms', 'percentile', 'std')
            percentile_range: Tuple of (lower, upper) percentiles
        """
        import numpy as np
        from ..plotting import plot_pattern_cut, plot_pattern_2d_polar, plot_pattern_statistics
        
        # Track if plot format is changing (for axis limits handling)
        old_plot_format = self.current_plot_format
        format_changing = (old_plot_format != plot_format)

        # Store current parameters for replotting
        self.current_pattern = pattern
        self.current_frequencies = frequencies
        self.current_phi_angles = phi_angles
        self.current_value_type = value_type
        self.current_show_cross_pol = show_cross_pol
        self.current_unwrap_phase = unwrap_phase
        self.current_plot_format = plot_format
        self.current_component = component
        self.current_statistics_enabled = statistics_enabled
        self.current_show_range = show_range
        self.current_statistic_type = statistic_type
        self.current_percentile_range = percentile_range
        self.current_pattern_key = pattern_key
        self.current_sweep_metric = sweep_metric
        self._comparison_args = None

        # Update control labels and visibility based on plot format
        self.update_controls_for_plot_format(format_changing, old_plot_format)

        # Axis limits describe the pattern they were taken from. Keeping them
        # across a different pattern leaves a narrow-beam pattern drawn on a
        # +/-180 degree axis, so they are dropped when the pattern changes.
        #
        # The key must identify the loaded pattern, not the object handed in:
        # every processing step builds a new FarFieldSpherical, so keying on
        # id(pattern) dropped the limits whenever MARS or any other step was
        # toggled, rescaling the axes mid-comparison. Callers that know which
        # instance is displayed pass its id; the fallback keeps the old
        # behaviour for callers that do not.
        if pattern_key is None:
            pattern_key = id(pattern) if pattern is not None else None
        if pattern_key != getattr(self, '_limits_pattern_key', None):
            self.clear_saved_limits()
            self._limits_pattern_key = pattern_key
            preserve_limits = False

        # Save current matplotlib axis limits before clearing (skip if resetting)
        if preserve_limits and self.figure.axes and not format_changing:
            ax = self._data_axes[0] if self._data_axes else self.figure.axes[0]
            limits = self._limits(old_plot_format)
            limits['ylim'] = ax.get_ylim()
            if hasattr(ax, 'set_theta_zero_location'):
                if getattr(self, 'current_colorbar', None):
                    limits['zlim'] = self.current_colorbar.mappable.get_clim()
            else:
                limits['xlim'] = ax.get_xlim()

        # Clear the current figure and create the axes the format needs;
        # the multi-axes layouts create their own.
        self.figure.clear()
        self.current_colorbar = None
        self._data_axes = []
        self._marker_axes = []
        self.ax = None
        if plot_format in self.POLAR_FORMATS:
            self.ax = self.figure.add_subplot(111, projection='polar')
        elif plot_format not in self.MULTI_AXES_FORMATS:
            self.ax = self.figure.add_subplot(111)
        self._apply_color_cycle(plot_format, frequencies, phi_angles, show_cross_pol)

        try:
            # Statistics plot (the single-axes formats it was written for)
            if statistics_enabled and plot_format in ('1d_cut', '2d_polar'):
                # Determine statistic_over based on what's selected
                if isinstance(phi_angles, list) and len(phi_angles) > 1:
                    statistic_over = 'phi'
                    freq_for_stats = frequencies if isinstance(frequencies, (int, float)) else frequencies[0]
                elif isinstance(frequencies, list) and len(frequencies) > 1:
                    statistic_over = 'frequency'
                    freq_for_stats = None
                else:
                    # Default to phi if only one of each is selected
                    statistic_over = 'phi'
                    freq_for_stats = frequencies if isinstance(frequencies, (int, float)) else frequencies[0]
                
                # Pass the selected cuts through for statistic_over='phi' too,
                # so the statistics describe what the user chose.
                phi_for_stats = (phi_angles if statistic_over == 'phi' else (
                    phi_angles if isinstance(phi_angles, (int, float)) else phi_angles[0]
                ))
                
                plot_pattern_statistics(
                    pattern=pattern,
                    statistic_over=statistic_over,
                    frequency=freq_for_stats,
                    phi=phi_for_stats,
                    component=component,
                    value_type=value_type,
                    statistic=statistic_type,
                    percentile_range=percentile_range,
                    show_range=show_range,
                    ax=self.ax
                )
            
            # 2D polar plot
            elif plot_format == "2d_polar":
                vmin, vmax = self.get_colorbar_limits()
                interpolation = 'bicubic' if self.smooth_check.isChecked() else 'none'
                fig, cbar = plot_pattern_2d_polar(
                    pattern=pattern,
                    frequency=frequencies,
                    component=component,
                    value_type=value_type,
                    ax=self.ax,
                    unwrap_phase=unwrap_phase,
                    normalize=self.normalize_check.isChecked(),
                    interpolation=interpolation,
                    vmin=vmin,
                    vmax=vmax,
                )
                # Store colorbar reference for formatting updates
                self.current_colorbar = cbar

            elif plot_format == 'polar_cut':
                plot_polar_cut(pattern, frequencies, phi_angles, value_type=value_type,
                               component=component, show_cross_pol=show_cross_pol,
                               unwrap_phase=unwrap_phase, ax=self.ax,
                               normalize=self.normalize_check.isChecked(),
                               colors=self._cycle_colors)

            elif plot_format == 'amp_phase':
                ax_amp, ax_phase = plot_amplitude_phase(
                    pattern, frequencies, phi_angles, component=component,
                    show_cross_pol=show_cross_pol, unwrap_phase=unwrap_phase,
                    normalize=self.normalize_check.isChecked(), fig=self.figure,
                    colors=self._cycle_colors)
                self.ax = ax_amp
                self._data_axes = [ax_amp, ax_phase]
                self._marker_axes = [ax_amp]

            elif plot_format == 'small_multiples':
                axes = plot_small_multiples(
                    pattern, frequencies, phi_angles, value_type=value_type,
                    component=component, show_cross_pol=show_cross_pol,
                    unwrap_phase=unwrap_phase, normalize=self.normalize_check.isChecked(),
                    fig=self.figure, colors=self._cycle_colors)
                self.ax = axes[0]
                self._data_axes = list(axes)
                self._marker_axes = list(axes)

            elif plot_format == 'sweep':
                plot_frequency_sweep(pattern, phi_angles, metric=sweep_metric,
                                     component=component, ax=self.ax, colors=self._cycle_colors)

            # 1D cut plot (default)
            else:
                plot_pattern_cut(
                    pattern=pattern,
                    frequency=frequencies,
                    phi=phi_angles,
                    show_cross_pol=show_cross_pol,
                    value_type=value_type,
                    component=component,
                    ax=self.ax,
                    unwrap_phase=unwrap_phase,
                    normalize=self.normalize_check.isChecked(),
                    colors=self._cycle_colors,
                )

            if not self._data_axes:
                self._data_axes = [self.ax]
            if plot_format == '1d_cut':
                self._marker_axes = [self.ax]

            # Restore saved axis limits to preserve scale across data changes.
            # Shared axes propagate x; y goes to the first (amplitude) panel.
            if preserve_limits:
                limits = self._limits(plot_format)
                if plot_format not in self.POLAR_FORMATS and limits.get('xlim'):
                    self.ax.set_xlim(limits['xlim'])
                if limits.get('ylim'):
                    self.ax.set_ylim(limits['ylim'])

            # Apply formatting
            self.update_plot_formatting()
            
        except Exception as e:
            if self.ax is None:
                self.figure.clear()
                self.ax = self.figure.add_subplot(111)
            self._data_axes = [self.ax]
            self._marker_axes = []
            self.ax.clear()
            self.ax.text(0.5, 0.5, f'Error plotting:\n{str(e)}',
                        ha='center', va='center', transform=self.ax.transAxes,
                        fontsize=10, color='red')
            self.ax.set_xlim(0, 1)
            self.ax.set_ylim(0, 1)
            self.ax.axis('off')
            # Do not let the 0-1 placeholder limits be captured and then pinned
            # onto the next successful plot.
            self.clear_saved_limits()
            logger.exception("Plotting error: %s", e)
            # The success path is drawn by update_plot_formatting(); only the
            # error placeholder needs its own draw. Drawing here unconditionally
            # rendered every figure twice.
            self.canvas.draw()

    def update_comparison_plot(self, patterns, labels, frequencies, phi_angles,
                               value_type, show_cross_pol, unwrap_phase=True,
                               preserve_limits=True):
        """
        Plot multiple patterns on the same axes for comparison.

        Args:
            patterns: List of FarFieldSpherical objects
            labels: List of legend labels for each pattern
            frequencies: List of frequencies to plot (applied to all patterns)
            phi_angles: List of phi angles to plot (applied to all patterns)
            value_type: Type of value to plot ('gain', 'phase', 'axial_ratio')
            show_cross_pol: Whether to show cross-polarization
            unwrap_phase: Whether to unwrap phase values
        """
        # Store current parameters (use first pattern as reference)
        self.current_pattern = patterns[0] if patterns else None
        self.current_frequencies = frequencies
        self.current_phi_angles = phi_angles
        self.current_value_type = value_type
        self.current_show_cross_pol = show_cross_pol
        self.current_unwrap_phase = unwrap_phase
        self.current_plot_format = '1d_cut'  # Comparison only supports 1D cuts
        self.current_colorbar = None
        # Remembered so that a replot from the strip or the style dialog
        # redraws the comparison rather than the active pattern alone.
        self._comparison_args = dict(patterns=list(patterns), labels=list(labels),
                                     frequencies=frequencies, phi_angles=phi_angles,
                                     value_type=value_type, show_cross_pol=show_cross_pol,
                                     unwrap_phase=unwrap_phase)

        # Update control labels for 1D plot
        self.update_controls_for_plot_format(format_changing=False)

        # Save current matplotlib axis limits before clearing
        limits = self._limits('1d_cut')
        if preserve_limits and self.figure.axes:
            ax = self.figure.axes[0]
            if not hasattr(ax, 'set_theta_zero_location'):  # Not polar
                limits['xlim'] = ax.get_xlim()
                limits['ylim'] = ax.get_ylim()
        elif not preserve_limits:
            limits['xlim'] = limits['ylim'] = None

        # Clear the current figure and create new axes
        self.figure.clear()
        self.ax = self.figure.add_subplot(111)
        self._data_axes = [self.ax]
        self._marker_axes = [self.ax]

        try:
            # plot_multiple_patterns expects phi_angles as a list of lists (one per pattern)
            # where each inner list contains the phi angles to plot for that pattern
            # Same for frequencies - wrap in list per pattern
            num_patterns = len(patterns)
            phi_angles_per_pattern = [phi_angles] * num_patterns
            freq_per_pattern = [frequencies[0] if frequencies else None] * num_patterns

            # Use plot_multiple_patterns for comparison
            plot_multiple_patterns(
                patterns=patterns,
                labels=labels,
                frequencies=freq_per_pattern,
                phi_angles=phi_angles_per_pattern,
                show_cross_pol=show_cross_pol,
                value_type=value_type,
                unwrap_phase=unwrap_phase,
                ax=self.ax
            )

            # Restore saved axis limits
            if limits['xlim']:
                self.ax.set_xlim(limits['xlim'])
            if limits['ylim']:
                self.ax.set_ylim(limits['ylim'])

            # Apply formatting
            self.update_plot_formatting()

        except Exception as e:
            self.ax.clear()
            self.ax.text(0.5, 0.5, f'Error plotting comparison:\n{str(e)}',
                        ha='center', va='center', transform=self.ax.transAxes,
                        fontsize=10, color='red')
            self.ax.set_xlim(0, 1)
            self.ax.set_ylim(0, 1)
            self.ax.axis('off')
            self.clear_saved_limits()
            logger.exception("Comparison plotting error: %s", e)
            self.canvas.draw()

    def _limits(self, plot_format):
        """Remembered matplotlib limits for a plot format (created on demand)."""
        return self.current_matplotlib_limits.setdefault(
            plot_format, {'xlim': None, 'ylim': None, 'zlim': None})

    def _limit_fields(self, plot_format):
        """Remembered text of the limit fields for a plot format."""
        return self.axis_limits_memory.setdefault(
            plot_format, {'x_min': '', 'x_max': '', 'y_min': '', 'y_max': '', 'z_min': '', 'z_max': ''})

    def update_controls_for_plot_format(self, format_changing=False, old_plot_format=None):
        """Show the strip controls that make sense for the current plot format."""
        fmt = self.current_plot_format
        is_polar = fmt in self.POLAR_FORMATS
        is_image = fmt == '2d_polar'

        if format_changing and old_plot_format is not None:
            self.save_current_axis_limits(old_plot_format)

        self.legend_colorbar_check.setText("Colorbar" if is_image else "Legend")
        if is_image:
            self.y_theta_label.setText("Theta:")
        elif fmt == 'polar_cut':
            self.y_theta_label.setText("Radial:")
        else:
            self.y_theta_label.setText("Y-axis:")
        self.x_phi_label.setText("X-axis:")

        show_x = not is_polar
        for widget in (self.x_phi_label, self.x_phi_min_edit, self.x_phi_max_edit):
            widget.setVisible(show_x)
        # The "to" label between the X fields
        parent_layout = self.x_phi_min_edit.parent().layout()
        for i in range(parent_layout.count()):
            item = parent_layout.itemAt(i)
            widget = item.widget() if item else None
            if (isinstance(widget, QLabel) and widget.text() == "to" and widget is not self.z_to_label
                    and parent_layout.indexOf(widget) > parent_layout.indexOf(self.x_phi_min_edit)
                    and parent_layout.indexOf(widget) < parent_layout.indexOf(self.y_theta_min_edit)):
                widget.setVisible(show_x)
                break

        for widget in (self.z_label, self.z_min_edit, self.z_to_label, self.z_max_edit):
            widget.setVisible(is_image)
        self.smooth_check.setVisible(is_image)
        self.markers_check.setVisible(fmt in self.MARKER_FORMATS)
        self.cursors_check.setVisible(fmt in self.CURSOR_FORMATS)
        self.masks_btn.setVisible(fmt in self.MASK_FORMATS)
        if fmt in self.CURSOR_FORMATS and self.cursors_check.isChecked():
            self.cursors.enable()
        else:
            self.cursors.disable()

        if format_changing:
            self.restore_axis_limits(fmt)

    def get_colorbar_limits(self):
        """Get colorbar limits from Z-axis controls."""
        try:
            vmin = float(self.z_min_edit.text()) if self.z_min_edit.text().strip() else None
        except ValueError:
            vmin = None
            
        try:
            vmax = float(self.z_max_edit.text()) if self.z_max_edit.text().strip() else None
        except ValueError:
            vmax = None
            
        return vmin, vmax

    def replot_current_data(self, preserve_limits=True):
        """Replot using stored parameters, as a comparison if that is what is shown."""
        comparison = getattr(self, '_comparison_args', None)
        if comparison is not None:
            self.update_comparison_plot(preserve_limits=preserve_limits, **comparison)
            return
        if self.current_pattern is not None:
            self.update_plot(
                pattern=self.current_pattern,
                frequencies=self.current_frequencies,
                phi_angles=self.current_phi_angles,
                value_type=self.current_value_type,
                show_cross_pol=self.current_show_cross_pol,
                unwrap_phase=self.current_unwrap_phase,
                plot_format=self.current_plot_format,
                component=self.current_component,
                statistics_enabled=self.current_statistics_enabled,
                show_range=self.current_show_range,
                statistic_type=self.current_statistic_type,
                percentile_range=self.current_percentile_range,
                preserve_limits=preserve_limits,
                pattern_key=getattr(self, 'current_pattern_key', None),
                sweep_metric=getattr(self, 'current_sweep_metric', 'peak_gain'),
            )
    
    def save_plot(self, filename):
        """Save the current plot to file."""
        self.figure.savefig(filename, dpi=300, bbox_inches='tight')
    
    def clear_plot(self):
        """Clear the current plot."""
        self.figure.clear()
        self.canvas.draw()
        self.current_pattern = None

    def save_current_axis_limits(self, plot_type):
        """Remember the limit fields for a plot type."""
        fields = self._limit_fields(plot_type)
        fields['x_min'] = self.x_phi_min_edit.text()
        fields['x_max'] = self.x_phi_max_edit.text()
        fields['y_min'] = self.y_theta_min_edit.text()
        fields['y_max'] = self.y_theta_max_edit.text()
        fields['z_min'] = self.z_min_edit.text()
        fields['z_max'] = self.z_max_edit.text()

    def restore_axis_limits(self, plot_type):
        """Put a plot type's remembered limit fields back into the strip."""
        fields = self._limit_fields(plot_type)
        self.x_phi_min_edit.setText(fields['x_min'])
        self.x_phi_max_edit.setText(fields['x_max'])
        self.y_theta_min_edit.setText(fields['y_min'])
        self.y_theta_max_edit.setText(fields['y_max'])
        self.z_min_edit.setText(fields['z_min'])
        self.z_max_edit.setText(fields['z_max'])

    def clear_axis_limits(self, plot_type=None):
        """Clear the limit fields for one plot type, or every plot type."""
        targets = [plot_type] if plot_type is not None else list(self.axis_limits_memory)
        for key in targets:
            fields = self._limit_fields(key)
            for name in fields:
                fields[name] = ''
        for edit in (self.x_phi_min_edit, self.x_phi_max_edit, self.y_theta_min_edit,
                     self.y_theta_max_edit, self.z_min_edit, self.z_max_edit):
            edit.setText('')

    def reset_scale(self):
        """Reset axis limits to auto-scale."""
        plot_type = self.current_plot_format
        self.current_matplotlib_limits[plot_type] = {'xlim': None, 'ylim': None, 'zlim': None}
        self.clear_axis_limits(plot_type)
        self.replot_current_data(preserve_limits=False)

    @staticmethod
    def _apply_axis_limit(setter, getter, min_text, max_text):
        """
        Apply whichever of a minimum and maximum the user actually typed.

        An empty field keeps the current value for that end of the axis, so a
        lower bound on its own works.
        """
        min_text = (min_text or "").strip()
        max_text = (max_text or "").strip()
        if not min_text and not max_text:
            return
        current_min, current_max = getter()
        try:
            new_min = float(min_text) if min_text else current_min
            new_max = float(max_text) if max_text else current_max
        except ValueError:
            return
        if new_min != new_max:
            setter(new_min, new_max)

    def get_plotted_data(self):
        """
        The curves currently drawn, as (x_label, x_values, [(label, y), ...]).

        Taken from the axes rather than recomputed, so what is written is what
        is displayed, including normalization and the chosen component.
        Returns None when nothing is plotted.
        """
        if not self.figure.axes:
            return None
        ax = self.figure.axes[0]
        traces = []
        for index, line in enumerate(ax.get_lines()):
            label = line.get_label()
            if label.startswith('_'):
                label = f"trace_{index + 1}"
            traces.append((label, line.get_xdata(), line.get_ydata()))
        if not traces:
            return None
        return ax.get_xlabel() or 'x', ax.get_ylabel() or 'y', traces

    def export_plotted_data(self):
        """Write the plotted curves to CSV."""
        import csv

        plotted = self.get_plotted_data()
        if plotted is None:
            QMessageBox.information(self, "Nothing to Export",
                                    "There is no plotted data to export.")
            return
        x_label, y_label, traces = plotted

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Plot Data", "plot_data.csv",
            "CSV Files (*.csv);;All Files (*)")
        if not file_path:
            return
        if not Path(file_path).suffix:
            file_path = f"{file_path}.csv"

        # Traces can differ in length (a comparison of patterns sampled
        # differently), so each one carries its own x column.
        try:
            with open(file_path, 'w', newline='') as handle:
                writer = csv.writer(handle)
                header = []
                for label, _x, _y in traces:
                    header += [f"{x_label} [{label}]", f"{y_label} [{label}]"]
                writer.writerow(header)
                for row in range(max(len(x) for _l, x, _y in traces)):
                    values = []
                    for _label, x, y in traces:
                        values += ([x[row], y[row]] if row < len(x) else ['', ''])
                    writer.writerow(values)
        except OSError as e:
            logger.error("Could not write %s: %s", file_path, e)
            QMessageBox.critical(self, "Export Failed", f"Could not write the file:\n{e}")
            return

        logger.info("Exported %d trace(s) to %s", len(traces), file_path)

    # --------------------------------------------------- markers / cursors
    MARKER_TRACE_LIMIT = 6

    def _markers_apply(self) -> bool:
        fmt = self.current_plot_format
        if not self.markers_check.isChecked() or fmt not in self.MARKER_FORMATS:
            return False
        if self.current_statistics_enabled:
            return False
        # The amplitude panel is always gain; the others follow the value type
        return fmt == 'amp_phase' or self.current_value_type == 'gain'

    def _draw_markers(self, axes=None):
        """Mark the co-pol traces on the gain axes; remove the marks otherwise."""
        for artist in self._marker_artists:
            try:
                artist.remove()
            except (ValueError, NotImplementedError):
                pass
        self._marker_artists = []
        self._marker_text = ""
        axes = list(self._marker_axes) if axes is None else list(axes)
        if not axes or not self._markers_apply():
            self._update_readout()
            return
        summaries = []
        count = 0
        for ax in axes:
            if ax is None or hasattr(ax, 'set_theta_zero_location'):
                continue
            panel = f"[{ax.get_title()}] " if len(axes) > 1 and ax.get_title() else ""
            for line in ax.get_lines():
                label = line.get_label()
                if label.startswith('_') or not line.get_visible() or 'cross' in label.lower():
                    continue
                if count >= self.MARKER_TRACE_LIMIT:
                    break
                analysis = analyze_cut(line.get_xdata(), line.get_ydata())
                if analysis is None:
                    continue
                count += 1
                self._marker_artists += draw_markers(ax, analysis, color=line.get_color())
                summaries.append(f"{panel}{label}: {analysis.summary()}")
        if count >= self.MARKER_TRACE_LIMIT:
            summaries.append(f"… only the first {self.MARKER_TRACE_LIMIT} traces are marked")
        self._marker_text = "\n".join(summaries)
        self._update_readout()

    def _on_cursors_toggled(self, checked):
        if checked and self.current_plot_format in self.CURSOR_FORMATS:
            self.cursors.enable()
        else:
            self.cursors.disable()
        self._update_readout()

    def _on_cursor_readout(self, text):
        self._cursor_text = text
        self._update_readout()

    def _update_readout(self):
        parts = [t for t in (self._cursor_text, self._mask_text, self._marker_text) if t]
        self.readout_label.setText("\n".join(parts))
        self.readout_label.setVisible(bool(parts))

    # ------------------------------------------------------------ masks
    def set_masks(self, masks):
        """Replace the specification masks and redraw."""
        self.masks = [SpecMask.from_dict(m.to_dict()) for m in masks]
        if self.mask_dialog is not None:
            self.mask_dialog.set_masks(self.masks)
        if self.figure.axes:
            self.update_plot_formatting()

    def open_mask_dialog(self):
        from ..dialogs.mask_dialog import MaskDialog

        if self.mask_dialog is None:
            self.mask_dialog = MaskDialog(self.masks, self)
            self.mask_dialog.masks_changed.connect(self._on_masks_changed)
        else:
            self.mask_dialog.set_masks(self.masks)
        self.mask_dialog.show()
        self.mask_dialog.raise_()
        self.mask_dialog.activateWindow()

    def _on_masks_changed(self, masks):
        self.masks = list(masks)
        if self.figure.axes:
            self.update_plot_formatting()

    def _draw_masks(self):
        """Draw the masks on the marker axes and report violations."""
        for artist in self._mask_artists:
            try:
                artist.remove()
            except (ValueError, NotImplementedError):
                pass
        self._mask_artists = []
        self._mask_text = ""
        fmt = self.current_plot_format
        axes = [a for a in self._marker_axes if a is not None]
        if not self.masks or fmt not in self.MASK_FORMATS or not axes:
            return
        reports = []
        for ax in axes:
            self._mask_artists += draw_masks(ax, self.masks)
            traces = [(line.get_label(), line.get_xdata(), line.get_ydata())
                      for line in ax.get_lines()
                      if not line.get_label().startswith('_') and line.get_visible()]
            panel = f"[{ax.get_title()}] " if len(axes) > 1 and ax.get_title() else ""
            reports += [panel + line for line in mask_report(self.masks, traces)]
        self._mask_text = "\n".join(reports)

    def strip_state(self) -> dict:
        """The plot strip's settings, for a session file."""
        # The live limit fields belong to the current format's memory; the
        # memory is only written on a format change, so write it now.
        self.save_current_axis_limits(self.current_plot_format)
        return {
            'grid': self.grid_check.isChecked(),
            'legend': self.legend_colorbar_check.isChecked(),
            'normalize': self.normalize_check.isChecked(),
            'smooth': self.smooth_check.isChecked(),
            'markers': self.markers_check.isChecked(),
            'cursors': self.cursors_check.isChecked(),
            'limits': {key: dict(value) for key, value in self.axis_limits_memory.items()},
            'current_limits': {'x_min': self.x_phi_min_edit.text(), 'x_max': self.x_phi_max_edit.text(),
                               'y_min': self.y_theta_min_edit.text(), 'y_max': self.y_theta_max_edit.text(),
                               'z_min': self.z_min_edit.text(), 'z_max': self.z_max_edit.text()},
        }

    def apply_strip_state(self, state: dict):
        """Restore the plot strip's settings from a session file."""
        if not state:
            return
        checks = {'grid': self.grid_check, 'legend': self.legend_colorbar_check,
                  'normalize': self.normalize_check, 'smooth': self.smooth_check,
                  'markers': self.markers_check, 'cursors': self.cursors_check}
        for key, widget in checks.items():
            if key in state:
                widget.blockSignals(True)
                widget.setChecked(bool(state[key]))
                widget.blockSignals(False)
        for key, fields in (state.get('limits') or {}).items():
            self._limit_fields(key).update({k: str(v) for k, v in fields.items()})
        # The fields on screen follow the memory of whatever format is (or
        # becomes) current; a later format switch restores its own entry.
        self.restore_axis_limits(self.current_plot_format)
        self._on_cursors_toggled(self.cursors_check.isChecked())
        if self.current_pattern is not None:
            self.replot_current_data(preserve_limits=False)

    # ------------------------------------------------------------ style
    def current_style(self) -> PlotStyle:
        """The style for the plot format on screen."""
        key = self.current_plot_format if self.current_plot_format in self.styles else '1d_cut'
        return self.styles[key]

    def set_style(self, style: PlotStyle, plot_format=None):
        """Replace the style for a plot format, re-apply it and remember it."""
        key = plot_format or self.current_plot_format
        if key not in self.styles:
            key = '1d_cut'
        self.styles[key] = style.copy()
        self._save_styles()
        if key != self.current_plot_format:
            return
        # Replot rather than restyle in place: a field set back to Auto must
        # bring the plotting default back, and a colour cycle only takes
        # effect when the lines are drawn. The limits are kept.
        if self.current_pattern is not None:
            self.replot_current_data(preserve_limits=True)
        else:
            self.update_plot_formatting()

    def open_style_dialog(self):
        """Show the floating Plot Style dialog for the current plot format."""
        from ..dialogs.plot_style_dialog import PlotStyleDialog

        if self.style_dialog is None:
            self.style_dialog = PlotStyleDialog(self)
            self.style_dialog.style_changed.connect(self._on_style_changed)
        self.style_dialog.set_style(self.current_style(),
                                    self.STYLE_FORMAT_NAMES.get(self.current_plot_format,
                                                                self.current_plot_format))
        ax = self.figure.axes[0] if self.figure.axes else None
        self.style_dialog.set_series(series_labels(ax))
        self.style_dialog.show()
        self.style_dialog.raise_()
        self.style_dialog.activateWindow()

    def _on_style_changed(self, style):
        self.set_style(style)

    def _apply_color_cycle(self, plot_format, frequencies, phi_angles, show_cross_pol):
        """
        Choose the line colours before the plotting function draws.

        The cut plotter takes an explicit colour list (one per frequency or
        per phi cut); anything drawing from the axes' own cycle picks the
        same colours up from set_prop_cycle.
        """
        style = self.styles.get(plot_format) or self.styles['1d_cut']
        self._cycle_colors = None
        if style.color_cycle in (None, '', 'default'):
            return
        n_freq = len(frequencies) if isinstance(frequencies, (list, tuple, np.ndarray)) else 1
        n_phi = len(phi_angles) if isinstance(phi_angles, (list, tuple, np.ndarray)) else 1
        colors = cycle_colors(style.color_cycle, max(n_freq, n_phi, 1))
        if colors:
            self._cycle_colors = colors
            if self.ax is not None:
                self.ax.set_prop_cycle(color=colors)

    def _settings(self) -> QSettings:
        return QSettings(self.SETTINGS_ORG, self.SETTINGS_APP)

    def _load_styles(self):
        try:
            settings = self._settings()
            for key in self.styles:
                text = settings.value(f"style/{key}")
                if text:
                    self.styles[key] = PlotStyle.from_json(text)
        except Exception as e:
            logger.warning("Saved plot styles could not be read: %s", e)

    def _save_styles(self):
        try:
            settings = self._settings()
            for key, style in self.styles.items():
                settings.setValue(f"style/{key}", style.to_json())
        except Exception as e:
            logger.warning("Plot styles could not be saved: %s", e)

    def clear_saved_limits(self):
        """Forget the remembered axis limits so the next plot auto-scales."""
        for key in self.current_matplotlib_limits:
            for axis in self.current_matplotlib_limits[key]:
                self.current_matplotlib_limits[key][axis] = None

    def update_plot_formatting(self):
        """Update plot formatting without replotting data."""
        axes = [a for a in self._data_axes if a is not None] or list(self.figure.axes)
        if not axes:
            return
        ax = axes[0]
        is_polar = hasattr(ax, 'set_theta_zero_location')

        for a in axes:
            a.grid(self.grid_check.isChecked())

        if is_polar:
            if getattr(self, 'current_colorbar', None):
                self.current_colorbar.ax.set_visible(self.legend_colorbar_check.isChecked())
                vmin, vmax = self.get_colorbar_limits()
                if vmin is not None or vmax is not None:
                    mappable = self.current_colorbar.mappable
                    current_vmin, current_vmax = mappable.get_clim()
                    mappable.set_clim(vmin=vmin if vmin is not None else current_vmin,
                                      vmax=vmax if vmax is not None else current_vmax)
                    self.current_colorbar.update_normal(mappable)
            elif ax.get_legend():
                ax.get_legend().set_visible(self.legend_colorbar_check.isChecked())
            # Radial limits
            self._apply_axis_limit(ax.set_ylim, ax.get_ylim,
                                   self.y_theta_min_edit.text(), self.y_theta_max_edit.text())
        else:
            for a in axes:
                if a.get_legend():
                    a.get_legend().set_visible(self.legend_colorbar_check.isChecked())
            # X and Y axis limits. A minimum on its own is applied too;
            # requiring both fields meant typing one did nothing. Shared x
            # propagates to every panel; y is the first (amplitude) panel.
            self._apply_axis_limit(ax.set_xlim, ax.get_xlim,
                                   self.x_phi_min_edit.text(), self.x_phi_max_edit.text())
            self._apply_axis_limit(ax.set_ylim, ax.get_ylim,
                                   self.y_theta_min_edit.text(), self.y_theta_max_edit.text())

        # Specification masks go on before the style so its legend rebuild
        # picks them up.
        self._draw_masks()

        # The user's style goes on last so it wins over the plotting defaults.
        style = self.current_style()
        secondary = style.copy()
        secondary.title = None
        try:
            for index, a in enumerate(axes):
                apply_style(self.figure, a, style if index == 0 else secondary,
                            colorbar=getattr(self, 'current_colorbar', None) if index == 0 else None,
                            legend_visible=self.legend_colorbar_check.isChecked())
        except Exception as e:      # a bad colour name must not kill the redraw
            logger.warning("Plot style could not be applied: %s", e)
        if self.style_dialog is not None and self.style_dialog.isVisible():
            self.style_dialog.set_series(series_labels(ax))

        self._draw_markers()
        self.cursors.refresh(axes)

        self.canvas.draw()

