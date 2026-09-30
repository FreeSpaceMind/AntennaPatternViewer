"""
3D view: the far-field pattern as a surface whose radius is the value
above a floor (gain in dB over a chosen dynamic range) and whose colour is
the value, for the frequency and component selected in the View panel.
"""
from __future__ import annotations

import logging

import numpy as np
from matplotlib import cm, colors as mcolors
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from PyQt6.QtWidgets import (QComboBox, QDoubleSpinBox, QHBoxLayout, QLabel, QVBoxLayout,
                             QWidget)

from ..plotting import _component_values
from .figure_tools import FigureTools

logger = logging.getLogger(__name__)

COLORMAPS = ['turbo', 'viridis', 'plasma', 'jet', 'coolwarm', 'gray']


def pattern_surface(pattern, frequency=None, component='e_co', value_type='gain',
                    dynamic_range=40.0, unwrap_phase=True):
    """
    Cartesian surface points (X, Y, Z) and the values that colour them for
    one frequency of a pattern. The pattern is closed to a full sphere in
    sided coordinates and the phi seam is closed so the surface has no gap.
    Gain is drawn as radius = value - (peak - dynamic_range), floored at 0.
    """
    work = pattern
    theta = np.asarray(pattern.theta_angles, dtype=float)
    if theta.min() < -0.5:                       # central: open into the sided sphere
        work = pattern.copy()
        work.transform_coordinates('sided')
    theta = np.asarray(work.theta_angles, dtype=float)
    phi = np.asarray(work.phi_angles, dtype=float)
    frequencies = np.asarray(work.frequencies, dtype=float)
    fi = 0 if frequency is None else int(np.argmin(np.abs(frequencies - float(frequency))))
    values = _component_values(work, component, value_type, [fi], unwrap_phase)[fi]   # (theta, phi)

    # Close the phi seam if the grid stops one step short of 360
    if phi.size > 1 and (phi[-1] - phi[0]) < 360.0 - 1e-6:
        phi = np.append(phi, phi[0] + 360.0)
        values = np.concatenate([values, values[:, :1]], axis=1)

    finite = values[np.isfinite(values)]
    if value_type == 'gain':
        top = float(finite.max()) if finite.size else 0.0
        floor = top - float(dynamic_range)
        radius = np.clip(np.nan_to_num(values, nan=floor) - floor, 0.0, None)
        color_range = (floor, top)
    elif value_type == 'phase':
        radius = np.ones_like(values)
        color_range = (-180.0, 180.0)
    else:
        radius = np.clip(np.nan_to_num(values, nan=0.0), 0.0, None)
        color_range = (0.0, float(finite.max()) if finite.size else 1.0)

    th, ph = np.meshgrid(np.radians(theta), np.radians(phi), indexing='ij')
    x = radius * np.sin(th) * np.cos(ph)
    y = radius * np.sin(th) * np.sin(ph)
    z = radius * np.cos(th)
    return x, y, z, values, color_range


def draw_pattern_surface(ax, pattern, frequency=None, component='e_co', value_type='gain',
                         dynamic_range=40.0, cmap='turbo', unwrap_phase=True, stride=1):
    """Draw the surface on a 3D axes and return (surface, mappable)."""
    x, y, z, values, (vmin, vmax) = pattern_surface(pattern, frequency, component, value_type,
                                                    dynamic_range, unwrap_phase)
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
    colormap = cm.get_cmap(cmap) if hasattr(cm, 'get_cmap') else __import__('matplotlib').colormaps[cmap]
    facecolors = colormap(norm(np.nan_to_num(values, nan=vmin)))
    surface = ax.plot_surface(x, y, z, facecolors=facecolors, rstride=stride, cstride=stride,
                              linewidth=0, antialiased=False, shade=False)
    mappable = cm.ScalarMappable(norm=norm, cmap=colormap)
    mappable.set_array(values)
    extent = float(np.nanmax(np.abs(np.stack([x, y, z])))) or 1.0
    ax.set_xlim(-extent, extent)
    ax.set_ylim(-extent, extent)
    ax.set_zlim(-extent, extent)
    ax.set_box_aspect((1, 1, 1))
    ax.set_xlabel('x')
    ax.set_ylabel('y')
    ax.set_zlabel('z')
    return surface, mappable


