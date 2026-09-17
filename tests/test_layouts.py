"""
The plot layouts: polar cut, amplitude + phase, small multiples and the
frequency sweep, both as plotting functions and through the plot widget.
"""
import numpy as np
import pytest
from matplotlib.figure import Figure

from .conftest import make_pattern

FREQS = np.array([8e9, 9e9, 10e9, 11e9])


@pytest.fixture
def widget(qapp, tmp_path, monkeypatch):
    from PyQt6.QtCore import QSettings
    from antenna_pattern_viewer.widgets.plot_widget import PlotWidget

    monkeypatch.setattr(PlotWidget, '_settings',
                        lambda self: QSettings(str(tmp_path / 's.ini'), QSettings.Format.IniFormat))
    w = PlotWidget()
    w.resize(1000, 700)
    w.show()
    return w


def base(**overrides):
    params = dict(frequencies=[8e9, 10e9], phi_angles=[0.0, 45.0, 90.0], value_type='gain',
                  show_cross_pol=True, unwrap_phase=True, component='e_co', pattern_key='k',
                  plot_format='1d_cut')
    params.update(overrides)
    return params


class TestPolarCut:
    def test_sided_pattern_becomes_a_full_ring(self):
        from antenna_pattern_viewer.plot_layouts import plot_polar_cut

        fig = Figure()
        ax = fig.add_subplot(111, projection='polar')
        plot_polar_cut(make_pattern(freqs=FREQS), [8e9], [0.0, 90.0], ax=ax)
        lines = ax.get_lines()
        assert len(lines) == 2
        angles = np.degrees(lines[0].get_xdata())
        assert angles.min() == pytest.approx(-180.0) and angles.max() == pytest.approx(180.0)
        assert ax.get_theta_direction() == -1
        rmin, rmax = ax.get_ylim()
        assert rmax - rmin == pytest.approx(40.0)

    def test_phi_beyond_180_maps_onto_its_great_circle(self):
        from antenna_pattern_viewer.plot_layouts import plot_polar_cut

        fig = Figure()
        ax = fig.add_subplot(111, projection='polar')
        plot_polar_cut(make_pattern(freqs=FREQS), [8e9], [30.0, 210.0], ax=ax)
        assert len(ax.get_lines()) == 1            # the same circle, drawn once

    def test_cross_pol_and_normalize(self):
        from antenna_pattern_viewer.plot_layouts import plot_polar_cut

        fig = Figure()
        ax = fig.add_subplot(111, projection='polar')
        plot_polar_cut(make_pattern(freqs=FREQS), [8e9], [0.0], show_cross_pol=True, normalize=True, ax=ax)
        assert [l.get_label() for l in ax.get_lines()] == ['φ=0.0°', 'φ=0.0° (cross)']
        assert np.nanmax(ax.get_lines()[0].get_ydata()) == pytest.approx(0.0, abs=1e-6)

    def test_needs_a_polar_axes(self):
        from antenna_pattern_viewer.plot_layouts import plot_polar_cut

        with pytest.raises(ValueError):
            plot_polar_cut(make_pattern(), [8e9], [0.0], ax=Figure().add_subplot(111))


class TestAmplitudePhase:
    def test_two_panels_share_theta(self):
        from antenna_pattern_viewer.plot_layouts import plot_amplitude_phase

        fig = Figure()
        ax_amp, ax_phase = plot_amplitude_phase(make_pattern(freqs=FREQS), [8e9], [0.0, 45.0], fig=fig)
        assert ax_amp.get_shared_x_axes().joined(ax_amp, ax_phase)
        assert 'Gain' in ax_amp.get_ylabel() and 'Phase' in ax_phase.get_ylabel()
        assert ax_amp.get_xlabel() == '' and ax_phase.get_xlabel()
        assert ax_amp.get_legend() is not None and ax_phase.get_legend() is None


