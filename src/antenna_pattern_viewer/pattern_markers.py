"""
Pattern markers for a 1D gain cut: peak, half-power beamwidth, first
sidelobe and first nulls, and the artists that show them on an axes.

All values are read from the plotted trace, so they describe what is on
screen (after normalization, processing and the chosen component). The
marker artists are collections and annotations, not Line2D, so they never
appear in the data export or the Series table.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import numpy as np


@dataclass
class CutAnalysis:
    peak_theta: float
    peak_value: float
    hp_left: Optional[float] = None       # theta where the trace crosses peak - 3 dB, left of the peak
    hp_right: Optional[float] = None
    hpbw: Optional[float] = None
    null_left: Optional[float] = None     # first local minimum either side of the main lobe
    null_right: Optional[float] = None
    null_depth: Optional[float] = None    # deeper of the two first nulls, relative to the peak (dB, negative)
    sidelobe_theta: Optional[float] = None
    sidelobe_level: Optional[float] = None  # highest lobe outside the first nulls, relative to the peak (dB)
    symmetric_assumed: bool = False       # sided cut with the peak at theta = 0: the missing half was mirrored

    def summary(self, unit='dBi') -> str:
        parts = [f"peak {self.peak_value:.2f} {unit} @ {self.peak_theta:.1f}°"]
        if self.hpbw is not None:
            parts.append(f"HPBW {self.hpbw:.1f}°" + (" (sym.)" if self.symmetric_assumed else ""))
        if self.sidelobe_level is not None:
            parts.append(f"SLL {self.sidelobe_level:+.1f} dB @ {self.sidelobe_theta:.1f}°")
        if self.null_depth is not None:
            parts.append(f"null {self.null_depth:+.1f} dB")
        return ", ".join(parts)


def _crossing(theta, values, level, start, step):
    """Interpolated theta where ``values`` first drops below ``level`` walking
    from index ``start`` in direction ``step``. None if it never does."""
    i = start
    n = len(values)
    while 0 <= i + step < n:
        j = i + step
        if values[j] < level:
            v0, v1 = values[i], values[j]
            if v1 == v0:
                return float(theta[j])
            frac = (v0 - level) / (v0 - v1)
            return float(theta[i] + frac * (theta[j] - theta[i]))
        i = j
    return None


def _first_minimum(values, start, step):
    """Index of the first local minimum walking from ``start`` in direction ``step``."""
    i = start
    n = len(values)
    while 0 <= i + step < n:
        j = i + step
        if values[j] > values[i]:
            return i if i != start else None
        i = j
    return None


def analyze_cut(theta, values, level_db=3.0) -> Optional[CutAnalysis]:
    """
    Peak, beamwidth, first nulls and first sidelobe of one trace in dB.

    Args:
        theta: angles in degrees, monotonic
        values: the trace in dB (any offset; results relative to the peak
            are unaffected)
        level_db: the beamwidth level below the peak, 3 dB by default

    Returns None when the trace has fewer than three finite samples.
    """
    theta = np.asarray(theta, dtype=float)
    values = np.asarray(values, dtype=float)
    keep = np.isfinite(theta) & np.isfinite(values)
    if keep.sum() < 3:
        return None
    theta, values = theta[keep], values[keep]
    order = np.argsort(theta)
    theta, values = theta[order], values[order]

    peak = int(np.argmax(values))
    result = CutAnalysis(peak_theta=float(theta[peak]), peak_value=float(values[peak]))

    level = values[peak] - level_db
    result.hp_left = _crossing(theta, values, level, peak, -1)
    result.hp_right = _crossing(theta, values, level, peak, +1)
    # A sided cut (theta from 0) with its peak at theta = 0 only holds half
    # the beam; the other half is taken as its mirror image.
    if peak == 0 and abs(theta[0]) < 1e-9 and result.hp_left is None and result.hp_right is not None:
        result.hp_left = -result.hp_right
        result.symmetric_assumed = True
    if result.hp_left is not None and result.hp_right is not None:
        result.hpbw = result.hp_right - result.hp_left

    left = _first_minimum(values, peak, -1)
    right = _first_minimum(values, peak, +1)
    if left is not None:
        result.null_left = float(theta[left])
    if right is not None:
        result.null_right = float(theta[right])
    depths = [values[i] - values[peak] for i in (left, right) if i is not None]
    if depths:
        result.null_depth = float(min(depths))

    # Highest sample outside the main lobe (beyond the first nulls)
    candidates = []
    if left is not None and left > 0:
        i = int(np.argmax(values[:left]))
        candidates.append((values[i], theta[i]))
    if right is not None and right < len(values) - 1:
        i = right + 1 + int(np.argmax(values[right + 1:]))
        candidates.append((values[i], theta[i]))
    if candidates:
        value, angle = max(candidates)
        result.sidelobe_level = float(value - values[peak])
        result.sidelobe_theta = float(angle)
    return result


def draw_markers(ax, analysis: CutAnalysis, color='black', label: Optional[str] = None,
                 fontsize=8) -> List:
    """
    Draw the markers for one trace and return the artists so they can be
    removed. Uses scatter, hlines and annotate so the export and the Series
    table, which read Line2D objects, are unaffected.
    """
    artists = []
    a = analysis
    artists.append(ax.scatter([a.peak_theta], [a.peak_value], s=36, color=color, zorder=5,
                              edgecolor='white', linewidth=0.6))
    prefix = f"{label}: " if label else ""
    artists.append(ax.annotate(f"{prefix}{a.peak_value:.1f} @ {a.peak_theta:.1f}°",
                               (a.peak_theta, a.peak_value), xytext=(4, 6),
                               textcoords='offset points', fontsize=fontsize, color=color,
                               zorder=6))
    if a.hpbw is not None:
        level = a.peak_value - 3.0
        artists.append(ax.hlines(level, a.hp_left, a.hp_right, colors=color, linewidth=1.2,
                                 linestyles='-', zorder=4))
        artists.append(ax.scatter([a.hp_left, a.hp_right], [level, level], marker='|', s=60,
                                  color=color, zorder=5))
        artists.append(ax.annotate(f"HPBW {a.hpbw:.1f}°", ((a.hp_left + a.hp_right) / 2, level),
                                   xytext=(0, -10), textcoords='offset points', ha='center',
                                   fontsize=fontsize, color=color, zorder=6))
    if a.sidelobe_level is not None:
        y = a.peak_value + a.sidelobe_level
        artists.append(ax.scatter([a.sidelobe_theta], [y], marker='v', s=40, color=color,
                                  zorder=5, edgecolor='white', linewidth=0.6))
        artists.append(ax.annotate(f"SLL {a.sidelobe_level:+.1f} dB", (a.sidelobe_theta, y),
                                   xytext=(4, 4), textcoords='offset points', fontsize=fontsize,
                                   color=color, zorder=6))
    return artists