class Plot3DWidget(QWidget):
    """3D surface of the active pattern, following the View panel's selection."""

    def __init__(self, data_model, parent=None):
        super().__init__(parent)
        self.data_model = data_model
        self.current_colorbar = None
        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.figure = Figure(figsize=(8, 7))
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.tools = FigureTools(self, self.figure, self.canvas, 'view_3d', '3D view', self.update_plot)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Dynamic range:"))
        self.range_spin = QDoubleSpinBox()
        self.range_spin.setRange(5.0, 120.0)
        self.range_spin.setValue(40.0)
        self.range_spin.setSuffix(" dB")
        self.range_spin.setToolTip("Gain below the peak minus this range is drawn at zero radius")
        self.range_spin.valueChanged.connect(lambda _v: self.update_plot())
        controls.addWidget(self.range_spin)
        controls.addWidget(QLabel("Colormap:"))
        self.cmap_combo = QComboBox()
        self.cmap_combo.addItems(COLORMAPS)
        self.cmap_combo.currentTextChanged.connect(lambda _t: self.update_plot())
        controls.addWidget(self.cmap_combo)
        controls.addStretch()
        controls.addWidget(self.tools.style_btn)
        controls.addWidget(self.tools.export_btn)

        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        layout.addLayout(controls)
        self.status = QLabel("Load a pattern to see it in 3D.")
        self.status.setStyleSheet("color: #666; font-size: 9pt;")
        layout.addWidget(self.status)

    def connect_signals(self):
        self.data_model.pattern_loaded.connect(self.on_pattern_changed)
        self.data_model.pattern_modified.connect(self.on_pattern_changed)
        self.data_model.view_parameters_changed.connect(lambda _p: self.update_plot())

    def on_pattern_changed(self, _pattern):
        self.update_plot()

    # ------------------------------------------------------------- drawing
    def _selection(self):
        params = self.data_model.get_all_view_params() or {}
        freqs = params.get('selected_frequencies') or []
        frequency = freqs[0] if freqs else None
        pattern = self.data_model.pattern
        if frequency is None and pattern is not None and len(pattern.frequencies):
            frequency = float(pattern.frequencies[0])
        return (frequency, params.get('component', 'e_co'), params.get('value_type', 'gain'),
                bool(params.get('unwrap_phase', True)))

    def update_plot(self):
        pattern = self.data_model.pattern
        self.figure.clear()
        self.current_colorbar = None
        if pattern is None:
            self.status.setText("Load a pattern to see it in 3D.")
            self.canvas.draw_idle()
            return
        frequency, component, value_type, unwrap = self._selection()
        ax = self.figure.add_subplot(111, projection='3d')
        try:
            _surface, mappable = draw_pattern_surface(
                ax, pattern, frequency=frequency, component=component, value_type=value_type,
                dynamic_range=float(self.range_spin.value()), cmap=self.cmap_combo.currentText(),
                unwrap_phase=unwrap)
            units = {'gain': 'dBi', 'phase': 'deg', 'axial_ratio': 'dB'}.get(value_type, '')
            self.current_colorbar = self.figure.colorbar(mappable, ax=ax, shrink=0.7, pad=0.08)
            self.current_colorbar.set_label(f"{value_type.replace('_', ' ').title()} ({units})")
            shown = f"{frequency / 1e6:.1f} MHz" if frequency is not None else "first frequency"
            ax.set_title(f"{component} {value_type.replace('_', ' ')}, {shown}")
            self.status.setText(f"{shown}, {component}, radius = {value_type.replace('_', ' ')} "
                                f"over {self.range_spin.value():g} dB")
        except Exception as e:
            logger.exception("3D plot failed")
            ax.text2D(0.5, 0.5, f"Could not draw the 3D view:\n{e}", ha='center', va='center',
                      transform=ax.transAxes, color='red')
            self.status.setText("3D view failed; see the log.")
        self.tools.apply(ax, colorbar=self.current_colorbar)
        self.canvas.draw_idle()
