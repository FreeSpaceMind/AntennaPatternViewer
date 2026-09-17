"""
Session files: collect, write, read and restore through the real
application window and file loader.
"""
import json
import time

import numpy as np
import pytest

from .conftest import make_pattern


def wait_until(qapp, predicate, timeout=20.0):
    start = time.time()
    while not predicate():
        qapp.processEvents()
        time.sleep(0.02)
        if time.time() - start > timeout:
            raise TimeoutError("condition not met in time")


@pytest.fixture
def window(qapp, tmp_path, monkeypatch):
    from PyQt6.QtCore import QSettings
    from antenna_pattern_viewer.antenna_pattern_widget import AntennaPatternWidget
    from antenna_pattern_viewer.widgets.plot_widget import PlotWidget

    monkeypatch.setattr(PlotWidget, '_settings',
                        lambda self: QSettings(str(tmp_path / 's.ini'), QSettings.Format.IniFormat))
    w = AntennaPatternWidget()
    w.resize(1100, 750)
    w.show()
    return w


@pytest.fixture
def files(tmp_path):
    from farfield_spherical import write_ffd

    a, b = tmp_path / 'a.ffd', tmp_path / 'b.ffd'
    write_ffd(make_pattern(freqs=np.array([8e9, 10e9])), a)
    write_ffd(make_pattern(beam_deg=10.0, freqs=np.array([8e9, 10e9])), b)
    return a, b


def load(window, qapp, paths):
    from antenna_pattern_viewer.widgets.file_manager_widget import FileManagerWidget

    fm = window.findChild(FileManagerWidget)
    done = []
    fm.load_files_with_options([(p, {}) for p in paths], on_finished=done.append)
    wait_until(qapp, lambda: done)
    qapp.processEvents()
    return done[0]


class TestRoundTrip:
    def test_everything_comes_back(self, window, qapp, files, tmp_path):
        from antenna_pattern_viewer.antenna_pattern_widget import AntennaPatternWidget
        from antenna_pattern_viewer.plot_style import PlotStyle
        from antenna_pattern_viewer.session import (collect_session, read_session,
                                                    restore_session, write_session)
        from antenna_pattern_viewer.spec_mask import SpecMask
        from antenna_pattern_viewer.widgets.plot_widget import PlotWidget
        from antenna_pattern_viewer.widgets.view_panel import ViewPanel

        a, b = files
        loaded = load(window, qapp, [a, b])
        assert [inst.display_name for _p, inst in loaded] == ['a.ffd', 'b.ffd']
        model = window.data_model
        first, second = model.get_all_instances()

        # State worth keeping: processing on both, comparison, view, style, masks, strip
        model.set_mars(0.05, taper=3)                       # on the active (first) instance
        model.set_active_instance(second.instance_id)
        model.set_theta_origin_shift(2.0)
        model.add_to_comparison(first.instance_id)
        view = window.findChild(ViewPanel)
        view.phi_list.selectAll()
        view.set_plot_format('amp_phase')
        qapp.processEvents()
        plot = window.findChild(PlotWidget)
        plot.set_style(PlotStyle(title='Session title'), 'amp_phase')
        plot.set_masks([SpecMask(name='env', points=[(0, 5), (90, -20)], mirror=True)])
        plot.markers_check.setChecked(True)
        plot.y_theta_min_edit.setText('-45')
        qapp.processEvents()

        data = collect_session(window)
        path = write_session(tmp_path / 'one', data)
        assert path.suffix == '.apvsession'
        raw = json.loads(path.read_text())
        assert [i['display_name'] for i in raw['instances']] == ['a.ffd', 'b.ffd']
        assert raw['instances'][0]['processing_state']['mars'] == [0.05, 3]
        assert raw['instances'][1]['processing_state']['theta_origin_shift'] == 2.0
        assert raw['instances'][0]['in_comparison'] and raw['instances'][1]['active']

        # A fresh window gets it all back
        other = AntennaPatternWidget()
        other.resize(1100, 750)
        other.show()
        finished = []
        restore_session(other, read_session(path), on_done=finished.append)
        wait_until(qapp, lambda: finished)
        qapp.processEvents()
        assert finished[0] == []                         # nothing missing

        m2 = other.data_model
        r_first, r_second = m2.get_all_instances()
        assert r_first.processing_state.get('mars') == (0.05, 3)
        assert m2.get_active_instance() is r_second
        assert m2._processing_state['theta_origin_shift'] == 2.0
        assert [i.display_name for i in m2.get_comparison_instances()] == ['a.ffd']
        v2 = other.findChild(ViewPanel)
        assert v2.get_plot_format() == 'amp_phase'
        assert len(v2.get_selected_phi_angles()) == len(r_second.pattern.phi_angles)
        p2 = other.findChild(PlotWidget)
        assert p2.styles['amp_phase'].title == 'Session title'
        assert [m.name for m in p2.masks] == ['env'] and p2.masks[0].mirror
        assert p2.markers_check.isChecked()
        assert p2.y_theta_min_edit.text() == '-45'
        assert p2.current_plot_format == 'amp_phase'

    def test_missing_file_is_reported_and_skipped(self, window, qapp, files, tmp_path):
        from antenna_pattern_viewer.session import collect_session, restore_session

        a, b = files
        load(window, qapp, [a, b])
        data = collect_session(window)
        b.unlink()
        finished = []
        restore_session(window, data, on_done=finished.append)
        wait_until(qapp, lambda: finished)
        qapp.processEvents()
        assert finished[0] == [str(b)]
        assert [i.display_name for i in window.data_model.get_all_instances()] == ['a.ffd']

    def test_load_options_are_kept(self, window, qapp, tmp_path):
        """A CUT file needs a frequency range; the session must carry it so
        no dialog is needed on restore."""
        from antenna_pattern_viewer.session import collect_session
        from antenna_pattern_viewer.widgets.file_manager_widget import FileManagerWidget
        from farfield_spherical import write_cut

        pattern = make_pattern(theta=np.arange(-180, 181, 10.0), phi=np.arange(0, 180, 30.0),
                               freqs=np.array([8e9, 10e9]))
        path = tmp_path / 'c.cut'
        write_cut(pattern, path)
        fm = window.findChild(FileManagerWidget)
        done = []
        fm.load_files_with_options([(path, {'frequency_start': 8e9, 'frequency_end': 10e9})],
                                   on_finished=done.append)
        wait_until(qapp, lambda: done)
        qapp.processEvents()
        inst = window.data_model.get_all_instances()[0]
        assert inst.load_options == {'frequency_start': 8e9, 'frequency_end': 10e9}
        assert collect_session(window)['instances'][0]['load_options']['frequency_end'] == 10e9


class TestFileFormat:
    def test_read_rejects_other_json(self, tmp_path):
        from antenna_pattern_viewer.session import read_session

        (tmp_path / 'x.json').write_text('{"hello": 1}')
        with pytest.raises(ValueError):
            read_session(tmp_path / 'x.json')

    def test_read_rejects_newer_version(self, tmp_path):
        from antenna_pattern_viewer.session import SESSION_VERSION, read_session

        (tmp_path / 'x.apvsession').write_text(json.dumps({'version': SESSION_VERSION + 1, 'instances': []}))
        with pytest.raises(ValueError):
            read_session(tmp_path / 'x.apvsession')

    def test_set_processing_state_ignores_unknown_keys(self, qapp, model, pattern):
        model.set_pattern(pattern)
        model.set_processing_state({'mars': [0.1, 2], 'bogus': 1})
        assert model._processing_state['mars'] == (0.1, 2)
        assert 'bogus' not in model._processing_state
