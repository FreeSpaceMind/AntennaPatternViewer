"""
Plot styling applied on top of a finished matplotlib axes.

The plotting functions draw with their own defaults (titles, labels, line
styles). A ``PlotStyle`` holds the user's overrides; ``apply_style`` applies
them to the axes after drawing, so no plotting function has to know about
styling and the style survives every replot. A field of ``None`` means
"leave the plotting function's default alone".

Series overrides are keyed by legend label rather than by position, so an
edit to one trace persists when the plot is rebuilt after a processing step
or a selection change.
"""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field, asdict, fields
from typing import Any, Dict, List, Optional

import matplotlib
from matplotlib.ticker import MultipleLocator

# Legend locations offered in the dialog, in matplotlib's spelling.
LEGEND_LOCATIONS = ['best', 'upper right', 'upper left', 'lower left', 'lower right',
                    'right', 'center left', 'center right', 'lower center',
                    'upper center', 'center', 'outside right']

# Colour cycles offered in the dialog. "default" keeps matplotlib's cycle.
COLOR_CYCLES = ['default', 'tab10', 'tab20', 'Set1', 'Set2', 'Dark2', 'viridis',
                'plasma', 'turbo', 'coolwarm', 'gray']

LINE_STYLES = ['-', '--', '-.', ':']


@dataclass
class SeriesStyle:
    """Per-trace overrides, keyed by the trace's legend label."""
    label: Optional[str] = None       # renamed legend entry
    color: Optional[str] = None       # any matplotlib colour spec
    linewidth: Optional[float] = None
    linestyle: Optional[str] = None
    visible: bool = True


@dataclass
class PlotStyle:
    """Overrides for one plot format. ``None`` keeps the default."""
    # Text
    title: Optional[str] = None
    xlabel: Optional[str] = None
    ylabel: Optional[str] = None
    colorbar_label: Optional[str] = None
    # Fonts
    font_family: Optional[str] = None
    title_size: Optional[float] = None
    label_size: Optional[float] = None
    tick_size: Optional[float] = None
    legend_size: Optional[float] = None
    # Legend (visibility is the existing checkbox on the plot strip)
    legend_loc: str = 'best'
    legend_columns: int = 1
    legend_frame: bool = True
    # Grid (visibility is the existing checkbox on the plot strip)
    grid_minor: bool = False
    grid_linestyle: str = '-'
    grid_alpha: float = 0.5
    # Axes
    x_tick_step: Optional[float] = None
    y_tick_step: Optional[float] = None
    polar_zero_location: str = 'N'
    polar_clockwise: bool = True
    # Lines
    line_width: Optional[float] = None
    color_cycle: str = 'default'
    # Colours
    dark: bool = False
    figure_color: Optional[str] = None
    axes_color: Optional[str] = None
    # Per-trace overrides keyed by the label the plotting function gave the trace
    series: Dict[str, SeriesStyle] = field(default_factory=dict)

    # ---- serialisation -------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['series'] = {key: asdict(value) for key, value in self.series.items()}
        return data

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> 'PlotStyle':
        data = dict(data or {})
        series_data = data.pop('series', {}) or {}
        known = {f.name for f in fields(cls)}
        style = cls(**{k: v for k, v in data.items() if k in known})
        series_known = {f.name for f in fields(SeriesStyle)}
        style.series = {
            str(key): SeriesStyle(**{k: v for k, v in (value or {}).items() if k in series_known})
            for key, value in series_data.items()
        }
        return style

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, text: str) -> 'PlotStyle':
        return cls.from_dict(json.loads(text))

    def copy(self) -> 'PlotStyle':
        return copy.deepcopy(self)


