"""
Specification masks for 1D cuts.

A mask is a piecewise-linear limit in (theta, value): an *upper* mask the
trace must stay below (a sidelobe envelope), or a *lower* mask it must stay
above (a minimum gain over the coverage). Masks come from a CSV file with
two columns, theta and value, or from points typed into the mask dialog.
A mask can be mirrored about theta = 0 so only one side needs defining.

Masks are drawn as a shaded region with a boundary line built from
collections, not Line2D, so the data export, the Series table, markers and
cursors do not see them. Their legend entries are added by the style
module's legend rebuild, which picks up labelled collections.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field, asdict, fields
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

MASK_KINDS = ('upper', 'lower')
DEFAULT_COLORS = ['#d62728', '#ff7f0e', '#9467bd', '#8c564b']


@dataclass
class SpecMask:
    name: str = 'Mask'
    kind: str = 'upper'                    # 'upper': trace must stay below; 'lower': above
    points: List[Tuple[float, float]] = field(default_factory=list)   # (theta_deg, value)
    mirror: bool = False                   # mirror the points about theta = 0
    color: str = DEFAULT_COLORS[0]
    visible: bool = True

    # ---- geometry ------------------------------------------------------
    def curve(self) -> Tuple[np.ndarray, np.ndarray]:
        """The mask as sorted theta and value arrays, mirrored if asked."""
        pts = [(float(t), float(v)) for t, v in self.points]
        if self.mirror:
            pts += [(-t, v) for t, v in pts if t != 0.0]
        if not pts:
            return np.array([]), np.array([])
        pts.sort()
        theta = np.array([p[0] for p in pts])
        value = np.array([p[1] for p in pts])
        # Duplicate theta (a vertical step) is kept as-is; interpolation
        # below handles it by taking the later value.
        return theta, value

    def evaluate(self, theta) -> np.ndarray:
        """The mask value at ``theta``; NaN outside the mask's theta span."""
        mask_theta, mask_value = self.curve()
        theta = np.asarray(theta, dtype=float)
        if mask_theta.size == 0:
            return np.full(theta.shape, np.nan)
        out = np.interp(theta, mask_theta, mask_value)
        out[(theta < mask_theta[0]) | (theta > mask_theta[-1])] = np.nan
        return out

    def violation(self, theta, values) -> Optional[Tuple[float, float]]:
        """
        Worst violation of the mask by a trace: (margin_db, theta) where
        margin is how far the trace crosses the limit (positive = violated).
        None when the trace never crosses inside the mask span.
        """
        limit = self.evaluate(theta)
        values = np.asarray(values, dtype=float)
        with np.errstate(invalid='ignore'):
            excess = (values - limit) if self.kind == 'upper' else (limit - values)
        ok = np.isfinite(excess)
        if not ok.any():
            return None
        i = int(np.nanargmax(np.where(ok, excess, -np.inf)))
        if excess[i] <= 0:
            return None
        return float(excess[i]), float(np.asarray(theta, dtype=float)[i])

    def margin(self, theta, values) -> Optional[float]:
        """Smallest clearance to the mask (negative when violated), or None."""
        limit = self.evaluate(theta)
        values = np.asarray(values, dtype=float)
        with np.errstate(invalid='ignore'):
            clearance = (limit - values) if self.kind == 'upper' else (values - limit)
        ok = np.isfinite(clearance)
        return float(np.min(clearance[ok])) if ok.any() else None

    # ---- serialisation -------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['points'] = [[float(t), float(v)] for t, v in self.points]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SpecMask':
        known = {f.name for f in fields(cls)}
        clean = {k: v for k, v in (data or {}).items() if k in known}
        clean['points'] = [(float(p[0]), float(p[1])) for p in clean.get('points', [])]
        if clean.get('kind') not in MASK_KINDS:
            clean['kind'] = 'upper'
        return cls(**clean)


# ---------------------------------------------------------------- CSV I/O

def read_mask_csv(path, name: Optional[str] = None, kind: str = 'upper',
                  mirror: bool = False) -> SpecMask:
    """
    Read a mask from a CSV/whitespace file with columns theta, value.

    A header line is skipped if its first field is not numeric. Comment
    lines starting with '#' are ignored. Commas, semicolons, tabs and
    spaces all separate columns.
    """
    path = Path(path)
    points: List[Tuple[float, float]] = []
    with open(path, 'r', encoding='utf-8-sig', newline='') as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith('#'):
                continue
            for sep in (',', ';', '\t'):
                line = line.replace(sep, ' ')
            parts = line.split()
            if len(parts) < 2:
                continue
            try:
                points.append((float(parts[0]), float(parts[1])))
            except ValueError:
                if points:
                    raise ValueError(f"{path.name}: non-numeric row {raw.strip()!r}")
                continue            # header
    if len(points) < 2:
        raise ValueError(f"{path.name}: a mask needs at least two theta, value rows")
    return SpecMask(name=name or path.stem, kind=kind, points=points, mirror=mirror)


def write_mask_csv(mask: SpecMask, path) -> None:
    with open(path, 'w', encoding='utf-8', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['theta_deg', 'value'])
        for theta, value in mask.points:
            writer.writerow([theta, value])


def masks_to_json(masks: Sequence[SpecMask]) -> str:
    return json.dumps([m.to_dict() for m in masks], indent=2)


def masks_from_json(text: str) -> List[SpecMask]:
    return [SpecMask.from_dict(item) for item in json.loads(text)]


# ---------------------------------------------------------------- drawing

def draw_masks(ax, masks: Sequence[SpecMask], alpha=0.15) -> List:
    """
    Draw every visible mask on ``ax`` and return the artists.

    The shaded side is the forbidden side: above an upper mask, below a
    lower one. The boundary is a LineCollection carrying the legend label.
    """
    from matplotlib.collections import LineCollection

    artists = []
    if ax is None or hasattr(ax, 'set_theta_zero_location'):
        return artists
    ymin, ymax = ax.get_ylim()
    for mask in masks:
        if not mask.visible:
            continue
        theta, value = mask.curve()
        if theta.size < 2:
            continue
        fill_to = ymax if mask.kind == 'upper' else ymin
        artists.append(ax.fill_between(theta, value, fill_to, color=mask.color, alpha=alpha,
                                       linewidth=0, zorder=1, label='_mask_fill'))
        segments = [np.column_stack([theta, value])]
        boundary = LineCollection(segments, colors=[mask.color], linewidths=1.5,
                                  linestyles='--', zorder=3,
                                  label=f"{mask.name} ({'max' if mask.kind == 'upper' else 'min'})")
        ax.add_collection(boundary)
        artists.append(boundary)
    ax.set_ylim(ymin, ymax)          # the fill must not stretch the axes
    return artists


def mask_report(masks: Sequence[SpecMask], traces) -> List[str]:
    """
    One line per (mask, trace) pair that violates, plus a pass line per
    mask that nothing violates. ``traces`` is a sequence of
    (label, theta, values).
    """
    lines = []
    for mask in masks:
        if not mask.visible:
            continue
        hits = []
        for label, theta, values in traces:
            worst = mask.violation(theta, values)
            if worst is not None:
                hits.append(f"{label} by {worst[0]:.2f} dB at θ={worst[1]:.1f}°")
        if hits:
            lines.append(f"Mask '{mask.name}' violated: " + "; ".join(hits))
        else:
            margins = [m for m in (mask.margin(t, v) for _l, t, v in traces) if m is not None]
            if margins:
                lines.append(f"Mask '{mask.name}' passed, margin {min(margins):.2f} dB")
    return lines
