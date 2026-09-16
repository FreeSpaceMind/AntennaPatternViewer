"""
Tests for the plotting helpers.

_component_values converts only the selected frequencies of a pattern. It
must agree with the library accessors (which convert the whole cube) on the
selected slabs and leave the others as NaN.
"""
import numpy as np
import pytest

from .conftest import make_pattern


@pytest.fixture(scope="module")
def plotting(qapp):
    from antenna_pattern_viewer import plotting
    return plotting


@pytest.mark.parametrize('polarization', ['x', 'rhcp'])
def test_component_values_match_accessors(plotting, polarization):
    pattern = make_pattern(freqs=np.array([8e9, 9e9, 10e9]), polarization=polarization)
    idx = [1]
    got = plotting._component_values(pattern, 'e_co', 'gain', idx)
    np.testing.assert_allclose(got[1], pattern.get_gain_db('e_co')[1], rtol=1e-6)
    assert np.isnan(got[0]).all() and np.isnan(got[2]).all()

    got = plotting._component_values(pattern, 'e_cx', 'phase', idx, unwrap_phase=True)
    np.testing.assert_allclose(got[1], pattern.get_phase('e_cx', unwrapped=True)[1], atol=1e-6)

    got = plotting._component_values(pattern, 'e_co', 'phase', idx, unwrap_phase=False)
    np.testing.assert_allclose(got[1], pattern.get_phase('e_co', unwrapped=False)[1], atol=1e-6)

    got = plotting._component_values(pattern, 'e_co', 'axial_ratio', idx)
    np.testing.assert_allclose(got[1], pattern.get_axial_ratio()[1], rtol=1e-6)


def test_component_values_several_frequencies(plotting):
    pattern = make_pattern(freqs=np.array([8e9, 9e9, 10e9]))
    got = plotting._component_values(pattern, 'e_co', 'gain', [2, 0, 2])
    want = pattern.get_gain_db('e_co')
    np.testing.assert_allclose(got[[0, 2]], want[[0, 2]], rtol=1e-6)
    assert np.isnan(got[1]).all()


@pytest.mark.parametrize('theta, phi', [
    (np.arange(0, 181, 5.0), np.arange(0, 360, 15.0)),        # sided
    (np.arange(0, 181, 5.0), np.arange(-180, 181, 15.0)),     # sided, .ffd style
    (np.arange(-180, 181, 5.0), np.arange(0, 180, 15.0)),     # central
])
def test_2d_polar_accepts_every_layout(plotting, theta, phi):
    """The polar plot converts to sided through the library and must not
    change the caller's pattern."""
    import matplotlib.pyplot as plt
    pattern = make_pattern(theta=theta, phi=phi)
    theta_before, phi_before = pattern.theta_angles.copy(), pattern.phi_angles.copy()
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='polar')
    plotting.plot_pattern_2d_polar(pattern, frequency=8e9, ax=ax)
    plt.close(fig)
    np.testing.assert_array_equal(pattern.theta_angles, theta_before)
    np.testing.assert_array_equal(pattern.phi_angles, phi_before)
