"""
Plot styling: the model, its application to a drawn axes, the live dialog,
per-trace overrides that survive a replot, persistence and figure export.
"""
import json

import matplotlib
import numpy as np
import pytest

from .conftest import make_pattern


@pytest.fixture
def widget(qapp, tmp_path, monkeypatch):
    """A PlotWidget whose settings live in a temporary INI file."""
    from PyQt6.QtCore import QSettings
    from antenna_pattern_viewer.widgets.plot_widget import PlotWidget

    monkeypatch.setattr(PlotWidget, '_settings',
                        lambda self: QSettings(str(tmp_path / 'style.ini'), QSettings.Format.IniFormat))
    return PlotWidget()


COMMON = dict(frequencies=[8e9], phi_angles=[0.0, 45.0], value_type='gain', show_cross_pol=True,
              unwrap_phase=True, plot_format='1d_cut', component='e_co', pattern_key='k')


class TestModel:
    def test_round_trip_through_json(self):
        from antenna_pattern_viewer.plot_style import PlotStyle, SeriesStyle

        style = PlotStyle(title='T', tick_size=9.0, dark=True, legend_loc='upper left',
                          series={'φ=0.0°': SeriesStyle(color='#ff0000', linewidth=2.5, label='Main')})
        again = PlotStyle.from_json(style.to_json())
        assert again == style
        assert json.loads(style.to_json())['series']['φ=0.0°']['color'] == '#ff0000'

    def test_unknown_keys_are_ignored(self):
        from antenna_pattern_viewer.plot_style import PlotStyle

        style = PlotStyle.from_dict({'title': 'x', 'not_a_field': 1, 'series': {'a': {'bogus': 2}}})
        assert style.title == 'x' and 'a' in style.series

    def test_presets_build(self):
        from antenna_pattern_viewer.plot_style import PRESETS, preset

        for name in PRESETS:
            assert preset(name) is not None
        assert preset('Publication').font_family == 'serif'
        assert preset('Dark').dark

    def test_cycle_colors(self):
        from antenna_pattern_viewer.plot_style import cycle_colors

        assert cycle_colors('default', 5) is None
        assert len(cycle_colors('tab10', 12)) == 12
        cont = cycle_colors('viridis', 4)
        assert len(cont) == 4 and cont[0] != cont[-1]


