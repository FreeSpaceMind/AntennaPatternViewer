"""
Pattern arithmetic: a new pattern derived from two loaded ones.

- ``ratio``: the complex ratio A / B of the co- and cross-polar components
  (the library's difference_patterns), with B's phase aligned to A at
  boresight. Its gain is the gain difference in dB and its phase the phase
  difference, so a before/after MARS comparison becomes one trace a mask
  can be put on.
- ``gain_difference``: |A / B| with zero phase, when only the level
  difference matters.
- ``difference`` and ``sum``: the complex field A - B and A + B on the
  theta/phi components, for cancellation or superposition studies.

The inputs are the patterns as processed (what the comparison plot shows),
on identical theta, phi and frequency grids.
"""
from __future__ import annotations

from typing import Dict

import numpy as np

from farfield_spherical import FarFieldSpherical
from farfield_spherical.package_functions import difference_patterns

OPERATIONS: Dict[str, str] = {
    'ratio': 'A / B  (complex ratio: gain and phase difference)',
    'gain_difference': '|A / B|  (gain difference in dB, zero phase)',
    'difference': 'A − B  (complex field difference)',
    'sum': 'A + B  (complex field sum)',
}

SYMBOLS = {'ratio': '/', 'gain_difference': '/', 'difference': '−', 'sum': '+'}


def derived_name(op: str, name_a: str, name_b: str) -> str:
    symbol = SYMBOLS.get(op, op)
    name = f"{name_a} {symbol} {name_b}"
    return f"|{name}|" if op == 'gain_difference' else name


def _check_grids(a: FarFieldSpherical, b: FarFieldSpherical) -> None:
    for what, x, y in (('theta', a.theta_angles, b.theta_angles),
                       ('phi', a.phi_angles, b.phi_angles),
                       ('frequency', a.frequencies, b.frequencies)):
        x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
        if x.shape != y.shape or not np.allclose(x, y, atol=1e-6):
            raise ValueError(
                f"The patterns have different {what} grids ({x.shape[0]} vs {y.shape[0]} samples). "
                f"Bring them onto the same grid first (coordinate format, subsample or "
                f"interpolation), then combine them.")


def _matched(a: FarFieldSpherical, b: FarFieldSpherical) -> FarFieldSpherical:
    """B on A's polarization, as a copy when a change is needed."""
    if b.polarization != a.polarization:
        b = b.copy()
        b.change_polarization(a.polarization)
    return b


def derive_pattern(op: str, a: FarFieldSpherical, b: FarFieldSpherical) -> FarFieldSpherical:
    """A new FarFieldSpherical for ``op`` applied to A and B."""
    if op not in OPERATIONS:
        raise ValueError(f"Unknown operation {op!r}; choose from {list(OPERATIONS)}")
    _check_grids(a, b)
    if op == 'ratio':
        return difference_patterns(a, b)
    if op == 'gain_difference':
        ratio = difference_patterns(a, b)
        # Keep the magnitudes of the Ludwig components, drop the phases
        e_co = np.abs(ratio.data.e_co.values).astype(np.complex64)
        e_cx = np.abs(ratio.data.e_cx.values).astype(np.complex64)
        return _from_components(ratio, e_co, e_cx)
    b = _matched(a, b)
    sign = -1.0 if op == 'difference' else 1.0
    e_theta = a.data.e_theta.values + sign * b.data.e_theta.values
    e_phi = a.data.e_phi.values + sign * b.data.e_phi.values
    return FarFieldSpherical(np.asarray(a.theta_angles, dtype=float), np.asarray(a.phi_angles, dtype=float),
                             np.asarray(a.frequencies, dtype=float), e_theta, e_phi,
                             polarization=a.polarization)


def _from_components(template: FarFieldSpherical, e_co, e_cx) -> FarFieldSpherical:
    """A pattern with the template's grid and polarization from co/cross components."""
    from farfield_spherical.polarization import polarization_rl2tp, polarization_xy2tp

    pol = str(template.polarization).lower()
    phi = np.asarray(template.phi_angles, dtype=float)
    if pol in ('x', 'l3x'):
        e_theta, e_phi = polarization_xy2tp(phi, e_co, e_cx)
    elif pol in ('y', 'l3y'):
        e_theta, e_phi = polarization_xy2tp(phi, e_cx, e_co)
    elif pol in ('rhcp', 'rh', 'r'):
        e_theta, e_phi = polarization_rl2tp(phi, e_co, e_cx)
    elif pol in ('lhcp', 'lh', 'l'):
        e_theta, e_phi = polarization_rl2tp(phi, e_cx, e_co)
    elif pol == 'theta':
        e_theta, e_phi = e_co, e_cx
    else:
        e_theta, e_phi = e_cx, e_co
    return FarFieldSpherical(np.asarray(template.theta_angles, dtype=float), phi,
                             np.asarray(template.frequencies, dtype=float), e_theta, e_phi,
                             polarization=template.polarization)
