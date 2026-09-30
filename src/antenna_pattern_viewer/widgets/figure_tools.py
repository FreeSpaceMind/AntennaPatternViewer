"""
Style and export for a widget that owns a matplotlib figure but is not the
main plot widget (the 3D view, the near-field view).

Gives the owner a Style… button opening the same Plot Style dialog, an
Export… button opening the figure export dialog, a PlotStyle stored per
view in QSettings, and a tight layout engine enforced on every draw.
"""
from __future__ import annotations

import logging
from typing import Callable, Optional

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QMessageBox, QPushButton

from ..plot_style import PlotStyle, apply_style, series_labels

logger = logging.getLogger(__name__)


class FigureTools:
    SETTINGS_ORG = 'AntennaPatternViewer'
    SETTINGS_APP = 'PlotStyle'

    def __init__(self, owner, figure, canvas, style_key: str, format_label: str,
                 redraw: Callable[[], None]):
        self.owner = owner
        self.figure = figure
        self.canvas = canvas
        self.style_key = style_key
        self.format_label = format_label
        self.redraw = redraw
        self.style = PlotStyle()
        self.dialog = None
        self._load()
        try:
            self.figure.set_layout_engine('tight')
        except Exception:
            pass

        self.style_btn = QPushButton("Style…")
        self.style_btn.setToolTip("Title, labels, fonts, ticks, grid, colours and presets for this view")
        self.style_btn.clicked.connect(self.open_style_dialog)
        self.export_btn = QPushButton("Export…")
        self.export_btn.setToolTip("Save this figure as PNG, PDF, SVG, JPEG or TIFF at a chosen size")
        self.export_btn.clicked.connect(self.export)

    # ------------------------------------------------------------ settings
    @classmethod
    def _settings(cls) -> QSettings:
        return QSettings(cls.SETTINGS_ORG, cls.SETTINGS_APP)

    def _load(self):
        try:
            text = self._settings().value(f"style/{self.style_key}")
            if text:
                self.style = PlotStyle.from_json(text)
        except Exception as e:
            logger.warning("Saved style for %s could not be read: %s", self.style_key, e)

    def _save(self):
        try:
            self._settings().setValue(f"style/{self.style_key}", self.style.to_json())
        except Exception as e:
            logger.warning("Style for %s could not be saved: %s", self.style_key, e)

    # --------------------------------------------------------------- style
    def set_style(self, style: PlotStyle):
        self.style = style.copy()
        self._save()
        if self.dialog is not None:
            self.dialog.set_style(self.style, self.format_label)
        self.redraw()

    def open_style_dialog(self):
        from ..dialogs.plot_style_dialog import PlotStyleDialog

        if self.dialog is None:
            self.dialog = PlotStyleDialog(self.owner)
            self.dialog.style_changed.connect(self.set_style)
        self.dialog.set_style(self.style, self.format_label)
        ax = self.figure.axes[0] if self.figure.axes else None
        self.dialog.set_series(series_labels(ax))
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()

    def apply(self, ax, colorbar=None, legend_visible=None):
        """Apply the view's style to a drawn axes and enforce the tight engine."""
        if ax is not None:
            try:
                apply_style(self.figure, ax, self.style, colorbar=colorbar,
                            legend_visible=legend_visible)
            except Exception as e:           # a 3D axes lacks some 2D pieces; never lose the plot
                logger.warning("Style could not be fully applied to %s: %s", self.style_key, e)
        try:
            self.figure.set_layout_engine('tight')
        except Exception:
            pass

    # -------------------------------------------------------------- export
    def export(self):
        from ..dialogs.export_figure_dialog import ExportFigureDialog, save_figure

        if not self.figure.axes:
            QMessageBox.information(self.owner, "Nothing to Export", "There is no plot to export.")
            return
        dialog = ExportFigureDialog(self.figure, self.owner, default_name=self.style_key)
        if dialog.exec() != ExportFigureDialog.DialogCode.Accepted:
            return
        options = dialog.options()
        try:
            save_figure(self.figure, options)
            self.canvas.draw_idle()
            logger.info("Exported %s to %s", self.style_key, options['path'])
        except Exception as e:
            logger.exception("Figure export failed")
            QMessageBox.critical(self.owner, "Export Error", f"Failed to export:\n{e}")