class TestApplyStyle:
    def _axes(self):
        from matplotlib.figure import Figure

        fig = Figure()
        ax = fig.add_subplot(111)
        x = np.linspace(-90, 90, 50)
        ax.plot(x, np.cos(np.radians(x)), label='co')
        ax.plot(x, 0.1 * np.cos(np.radians(x)), label='cx')
        ax.set_title('default title'); ax.set_xlabel('x'); ax.set_ylabel('y')
        ax.legend(); ax.grid(True)
        return fig, ax

    def test_none_leaves_defaults(self):
        from antenna_pattern_viewer.plot_style import PlotStyle, apply_style

        fig, ax = self._axes()
        apply_style(fig, ax, PlotStyle())
        assert ax.get_title() == 'default title' and ax.get_xlabel() == 'x'

    def test_text_fonts_ticks_and_legend(self):
        from antenna_pattern_viewer.plot_style import PlotStyle, apply_style

        fig, ax = self._axes()
        apply_style(fig, ax, PlotStyle(title='T', xlabel='X', ylabel='Y', title_size=20, label_size=15,
                                       tick_size=7, x_tick_step=30, legend_loc='upper left',
                                       legend_columns=2, legend_frame=False, line_width=3.0))
        assert (ax.get_title(), ax.get_xlabel(), ax.get_ylabel()) == ('T', 'X', 'Y')
        assert ax.title.get_fontsize() == 20 and ax.xaxis.label.get_fontsize() == 15
        assert ax.get_xticklabels()[0].get_fontsize() == 7
        assert np.allclose(np.diff(ax.get_xticks()), 30)
        legend = ax.get_legend()
        assert legend._ncols == 2 and not legend.get_frame_on()
        assert {line.get_linewidth() for line in ax.get_lines()} == {3.0}

    def test_dark_mode(self):
        from antenna_pattern_viewer.plot_style import PlotStyle, apply_style

        fig, ax = self._axes()
        apply_style(fig, ax, PlotStyle(dark=True))
        assert ax.get_facecolor()[:3] != (1.0, 1.0, 1.0)
        assert matplotlib.colors.to_hex(ax.title.get_color()) != '#000000'

    def test_series_override_keyed_by_label(self):
        from antenna_pattern_viewer.plot_style import PlotStyle, SeriesStyle, apply_style

        fig, ax = self._axes()
        style = PlotStyle(series={'cx': SeriesStyle(color='#00ff00', linewidth=4.0, linestyle='--',
                                                    label='cross-pol')})
        apply_style(fig, ax, style, legend_visible=True)
        co, cx = ax.get_lines()
        assert matplotlib.colors.to_hex(cx.get_color()) == '#00ff00'
        assert cx.get_linewidth() == 4.0 and cx.get_linestyle() == '--'
        assert co.get_linewidth() != 4.0
        assert [t.get_text() for t in ax.get_legend().get_texts()] == ['co', 'cross-pol']

    def test_hidden_series_leaves_the_legend(self):
        from antenna_pattern_viewer.plot_style import PlotStyle, SeriesStyle, apply_style

        fig, ax = self._axes()
        apply_style(fig, ax, PlotStyle(series={'cx': SeriesStyle(visible=False)}), legend_visible=True)
        assert not ax.get_lines()[1].get_visible()
        assert [t.get_text() for t in ax.get_legend().get_texts()] == ['co']

    def test_bad_colour_does_not_raise_in_widget(self, widget):
        from antenna_pattern_viewer.plot_style import PlotStyle, SeriesStyle

        widget.update_plot(pattern=make_pattern(), **COMMON)
        widget.set_style(PlotStyle(series={'φ=0.0°': SeriesStyle(color='not a colour')}))
        assert widget.figure.axes            # still drawn


