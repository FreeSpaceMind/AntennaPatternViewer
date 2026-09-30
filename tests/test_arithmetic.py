"""Pattern arithmetic: the operations, derived instances, the dialog and sessions."""
import time

import numpy as np
import pytest

from .conftest import make_pattern


class TestOperations:
    def test_ratio_of_a_pattern_with_itself_is_flat(self):
        from antenna_pattern_viewer.pattern_math import derive_pattern

        a = make_pattern()
        r = derive_pattern('ratio', a, a.copy())
        gain = 20 * np.log10(np.abs(r.data.e_co.values))
        # where the field is essentially zero the library keeps A rather than dividing
        meaningful = np.abs(a.data.e_co.values) > 1e-12
        np.testing.assert_allclose(gain[meaningful], 0.0, atol=1e-4)

    def test_ratio_is_the_gain_difference(self):
        from antenna_pattern_viewer.pattern_math import derive_pattern

        a, b = make_pattern(beam_deg=20.0), make_pattern(beam_deg=10.0)
        r = derive_pattern('ratio', a, b)
        expected = 20 * np.log10(np.abs(a.data.e_co.values)) - 20 * np.log10(np.abs(b.data.e_co.values))
        got = 20 * np.log10(np.abs(r.data.e_co.values))
        finite = np.isfinite(expected) & (np.abs(b.data.e_co.values) > 1e-6)
        np.testing.assert_allclose(got[finite], expected[finite], atol=1e-3)

    def test_gain_difference_has_zero_phase(self):
        from antenna_pattern_viewer.pattern_math import derive_pattern

        a, b = make_pattern(beam_deg=20.0), make_pattern(beam_deg=10.0)
        g = derive_pattern('gain_difference', a, b)
        assert np.allclose(np.angle(g.data.e_co.values), 0.0, atol=1e-6)
        r = derive_pattern('ratio', a, b)
        np.testing.assert_allclose(np.abs(g.data.e_co.values), np.abs(r.data.e_co.values), rtol=1e-5)

    def test_sum_and_difference(self):
        from antenna_pattern_viewer.pattern_math import derive_pattern

        a, b = make_pattern(beam_deg=20.0), make_pattern(beam_deg=10.0)
        s, d = derive_pattern('sum', a, b), derive_pattern('difference', a, b)
        np.testing.assert_allclose(s.data.e_theta.values, a.data.e_theta.values + b.data.e_theta.values, atol=1e-6)
        np.testing.assert_allclose(d.data.e_phi.values, a.data.e_phi.values - b.data.e_phi.values, atol=1e-6)
        assert s.polarization == a.polarization

    def test_mismatched_grids_and_unknown_op(self):
        from antenna_pattern_viewer.pattern_math import derive_pattern

        a, b = make_pattern(), make_pattern(theta=np.arange(0, 181, 10.0))
        with pytest.raises(ValueError, match='theta grids'):
            derive_pattern('sum', a, b)
        with pytest.raises(ValueError, match='Unknown operation'):
            derive_pattern('nope', a, a)

    def test_names(self):
        from antenna_pattern_viewer.pattern_math import derived_name

        assert derived_name('ratio', 'a.ffd', 'b.ffd') == 'a.ffd / b.ffd'
        assert derived_name('gain_difference', 'a', 'b') == '|a / b|'
        assert derived_name('difference', 'a', 'b') == 'a − b'


class TestDerivedInstances:
    def test_added_from_processed_inputs(self, qapp, model, instance_factory):
        a, b = instance_factory('a.ffd'), instance_factory('b.ffd', beam_deg=10.0)
        model.add_instance(a)
        model.add_instance(b)
        model.set_mars(0.05, taper=0)          # processing on the active (a)
        derived = model.add_derived_instance('ratio', a.instance_id, b.instance_id)
        assert derived.display_name == 'a.ffd / b.ffd'
        assert derived.source_file is None and derived.derived_from['op'] == 'ratio'
        assert derived.instance_id in [i.instance_id for i in model.get_all_instances()]
        # the input was a's processed pattern, not its raw one
        assert model.get_instance_pattern(a).metadata['operations'][-1]['type'] == 'apply_mars'

    def test_dialog_choice_and_auto_name(self, qapp, instance_factory):
        from antenna_pattern_viewer.dialogs.arithmetic_dialog import ArithmeticDialog

        a, b = instance_factory('a.ffd'), instance_factory('b.ffd')
        dialog = ArithmeticDialog([a, b], default_a=a.instance_id)
        op, a_id, b_id, name = dialog.choice()
        assert (op, a_id, b_id, name) == ('ratio', a.instance_id, b.instance_id, 'a.ffd / b.ffd')
        dialog.op_combo.setCurrentIndex(2)
        assert dialog.choice()[3] == 'a.ffd − b.ffd'
        dialog.name_edit.setText('custom')
        dialog.name_edit.textEdited.emit('custom')
        dialog.op_combo.setCurrentIndex(0)
        assert dialog.choice()[3] == 'custom'


def _wait(qapp, predicate, timeout=20.0):
    start = time.time()
    while not predicate():
        qapp.processEvents()
        time.sleep(0.02)
        if time.time() - start > timeout:
            raise TimeoutError


class TestSession:
    def test_derived_pattern_is_rebuilt_on_restore(self, qapp, tmp_path, monkeypatch):
        from PyQt6.QtCore import QSettings
        from farfield_spherical import write_ffd
        from antenna_pattern_viewer.antenna_pattern_widget import AntennaPatternWidget
        from antenna_pattern_viewer.session import collect_session, read_session, restore_session, write_session
        from antenna_pattern_viewer.widgets.file_manager_widget import FileManagerWidget
        from antenna_pattern_viewer.widgets.plot_widget import PlotWidget

        monkeypatch.setattr(PlotWidget, '_settings',
                            lambda self: QSettings(str(tmp_path / 's.ini'), QSettings.Format.IniFormat))
        a_path, b_path = tmp_path / 'a.ffd', tmp_path / 'b.ffd'
        write_ffd(make_pattern(freqs=np.array([8e9, 10e9])), a_path)
        write_ffd(make_pattern(beam_deg=10.0, freqs=np.array([8e9, 10e9])), b_path)

        window = AntennaPatternWidget()
        window.show()
        fm = window.findChild(FileManagerWidget)
        done = []
        fm.load_files_with_options([(a_path, {}), (b_path, {})], on_finished=done.append)
        _wait(qapp, lambda: done)
        model = window.data_model
        a, b = model.get_all_instances()
        model.set_mars(0.05, taper=0)
        derived = model.add_derived_instance('ratio', a.instance_id, b.instance_id)
        model.add_to_comparison(derived.instance_id)
        path = write_session(tmp_path / 's', collect_session(window))

        other = AntennaPatternWidget()
        other.show()
        finished = []
        restore_session(other, read_session(path), on_done=finished.append)
        _wait(qapp, lambda: finished)
        qapp.processEvents()
        names = [i.display_name for i in other.data_model.get_all_instances()]
        assert names == ['a.ffd', 'b.ffd', 'a.ffd / b.ffd']
        rebuilt = other.data_model.get_all_instances()[2]
        assert rebuilt.derived_from == {'op': 'ratio', 'a': 'a.ffd', 'b': 'b.ffd'}
        assert [i.display_name for i in other.data_model.get_comparison_instances()] == ['a.ffd / b.ffd']
        # the rebuilt ratio used a's restored MARS state, as the original did
        np.testing.assert_allclose(np.abs(rebuilt.pattern.data.e_co.values),
                                   np.abs(derived.pattern.data.e_co.values), rtol=1e-4)
