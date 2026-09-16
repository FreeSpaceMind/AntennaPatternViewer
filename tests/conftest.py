"""
Shared fixtures for the AntennaPatternViewer test suite.

The tests run headless: QT_QPA_PLATFORM is forced to "offscreen" and
matplotlib to "Agg" before either is imported, so no display is required.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MPLBACKEND", "Agg")

import numpy as np
import pytest

from farfield_spherical import FarFieldSpherical
from farfield_spherical.polarization import polarization_xy2tp

FREQS = np.array([8e9, 10e9])


@pytest.fixture(scope="session")
def qapp():
    """A single QApplication for the whole session."""
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def make_pattern(theta=None, phi=None, freqs=FREQS, polarization='x', beam_deg=20.0):
    """A smooth, x-polarized test pattern on a full sided sphere."""
    theta = np.arange(0, 181, 5.0) if theta is None else np.asarray(theta, float)
    phi = np.arange(0, 360, 15.0) if phi is None else np.asarray(phi, float)
    th = np.radians(theta)[:, None]
    ph = np.radians(phi)[None, :]
    e_co = np.stack([np.exp(-(th / np.radians(beam_deg)) ** 2) * np.ones_like(ph) * (1.0 + 0.1 * i)
                     for i in range(len(freqs))])
    e_cx = 0.01 * np.sin(th) ** 2 * np.cos(2 * ph)
    e_cx = np.stack([e_cx for _ in freqs])
    e_theta, e_phi = polarization_xy2tp(phi, e_co, e_cx)
    return FarFieldSpherical(theta, phi, np.asarray(freqs, float),
                             e_theta, e_phi, polarization=polarization)


@pytest.fixture
def pattern():
    return make_pattern()


@pytest.fixture
def model(qapp):
    from antenna_pattern_viewer.data_model import PatternDataModel

    return PatternDataModel()


@pytest.fixture
def instance_factory():
    """Build a PatternInstance around a fresh pattern."""
    from pathlib import Path

    from antenna_pattern_viewer.pattern_instance import PatternInstance

    def _make(name="p", **kwargs):
        return PatternInstance(pattern=make_pattern(**kwargs),
                               source_file=Path(f"/tmp/{name}.ffd"),
                               display_name=name)

    return _make
