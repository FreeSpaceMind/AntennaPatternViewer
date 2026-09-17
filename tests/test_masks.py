"""
Specification masks: the model, CSV import, violation reporting, drawing
on the plot and the dialog.
"""
import numpy as np
import pytest
from matplotlib.figure import Figure

from .conftest import make_pattern


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


COMMON = dict(frequencies=[8e9], phi_angles=[0.0], value_type='gain', show_cross_pol=True,
              unwrap_phase=True, component='e_co', pattern_key='k', plot_format='1d_cut')


class TestModel:
    def test_curve_sorts_and_mirrors(self):
        from antenna_pattern_viewer.spec_mask import SpecMask

        mask = SpecMask(points=[(60.0, -20.0), (0.0, 5.0), (20.0, 0.0)], mirror=True)
        theta, value = mask.curve()
        assert list(theta) == [-60.0, -20.0, 0.0, 20.0, 60.0]
        assert list(value) == [-20.0, 0.0, 5.0, 0.0, -20.0]

    def test_evaluate_interpolates_and_is_nan_outside(self):
        from antenna_pattern_viewer.spec_mask import SpecMask

        mask = SpecMask(points=[(0.0, 0.0), (10.0, -10.0)])
        out = mask.evaluate([-1.0, 5.0, 10.0, 11.0])
        assert np.isnan(out[0]) and out[1] == -5.0 and out[2] == -10.0 and np.isnan(out[3])

    def test_upper_and_lower_violations(self):
        from antenna_pattern_viewer.spec_mask import SpecMask

        theta = np.arange(0, 91, 1.0)
        trace = -0.5 * theta                       # falls 0.5 dB per degree
        upper = SpecMask(kind='upper', points=[(0.0, 1.0), (90.0, -44.0)])     # 1 dB above everywhere
        assert upper.violation(theta, trace) is None
        assert upper.margin(theta, trace) == pytest.approx(1.0)
        tight = SpecMask(kind='upper', points=[(0.0, 1.0), (10.0, -20.0), (90.0, -50.0)])
        excess, at = tight.violation(theta, trace)
        assert excess == pytest.approx(15.0) and at == 10.0
        lower = SpecMask(kind='lower', points=[(0.0, -1.0), (90.0, -30.0)])
        excess, at = lower.violation(theta, trace)
        assert excess > 0 and at == 90.0

    def test_json_round_trip(self):
        from antenna_pattern_viewer.spec_mask import SpecMask, masks_from_json, masks_to_json

        masks = [SpecMask(name='a', kind='lower', points=[(0, 1), (5, 2)], mirror=True, color='#123456',
                          visible=False)]
        again = masks_from_json(masks_to_json(masks))
        assert again == masks


class TestCsv:
    @pytest.mark.parametrize('text', [
        "theta,value\n0,10\n30,-5\n90,-20\n",
        "# comment\n0;10\n30;-5\n90;-20\n",
        "0\t10\n30\t-5\n90\t-20\n",
        "0 10\n30 -5\n90 -20\n",
    ])
    def test_separators_and_headers(self, tmp_path, text):
        from antenna_pattern_viewer.spec_mask import read_mask_csv

        path = tmp_path / 'm.csv'
        path.write_text(text)
        mask = read_mask_csv(path, kind='lower', mirror=True)
        assert mask.points == [(0.0, 10.0), (30.0, -5.0), (90.0, -20.0)]
        assert mask.name == 'm' and mask.kind == 'lower' and mask.mirror

    def test_too_short_or_bad_rows(self, tmp_path):
        from antenna_pattern_viewer.spec_mask import read_mask_csv

        (tmp_path / 'one.csv').write_text("0,1\n")
        with pytest.raises(ValueError):
            read_mask_csv(tmp_path / 'one.csv')
        (tmp_path / 'bad.csv').write_text("0,1\n5,2\nx,y\n")
        with pytest.raises(ValueError):
            read_mask_csv(tmp_path / 'bad.csv')

    def test_write_then_read(self, tmp_path):
        from antenna_pattern_viewer.spec_mask import SpecMask, read_mask_csv, write_mask_csv

        mask = SpecMask(points=[(0.0, 3.5), (45.0, -12.25)])
        write_mask_csv(mask, tmp_path / 'out.csv')
        assert read_mask_csv(tmp_path / 'out.csv').points == mask.points


