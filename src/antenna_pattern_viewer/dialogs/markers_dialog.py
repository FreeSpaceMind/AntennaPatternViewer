"""
Non-modal Markers dialog.

Chooses which markers are drawn (peak, beamwidth at one or more levels,
first sidelobe, nulls, values at custom angles, text labels), for all
patterns or for one pattern at a time, so the two copies of a file in a
comparison can carry different markers. The markers stay on the plot when
the dialog is closed; the Markers checkbox on the plot strip is what turns
drawing on and off.
"""
from __future__ import annotations

from typing import List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QVBoxLayout)

from ..pattern_markers import MarkerConfig, MarkerSet

ALL = "All patterns (default)"


def _parse_numbers(text: str) -> List[float]:
    values = []
    for token in text.replace(';', ',').replace(' ', ',').split(','):
        token = token.strip()
        if not token:
            continue
        try:
            values.append(float(token))
        except ValueError:
            continue
    return values


class MarkersDialog(QDialog):
    config_changed = pyqtSignal(object)      # MarkerConfig

    def __init__(self, config: MarkerConfig, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Markers")
        self.setModal(False)
        self.setWindowFlag(Qt.WindowType.Tool, True)
        self.setMinimumWidth(380)
        self._config = config.copy()
        self._patterns: List[str] = []
        self._updating = False
        self._build_ui()
        self._show_current()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        row.addWidget(QLabel("Applies to:"))
        self.target_combo = QComboBox()
        self.target_combo.addItem(ALL)
        self.target_combo.setToolTip("Edit the default set, or the set for one pattern on the plot")
        row.addWidget(self.target_combo, 1)
        layout.addLayout(row)

        self.enabled_check = QCheckBox("Draw markers on this pattern")
        self.enabled_check.setChecked(True)
        layout.addWidget(self.enabled_check)
        self.override_label = QLabel("")
        self.override_label.setStyleSheet("color: #666; font-size: 9pt;")
        layout.addWidget(self.override_label)

        form = QFormLayout()
        self.peak_check = QCheckBox("Peak")
        self.beamwidth_check = QCheckBox("Beamwidth at levels below the peak (dB):")
        self.levels_edit = QLineEdit("3")
        self.levels_edit.setToolTip("Comma-separated, e.g. 3, 10 for the half-power and 10 dB widths")
        self.sidelobe_check = QCheckBox("First sidelobe")
        self.nulls_check = QCheckBox("First nulls")
        self.custom_label = QLabel("Read the trace at angles (deg):")
        self.custom_edit = QLineEdit("")
        self.custom_edit.setToolTip("Comma-separated theta values, e.g. -30, 0, 30")
        self.labels_check = QCheckBox("Text labels next to the symbols")
        form.addRow(self.peak_check)
        form.addRow(self.beamwidth_check)
        form.addRow("", self.levels_edit)
        form.addRow(self.sidelobe_check)
        form.addRow(self.nulls_check)
        form.addRow(self.custom_label, self.custom_edit)
        form.addRow(self.labels_check)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        self.reset_btn = QPushButton("Use default for this pattern")
        self.reset_btn.setToolTip("Drop this pattern's own set and follow the default")
        self.close_btn = QPushButton("Close")
        buttons.addWidget(self.reset_btn)
        buttons.addStretch()
        buttons.addWidget(self.close_btn)
        layout.addLayout(buttons)

        self.target_combo.currentIndexChanged.connect(lambda _i: self._show_current())
        self.enabled_check.toggled.connect(self._changed)
        for check in (self.peak_check, self.beamwidth_check, self.sidelobe_check,
                      self.nulls_check, self.labels_check):
            check.toggled.connect(self._changed)
        self.levels_edit.editingFinished.connect(self._changed)
        self.custom_edit.editingFinished.connect(self._changed)
        self.reset_btn.clicked.connect(self._use_default)
        self.close_btn.clicked.connect(self.hide)

    # --------------------------------------------------------------- state
    def config(self) -> MarkerConfig:
        return self._config.copy()

    def set_config(self, config: MarkerConfig):
        self._config = config.copy()
        self._show_current()

    def set_patterns(self, names: List[str]):
        """Offer the patterns currently on the plot in the Applies-to combo."""
        current = self.target_combo.currentText()
        self._patterns = [n for n in names if n]
        self.target_combo.blockSignals(True)
        try:
            self.target_combo.clear()
            self.target_combo.addItem(ALL)
            for name in self._patterns:
                self.target_combo.addItem(name)
            index = self.target_combo.findText(current)
            self.target_combo.setCurrentIndex(index if index >= 0 else 0)
        finally:
            self.target_combo.blockSignals(False)
        self._show_current()

    def _target(self) -> Optional[str]:
        text = self.target_combo.currentText()
        return None if text == ALL else text

    def _show_current(self):
        target = self._target()
        if target is None:
            marker_set = self._config.default
            enabled = True
            note = "Patterns without their own set follow this one."
        else:
            marker_set = self._config.per_pattern.get(target, self._config.default)
            enabled = target not in self._config.disabled
            note = ("This pattern has its own set." if target in self._config.per_pattern
                    else "Following the default; editing here gives this pattern its own set.")
        self._updating = True
        try:
            self.enabled_check.setVisible(target is not None)
            self.enabled_check.setChecked(enabled)
            self.reset_btn.setEnabled(target is not None
                                      and (target in self._config.per_pattern or not enabled))
            self.override_label.setText(note)
            self.peak_check.setChecked(marker_set.peak)
            self.beamwidth_check.setChecked(marker_set.beamwidth)
            self.levels_edit.setText(", ".join(f"{v:g}" for v in marker_set.levels_db))
            self.sidelobe_check.setChecked(marker_set.sidelobe)
            self.nulls_check.setChecked(marker_set.nulls)
            self.custom_edit.setText(", ".join(f"{v:g}" for v in marker_set.custom_thetas))
            self.labels_check.setChecked(marker_set.labels)
        finally:
            self._updating = False

    def _collect(self) -> MarkerSet:
        levels = _parse_numbers(self.levels_edit.text()) or [3.0]
        return MarkerSet(peak=self.peak_check.isChecked(),
                         beamwidth=self.beamwidth_check.isChecked(),
                         levels_db=levels,
                         sidelobe=self.sidelobe_check.isChecked(),
                         nulls=self.nulls_check.isChecked(),
                         custom_thetas=_parse_numbers(self.custom_edit.text()),
                         labels=self.labels_check.isChecked())

    def _changed(self, *_args):
        if self._updating:
            return
        target = self._target()
        marker_set = self._collect()
        if target is None:
            self._config.default = marker_set
        else:
            self._config.per_pattern[target] = marker_set
            if self.enabled_check.isChecked():
                if target in self._config.disabled:
                    self._config.disabled.remove(target)
            elif target not in self._config.disabled:
                self._config.disabled.append(target)
        self._show_current()
        self.config_changed.emit(self.config())

    def _use_default(self):
        target = self._target()
        if target is None:
            return
        self._config.per_pattern.pop(target, None)
        if target in self._config.disabled:
            self._config.disabled.remove(target)
        self._show_current()
        self.config_changed.emit(self.config())
