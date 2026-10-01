"""
Configurable markers: the marker sets, per-pattern overrides in a
comparison, custom angles, the dialog, the collapsible readout and the
tight layout that must survive every replot.
"""
import numpy as np
import pytest

from .conftest import make_pattern

COMMON = dict(frequencies=[8e9], phi_angles=[0.0, 90.0], value_type='gain', show_cross_pol=True,
              unwrap_phase=True, plot_format='1d_cut', component='e_co', pattern_key='k')


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


class TestConfigModel:
    def test_round_trip_and_defaults(self):
        from antenna_pattern_viewer.pattern_markers import MarkerConfig, MarkerSet

        config = MarkerConfig(default=MarkerSet(levels_db=[3.0, 10.0], custom_thetas=[-30.0, 30.0]),
                              per_pattern={'b': MarkerSet(peak=False, sidelobe=False)},
                              disabled=['c'])
        again = MarkerConfig.from_dict(config.to_dict())
        assert again == config
        assert again.for_pattern('a') is again.default
        assert again.for_pattern('b').peak is False
        assert again.for_pattern('c') is None
        assert MarkerSet.from_dict({'levels_db': []}).levels_db == [3.0]

    def test_custom_values_and_describe(self):
        from antenna_pattern_viewer.pattern_markers import (MarkerSet, analyze_cut, custom_values,
                                                            describe, levels_for)

        theta = np.arange(-90, 91, 1.0)
        y = -3.0 * (theta / 10.0) ** 2
        marker_set = MarkerSet(levels_db=[10.0], custom_thetas=[15.0, 400.0], sidelobe=False)
        metrics = analyze_cut(theta, y, levels_db=levels_for(marker_set))
        customs = custom_values(theta, y, marker_set)
        assert customs == [(15.0, pytest.approx(-6.75))]
        text = describe(metrics, marker_set, customs)
        assert 'BW10dB' in text and 'HPBW' not in text and 'θ=15°: -6.75' in text


class TestPerPatternInComparison:
    def test_lines_carry_the_pattern_name(self, widget):
        widget.update_comparison_plot([make_pattern(), make_pattern(beam_deg=10.0)], ['a', 'b'],
                                      frequencies=[8e9], phi_angles=[0.0, 90.0], value_type='gain',
                                      show_cross_pol=False)
        assert widget.pattern_names() == ['a', 'b']
        widget.update_plot(pattern=make_pattern(), pattern_name='horn.ffd', **COMMON)
        assert widget.pattern_names() == ['horn.ffd']

    def test_each_pattern_gets_its_own_markers(self, widget, qapp):
        from antenna_pattern_viewer.pattern_markers import MarkerConfig, MarkerSet

        widget.update_comparison_plot([make_pattern(), make_pattern(beam_deg=10.0)], ['a', 'b'],
                                      frequencies=[8e9], phi_angles=[0.0, 90.0], value_type='gain',
                                      show_cross_pol=False)
        widget.set_marker_config(MarkerConfig(
            default=MarkerSet(),
            per_pattern={'b': MarkerSet(peak=True, beamwidth=False, sidelobe=False,
                                        custom_thetas=[20.0])},
            disabled=[]))
        widget.markers_check.setChecked(True)
        qapp.processEvents()
        lines = widget.overlays.marker_text.splitlines()
        # a: two cuts, both marked, the second named by its pattern
        assert lines[0].startswith('a: peak') and 'HPBW' in lines[0]
        assert lines[1].startswith('a (cut 2): peak')
        # b: peak and the custom angle only
        assert lines[2].startswith('b: peak') and 'θ=20°' in lines[2] and 'HPBW' not in lines[2]

    def test_disabled_pattern_draws_nothing(self, widget, qapp):
        from antenna_pattern_viewer.pattern_markers import MarkerConfig

        widget.update_comparison_plot([make_pattern(), make_pattern(beam_deg=10.0)], ['a', 'b'],
                                      frequencies=[8e9], phi_angles=[0.0], value_type='gain',
                                      show_cross_pol=False)
        widget.set_marker_config(MarkerConfig(disabled=['a']))
        widget.markers_check.setChecked(True)
        qapp.processEvents()
        assert [l.split(':')[0] for l in widget.overlays.marker_text.splitlines()] == ['b']

    def test_markers_survive_the_dialog_closing_and_a_replot(self, widget, qapp):
        widget.update_plot(pattern=make_pattern(), pattern_name='p', **COMMON)
        widget.open_markers_dialog()
        assert widget.markers_check.isChecked()          # opening the dialog turns markers on
        widget.overlays.markers_dialog.hide()
        widget.update_plot(pattern=make_pattern(beam_deg=10.0), pattern_name='p', **COMMON)
        assert widget.overlays.marker_artists