class TestDrawing:
    def test_draw_masks_uses_collections_and_keeps_ylim(self):
        from antenna_pattern_viewer.spec_mask import SpecMask, draw_masks

        ax = Figure().add_subplot(111)
        ax.plot([0, 90], [0, -40], label='trace')
        ax.set_ylim(-50, 5)
        artists = draw_masks(ax, [SpecMask(points=[(0, 100), (90, 100)])])   # far above the axes
        assert len(artists) == 2
        assert len(ax.get_lines()) == 1
        assert ax.get_ylim() == (-50.0, 5.0)

    def test_report_lines(self):
        from antenna_pattern_viewer.spec_mask import SpecMask, mask_report

        theta = np.arange(0, 91, 1.0)
        traces = [('co', theta, -0.5 * theta), ('cx', theta, -20 - 0.5 * theta)]
        lines = mask_report([SpecMask(name='env', points=[(0, 1), (90, -44)]),
                             SpecMask(name='tight', points=[(0, -10), (90, -60)])], traces)
        assert lines[0].startswith("Mask 'env' passed")
        # excess over the tight mask grows from 10 dB at 0 to 15 dB at 90
        assert "Mask 'tight' violated: co by 15.00 dB at θ=90.0°" in lines[1]
        assert 'cx' not in lines[1]                     # cx is below the tight mask

    def test_invisible_mask_is_skipped(self):
        from antenna_pattern_viewer.spec_mask import SpecMask, draw_masks, mask_report

        ax = Figure().add_subplot(111)
        mask = SpecMask(points=[(0, 0), (1, 0)], visible=False)
        assert draw_masks(ax, [mask]) == []
        assert mask_report([mask], [('t', [0, 1], [5, 5])]) == []


class TestInWidget:
    def test_masks_draw_report_and_stay_out_of_the_export(self, widget, qapp):
        from antenna_pattern_viewer.spec_mask import SpecMask

        widget.update_plot(pattern=make_pattern(), **COMMON)
        lines = len(widget.figure.axes[0].get_lines())
        peak = np.nanmax(widget.figure.axes[0].get_lines()[0].get_ydata())
        widget.set_masks([SpecMask(name='env', points=[(0, peak + 1), (180, peak + 1)]),
                          SpecMask(name='tight', points=[(0, peak + 1), (5, peak - 40), (180, peak - 40)])])
        qapp.processEvents()
        assert len(widget._mask_artists) == 4
        assert len(widget.figure.axes[0].get_lines()) == lines
        assert len(widget.get_plotted_data()[2]) == lines
        text = widget.readout_label.text()
        assert "Mask 'env' passed" in text and "Mask 'tight' violated" in text
        legend = [t.get_text() for t in widget.figure.axes[0].get_legend().get_texts()]
        assert 'env (max)' in legend and 'tight (max)' in legend

    def test_masks_survive_a_replot_and_clear(self, widget, qapp):
        from antenna_pattern_viewer.spec_mask import SpecMask

        widget.update_plot(pattern=make_pattern(), **COMMON)
        widget.set_masks([SpecMask(points=[(0, 50), (180, 50)])])
        widget.update_plot(pattern=make_pattern(beam_deg=10.0), **COMMON)
        assert widget._mask_artists and widget._mask_artists[0].axes is widget.figure.axes[0]
        widget.set_masks([])
        assert widget._mask_artists == [] and not widget.readout_label.isVisible()

    def test_masks_on_every_small_multiple_and_not_on_polar(self, widget):
        from antenna_pattern_viewer.spec_mask import SpecMask

        widget.update_plot(pattern=make_pattern(freqs=np.array([8e9, 10e9])),
                           **dict(COMMON, plot_format='small_multiples', frequencies=[8e9, 10e9]))
        widget.set_masks([SpecMask(points=[(0, 50), (180, 50)])])
        assert len(widget._mask_artists) == 4
        widget.update_plot(pattern=make_pattern(), **dict(COMMON, plot_format='polar_cut'))
        assert widget._mask_artists == [] and not widget.masks_btn.isVisible()

    def test_dialog_round_trip(self, widget, qapp):
        from antenna_pattern_viewer.spec_mask import SpecMask

        widget.update_plot(pattern=make_pattern(), **COMMON)
        widget.set_masks([SpecMask(name='one', points=[(0, 1), (10, 2)])])
        widget.open_mask_dialog()
        dialog = widget.mask_dialog
        assert dialog.table.rowCount() == 1
        dialog.table.item(0, 0).setText('renamed')
        qapp.processEvents()
        assert widget.masks[0].name == 'renamed'
        from PyQt6.QtCore import Qt
        dialog.table.item(0, 5).setCheckState(Qt.CheckState.Unchecked)
        qapp.processEvents()
        assert not widget.masks[0].visible and widget._mask_artists == []
