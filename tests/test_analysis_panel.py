"""
Tests for the analysis panel's SWE controls.

A merge once kept the multi-frequency list UI and its call sites while
dropping the accessors that read it, so the panel imported cleanly and then
raised AttributeError the moment SWE was calculated. These tests exercise
the selection round-trip and the worker hand-off so that a missing accessor
or a wrong argument fails here instead of in front of a user.
"""
import inspect

import pytest
from PyQt6.QtCore import Qt

from .conftest import make_pattern


@pytest.fixture
def panel(qapp, model):
    from antenna_pattern_viewer.widgets.analysis_panel import AnalysisPanel

    panel = AnalysisPanel(model)
    pattern = make_pattern()
    model.set_pattern(pattern)
    panel.on_pattern_loaded(pattern)
    return panel


class TestSweFrequencySelection:
    def test_every_frequency_is_listed(self, panel, model):
        assert panel.swe_freq_list.count() == len(model.pattern.frequencies)

    def test_check_all_and_none(self, panel, model):
        panel._set_all_swe_frequencies(Qt.CheckState.Checked)
        assert panel.get_swe_frequencies() == [float(f) for f in model.pattern.frequencies]
        panel._set_all_swe_frequencies(Qt.CheckState.Unchecked)
        assert panel.get_swe_frequencies() == []

    def test_single_frequency_accessor_follows_the_list(self, panel, model):
        panel._set_all_swe_frequencies(Qt.CheckState.Unchecked)
        assert panel.get_swe_frequency() is None
        panel.swe_freq_list.item(1).setCheckState(Qt.CheckState.Checked)
        assert panel.get_swe_frequency() == pytest.approx(float(model.pattern.frequencies[1]))

    def test_resolve_swe_frequency_picks_the_nearest_stored_key(self, panel, model):
        pattern = model.pattern
        pattern.swe = {float(f): object() for f in pattern.frequencies}
        panel._set_all_swe_frequencies(Qt.CheckState.Unchecked)
        panel.swe_freq_list.item(1).setCheckState(Qt.CheckState.Checked)
        assert panel.resolve_swe_frequency(pattern) == pytest.approx(float(pattern.frequencies[1]))


class TestSweWorkerHandoff:
    def test_worker_receives_the_checked_frequencies_and_radius(self, panel, monkeypatch):
        from antenna_pattern_viewer.widgets import analysis_panel as module

        captured = {}

        class FakeWorker:
            def __init__(self, pattern, frequency, r, nmax=None, mmax=None):
                captured.update(pattern=pattern, frequency=frequency, r=r,
                                nmax=nmax, mmax=mmax)

            def __getattr__(self, name):
                return lambda *a, **k: None

        monkeypatch.setattr('antenna_pattern_viewer.workers.swe_worker.SWEWorker', FakeWorker)
        panel._set_all_swe_frequencies(Qt.CheckState.Checked)
        panel.swe_radius_spin.setValue(0.25)
        panel.on_calculate_swe()

        assert captured, "the worker was never constructed"
        assert captured['frequency'] == panel.get_swe_frequencies()
        assert captured['r'] == pytest.approx(0.25)

    def test_worker_signature_matches_the_call(self):
        """The call site passes a frequency list and r by keyword."""
        from antenna_pattern_viewer.workers.swe_worker import SWEWorker

        parameters = inspect.signature(SWEWorker.__init__).parameters
        assert 'r' in parameters
        source = inspect.getsource(
            __import__('antenna_pattern_viewer.widgets.analysis_panel',
                       fromlist=['AnalysisPanel']).AnalysisPanel.on_calculate_swe)
        assert 'frequencies' in source and 'r=radius' in source

    def test_worker_accepts_a_list_of_frequencies(self):
        from antenna_pattern_viewer.workers.swe_worker import SWEWorker

        worker = SWEWorker(make_pattern(), [8e9, 10e9], r=0.1)
        assert worker.frequencies == [8e9, 10e9]
        assert worker.r == pytest.approx(0.1)
