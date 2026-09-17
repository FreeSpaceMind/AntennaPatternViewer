"""
Plot layouts beyond the single 1D cut and the 2D polar image:

- ``plot_polar_cut``: a true polar line plot of one or more cuts, angle
  = theta, radius = value (dB with a dynamic-range floor).
- ``plot_amplitude_phase``: gain over phase in two stacked axes that share
  theta.
- ``plot_small_multiples``: one panel per frequency, shared axes.
- ``plot_frequency_sweep``: a pattern metric (peak or boresight gain, HPBW,
  first sidelobe, squint, boresight XPD) against frequency, one trace per
  phi cut.

They reuse plot_pattern_cut and the pattern markers analysis so a cut looks
the same wherever it appears.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence

import numpy as np
from matplotlib.figure import Figure

from farfield_spherical import FarFieldSpherical, find_nearest

from .pattern_markers import analyze_cut
from .plotting import _component_values, _line_colors, plot_pattern_cut

SWEEP_METRICS: Dict[str, str] = {
    'peak_gain': 'Peak gain (dBi)',
    'boresight_gain': 'Boresight gain (dBi)',
    'hpbw': 'Half-power beamwidth (deg)',
    'sidelobe_level': 'First sidelobe level (dB)',
    'squint': 'Peak angle (deg)',
    'xpd_boresight': 'Boresight XPD (dB)',
    'null_depth': 'First null depth (dB)',
}


def _phi_indices(pattern, phi) -> List[int]:
    if phi is None:
        return list(range(len(pattern.phi_angles)))
    wanted = np.atleast_1d(np.asarray(phi, dtype=float))
    seen, indices = set(), []
    for value in wanted:
        _val, idx = find_nearest(pattern.phi_angles, value)
        if idx not in seen:
            seen.add(idx)
            indices.append(int(idx))
    return indices


def _freq_indices(pattern, frequencies) -> List[int]:
    if frequencies is None:
        return [0]
    wanted = np.atleast_1d(np.asarray(frequencies, dtype=float))
    seen, indices = set(), []
    for value in wanted:
        _val, idx = find_nearest(pattern.frequencies, value)
        if idx not in seen:
            seen.add(idx)
            indices.append(int(idx))
    return indices


# ---------------------------------------------------------------- polar cut

def plot_polar_cut(pattern: FarFieldSpherical, frequencies, phi, value_type='gain',
                   component='e_co', show_cross_pol=False, unwrap_phase=True,
                   normalize=False, ax=None, dynamic_range=40.0, colors=None,
                   title: Optional[str] = None):
    """
    Draw the selected cuts on a polar axes with theta as the angle.

    A sided pattern is converted to central on a copy so that each phi cut
    is a full great circle (theta -180..180) and the plot is a full ring;
    a phi at or above 180 selects the same circle as phi - 180. Boresight is
    at the top and positive theta runs clockwise. For gain the radial axis
    is dB from the peak down to ``dynamic_range`` below it.
    """
    if ax is None:
        fig = Figure(figsize=(7, 7))
        ax = fig.add_subplot(111, projection='polar')
    if not hasattr(ax, 'set_theta_zero_location'):
        raise ValueError("plot_polar_cut needs a polar axes")

    work = pattern
    theta = np.asarray(pattern.theta_angles, dtype=float)
    if theta.min() >= -0.5:                       # sided: close the circles
        work = pattern.copy()
        work.transform_coordinates('central')
    theta = np.asarray(work.theta_angles, dtype=float)

    # Map requested phi onto the central cut that contains it
    span = float(np.max(work.phi_angles)) - float(np.min(work.phi_angles))
    requested = np.atleast_1d(np.asarray(phi if phi is not None else work.phi_angles, dtype=float))
    if span < 190.0:                               # central phi covers 0..180
        requested = np.mod(requested, 180.0)
    phi_idx = _phi_indices(work, requested)
    freq_idx = _freq_indices(work, frequencies)

    main = component
    cross = 'e_cx' if component == 'e_co' else 'e_co'
    kind = value_type
    data_main = _component_values(work, main, kind, freq_idx, unwrap_phase)
    data_cross = (_component_values(work, cross, kind, freq_idx, unwrap_phase)
                  if show_cross_pol and kind != 'axial_ratio' else None)

    if normalize and kind == 'gain':
        peak = np.nanmax(data_main[freq_idx])
        data_main = data_main - peak
        if data_cross is not None:
            data_cross = data_cross - peak

    n_traces = len(freq_idx) * len(phi_idx)
    palette = _line_colors(colors, len(phi_idx) if len(freq_idx) == 1 else len(freq_idx))
    angle = np.radians(theta)
    for i, fi in enumerate(freq_idx):
        for j, pj in enumerate(phi_idx):
            color = palette[j if len(freq_idx) == 1 else i]
            phi_value = float(work.phi_angles[pj])
            if len(freq_idx) == 1:
                label = f"φ={phi_value:.1f}°"
            else:
                label = f"{work.frequencies[fi] / 1e6:.1f} MHz, φ={phi_value:.1f}°"
            ax.plot(angle, data_main[fi, :, pj], '-', color=color, label=label)
            if data_cross is not None:
                ax.plot(angle, data_cross[fi, :, pj], ':', color=color, label=f"{label} (cross)")

    ax.set_theta_zero_location('N')
    ax.set_theta_direction(-1)
    grid_angles = np.arange(0, 360, 30)
    ax.set_thetagrids(grid_angles, labels=[f"{a if a <= 180 else a - 360:g}°" for a in grid_angles])

    finite = data_main[freq_idx][np.isfinite(data_main[freq_idx])]
    if kind == 'gain' and finite.size:
        top = float(np.ceil(finite.max() / 5.0) * 5.0)
        ax.set_rlim(top - dynamic_range, top)
        ax.set_rlabel_position(22.5)
        units = 'dB' if normalize else 'dBi'
        ax.set_title(title or f"Polar cut, {units}", pad=18)
    elif kind == 'phase':
        ax.set_title(title or "Polar cut, phase (deg)", pad=18)
    else:
        ax.set_title(title or "Polar cut, axial ratio (dB)", pad=18)
    if n_traces:
        ax.legend(loc='lower left', bbox_to_anchor=(1.0, 0.0), fontsize=8)
    return ax


# ------------------------------------------------------- amplitude + phase

def plot_amplitude_phase(pattern, frequencies, phi, component='e_co', show_cross_pol=False,
                         unwrap_phase=True, normalize=False, fig=None, colors=None):
    """
    Gain over phase for the same cuts, sharing the theta axis.

    Returns (amplitude_axes, phase_axes).
    """
    if fig is None:
        fig = Figure(figsize=(10, 8))
    fig.clear()
    ax_amp, ax_phase = fig.subplots(2, 1, sharex=True, gridspec_kw={'height_ratios': [2, 1]})
    plot_pattern_cut(pattern, frequency=frequencies, phi=phi, show_cross_pol=show_cross_pol,
                     value_type='gain', component=component, ax=ax_amp,
                     unwrap_phase=unwrap_phase, normalize=normalize, colors=colors)
    plot_pattern_cut(pattern, frequency=frequencies, phi=phi, show_cross_pol=show_cross_pol,
                     value_type='phase', component=component, ax=ax_phase,
                     unwrap_phase=unwrap_phase, normalize=False, colors=colors)
    ax_amp.set_xlabel('')
    ax_phase.set_title('')
    legend = ax_phase.get_legend()
    if legend is not None:
        legend.remove()
    fig.tight_layout()
    return ax_amp, ax_phase


# ---------------------------------------------------------- small multiples

def plot_small_multiples(pattern, frequencies, phi, value_type='gain', component='e_co',
                         show_cross_pol=False, unwrap_phase=True, normalize=False,
                         fig=None, colors=None, ncols: Optional[int] = None):
    """
    One panel per selected frequency, every panel showing the selected phi
    cuts, with shared x and y axes. Returns the list of axes in order.
    """
    if fig is None:
        fig = Figure(figsize=(12, 8))
    fig.clear()
    freq_idx = _freq_indices(pattern, frequencies)
    n = max(len(freq_idx), 1)
    ncols = ncols or int(math.ceil(math.sqrt(n)))
    nrows = int(math.ceil(n / ncols))
    axes = fig.subplots(nrows, ncols, sharex=True, sharey=True, squeeze=False)
    flat = list(axes.ravel())
    for k, ax in enumerate(flat):
        if k >= n:
            ax.set_visible(False)
            continue
        frequency = float(pattern.frequencies[freq_idx[k]])
        plot_pattern_cut(pattern, frequency=frequency, phi=phi, show_cross_pol=show_cross_pol,
                         value_type=value_type, component=component, ax=ax,
                         unwrap_phase=unwrap_phase, normalize=normalize, colors=colors,
                         title=f"{frequency / 1e6:.1f} MHz")
        ax.title.set_fontsize(10)
        if k != 0 and ax.get_legend() is not None:
            ax.get_legend().remove()
        ax.label_outer()
    used = flat[:n]
    fig.tight_layout()
    return used


# --------------------------------------------------------- frequency sweep

def sweep_metrics(pattern, phi, component='e_co') -> Dict[str, np.ndarray]:
    """
    Every sweep metric for the selected phi cuts, as arrays shaped
    (n_frequency, n_phi). Values that do not exist (no sidelobe) are NaN.
    """
    phi_idx = _phi_indices(pattern, phi)
    n_freq = len(pattern.frequencies)
    cross = 'e_cx' if component == 'e_co' else 'e_co'
    all_idx = list(range(n_freq))
    main = _component_values(pattern, component, 'gain', all_idx)
    cx = _component_values(pattern, cross, 'gain', all_idx)
    out = {key: np.full((n_freq, len(phi_idx)), np.nan) for key in SWEEP_METRICS}
    for fi in range(n_freq):
        for j, pj in enumerate(phi_idx):
            theta = np.asarray(pattern.get_theta_for_phi(pj) if hasattr(pattern, 'get_theta_for_phi')
                               else pattern.theta_angles, dtype=float)
            values = main[fi, :, pj]
            analysis = analyze_cut(theta, values)
            if analysis is None:
                continue
            out['peak_gain'][fi, j] = analysis.peak_value
            out['squint'][fi, j] = analysis.peak_theta
            if analysis.hpbw is not None:
                out['hpbw'][fi, j] = analysis.hpbw
            if analysis.sidelobe_level is not None:
                out['sidelobe_level'][fi, j] = analysis.sidelobe_level
            if analysis.null_depth is not None:
                out['null_depth'][fi, j] = analysis.null_depth
            i0 = int(np.argmin(np.abs(theta)))
            out['boresight_gain'][fi, j] = values[i0]
            xpd = values[i0] - cx[fi, i0, pj]
            out['xpd_boresight'][fi, j] = xpd if np.isfinite(xpd) else np.nan
    return out


def plot_frequency_sweep(pattern, phi, metric='peak_gain', component='e_co', ax=None,
                         colors=None, title: Optional[str] = None):
    """One trace per phi cut of ``metric`` against frequency in MHz."""
    if metric not in SWEEP_METRICS:
        raise ValueError(f"Unknown sweep metric {metric!r}; choose from {list(SWEEP_METRICS)}")
    if ax is None:
        fig = Figure(figsize=(10, 6))
        ax = fig.add_subplot(111)
    phi_idx = _phi_indices(pattern, phi)
    data = sweep_metrics(pattern, phi, component)[metric]
    x = np.asarray(pattern.frequencies, dtype=float) / 1e6
    palette = _line_colors(colors, len(phi_idx))
    for j, pj in enumerate(phi_idx):
        ax.plot(x, data[:, j], 'o-', color=palette[j], markersize=4,
                label=f"φ={float(pattern.phi_angles[pj]):.1f}°")
    ax.set_xlabel('Frequency (MHz)')
    ax.set_ylabel(SWEEP_METRICS[metric])
    ax.set_title(title or f"{SWEEP_METRICS[metric]} vs frequency")
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best')
    return ax
