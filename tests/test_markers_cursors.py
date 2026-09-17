"""
Pattern markers (peak, HPBW, first sidelobe, null) and the hover/delta
cursors on a 1D cut.
"""
import numpy as np
import pytest
from matplotlib.backend_bases import MouseButton, MouseEvent

from .conftest import make_pattern

COMMON = dict(frequencies=[8e9], phi_angles=[0.0, 90.0], value_type='gain', show_cross_pol=True,
              unwrap_phase=True, plot_format='1d_cut', component='e_co', pattern_key='k')


def synthetic_cut(hpbw=20.0, sidelobe_db=-18.0, sidelobe_theta=40.0, peak=12.0):
    theta = np.arange(-90, 91, 0.5)
    main = -3.0 * (theta / (hpbw / 2)) ** 2
    side = sidelobe_db - 3.0 * ((np.abs(theta) - sidelobe_theta) / 4.0) ** 2
    return theta, 10 * np.log10(10 ** (main / 10) + 10 ** (side / 10)) + peak


@pytest.fixture
def widget(qapp, tmp_path, monkeypatch):
    from PyQt6.QtCore import QSettings
    from antenna_pattern_viewer.widgets.plot_widget import PlotWidget

    monkeypatch.setattr(PlotWidget, '_settings',
                        lambda self: QSettings(str(tmp_path / 's.ini'), QSettings.Format.IniFormat))
    w = PlotWidget()
    w.resize(900, 600)
    w.show()
    return w


class TestAnalyzeCut:
    def test_gaussian_with_sidelobe(self):
        from antenna_pattern_viewer.pattern_markers import analyze_cut

        theta, y = synthetic_cut()
        a = analyze_cut(theta, y)
        assert a.peak_value == pytest.approx(12.0, abs=1e-6)
        assert a.peak_theta == 0.0
        assert a.hpbw == pytest.approx(20.0, abs=0.1)
        assert a.hp_left == pytest.approx(-10.0, abs=0.1)
        assert a.sidelobe_level == pytest.approx(-18.0, abs=0.1)
        assert abs(a.sidelobe_theta) == pytest.approx(40.0, abs=0.5)
        assert a.null_depth < -20

    def test_offset_does_not_change_relative_values(self):
        from antenna_pattern_viewer.pattern_markers import analyze_cut

        theta, y = synthetic_cut()
        a, b = analyze_cut(theta, y), analyze_cut(theta, y - 30.0)
        assert a.hpbw == b.hpbw and a.sidelobe_level == pytest.approx(b.sidelobe_level)

    def test_no_sidelobe_reports_none(self):
        from antenna_pattern_viewer.pattern_markers import analyze_cut

        theta = np.arange(-60, 61, 1.0)
        a = analyze_cut(theta, -3.0 * (theta / 15.0) ** 2)
        assert a.hpbw == pytest.approx(30.0, abs=0.1)
        assert a.sidelobe_level is None and a.null_depth is None

    def test_nan_and_short_traces(self):
        from antenna_pattern_viewer.pattern_markers import analyze_cut

        theta, y = synthetic_cut()
        y = y.copy(); y[::7] = np.nan
        assert analyze_cut(theta, y).hpbw == pytest.approx(20.0, abs=0.6)
        assert analyze_cut([0, 1], [1, 2]) is None

    def test_summary_text(self):
        from antenna_pattern_viewer.pattern_markers import analyze_cut

        text = analyze_cut(*synthetic_cut()).summary()
        assert 'HPBW 20.0°' in text and 'SLL -18.0 dB' in text


class TestMarkersInWidget:
    def test_markers_annotate_co_pol_only_and_leave_export_alone(self, widget, qapp):
        widget.update_plot(pattern=make_pattern(), **COMMON)
        lines = len(widget.figure.axes[0].get_lines())
        widget.markers_check.setChecked(True)
        qapp.processEvents()
        assert widget._marker_artists                      # something was drawn
        assert len(widget.figure.axes[0].get_lines()) == lines
        assert len(widget.get_plotted_data()[2]) == lines
        text = widget.readout_label.text()
        assert widget.readout_label.isVisible()
        assert 'φ=0.0°: peak' in text and 'cross' not in text

    def test_markers_survive_a_replot_and_clear_when_off(self, widget, qapp):
        widget.update_plot(pattern=make_pattern(), **COMMON)
        widget.markers_check.setChecked(True)
        widget.update_plot(pattern=make_pattern(beam_deg=10.0), **COMMON)
        assert widget._marker_artists and widget._marker_artists[0].axes is widget.figure.axes[0]
        widget.markers_check.setChecked(False)
        qapp.processEvents()
        assert widget._marker_artists == [] and not widget.readout_label.isVisible()

    def test_not_on_phase_or_polar(self, widget, qapp):
        widget.update_plot(pattern=make_pattern(), **dict(COMMON, value_type='phase'))
        widget.markers_check.setChecked(True)
        qapp.processEvents()
        assert widget._marker_artists == []
        widget.update_plot(pattern=make_pattern(), frequencies=[8e9], phi_angles=[0.0], value_type='gain',
                           show_cross_pol=False, unwrap_phase=True, plot_format='2d_polar',
                           component='e_co', pattern_key='k')
        assert not widget.markers_check.isVisible() and widget._marker_artists == []


