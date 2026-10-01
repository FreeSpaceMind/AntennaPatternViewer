"""
Dialog for deriving a pattern from two loaded ones (A / B, |A / B|, A − B,
A + B). Returns the operation, the two instance ids and the new name.
"""
from __future__ import annotations

from typing import Optional, Tuple

from PyQt6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel,
                             QLineEdit, QVBoxLayout)

from ..pattern_math import OPERATIONS, derived_name


class ArithmeticDialog(QDialog):
    def __init__(self, instances, parent=None, default_a: Optional[str] = None,
                 default_b: Optional[str] = None):
        """
        Args:
            instances: PatternInstance objects to choose from (at least two)
            default_a, default_b: instance ids to preselect
        """
        super().__init__(parent)
        self.setWindowTitle("Combine Patterns")
        self._instances = list(instances)
        self._auto_name = True

        layout = QVBoxLayout(self)
        hint = QLabel("The inputs are the patterns as processed. Both must be on the same "
                      "theta, phi and frequency grids. The result is added as a new pattern.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #666;")
        layout.addWidget(hint)

        form = QFormLayout()
        self.a_combo = QComboBox()
        self.b_combo = QComboBox()
        for inst in self._instances:
            self.a_combo.addItem(inst.display_name, inst.instance_id)
            self.b_combo.addItem(inst.display_name, inst.instance_id)
        self.op_combo = QComboBox()
        for key, label in OPERATIONS.items():
            self.op_combo.addItem(label, key)
        self.name_edit = QLineEdit()
        form.addRow("A:", self.a_combo)
        form.addRow("Operation:", self.op_combo)
        form.addRow("B:", self.b_combo)
        form.addRow("Name:", self.name_edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                   | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if default_a is not None:
            self.a_combo.setCurrentIndex(max(self.a_combo.findData(default_a), 0))
        if default_b is not None:
            self.b_combo.setCurrentIndex(max(self.b_combo.findData(default_b), 0))
        elif self.b_combo.count() > 1:
            self.b_combo.setCurrentIndex(1 if self.a_combo.currentIndex() == 0 else 0)
        for combo in (self.a_combo, self.b_combo, self.op_combo):
            combo.currentIndexChanged.connect(lambda _i: self._refresh_name())
        self.name_edit.textEdited.connect(lambda _t: setattr(self, '_auto_name', False))
        self._refresh_name()

    def _refresh_name(self):
        if self._auto_name:
            self.name_edit.setText(derived_name(self.op_combo.currentData(),
                                                self.a_combo.currentText(), self.b_combo.currentText()))

    def choice(self) -> Tuple[str, str, str, str]:
        """(operation, id of A, id of B, name)."""
        return (self.op_combo.currentData(), self.a_combo.currentData(), self.b_combo.currentData(),
                self.name_edit.text().strip() or derived_name(
                    self.op_combo.currentData(), self.a_combo.currentText(), self.b_combo.currentText()))