class TestSmallMultiples:
    def test_one_panel_per_frequency_with_shared_axes(self):
        from antenna_pattern_viewer.plot_layouts import plot_small_multiples

        fig = Figure()
        axes = plot_small_multiples(make_pattern(freqs=FREQS), [8e9, 9e9, 10e9], [0.0, 90.0], fig=fig)
        assert len(axes) == 3
        assert all(a.get_shared_y_axes().joined(axes[0], a) for a in axes[1:])
        assert [a.get_title() for a in axes] == ['8000.0 MHz', '9000.0 MHz', '10000.0 MHz']
        assert len(axes[0].get_lines()) == 2
        # the unused fourth cell of the 2x2 grid is hidden
        hidden = [a for a in fig.axes if not a.get_visible()]
        assert len(hidden) == 1

    def test_only_first_panel_has_a_legend(self):
        from antenna_pattern_viewer.plot_layouts import plot_small_multiples

        axes = plot_small_multiples(make_pattern(freqs=FREQS), list(FREQS), [0.0], fig=Figure())
        assert axes[0].get_legend() is not None
        assert all(a.get_legend() is None for a in axes[1:])


class TestFrequencySweep:
    def test_metrics_shape_and_values(self):
        from antenna_pattern_viewer.plot_layouts import SWEEP_METRICS, sweep_metrics

        pattern = make_pattern(freqs=FREQS)
        metrics = sweep_metrics(pattern, [0.0, 90.0])
        assert set(metrics) == set(SWEEP_METRICS)
        assert all(v.shape == (4, 2) for v in metrics.values())
        # make_pattern scales the beam by (1 + 0.1 i) per frequency
        peak = metrics['peak_gain'][:, 0]
        assert np.all(np.diff(peak) > 0)
        assert peak[1] - peak[0] == pytest.approx(20 * np.log10(1.1), abs=1e-3)
        assert metrics['squint'][0, 0] == 0.0
        # a sided cut's beamwidth is taken as symmetric about boresight
        assert np.isfinite(metrics['hpbw']).all()
        # zero cross-pol at boresight gives NaN, never infinity
        assert not np.isinf(metrics['xpd_boresight']).any()

    def test_plot_one_trace_per_cut(self):
        from antenna_pattern_viewer.plot_layouts import plot_frequency_sweep

        ax = Figure().add_subplot(111)
        plot_frequency_sweep(make_pattern(freqs=FREQS), [0.0, 45.0, 90.0], metric='hpbw', ax=ax)
        assert len(ax.get_lines()) == 3
        assert 'beamwidth' in ax.get_ylabel().lower()
        assert list(ax.get_lines()[0].get_xdata()) == list(FREQS / 1e6)

    def test_unknown_metric(self):
        from antenna_pattern_viewer.plot_layouts import plot_frequency_sweep

        with pytest.raises(ValueError):
            plot_frequency_sweep(make_pattern(), [0.0], metric='nope', ax=Figure().add_subplot(111))


class TestSidedBeamwidth:
    def test_peak_at_first_sample_uses_the_mirror(self):
        from antenna_pattern_viewer.pattern_markers import analyze_cut

        theta = np.arange(0, 91, 1.0)
        a = analyze_cut(theta, -3.0 * (theta / 10.0) ** 2)
        assert a.symmetric_assumed and a.hpbw == pytest.approx(20.0, abs=0.1)
        assert '(sym.)' in a.summary()