# Built-in presets. Each is the set of fields that differ from PlotStyle().
PRESETS: Dict[str, Dict[str, Any]] = {
    'Default': {},
    'Publication': {
        'font_family': 'serif', 'title_size': 11.0, 'label_size': 10.0,
        'tick_size': 9.0, 'legend_size': 8.0, 'line_width': 1.0,
        'legend_frame': False, 'grid_alpha': 0.3, 'grid_linestyle': ':',
    },
    'Presentation': {
        'font_family': 'sans-serif', 'title_size': 18.0, 'label_size': 16.0,
        'tick_size': 14.0, 'legend_size': 13.0, 'line_width': 2.5,
        'grid_alpha': 0.4,
    },
    'Dark': {
        'dark': True, 'grid_alpha': 0.3, 'color_cycle': 'tab10',
    },
}


def preset(name: str) -> PlotStyle:
    """A fresh PlotStyle for a built-in preset name."""
    return PlotStyle.from_dict(PRESETS[name])


# ---- colour cycle ----------------------------------------------------------

def cycle_colors(name: str, count: int) -> Optional[List[Any]]:
    """
    Colours for ``count`` traces from a named cycle, or None for the default.

    Qualitative maps (tab10 etc.) are sampled in order so neighbouring traces
    differ; continuous maps are sampled evenly over their range.
    """
    if not name or name == 'default':
        return None
    cmap = matplotlib.colormaps[name]
    n = max(int(count), 1)
    qualitative = getattr(cmap, 'colors', None) is not None
    if qualitative:
        base = list(cmap.colors)
        return [base[i % len(base)] for i in range(n)]
    if n == 1:
        return [cmap(0.5)]
    return [cmap(i / (n - 1)) for i in range(n)]


# ---- application -----------------------------------------------------------

_DARK_FG = '#e6e6e6'
_DARK_FIG = '#1e1e1e'
_DARK_AXES = '#2a2a2a'


def _series_key(line) -> str:
    return line.get_label()


