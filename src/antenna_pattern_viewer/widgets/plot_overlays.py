"""
The overlays drawn on top of the plot widget's data: pattern markers,
specification masks, the cursors, and the readout panel that reports all
three. The plot widget owns the figure and decides which axes carry data
and which may take overlays; this helper owns everything else about them.
"""
from __future__ import annotations

import logging
from typing import Callable, List, Optional

from ..pattern_markers import (MarkerConfig, analyze_cut, custom_values, describe, draw_markers,
                               levels_for)
from ..plot_cursors import CursorTracker
from ..spec_mask import SpecMask, draw_masks, mask_report
from .readout_panel import ReadoutPanel

logger = logging.getLogger(__name__)


class PlotOverlays:
    """Markers, masks, cursors and their readout for one figure."""

    MARKER_TRACE_LIMIT = 6

    def __init__(self, owner, canvas, toolbar, axes_provider: Callable[[], list],
                 redraw: Callable[[], None]):
        """
        ``owner`` parents the dialogs; ``axes_provider`` returns the axes
        carrying data (for the cursors and the pattern names); ``redraw``
        re-applies the formatting after a configuration change.
        """
        self.owner = owner
        self.axes_provider = axes_provider
        self.redraw = redraw
        self.marker_config = MarkerConfig()
        self.markers_dialog = None
        self.masks: List[SpecMask] = []
        self.mask_dialog = None
        self.marker_artists: list = []
        self.mask_artists: list = []
        self.marker_text = ""
        self.mask_text = ""
        self.cursor_text = ""
        # A fixed-height, scrollable panel that can be collapsed, so many
        # traces cannot crowd the plot.
        self.readout = ReadoutPanel()
        self.readout.setVisible(False)
        self.cursors = CursorTracker(canvas, axes_provider, toolbar=toolbar)
        self.cursors.on_readout = self._on_cursor_readout

    # ------------------------------------------------------------ readout
    def _on_cursor_readout(self, text):
        self.cursor_text = text
        self.update_readout()

    def update_readout(self):
        parts = [t for t in (self.cursor_text, self.mask_text, self.marker_text) if t]
        self.readout.setText("\n".join(parts))
        self.readout.setVisible(bool(parts))

    # ------------------------------------------------------------ cursors
    def set_cursors_enabled(self, enabled: bool):
        if enabled:
            self.cursors.enable()
        else:
            self.cursors.disable()
        self.update_readout()

    # ------------------------------------------------------------ markers
    def pattern_names(self) -> list:
        """Names of the patterns on the plot, in drawing order."""
        names = []
        for ax in self.axes_provider():
            for line in ax.get_lines():
                name = line.get_gid()
                if name and name not in names:
                    names.append(name)
        return names

    @staticmethod
    def _remove(artists):
        for artist in artists:
            try:
                artist.remove()
            except (ValueError, NotImplementedError):
                pass

    def draw_markers(self, axes, enabled: bool):
        """Mark the co-pol traces on ``axes`` as the marker config asks."""
        self._remove(self.marker_artists)
        self.marker_artists = []
        self.marker_text = ""
        axes = [a for a in (axes or []) if a is not None]
        if not axes or not enabled:
            self.update_readout()
            return
        summaries = []
        count = 0
        for ax in axes:
            if hasattr(ax, 'set_theta_zero_location'):
                continue
            panel = f"[{ax.get_title()}] " if len(axes) > 1 and ax.get_title() else ""
            seen_per_pattern: dict = {}
            for line in ax.get_lines():
                label = line.get_label()
                name = line.get_gid()
                if not line.get_visible() or 'cross' in label.lower():
                    continue
                if label.startswith('_') and name is None:
                    continue
                marker_set = self.marker_config.for_pattern(name)
                if marker_set is None:
                    continue
                if count >= self.MARKER_TRACE_LIMIT:
                    break
                theta, values = line.get_xdata(), line.get_ydata()
                metrics = analyze_cut(theta, values, levels_db=levels_for(marker_set))
                customs = custom_values(theta, values, marker_set)
                if metrics is None and not customs:
                    continue
                count += 1
                self.marker_artists += draw_markers(ax, metrics, color=line.get_color(),
                                                    marker_set=marker_set, customs=customs)
                # A comparison labels only the first cut of each pattern
                if label.startswith('_'):
                    k = seen_per_pattern.get(name, 1) + 1
                    seen_per_pattern[name] = k
                    shown = f"{name} (cut {k})"
                else:
                    seen_per_pattern.setdefault(name, 1)
                    shown = label
                summaries.append(f"{panel}{shown}: {describe(metrics, marker_set, customs)}")
        if count >= self.MARKER_TRACE_LIMIT:
            summaries.append(f"… only the first {self.MARKER_TRACE_LIMIT} traces are marked")
        self.marker_text = "\n".join(summaries)
        self.update_readout()
        if self.markers_dialog is not None and self.markers_dialog.isVisible():
            self.markers_dialog.set_patterns(self.pattern_names())

    def set_marker_config(self, config: MarkerConfig, redraw: bool = True):
        self.marker_config = config.copy()
        if self.markers_dialog is not None:
            self.markers_dialog.set_config(self.marker_config)
        if redraw:
            self.redraw()

    def open_markers_dialog(self):
        from ..dialogs.markers_dialog import MarkersDialog

        if self.markers_dialog is None:
            self.markers_dialog = MarkersDialog(self.marker_config, self.owner)
            self.markers_dialog.config_changed.connect(self._on_marker_config_changed)
        else:
            self.markers_dialog.set_config(self.marker_config)
        self.markers_dialog.set_patterns(self.pattern_names())
        self.markers_dialog.show()
        self.markers_dialog.raise_()
        self.markers_dialog.activateWindow()

    def _on_marker_config_changed(self, config):
        self.marker_config = config.copy()
        self.redraw()

    # ------------------------------------------------------------ masks
    def set_masks(self, masks, redraw: bool = True):
        """Replace the specification masks."""
        self.masks = [SpecMask.from_dict(m.to_dict()) for m in masks]
        if self.mask_dialog is not None:
            self.mask_dialog.set_masks(self.masks)
        if redraw:
            self.redraw()

    def open_mask_dialog(self):
        from ..dialogs.mask_dialog import MaskDialog

        if self.mask_dialog is None:
            self.mask_dialog = MaskDialog(self.masks, self.owner)
            self.mask_dialog.masks_changed.connect(self._on_masks_changed)
        else:
            self.mask_dialog.set_masks(self.masks)
        self.mask_dialog.show()
        self.mask_dialog.raise_()
        self.mask_dialog.activateWindow()

    def _on_masks_changed(self, masks):
        self.masks = list(masks)
        self.redraw()

    def draw_masks(self, axes, enabled: bool):
        """Draw the masks on ``axes`` and report violations."""
        self._remove(self.mask_artists)
        self.mask_artists = []
        self.mask_text = ""
        axes = [a for a in (axes or []) if a is not None]
        if not self.masks or not enabled or not axes:
            return
        reports = []
        for ax in axes:
            self.mask_artists += draw_masks(ax, self.masks)
            traces = [(line.get_label(), line.get_xdata(), line.get_ydata())
                      for line in ax.get_lines()
                      if not line.get_label().startswith('_') and line.get_visible()]
            panel = f"[{ax.get_title()}] " if len(axes) > 1 and ax.get_title() else ""
            reports += [panel + line for line in mask_report(self.masks, traces)]
        self.mask_text = "\n".join(reports)

    # ------------------------------------------------------------ sessions
    def state(self) -> dict:
        return {'marker_config': self.marker_config.to_dict()}

    def apply_state(self, state: Optional[dict]):
        if state and state.get('marker_config'):
            self.set_marker_config(MarkerConfig.from_dict(state['marker_config']), redraw=False)