class TestFormatsInWidget:
    @pytest.mark.parametrize('fmt, n_axes, polar', [
        ('polar_cut', 1, True), ('amp_phase', 2, False), ('small_multiples', 2, False),
        ('sweep', 1, False), ('1d_cut', 1, False)])
    def test_each_format_draws_without_error(self, widget, fmt, n_axes, polar):
        widget.update_plot(pattern=make_pattern(freqs=FREQS), **base(plot_format=fmt))
        assert len(widget._data_axes) == n_axes
        assert hasattr(widget._data_axes[0], 'set_theta_zero_location') == polar
        assert not any('Error plotting' in t.get_text() for a in widget.figure.axes for t in a.texts)

    def test_controls_follow_the_format(self, widget):
        widget.update_plot(pattern=make_pattern(freqs=FREQS), **base(plot_format='polar_cut'))
        assert not widget.markers_check.isVisible() and not widget.x_phi_min_edit.isVisible()
        assert widget.y_theta_label.text() == 'Radial:'
        widget.update_plot(pattern=make_pattern(freqs=FREQS), **base(plot_format='small_multiples'))
        assert widget.markers_check.isVisible() and widget.cursors_check.isVisible()
        widget.update_plot(pattern=make_pattern(freqs=FREQS), **base(plot_format='sweep'))
        assert not widget.markers_check.isVisible() and widget.cursors_check.isVisible()

    def test_limits_are_kept_per_format(self, widget):
        widget.update_plot(pattern=make_pattern(freqs=FREQS), **base(plot_format='1d_cut'))
        widget.y_theta_min_edit.setText('-30')
        widget.update_plot(pattern=make_pattern(freqs=FREQS), **base(plot_format='polar_cut'))
        assert widget.y_theta_min_edit.text() == ''
        widget.update_plot(pattern=make_pattern(freqs=FREQS), **base(plot_format='1d_cut'))
        assert widget.y_theta_min_edit.text() == '-30'

    def test_markers_on_each_small_multiple(self, widget, qapp):
        widget.update_plot(pattern=make_pattern(freqs=FREQS),
                           **base(plot_format='small_multiples', phi_angles=[0.0], show_cross_pol=False))
        widget.markers_check.setChecked(True)
        qapp.processEvents()
        assert len(widget._marker_text.splitlines()) == 2
        assert widget._marker_text.startswith('[8000.0 MHz]')

    def test_style_applies_to_every_panel(self, widget):
        from antenna_pattern_viewer.plot_style import PlotStyle

        widget.update_plot(pattern=make_pattern(freqs=FREQS), **base(plot_format='amp_phase'))
        widget.set_style(PlotStyle(title='Top only', line_width=3.0), 'amp_phase')
        top, bottom = widget._data_axes
        assert top.get_title() == 'Top only' and bottom.get_title() == ''
        assert {l.get_linewidth() for l in bottom.get_lines()} == {3.0}

    def test_sweep_metric_reaches_the_plot(self, widget):
        widget.update_plot(pattern=make_pattern(freqs=FREQS), **base(plot_format='sweep'),
                           sweep_metric='squint')
        assert 'Peak angle' in widget._data_axes[0].get_ylabel()
        widget.replot_current_data()
        assert 'Peak angle' in widget._data_axes[0].get_ylabel()


class TestViewPanelFormats:
    def test_format_keys_and_sweep_row(self, qapp, model, pattern):
        from antenna_pattern_viewer.widgets.view_panel import ViewPanel

        panel = ViewPanel(model)
        model.set_pattern(pattern)
        panel.on_pattern_loaded(pattern)
        assert set(panel.PLOT_FORMATS.values()) == {'1d_cut', '2d_polar', 'polar_cut', 'amp_phase',
                                                    'small_multiples', 'sweep'}
        assert not panel.sweep_row.isVisibleTo(panel)
        panel.set_plot_format('sweep')
        assert panel.get_plot_format() == 'sweep'
        assert panel.sweep_row.isVisibleTo(panel)
        assert panel.get_current_parameters()['sweep_metric'] == 'peak_gain'

    def test_apply_parameters_round_trip(self, qapp, model, pattern):
        from antenna_pattern_viewer.widgets.view_panel import ViewPanel

        panel = ViewPanel(model)
        model.set_pattern(pattern)
        panel.on_pattern_loaded(pattern)
        panel.apply_parameters({'plot_type': 'small_multiples', 'value_type': 'phase',
                                'component': 'e_cx', 'show_cross_pol': True, 'unwrap_phase': True,
                                'sweep_metric': 'hpbw', 'selected_phi': [45.0, 90.0],
                                'selected_frequencies': [10e9]})
        params = panel.get_current_parameters()
        assert params['plot_type'] == 'small_multiples' and params['value_type'] == 'phase'
        assert params['component'] == 'e_cx' and params['show_cross_pol'] and params['unwrap_phase']
        assert params['sweep_metric'] == 'hpbw'
        assert sorted(params['selected_phi']) == [45.0, 90.0]
        assert params['selected_frequencies'] == [10e9]
