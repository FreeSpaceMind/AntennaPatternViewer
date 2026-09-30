"""
Pattern markers on a 1D gain cut, configurable per pattern.

The numbers come from the library's metrics module (peak, beamwidth at any
level, first nulls, first sidelobe, value at an angle), so a marker, a
frequency sweep and a script agree. This module holds the marker
configuration and draws it.

A ``MarkerSet`` says which markers to draw and at what levels or angles. A
``MarkerConfig`` has a default set plus per-pattern overrides keyed by the
pattern's name (the line's gid), so two copies of one file rotated
differently can carry different markers.

Marker artists are collections and annotations, not Line2D, so they never
appear in the data export or the Series table.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict, fields
from typing import Any, Dict, List, Optional

import numpy as np

from farfield_spherical.metrics import CutMetrics, analyze_cut as _analyze_cut, value_at

# Kept for callers and tests that import the analysis from here.
CutAnalysis = CutMetrics


def analyze_cut(theta, values, level_db: float = 3.0, levels_db=None) -> Optional[CutMetrics]:
    """The library's analyze_cut with the viewer's old single-level signature."""
    levels = tuple(levels_db) if levels_db else (float(level_db),)
    if 3.0 not in levels:
        levels = (3.0, *levels)
    return _analyze_cut(theta, values, levels)


@dataclass
class MarkerSet:
    """Which markers to draw on a trace."""
    peak: bool = True
    beamwidth: bool = True
    levels_db: List[float] = field(default_factory=lambda: [3.0])   # beamwidth levels below the peak
    sidelobe: bool = True
    nulls: bool = False
    custom_thetas: List[float] = field(default_factory=list)        # read the trace at these angles
    labels: bool = True                                              # text next to the symbols

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> 'MarkerSet':
        known = {f.name for f in fields(cls)}
        clean = {k: v for k, v in (data or {}).items() if k in known}
        clean['levels_db'] = [float(v) for v in clean.get('levels_db', [3.0])] or [3.0]
        clean['custom_thetas'] = [float(v) for v in clean.get('custom_thetas', [])]
        return cls(**clean)

    def copy(self) -> 'MarkerSet':
        return MarkerSet.from_dict(self.to_dict())


@dataclass
class MarkerConfig:
    default: MarkerSet = field(default_factory=MarkerSet)
    per_pattern: Dict[str, MarkerSet] = field(default_factory=dict)   # overrides by pattern name
    disabled: List[str] = field(default_factory=list)                 # patterns drawn without markers

    def for_pattern(self, name: Optional[str]) -> Optional[MarkerSet]:
        """The set for a pattern, or None when its markers are switched off."""
        if name is not None and name in self.disabled:
            return None
        if name is not None and name in self.per_pattern:
            return self.per_pattern[name]
        return self.default

    def to_dict(self) -> Dict[str, Any]:
        return {'default': self.default.to_dict(),
                'per_pattern': {k: v.to_dict() for k, v in self.per_pattern.items()},
                'disabled': list(self.disabled)}

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> 'MarkerConfig':
        data = data or {}
        return cls(default=MarkerSet.from_dict(data.get('default')),
                   per_pattern={str(k): MarkerSet.from_dict(v)
                                for k, v in (data.get('per_pattern') or {}).items()},
                   disabled=[str(v) for v in data.get('disabled', [])])

    def copy(self) -> 'MarkerConfig':
        return MarkerConfig.from_dict(self.to_dict())


def levels_for(marker_set: MarkerSet) -> tuple:
    levels = tuple(float(v) for v in marker_set.levels_db) or (3.0,)
    return levels if 3.0 in levels else (3.0, *levels)


def custom_values(theta, values, marker_set: MarkerSet) -> List[tuple]:
    """(theta, value) for each custom angle that lies inside the trace."""
    out = []
    for angle in marker_set.custom_thetas:
        value = value_at(theta, values, float(angle))
        if value is not None:
            out.append((float(angle), value))
    return out


def describe(metrics: Optional[CutMetrics], marker_set: MarkerSet, customs, unit='dBi') -> str:
    """One readout line's worth of text for a trace."""
    parts = []
    if metrics is not None:
        if marker_set.peak:
            parts.append(f"peak {metrics.peak_value:.2f} {unit} @ {metrics.peak_theta:.1f}°")
        if marker_set.beamwidth:
            for level in sorted(metrics.beamwidths):
                bw = metrics.beamwidths[level]
                if bw.width is None or level not in [float(v) for v in marker_set.levels_db]:
                    continue
                name = "HPBW" if level == 3.0 else f"BW{level:g}dB"
                parts.append(f"{name} {bw.width:.1f}°" + (" (sym.)" if bw.symmetric_assumed else ""))
        if marker_set.sidelobe and metrics.sidelobe_level is not None:
            parts.append(f"SLL {metrics.sidelobe_level:+.1f} dB @ {metrics.sidelobe_theta:.1f}°")
        if marker_set.nulls and metrics.null_depth is not None:
            parts.append(f"null {metrics.null_depth:+.1f} dB")
    for angle, value in customs:
        parts.append(f"θ={angle:g}°: {value:.2f}")
    return ", ".join(parts)