class TestDialog:
    def test_edits_default_and_per_pattern(self, widget, qapp):
        widget.update_comparison_plot([make_pattern(), make_pattern(beam_deg=10.0)], ['a', 'b'],
                                      frequencies=[8e9], phi_angles=[0.0], value_type='gain',
                                      show_cross_pol=False)
        widget.open_markers_dialog()
        d = widget.overlays.markers_dialog
        assert [d.target_combo.itemText(i) for i in range(d.target_combo.count())][1:] == ['a', 'b']

        d.levels_edit.setText('3, 10')
        d.levels_edit.editingFinished.emit()
        assert widget.marker_config.default.levels_db == [3.0, 10.0]

        d.target_combo.setCurrentText('b')
        d.custom_edit.setText('-30 30')
        d.custom_edit.editingFinished.emit()
        assert widget.marker_config.per_pattern['b'].custom_thetas == [-30.0, 30.0]
        assert widget.marker_config.default.custom_thetas == []

        d.enabled_check.setChecked(False)
        assert 'b' in widget.marker_config.disabled
        d.reset_btn.click()
        assert 'b' not in widget.marker_config.per_pattern and 'b' not in widget.marker_config.disabled

    def test_config_is_part_of_the_strip_state(self, widget):
        from antenna_pattern_viewer.pattern_markers import MarkerConfig, MarkerSet

        widget.set_marker_config(MarkerConfig(default=MarkerSet(levels_db=[6.0])))
        state = widget.strip_state()
        assert state['marker_config']['default']['levels_db'] == [6.0]
        other = widget.__class__()
        other.apply_strip_state(state)
        assert other.marker_config.default.levels_db == [6.0]


class TestReadoutPanel:
    def test_collapses_and_reports_lines(self, qapp):
        from antenna_pattern_viewer.widgets.readout_panel import ReadoutPanel

        panel = ReadoutPanel()
        panel.setText("one\ntwo\nthree")
        assert panel.text() == "one\ntwo\nthree"
        assert panel.box.maximumHeight() == ReadoutPanel.MAX_HEIGHT
        panel.toggle.setChecked(True)
        assert not panel.box.isVisibleTo(panel) and '+2 more' in panel.toggle.text()
        panel.toggle.setChecked(False)
        assert panel.box.isVisibleTo(panel) and '3 lines' in panel.toggle.text()


class TestTightLayout:
    def test_engine_survives_every_format_and_replot(self, widget):
        from matplotlib.layout_engine import TightLayoutEngine

        for fmt in ('1d_cut', 'amp_phase', 'small_multiples', '2d_polar', 'polar_cut', 'sweep', '1d_cut'):
            kw = dict(COMMON, plot_format=fmt)
            widget.update_plot(pattern=make_pattern(freqs=np.array([8e9, 10e9])), **kw)
            assert isinstance(widget.figure.get_layout_engine(), TightLayoutEngine), fmt
        widget.update_comparison_plot([make_pattern(), make_pattern(beam_deg=10.0)], ['a', 'b'],
                                      frequencies=[8e9], phi_angles=[0.0], value_type='gain',
                                      show_cross_pol=False)
        assert isinstance(widget.figure.get_layout_engine(), TightLayoutEngine)

    def test_plotting_functions_do_not_disturb_an_engine(self):
        from matplotlib.figure import Figure
        from matplotlib.layout_engine import TightLayoutEngine
        from antenna_pattern_viewer.plotting import plot_pattern_cut

        fig = Figure(layout='tight')
        plot_pattern_cut(make_pattern(), frequency=8e9, phi=[0.0], ax=fig.add_subplot(111))
        assert isinstance(fig.get_layout_engine(), TightLayoutEngine)
        bare = Figure()
        plot_pattern_cut(make_pattern(), frequency=8e9, phi=[0.0], ax=bare.add_subplot(111))
        assert not isinstance(bare.get_layout_engine(), TightLayoutEngine)   # untouched figures still tighten once