def apply_style(figure, ax, style: PlotStyle, colorbar=None, legend_visible=None):
    """
    Apply ``style`` to a drawn axes.

    Text and font overrides replace what the plotting function set. Line
    overrides are applied to every line, then per-series overrides on top.
    The legend is rebuilt when a series label or colour changes so it stays
    in step with the lines; ``legend_visible`` (None = leave as is) is the
    plot strip's checkbox.
    """
    if ax is None:
        return
    is_polar = hasattr(ax, 'set_theta_zero_location')

    # --- colours -------------------------------------------------------
    fg = None
    if style.dark:
        figure.set_facecolor(style.figure_color or _DARK_FIG)
        ax.set_facecolor(style.axes_color or _DARK_AXES)
        fg = _DARK_FG
    else:
        figure.set_facecolor(style.figure_color or 'white')
        ax.set_facecolor(style.axes_color or 'white')
        fg = 'black'
    for spine in ax.spines.values():
        spine.set_color(fg)
    ax.tick_params(colors=fg, which='both')
    ax.xaxis.label.set_color(fg)
    ax.yaxis.label.set_color(fg)
    ax.title.set_color(fg)

    # --- text ----------------------------------------------------------
    if style.title is not None:
        ax.set_title(style.title)
    if style.xlabel is not None:
        ax.set_xlabel(style.xlabel)
    if style.ylabel is not None:
        ax.set_ylabel(style.ylabel)
    if colorbar is not None and style.colorbar_label is not None:
        colorbar.set_label(style.colorbar_label)

    # --- fonts ---------------------------------------------------------
    family = style.font_family
    if family:
        ax.title.set_family(family)
        ax.xaxis.label.set_family(family)
        ax.yaxis.label.set_family(family)
        for tick in ax.get_xticklabels() + ax.get_yticklabels():
            tick.set_family(family)
    if style.title_size:
        ax.title.set_fontsize(style.title_size)
    if style.label_size:
        ax.xaxis.label.set_fontsize(style.label_size)
        ax.yaxis.label.set_fontsize(style.label_size)
        if colorbar is not None:
            colorbar.ax.yaxis.label.set_fontsize(style.label_size)
    if style.tick_size:
        ax.tick_params(labelsize=style.tick_size, which='both')
        if colorbar is not None:
            colorbar.ax.tick_params(labelsize=style.tick_size)
    if colorbar is not None:
        colorbar.ax.yaxis.label.set_color(fg)
        colorbar.ax.tick_params(colors=fg)

    # --- axes ----------------------------------------------------------
    if is_polar:
        ax.set_theta_zero_location(style.polar_zero_location or 'N')
        ax.set_theta_direction(-1 if style.polar_clockwise else 1)
        if style.y_tick_step:
            ax.yaxis.set_major_locator(MultipleLocator(style.y_tick_step))
    else:
        if style.x_tick_step:
            ax.xaxis.set_major_locator(MultipleLocator(style.x_tick_step))
        if style.y_tick_step:
            ax.yaxis.set_major_locator(MultipleLocator(style.y_tick_step))

    # --- grid ----------------------------------------------------------
    grid_on = any(line.get_visible() for line in ax.get_xgridlines() + ax.get_ygridlines())
    if grid_on:
        ax.grid(True, which='major', linestyle=style.grid_linestyle or '-',
                alpha=style.grid_alpha, color=fg)
        if style.grid_minor:
            ax.minorticks_on()
            ax.grid(True, which='minor', linestyle=':', alpha=max(style.grid_alpha * 0.6, 0.05),
                    color=fg)
        else:
            ax.grid(False, which='minor')

    # --- lines ---------------------------------------------------------
    legend_dirty = False
    for line in ax.get_lines():
        if style.line_width:
            line.set_linewidth(style.line_width)
        override = style.series.get(_series_key(line))
        if override is None:
            continue
        if override.color:
            line.set_color(override.color)
            legend_dirty = True
        if override.linewidth:
            line.set_linewidth(override.linewidth)
        if override.linestyle:
            line.set_linestyle(override.linestyle)
            legend_dirty = True
        line.set_visible(override.visible)
        legend_dirty = True

    # --- legend --------------------------------------------------------
    # Labelled collections (specification masks) are drawn after the
    # plotting function built its legend, so their presence forces a rebuild.
    labelled_collections = [c for c in ax.collections
                            if c.get_label() and not str(c.get_label()).startswith('_')]
    legend_dirty = legend_dirty or bool(labelled_collections)
    legend = ax.get_legend()
    wants_legend = legend is not None and (legend_visible if legend_visible is not None
                                           else legend.get_visible())
    if legend is not None and (wants_legend or legend_dirty):
        handles, labels = [], []
        for line in ax.get_lines():
            raw = _series_key(line)
            if raw.startswith('_') or not line.get_visible():
                continue
            override = style.series.get(raw)
            handles.append(line)
            labels.append(override.label if override and override.label else raw)
        for collection in labelled_collections:
            handles.append(collection)
            labels.append(str(collection.get_label()))
        if handles:
            kwargs = dict(ncol=max(int(style.legend_columns), 1), frameon=style.legend_frame)
            if style.legend_loc == 'outside right':
                kwargs.update(loc='center left', bbox_to_anchor=(1.02, 0.5))
            else:
                kwargs['loc'] = style.legend_loc or 'best'
            if style.legend_size:
                kwargs['fontsize'] = style.legend_size
            legend = ax.legend(handles, labels, **kwargs)
            if family:
                for text in legend.get_texts():
                    text.set_family(family)
            if style.dark:
                legend.get_frame().set_facecolor(_DARK_AXES)
                legend.get_frame().set_edgecolor(_DARK_FG)
                for text in legend.get_texts():
                    text.set_color(_DARK_FG)
            legend.set_visible(bool(wants_legend))


def series_labels(ax) -> List[str]:
    """Legend labels of the traces on ``ax``, in drawing order, without hidden ones."""
    if ax is None:
        return []
    return [_series_key(line) for line in ax.get_lines() if not _series_key(line).startswith('_')]
