"""
Data-tip hover and delta cursors for 1D axes.

Hovering shows the nearest sample of the nearest trace. A left click pins
cursor A, a second click pins cursor B and shows the difference between
them; a third click starts again. A right click clears both. The hover
tip is blitted over a cached background so it follows the mouse without a
full redraw; the pinned cursors are drawn with the figure.

The tracker works on every non-polar axes the getter returns (a single
cut, the two panels of an amplitude/phase plot, the panels of small
multiples); a pinned cursor remembers which panel it belongs to.

Cursor artists are collections and text, never Line2D, so the data export
and the Series table do not see them.
"""
from __future__ import annotations

from typing import Callable, List, Optional, Tuple

import numpy as np

# (theta, value, label, axes index)
Pin = Tuple[float, float, str, int]


class CursorTracker:
    def __init__(self, canvas, axes_getter: Callable, toolbar=None, fontsize=8):
        self.canvas = canvas
        self.axes_getter = axes_getter
        self.toolbar = toolbar
        self.fontsize = fontsize
        self.enabled = False
        self._cids: List[int] = []
        self._background = None
        self._hover = None            # (scatter, annotation)
        self._pinned: List[Pin] = []
        self._pinned_artists: List = []
        self.on_readout: Optional[Callable[[str], None]] = None

    # ------------------------------------------------------------ control
    def enable(self):
        if self.enabled:
            return
        self.enabled = True
        self._cids = [
            self.canvas.mpl_connect('motion_notify_event', self._on_motion),
            self.canvas.mpl_connect('button_press_event', self._on_click),
            self.canvas.mpl_connect('draw_event', self._on_draw),
            self.canvas.mpl_connect('axes_leave_event', self._on_leave),
        ]

    def disable(self):
        if not self.enabled:
            return
        self.enabled = False
        for cid in self._cids:
            self.canvas.mpl_disconnect(cid)
        self._cids = []
        self.clear(redraw=True)

    def clear(self, redraw=False):
        """Remove the hover tip and both pinned cursors."""
        self._remove_hover()
        self._remove_pinned_artists()
        self._pinned = []
        self._background = None
        self._report("")
        if redraw:
            self.canvas.draw_idle()

    def pinned(self) -> List[Tuple[float, float, str]]:
        return [(t, v, label) for t, v, label, _i in self._pinned]

    # ------------------------------------------------------------ events
    def _axes_list(self) -> list:
        axes = self.axes_getter()
        if axes is None:
            return []
        if not isinstance(axes, (list, tuple)):
            axes = [axes]
        return [ax for ax in axes if ax is not None and not hasattr(ax, 'set_theta_zero_location')]

    def _axes_for(self, event):
        axes = self._axes_list()
        return event.inaxes if event.inaxes in axes else None

    def _toolbar_busy(self) -> bool:
        return bool(getattr(self.toolbar, 'mode', ''))

    def _on_draw(self, _event):
        # The figure was redrawn (a replot, a style change): the cached
        # hover background is stale.
        self._background = None

    def refresh(self, axes=None):
        """
        Re-create the pinned cursors if a replot replaced the axes they
        were drawn on. The plot widget calls this before its draw.
        """
        axes_list = self._axes_list() if axes is None else (
            [a for a in (axes if isinstance(axes, (list, tuple)) else [axes])
             if a is not None and not hasattr(a, 'set_theta_zero_location')])
        if not self._pinned or not axes_list:
            return
        current = {id(a) for a in axes_list}
        if self._pinned_artists and all(id(getattr(art, 'axes', None)) in current
                                        for art in self._pinned_artists):
            return
        self._remove_pinned_artists()
        self._draw_pinned(axes_list)

    def _on_leave(self, _event):
        if self._hover is not None:
            self._remove_hover()
            self._restore()

    def _on_motion(self, event):
        ax = self._axes_for(event)
        if ax is None or self._toolbar_busy():
            return
        hit = self._nearest(ax, event)
        if hit is None:
            return
        theta, value, label = hit
        if self._hover is not None and getattr(self._hover[0], 'axes', None) is not ax:
            self._remove_hover()          # a replot replaced the axes, or another panel
            self._background = None
        if self._hover is None:
            marker = ax.scatter([theta], [value], s=40, facecolor='none', edgecolor='black',
                                linewidth=1.0, zorder=7, animated=True)
            tip = ax.annotate("", (theta, value), xytext=(10, 10), textcoords='offset points',
                              fontsize=self.fontsize, zorder=8, animated=True,
                              bbox=dict(boxstyle='round,pad=0.3', fc='white', ec='0.5', alpha=0.9))
            self._hover = (marker, tip)
        marker, tip = self._hover
        marker.set_offsets([[theta, value]])
        tip.xy = (theta, value)
        tip.set_text(f"{label}\nθ = {theta:.2f}°\n{value:.2f}")
        self._blit(ax)

    def _on_click(self, event):
        ax = self._axes_for(event)
        if ax is None or self._toolbar_busy():
            return
        if event.button == 3:
            self.clear(redraw=True)
            return
        if event.button != 1:
            return
        hit = self._nearest(ax, event)
        if hit is None:
            return
        if len(self._pinned) >= 2:
            self.clear()
        axes_list = self._axes_list()
        self._pinned.append((*hit, axes_list.index(ax)))
        self._remove_pinned_artists()
        self._draw_pinned(axes_list)
        self._background = None
        self.canvas.draw_idle()

    # ------------------------------------------------------------ helpers
    def _nearest(self, ax, event):
        """Nearest sample of any visible trace on ``ax``, in display space."""
        if event.x is None or event.y is None:
            return None
        best = None
        for line in ax.get_lines():
            if not line.get_visible() or line.get_label().startswith('_'):
                continue
            xy = line.get_xydata()
            if xy.size == 0:
                continue
            finite = np.isfinite(xy).all(axis=1)
            if not finite.any():
                continue
            display = ax.transData.transform(xy[finite])
            d2 = (display[:, 0] - event.x) ** 2 + (display[:, 1] - event.y) ** 2
            i = int(np.argmin(d2))
            if best is None or d2[i] < best[0]:
                theta, value = xy[finite][i]
                best = (d2[i], float(theta), float(value), line.get_label())
        if best is None or best[0] > 30 ** 2:      # within 30 px of a sample
            return None
        return best[1], best[2], best[3]

    def _remove_pinned_artists(self):
        for artist in self._pinned_artists:
            try:
                artist.remove()
            except (ValueError, NotImplementedError):
                pass
        self._pinned_artists = []

    def _draw_pinned(self, axes_list):
        colors = ['#d62728', '#1f77b4']
        for index, (theta, value, label, ax_index) in enumerate(self._pinned):
            if ax_index >= len(axes_list):
                continue
            ax = axes_list[ax_index]
            ymin, ymax = ax.get_ylim()
            color = colors[index % len(colors)]
            name = 'A' if index == 0 else 'B'
            self._pinned_artists.append(
                ax.vlines(theta, ymin, ymax, colors=color, linestyles='--', linewidth=1.0, zorder=6))
            self._pinned_artists.append(
                ax.scatter([theta], [value], s=45, color=color, zorder=7, edgecolor='white'))
            self._pinned_artists.append(
                ax.annotate(f"{name}: θ={theta:.2f}°, {value:.2f}", (theta, value),
                            xytext=(6, -14 if index else 8), textcoords='offset points',
                            fontsize=self.fontsize, color=color, zorder=8,
                            bbox=dict(boxstyle='round,pad=0.2', fc='white', ec=color, alpha=0.9)))
            ax.set_ylim(ymin, ymax)
        text = self.delta_text()
        if text and len(self._pinned) == 2 and axes_list:
            ax = axes_list[min(self._pinned[0][3], len(axes_list) - 1)]
            self._pinned_artists.append(
                ax.text(0.02, 0.98, text, transform=ax.transAxes, va='top', ha='left',
                        fontsize=self.fontsize, zorder=8,
                        bbox=dict(boxstyle='round,pad=0.3', fc='white', ec='0.5', alpha=0.9)))
        self._report(text)

    def delta_text(self) -> str:
        if len(self._pinned) == 1:
            t, v, label, _i = self._pinned[0]
            return f"A: θ = {t:.2f}°, {v:.2f}  ({label})"
        if len(self._pinned) == 2:
            (ta, va, la, _ia), (tb, vb, lb, _ib) = self._pinned
            traces = f"  ({la})" if la == lb else f"  (A: {la}, B: {lb})"
            return (f"A: θ = {ta:.2f}°, {va:.2f}   B: θ = {tb:.2f}°, {vb:.2f}   "
                    f"Δθ = {tb - ta:.2f}°   Δ = {vb - va:.2f}{traces}")
        return ""

    def _report(self, text: str):
        if self.on_readout is not None:
            self.on_readout(text)

    def _remove_hover(self):
        if self._hover is None:
            return
        for artist in self._hover:
            try:
                artist.remove()
            except (ValueError, NotImplementedError):
                pass
        self._hover = None

    def _restore(self):
        if self._background is not None:
            self.canvas.restore_region(self._background)
            self.canvas.blit(self.canvas.figure.bbox)

    def _blit(self, ax):
        if not hasattr(self.canvas, 'copy_from_bbox'):
            self.canvas.draw_idle()
            return
        if self._background is None:
            # Draw once without the animated tip to cache the background.
            self.canvas.draw()
            self._background = self.canvas.copy_from_bbox(self.canvas.figure.bbox)
        self.canvas.restore_region(self._background)
        for artist in self._hover or ():
            ax.draw_artist(artist)
        self.canvas.blit(self.canvas.figure.bbox)
