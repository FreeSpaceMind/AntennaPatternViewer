"""
Headless tests for PatternDataModel: the processing pipeline and the
instance lifecycle. No display or data files are required.
"""
import numpy as np
import pytest

from antenna_pattern_viewer.data_model import PatternDataModel, default_processing_state
from .conftest import make_pattern, FREQS


class TestProcessingPipeline:
    def test_processing_starts_from_the_original(self, model, pattern):
        """Every toggle rebuilds from the original, so steps do not stack."""
        model.set_pattern(pattern)
        model.set_amplitude_normalization('peak')
        first = model.pattern.data.e_co.values.copy()
        model.set_amplitude_normalization('peak')
        np.testing.assert_allclose(model.pattern.data.e_co.values, first)

    def test_polarization_survives_another_toggle(self, model, pattern):
        """Polarization used to be written straight into the model's pattern,
        so the next processing toggle rebuilt from the original and silently
        reverted it."""
        model.set_pattern(pattern)
        model.set_polarization('rhcp')
        assert model.pattern.polarization == 'rhcp'
        model.set_mars(None)
        model.set_coordinate_format('central')
        assert model.pattern.polarization == 'rhcp'

    def test_polarization_none_keeps_the_file_value(self, model, pattern):
        model.set_pattern(pattern)
        model.set_polarization('rhcp')
        model.set_polarization(None)
        assert model.pattern.polarization == 'x'

    def test_rotation_runs_after_measurement_corrections(self, model):
        """A squinted beam, corrected onto boresight and then rotated, ends up
        at exactly the rotation angle: the correction runs in the measurement
        frame and the rotation afterwards."""
        theta = np.arange(0, 181, 1.0)
        phi = np.arange(0, 360, 10.0)
        squint = np.radians(3.0)
        # angle between each direction and an axis tilted by `squint` toward +x
        axis = np.array([np.sin(squint), 0.0, np.cos(squint)])
        th = np.radians(theta)[:, None]
        ph = np.radians(phi)[None, :]
        r = np.stack([np.sin(th) * np.cos(ph) * np.ones_like(ph),
                      np.sin(th) * np.sin(ph) * np.ones_like(ph),
                      np.cos(th) * np.ones_like(ph)], axis=-1)
        ang = np.arccos(np.clip(r @ axis, -1, 1))
        beam = np.exp(-(ang / np.radians(12.0)) ** 2)[None]

        from farfield_spherical import FarFieldSpherical
        p = FarFieldSpherical(theta, phi, FREQS[:1], beam,
                              np.zeros_like(beam), polarization='x')
        model.set_pattern(p)

        def peak():
            mag = np.abs(model.pattern.data.e_co.values[0])
            i, j = np.unravel_index(np.argmax(mag), mag.shape)
            return model.pattern.theta_angles[i], model.pattern.phi_angles[j]

        assert peak()[0] == pytest.approx(3.0, abs=1.0)

        model.set_theta_origin_shift(3.0)
        assert peak()[0] == pytest.approx(0.0, abs=1.0)

        model.set_rotation((30.0, 0.0, 0.0, 'linear'))
        theta_peak, phi_peak = peak()
        assert theta_peak == pytest.approx(30.0, abs=1.0)
        assert phi_peak == pytest.approx(0.0, abs=10.0)

    def test_failed_step_rolls_back_and_reports(self, model, pattern, qapp):
        """A step that raises used to stay set, so every later toggle raised
        too and the panel appeared dead."""
        messages = []
        model.processing_failed.connect(messages.append)
        model.set_pattern(pattern)
        model.set_coordinate_format('bogus')   # transform_coordinates raises
        assert messages, "processing_failed was not emitted"
        assert model._processing_state['coordinate_format'] is None
        # the model still holds a usable pattern and later steps still work
        assert model.pattern is not None
        model.set_amplitude_normalization('peak')
        assert model.pattern is not None

    def test_pattern_modified_is_emitted(self, model, pattern):
        seen = []
        model.pattern_modified.connect(seen.append)
        model.set_pattern(pattern)
        model.set_coordinate_format('central')
        assert len(seen) == 1
        assert seen[0].theta_angles.min() < 0

    def test_set_pattern_resets_processing_state(self, model, pattern):
        model.set_pattern(pattern)
        model.set_coordinate_format('central')
        model.set_pattern(make_pattern())
        assert model._processing_state == default_processing_state()