def _event(widget, name, index, trace=0, button=None):
    ax = widget.figure.axes[0]
    line = ax.get_lines()[trace]
    x, y = ax.transData.transform((line.get_xdata()[index], line.get_ydata()[index]))
    return MouseEvent(name, widget.canvas, x, y, button=button)


class TestCursors:
    def test_hover_reports_the_nearest_sample(self, widget, qapp):
        widget.update_plot(pattern=make_pattern(), **COMMON)
        widget.cursors_check.setChecked(True)
        widget.cursors._on_motion(_event(widget, 'motion_notify_event', 5))
        line = widget.figure.axes[0].get_lines()[0]
        tip = widget.cursors._hover[1].get_text()
        assert line.get_label() in tip
        assert f"θ = {line.get_xdata()[5]:.2f}°" in tip

    def test_two_clicks_give_a_delta_and_right_click_clears(self, widget, qapp):
        widget.update_plot(pattern=make_pattern(), **COMMON)
        widget.cursors_check.setChecked(True)
        widget.cursors._on_click(_event(widget, 'button_press_event', 4, button=MouseButton.LEFT))
        widget.cursors._on_click(_event(widget, 'button_press_event', 10, button=MouseButton.LEFT))
        qapp.processEvents()
        line = widget.figure.axes[0].get_lines()[0]
        x, y = line.get_xdata(), line.get_ydata()
        text = widget.cursors.delta_text()
        assert f"Δθ = {x[10] - x[4]:.2f}°" in text
        assert f"Δ = {y[10] - y[4]:.2f}" in text
        assert 'Δθ' in widget.readout_label.text()
        assert len(widget.figure.axes[0].get_lines()) == 4     # cursors are not traces
        widget.cursors._on_click(_event(widget, 'button_press_event', 4, button=MouseButton.RIGHT))
        assert widget.cursors.pinned() == [] and widget.cursors._pinned_artists == []

    def test_pinned_cursors_survive_a_replot(self, widget, qapp):
        widget.update_plot(pattern=make_pattern(), **COMMON)
        widget.cursors_check.setChecked(True)
        widget.cursors._on_click(_event(widget, 'button_press_event', 4, button=MouseButton.LEFT))
        widget.update_plot(pattern=make_pattern(beam_deg=10.0), **COMMON)
        assert len(widget.cursors.pinned()) == 1
        assert widget.cursors._pinned_artists[0].axes is widget.figure.axes[0]

    def test_disabled_by_the_polar_view_and_restored(self, widget, qapp):
        widget.update_plot(pattern=make_pattern(), **COMMON)
        widget.cursors_check.setChecked(True)
        assert widget.cursors.enabled
        widget.update_plot(pattern=make_pattern(), frequencies=[8e9], phi_angles=[0.0], value_type='gain',
                           show_cross_pol=False, unwrap_phase=True, plot_format='2d_polar',
                           component='e_co', pattern_key='k')
        assert not widget.cursors.enabled and not widget.cursors_check.isVisible()
        widget.update_plot(pattern=make_pattern(), **COMMON)
        assert widget.cursors.enabled

    def test_toolbar_mode_blocks_clicks(self, widget, qapp, monkeypatch):
        widget.update_plot(pattern=make_pattern(), **COMMON)
        widget.cursors_check.setChecked(True)
        monkeypatch.setattr(type(widget.toolbar), 'mode', property(lambda self: 'zoom rect'), raising=False)
        widget.cursors._on_click(_event(widget, 'button_press_event', 4, button=MouseButton.LEFT))
        assert widget.cursors.pinned() == []
