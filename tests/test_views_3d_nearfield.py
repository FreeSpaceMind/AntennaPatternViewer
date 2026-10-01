"""The 3D view, the near-field view and the figure tools they share."""
import numpy as np
import pytest

from .conftest import make_pattern


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch):
    from PyQt6.QtCore import QSettings
    from antenna_pattern_viewer.widgets.figure_tools import FigureTools

    monkeypatch.setattr(FigureTools, '_settings',
                        classmethod(lambda cls: QSettings(str(tmp_path / 'ft.ini'), QSettings.Format.IniFormat)))


class TestSurface:
    def test_sided_and_central_give_closed_surfaces(self):
        from antenna_pattern_viewer.widgets.plot_3d_widget import pattern_surface

        for pattern in (make_pattern(), make_pattern(theta=np.arange(-180, 181, 10.0),
                                                     phi=np.arange(0, 180, 30.0))):
            x, y, z, values, (vmin, vmax) = pattern_surface(pattern, 8e9, dynamic_range=30.0)
            assert x.shape == y.shape == z.shape == values.shape
            # the phi seam is closed: first and last columns coincide
            np.testing.assert_allclose(x[:, 0], x[:, -1], atol=1e-9)
            radius = np.sqrt(x ** 2 + y ** 2 + z ** 2)
            assert radius.max() == pytest.approx(30.0, abs=1e-6)     # peak sits at the top of the range
            assert radius.min() >= 0.0
            assert vmax - vmin == pytest.approx(30.0)

    def test_phase_surface_is_a_unit_sphere(self):
        from antenna_pattern_viewer.widgets.plot_3d_widget import pattern_surface

        x, y, z, _values, rng = pattern_surface(make_pattern(), 8e9, value_type='phase')
        np.testing.assert_allclose(np.sqrt(x ** 2 + y ** 2 + z ** 2), 1.0, atol=1e-9)
        assert rng == (-180.0, 180.0)


def settle(qapp, seconds=0.2):
    """Let the 3D view's coalescing timer fire."""
    import time
    end = time.time() + seconds
    while time.time() < end:
        qapp.processEvents()
        time.sleep(0.01)


class TestPlot3DWidget:
    def test_draws_and_follows_the_view(self, qapp, model):
        from antenna_pattern_viewer.widgets.plot_3d_widget import Plot3DWidget

        widget = Plot3DWidget(model)
        widget.show()
        model.set_pattern(make_pattern(freqs=np.array([8e9, 10e9])))
        settle(qapp)
        ax = widget.figure.axes[0]
        assert ax.name == '3d' and ax.collections            # a surface was drawn
        assert widget.current_colorbar is not None
        assert '8000.0 MHz' in ax.get_title()

        model.update_view_params({'selected_frequencies': [10e9], 'component': 'e_cx'})
        settle(qapp)
        assert '10000.0 MHz' in widget.figure.axes[0].get_title()
        assert 'e_cx' in widget.figure.axes[0].get_title()

    def test_dynamic_range_and_style(self, qapp, model):
        from matplotlib.layout_engine import TightLayoutEngine
        from antenna_pattern_viewer.plot_style import PlotStyle
        from antenna_pattern_viewer.widgets.plot_3d_widget import Plot3DWidget

        widget = Plot3DWidget(model)
        widget.show()
        model.set_pattern(make_pattern())
        widget.range_spin.setValue(20.0)          # the controls redraw at once
        assert widget.figure.axes[0].get_xlim()[1] == pytest.approx(20.0, abs=1e-6)
        widget.tools.set_style(PlotStyle(title='My horn', colorbar_label='dBi custom'))
        ax = widget.figure.axes[0]
        assert ax.get_title() == 'My horn'
        assert widget.current_colorbar.ax.get_ylabel() == 'dBi custom'
        assert isinstance(widget.figure.get_layout_engine(), TightLayoutEngine)

    def test_no_pattern_shows_a_hint(self, qapp, model):
        from antenna_pattern_viewer.widgets.plot_3d_widget import Plot3DWidget

        widget = Plot3DWidget(model)
        widget.update_plot()
        assert 'Load a pattern' in widget.status.text()