class TestInstanceLifecycle:
    def test_removing_the_last_instance_clears_the_model(self, model, instance_factory):
        """remove_instance computed the remaining ids before deleting, so it
        re-activated the instance it was deleting and left the model pointing
        at a pattern that was no longer in the list."""
        inst = instance_factory("only")
        model.add_instance(inst)
        loaded = []
        model.pattern_loaded.connect(loaded.append)

        model.remove_instance(inst.instance_id)

        assert model.get_all_instances() == []
        assert model.get_active_instance() is None
        assert model.pattern is None
        assert model.original_pattern is None
        assert loaded and loaded[-1] is None

    def test_removing_the_active_instance_activates_another(self, model, instance_factory):
        a, b = instance_factory("a"), instance_factory("b")
        model.add_instance(a)
        model.add_instance(b)
        model.set_active_instance(a.instance_id)
        model.remove_instance(a.instance_id)
        assert model.get_active_instance() is b
        assert model.pattern is not None

    def test_removing_an_inactive_instance_keeps_the_active_one(self, model, instance_factory):
        a, b = instance_factory("a"), instance_factory("b")
        model.add_instance(a)
        model.add_instance(b)
        model.set_active_instance(a.instance_id)
        model.remove_instance(b.instance_id)
        assert model.get_active_instance() is a

    def test_unknown_instance_id_is_ignored(self, model, instance_factory):
        model.add_instance(instance_factory("a"))
        model.set_active_instance("does-not-exist")   # must not raise
        model.remove_instance("does-not-exist")
        assert len(model.get_all_instances()) == 1

    def test_processing_is_kept_per_instance(self, model, instance_factory):
        """Switching away and back used to discard everything applied."""
        a, b = instance_factory("a"), instance_factory("b")
        model.add_instance(a)
        model.add_instance(b)

        model.set_active_instance(a.instance_id)
        model.set_coordinate_format('central')
        assert model.pattern.theta_angles.min() < 0

        model.set_active_instance(b.instance_id)
        assert model.pattern.theta_angles.min() >= 0

        model.set_active_instance(a.instance_id)
        assert model._processing_state['coordinate_format'] == 'central'
        assert model.pattern.theta_angles.min() < 0

    def test_view_params_are_restored_on_switch(self, model, instance_factory):
        """set_pattern clears the selections, so restoring them before it ran
        threw them away."""
        a, b = instance_factory("a"), instance_factory("b")
        model.add_instance(a)
        model.add_instance(b)
        model.set_active_instance(a.instance_id)
        model.update_view_params({'selected_frequencies': [FREQS[1]]})

        model.set_active_instance(b.instance_id)
        model.set_active_instance(a.instance_id)
        assert model.get_view_param('selected_frequencies') == [FREQS[1]]

    def test_pattern_loaded_is_emitted_once_per_switch(self, model, instance_factory):
        """It used to be emitted by set_pattern and again by the caller, so
        every listener ran twice."""
        a, b = instance_factory("a"), instance_factory("b")
        model.add_instance(a)
        model.add_instance(b)
        model.set_active_instance(a.instance_id)

        seen = []
        model.pattern_loaded.connect(seen.append)
        model.set_active_instance(b.instance_id)
        assert len(seen) == 1

    def test_clone_does_not_share_the_pattern(self, instance_factory):
        original = instance_factory("a")
        clone = original.clone()
        assert clone.pattern is not original.pattern
        clone.pattern.assign_polarization('rhcp')
        assert original.pattern.polarization == 'x'


class TestComparison:
    def test_comparison_order_is_stable(self, model, instance_factory):
        """The set was unordered, so plot colours reshuffled between redraws."""
        ids = []
        for name in "abcd":
            inst = instance_factory(name)
            model.add_instance(inst)
            ids.append(inst.instance_id)
        for iid in ids:
            model.add_to_comparison(iid)
        order = [i.instance_id for i in model.get_comparison_instances()]
        assert order == ids
        for _ in range(5):
            assert [i.instance_id for i in model.get_comparison_instances()] == ids

    def test_comparison_uses_each_instance_processed_pattern(self, model, instance_factory):
        """A comparison curve used to be the raw pattern while the same file,
        when active, plotted processed."""
        a, b = instance_factory("a"), instance_factory("b")
        model.add_instance(a)
        model.add_instance(b)
        model.set_active_instance(a.instance_id)
        model.set_coordinate_format('central')

        model.set_active_instance(b.instance_id)
        assert model.get_instance_pattern(a).theta_angles.min() < 0
        assert model.get_instance_pattern(b).theta_angles.min() >= 0

    def test_compatibility_tolerates_float_noise(self, model, instance_factory):
        """Exact float equality reported 0 common frequencies for patterns that
        are physically identical."""
        a = instance_factory("a")
        jittered = make_pattern(freqs=FREQS + np.array([1e-3, -1e-3]))
        b = instance_factory("b")
        b.pattern = jittered
        model.add_instance(a)
        model.add_instance(b)
        model.set_active_instance(a.instance_id)
        model.add_to_comparison(b.instance_id)

        result = model.get_comparison_compatibility()
        assert len(result['common_frequencies']) == len(FREQS)
        assert result['compatible']