class TestWidget:
    def test_style_survives_a_replot(self, widget):
        from antenna_pattern_viewer.plot_style import PlotStyle, SeriesStyle

        widget.update_plot(pattern=make_pattern(), **COMMON)
        widget.set_style(PlotStyle(title='Kept', series={'φ=0.0°': SeriesStyle(linewidth=3.5, label='Main')}))
        widget.update_plot(pattern=make_pattern(beam_deg=10.0), **COMMON)     # a processing step
        ax = widget.figure.axes[0]
        assert ax.get_title() == 'Kept'
        assert ax.get_lines()[0].get_linewidth() == 3.5
        assert ax.get_legend().get_texts()[0].get_text() == 'Main'

    def test_auto_restores_the_default_text(self, widget):
        from antenna_pattern_viewer.plot_style import PlotStyle

        widget.update_plot(pattern=make_pattern(), **COMMON)
        default = widget.figure.axes[0].get_title()
        widget.set_style(PlotStyle(title='Custom'))
        assert widget.figure.axes[0].get_title() == 'Custom'
        widget.set_style(PlotStyle())
        assert widget.figure.axes[0].get_title() == default

    def test_axis_limits_survive_a_style_change(self, widget):
        from antenna_pattern_viewer.plot_style import PlotStyle

        widget.update_plot(pattern=make_pattern(), **COMMON)
        widget.figure.axes[0].set_ylim(-50.0, 5.0)
        widget.set_style(PlotStyle(title='x'))
        assert widget.figure.axes[0].get_ylim() == pytest.approx((-50.0, 5.0))

    def test_colour_cycle_is_used_when_drawing(self, widget):
        from antenna_pattern_viewer.plot_style import PlotStyle

        widget.update_plot(pattern=make_pattern(), **COMMON)
        before = [matplotlib.colors.to_hex(l.get_color()) for l in widget.figure.axes[0].get_lines()]
        widget.set_style(PlotStyle(color_cycle='Dark2'))
        after = [matplotlib.colors.to_hex(l.get_color()) for l in widget.figure.axes[0].get_lines()]
        assert after != before

    def test_styles_are_per_format_and_persist(self, widget, qapp, tmp_path, monkeypatch):
        from PyQt6.QtCore import QSettings
        from antenna_pattern_viewer.plot_style import PlotStyle
        from antenna_pattern_viewer.widgets.plot_widget import PlotWidget

        widget.set_style(PlotStyle(title='cut'), '1d_cut')
        widget.set_style(PlotStyle(colorbar_label='cb'), '2d_polar')
        fresh = PlotWidget()          # same temporary INI via the fixture's monkeypatch
        assert fresh.styles['1d_cut'].title == 'cut'
        assert fresh.styles['2d_polar'].colorbar_label == 'cb'
        assert fresh.styles['2d_polar'].title is None

    def test_dialog_edits_apply_live(self, widget, qapp):
        widget.update_plot(pattern=make_pattern(), **COMMON)
        widget.open_style_dialog()
        dialog = widget.style_dialog
        dialog.title_edit.setText('From dialog')
        dialog.title_edit.editingFinished.emit()
        dialog.legend_loc.setCurrentText('lower right')
        qapp.processEvents()
        ax = widget.figure.axes[0]
        assert ax.get_title() == 'From dialog'
        assert widget.current_style().legend_loc == 'lower right'
        # the Series tab lists the traces on screen
        rows = [dialog.series_table.item(r, 0).text() for r in range(dialog.series_table.rowCount())]
        assert rows == [l.get_label() for l in ax.get_lines()]

    def test_series_table_edit_applies_and_persists(self, widget, qapp):
        widget.update_plot(pattern=make_pattern(), **COMMON)
        widget.open_style_dialog()
        dialog = widget.style_dialog
        dialog.series_table.item(1, 3).setText('4')          # width of the second trace
        qapp.processEvents()
        assert widget.figure.axes[0].get_lines()[1].get_linewidth() == 4.0
        label = dialog.series_table.item(1, 0).text()
        assert widget.current_style().series[label].linewidth == 4.0

    def test_preset_keeps_series_overrides(self, widget, qapp):
        from antenna_pattern_viewer.plot_style import PlotStyle, SeriesStyle

        widget.update_plot(pattern=make_pattern(), **COMMON)
        widget.set_style(PlotStyle(series={'φ=0.0°': SeriesStyle(color='#123456')}))
        widget.open_style_dialog()
        widget.style_dialog.preset_combo.setCurrentText('Presentation')
        widget.style_dialog.apply_preset_btn.click()
        qapp.processEvents()
        assert widget.current_style().title_size == 18.0
        assert widget.current_style().series['φ=0.0°'].color == '#123456'


class TestExport:
    def test_export_dialog_writes_at_the_requested_size(self, widget, tmp_path):
        from antenna_pattern_viewer.dialogs.export_figure_dialog import ExportFigureDialog, save_figure

        widget.update_plot(pattern=make_pattern(), **COMMON)
        original = tuple(widget.figure.get_size_inches())
        dialog = ExportFigureDialog(widget.figure)
        dialog.path_edit.setText(str(tmp_path / 'figure'))
        dialog.format_combo.setCurrentText('SVG (vector) (*.svg)')
        dialog.width_spin.setValue(6.5)
        dialog.height_spin.setValue(4.0)
        options = dialog.options()
        assert options['path'].endswith('.svg') and options['size'] == (6.5, 4.0)
        save_figure(widget.figure, options)
        assert (tmp_path / 'figure.svg').stat().st_size > 1000
        assert tuple(widget.figure.get_size_inches()) == original