class TestNearFieldWidget:
    def _data(self):
        theta = np.linspace(0, 90, 10)
        phi = np.linspace(0, 360, 13)
        T, P = np.meshgrid(np.radians(theta), np.radians(phi), indexing='ij')
        return {'is_spherical': True, 'theta': theta, 'phi': phi,
                'E_r': np.zeros_like(T), 'E_theta': np.cos(T), 'E_phi': 0.1 * np.sin(P),
                'H_r': np.zeros_like(T), 'H_theta': 0.1 * np.sin(P), 'H_phi': np.cos(T)}

    def test_style_export_and_tight_layout(self, qapp, model, tmp_path):
        from matplotlib.layout_engine import TightLayoutEngine
        from antenna_pattern_viewer.plot_style import PlotStyle
        from antenna_pattern_viewer.widgets.plot_nearfield_widget import PlotNearFieldWidget
        from antenna_pattern_viewer.dialogs.export_figure_dialog import ExportFigureDialog, save_figure

        widget = PlotNearFieldWidget(model)
        widget.plot_near_field(self._data())
        assert widget.current_colorbar is not None
        assert isinstance(widget.figure.get_layout_engine(), TightLayoutEngine)
        widget.tools.set_style(PlotStyle(title='NF custom', tick_size=6))
        ax = widget.figure.axes[0]
        assert ax.get_title() == 'NF custom'
        assert ax.get_xticklabels()[0].get_fontsize() == 6

        dialog = ExportFigureDialog(widget.figure, default_name='nf')
        dialog.path_edit.setText(str(tmp_path / 'nf'))
        save_figure(widget.figure, dialog.options())
        assert (tmp_path / 'nf.png').stat().st_size > 1000


class TestFigureTools:
    def test_style_is_remembered_per_view(self, qapp):
        from matplotlib.figure import Figure
        from antenna_pattern_viewer.plot_style import PlotStyle
        from antenna_pattern_viewer.widgets.figure_tools import FigureTools
        from PyQt6.QtWidgets import QWidget

        owner = QWidget()
        fig = Figure()
        calls = []
        tools = FigureTools(owner, fig, None, 'unit_test_view', 'Unit', lambda: calls.append(1))
        tools.set_style(PlotStyle(title='remembered'))
        assert calls == [1]
        again = FigureTools(owner, Figure(), None, 'unit_test_view', 'Unit', lambda: None)
        assert again.style.title == 'remembered'
        other = FigureTools(owner, Figure(), None, 'another_view', 'Other', lambda: None)
        assert other.style.title is None


class TestPlot3DPerformance:
    def test_hidden_view_does_not_draw_until_shown(self, qapp, model):
        from antenna_pattern_viewer.widgets.plot_3d_widget import Plot3DWidget

        widget = Plot3DWidget(model)                 # never shown
        draws = []
        original = widget.update_plot
        widget.update_plot = lambda: (draws.append(1), original())[1]
        model.set_pattern(make_pattern(freqs=np.array([8e9, 10e9])))
        for f in (8e9, 10e9, 8e9):
            model.update_view_params({'selected_frequencies': [f]})
        settle(qapp)
        assert draws == [] and widget._stale
        widget.show()
        settle(qapp)
        assert draws == [1] and not widget._stale

    def test_bursts_coalesce_into_one_draw(self, qapp, model):
        from antenna_pattern_viewer.widgets.plot_3d_widget import Plot3DWidget

        widget = Plot3DWidget(model)
        widget.show()
        model.set_pattern(make_pattern())
        settle(qapp)
        draws = []
        original = widget.update_plot
        widget.update_plot = lambda: (draws.append(1), original())[1]
        for f in (8e9, 10e9, 8e9, 10e9):
            model.update_view_params({'selected_frequencies': [f]})
        settle(qapp)
        assert draws == [1]

    def test_surface_resolution_is_capped(self):
        from antenna_pattern_viewer.widgets.plot_3d_widget import MAX_FACETS, surface_stride

        assert surface_stride((181, 361)) == 4 and surface_stride((60, 60)) == 1
        assert max(181, 361) / surface_stride((181, 361)) <= MAX_FACETS
