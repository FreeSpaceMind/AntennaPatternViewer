"""
The view must survive a processing step.

Every processing toggle rebuilds the pattern, and the view panel repopulates
its frequency and phi lists from the new grids. Two regressions came from
that: the repopulation announced itself before the previous selection was
restored, so listeners replotted a single cut; and the saved axis limits were
keyed to the pattern object, which is new after every step, so the axes
rescaled. Both made an A/B comparison of a step impossible.
"""
import numpy as np
import pytest

from .conftest import make_pattern


@pytest.fixture
def app_widget(qapp):
    from antenna_pattern_viewer.antenna_pattern_widget import AntennaPatternWidget

    widget = AntennaPatternWidget()
    widget.resize(1000, 700)
    widget.data_model.set_pattern(make_pattern())
    qapp.processEvents()
    return widget, qapp


def _plot_widget(widget):
    from antenna_pattern_viewer.widgets.plot_widget import PlotWidget

    return widget.findChild(PlotWidget)


class TestSelectionSurvivesProcessing:
    def test_all_cuts_stay_plotted(self, app_widget):
        widget, qapp = app_widget
        panel = widget.left_panel.view_panel
        plot = _plot_widget(widget)

        panel.phi_list.selectAll()
        qapp.processEvents()
        selected = len(panel.get_selected_phi_angles())
        lines = len(plot.figure.axes[0].get_lines())
        assert selected > 1 and lines > 1

        widget.data_model.set_mars(0.05, taper=0)
        qapp.processEvents()

        assert len(panel.get_selected_phi_angles()) == selected
        assert len(plot.figure.axes[0].get_lines()) == lines

    def test_selection_survives_disabling_too(self, app_widget):
        widget, qapp = app_widget
        panel = widget.left_panel.view_panel
        plot = _plot_widget(widget)
        panel.phi_list.selectAll()
        qapp.processEvents()
        lines = len(plot.figure.axes[0].get_lines())

        for state in (dict(max_extent=0.05, taper=0), dict(max_extent=0.05, taper=5), None):
            if state is None:
                widget.data_model.set_mars(None)
            else:
                widget.data_model.set_mars(state['max_extent'], taper=state['taper'])
            qapp.processEvents()
            assert len(plot.figure.axes[0].get_lines()) == lines

    def test_a_smaller_grid_keeps_the_nearest_cuts(self, app_widget):
        """A coordinate-format change halves the phi range; the selection is
        re-applied by nearest value rather than reset."""
        widget, qapp = app_widget
        panel = widget.left_panel.view_panel
        panel.phi_list.selectAll()
        qapp.processEvents()

        widget.data_model.set_coordinate_format('central')
        qapp.processEvents()
        selected = panel.get_selected_phi_angles()
        available = set(np.asarray(widget.data_model.pattern.phi_angles, dtype=float))
        assert selected, "the selection was emptied"
        assert set(np.asarray(selected, dtype=float)) <= available


class TestAxisLimitsSurviveProcessing:
    def test_limits_are_kept_when_only_the_processing_changed(self, qapp):
        from antenna_pattern_viewer.widgets.plot_widget import PlotWidget

        plot = PlotWidget()
        common = dict(frequencies=[8e9], phi_angles=[0.0, 45.0], value_type='gain',
                      show_cross_pol=False, unwrap_phase=True, plot_format='1d_cut',
                      component='e_co', pattern_key='instance-1')
        plot.update_plot(pattern=make_pattern(), **common)
        plot.figure.axes[0].set_ylim(-40.0, 5.0)

        # A processing step hands over a different object for the same instance.
        plot.update_plot(pattern=make_pattern(beam_deg=5.0), **common)
        assert plot.figure.axes[0].get_ylim() == pytest.approx((-40.0, 5.0))

    def test_limits_are_dropped_when_the_instance_changes(self, qapp):
        from antenna_pattern_viewer.widgets.plot_widget import PlotWidget

        plot = PlotWidget()
        common = dict(frequencies=[8e9], phi_angles=[0.0, 45.0], value_type='gain',
                      show_cross_pol=False, unwrap_phase=True, plot_format='1d_cut',
                      component='e_co')
        plot.update_plot(pattern=make_pattern(), pattern_key='instance-1', **common)
        plot.figure.axes[0].set_ylim(-40.0, 5.0)

        plot.update_plot(pattern=make_pattern(beam_deg=5.0), pattern_key='instance-2', **common)
        assert plot.figure.axes[0].get_ylim() != pytest.approx((-40.0, 5.0))

    def test_the_widget_supplies_a_key_that_survives_processing(self, qapp):
        """plot_2d_widget must key on the loaded instance, not the object."""
        from antenna_pattern_viewer.widgets.plot_2d_widget import Plot2DWidget
        from antenna_pattern_viewer.data_model import PatternDataModel

        model = PatternDataModel()
        widget = Plot2DWidget(model)
        model.set_pattern(make_pattern())
        first = widget._active_pattern_key()
        model.set_mars(0.05, taper=0)
        assert widget._active_pattern_key() == first