def draw_markers(ax, metrics: Optional[CutMetrics], color='black', marker_set: Optional[MarkerSet] = None,
                 customs=None, label: Optional[str] = None, fontsize=8) -> List:
    """
    Draw the markers a MarkerSet asks for and return the artists so they
    can be removed. Uses scatter, hlines and annotate so the export and the
    Series table, which read Line2D objects, are unaffected.
    """
    marker_set = marker_set or MarkerSet()
    artists: List = []
    text = marker_set.labels
    prefix = f"{label}: " if label else ""
    if metrics is not None:
        m = metrics
        if marker_set.peak:
            artists.append(ax.scatter([m.peak_theta], [m.peak_value], s=36, color=color, zorder=5,
                                      edgecolor='white', linewidth=0.6))
            if text:
                artists.append(ax.annotate(f"{prefix}{m.peak_value:.1f} @ {m.peak_theta:.1f}°",
                                           (m.peak_theta, m.peak_value), xytext=(4, 6),
                                           textcoords='offset points', fontsize=fontsize,
                                           color=color, zorder=6))
        if marker_set.beamwidth:
            wanted = [float(v) for v in marker_set.levels_db]
            for level, bw in m.beamwidths.items():
                if bw.width is None or level not in wanted:
                    continue
                y = m.peak_value - level
                artists.append(ax.hlines(y, bw.left, bw.right, colors=color, linewidth=1.2, zorder=4))
                artists.append(ax.scatter([bw.left, bw.right], [y, y], marker='|', s=60,
                                          color=color, zorder=5))
                if text:
                    name = "HPBW" if level == 3.0 else f"BW{level:g}dB"
                    artists.append(ax.annotate(f"{name} {bw.width:.1f}°", ((bw.left + bw.right) / 2, y),
                                               xytext=(0, -10), textcoords='offset points',
                                               ha='center', fontsize=fontsize, color=color, zorder=6))
        if marker_set.sidelobe and m.sidelobe_level is not None:
            y = m.peak_value + m.sidelobe_level
            artists.append(ax.scatter([m.sidelobe_theta], [y], marker='v', s=40, color=color,
                                      zorder=5, edgecolor='white', linewidth=0.6))
            if text:
                artists.append(ax.annotate(f"SLL {m.sidelobe_level:+.1f} dB", (m.sidelobe_theta, y),
                                           xytext=(4, 4), textcoords='offset points',
                                           fontsize=fontsize, color=color, zorder=6))
        if marker_set.nulls:
            for angle in (m.null_left, m.null_right):
                if angle is None:
                    continue
                artists.append(ax.scatter([angle], [m.peak_value + (m.null_depth or 0.0)], marker='^',
                                          s=30, color=color, zorder=5, edgecolor='white', linewidth=0.6))
    for angle, value in (customs or []):
        artists.append(ax.scatter([angle], [value], marker='x', s=45, color=color, zorder=5,
                                  linewidth=1.2))
        if text:
            artists.append(ax.annotate(f"θ={angle:g}°\n{value:.2f}", (angle, value), xytext=(4, -14),
                                       textcoords='offset points', fontsize=fontsize, color=color,
                                       zorder=6))
    return artists
