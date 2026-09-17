"""
Specification mask dialog: a list of masks with import from CSV, a
points editor for piecewise-linear masks, colour, kind and mirroring.
Non-modal; every change emits ``masks_changed`` and the plot redraws.
"""
from __future__ import annotations

from typing import List

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox, QColorDialog, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
    QFormLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from ..spec_mask import (DEFAULT_COLORS, MASK_KINDS, SpecMask, masks_from_json,
                         masks_to_json, read_mask_csv)


class MaskPointsDialog(QDialog):
    """Edit one mask: name, kind, mirror, and its (theta, value) points."""

    def __init__(self, mask: SpecMask, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mask Points")
        self.setMinimumSize(380, 420)
        self._mask = mask

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name_edit = QLineEdit(mask.name)
        self.kind_combo = QComboBox()
        self.kind_combo.addItems(["upper (trace must stay below)", "lower (trace must stay above)"])
        self.kind_combo.setCurrentIndex(MASK_KINDS.index(mask.kind))
        self.mirror_check = QCheckBox("Mirror about θ = 0")
        self.mirror_check.setChecked(mask.mirror)
        form.addRow("Name:", self.name_edit)
        form.addRow("Kind:", self.kind_combo)
        form.addRow("", self.mirror_check)
        layout.addLayout(form)

        hint = QLabel("One row per breakpoint: θ in degrees and the limit value. "
                      "Rows are sorted by θ when applied.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #666;")
        layout.addWidget(hint)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["θ (deg)", "Value"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        for theta, value in mask.points:
            self._add_row(theta, value)
        layout.addWidget(self.table)

        row = QHBoxLayout()
        self.add_btn = QPushButton("Add row")
        self.remove_btn = QPushButton("Remove row")
        self.add_btn.clicked.connect(lambda: self._add_row(0.0, 0.0))
        self.remove_btn.clicked.connect(self._remove_row)
        row.addWidget(self.add_btn)
        row.addWidget(self.remove_btn)
        row.addStretch()
        layout.addLayout(row)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                   | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _add_row(self, theta, value):
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setItem(r, 0, QTableWidgetItem(f"{theta:g}"))
        self.table.setItem(r, 1, QTableWidgetItem(f"{value:g}"))

    def _remove_row(self):
        r = self.table.currentRow()
        if r >= 0:
            self.table.removeRow(r)

    def points(self) -> List[tuple]:
        pts = []
        for r in range(self.table.rowCount()):
            a, b = self.table.item(r, 0), self.table.item(r, 1)
            try:
                pts.append((float(a.text()), float(b.text())))
            except (AttributeError, ValueError):
                raise ValueError(f"Row {r + 1} is not two numbers")
        return pts

    def _accept(self):
        try:
            pts = self.points()
        except ValueError as e:
            QMessageBox.warning(self, "Invalid Points", str(e))
            return
        if len(pts) < 2:
            QMessageBox.warning(self, "Invalid Points", "A mask needs at least two points.")
            return
        self._mask.name = self.name_edit.text().strip() or self._mask.name
        self._mask.kind = MASK_KINDS[self.kind_combo.currentIndex()]
        self._mask.mirror = self.mirror_check.isChecked()
        self._mask.points = pts
        self.accept()

    def mask(self) -> SpecMask:
        return self._mask


class MaskDialog(QDialog):
    masks_changed = pyqtSignal(object)      # list of SpecMask

    COLUMNS = ("Name", "Kind", "Points", "Mirror", "Colour", "Visible")

    def __init__(self, masks: List[SpecMask], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Specification Masks")
        self.setModal(False)
        self.setWindowFlag(Qt.WindowType.Tool, True)
        self.setMinimumSize(520, 320)
        self._masks: List[SpecMask] = [SpecMask.from_dict(m.to_dict()) for m in masks]
        self._updating = False
        self._build_ui()
        self._fill()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        layout = QVBoxLayout(self)
        hint = QLabel("An upper mask shades the region a trace must stay below; a lower mask "
                      "the region it must stay above. Violations are reported under the plot.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #666;")
        layout.addWidget(hint)

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.cellChanged.connect(self._cell_changed)
        self.table.cellDoubleClicked.connect(self._cell_double_clicked)
        layout.addWidget(self.table)

        row = QHBoxLayout()
        self.import_btn = QPushButton("Import CSV…")
        self.import_btn.setToolTip("Two columns: theta in degrees, value. Header optional.")
        self.add_btn = QPushButton("Add points…")
        self.edit_btn = QPushButton("Edit…")
        self.remove_btn = QPushButton("Remove")
        self.load_btn = QPushButton("Load set…")
        self.save_btn = QPushButton("Save set…")
        self.close_btn = QPushButton("Close")
        for b in (self.import_btn, self.add_btn, self.edit_btn, self.remove_btn):
            row.addWidget(b)
        row.addStretch()
        for b in (self.load_btn, self.save_btn, self.close_btn):
            row.addWidget(b)
        layout.addLayout(row)

        self.import_btn.clicked.connect(self._import_csv)
        self.add_btn.clicked.connect(self._add_points)
        self.edit_btn.clicked.connect(self._edit_current)
        self.remove_btn.clicked.connect(self._remove_current)
        self.load_btn.clicked.connect(self._load_set)
        self.save_btn.clicked.connect(self._save_set)
        self.close_btn.clicked.connect(self.hide)

    # ------------------------------------------------------------ state
    def masks(self) -> List[SpecMask]:
        return [SpecMask.from_dict(m.to_dict()) for m in self._masks]

    def set_masks(self, masks: List[SpecMask]):
        self._masks = [SpecMask.from_dict(m.to_dict()) for m in masks]
        self._fill()

    def _emit(self):
        self.masks_changed.emit(self.masks())

    def _fill(self):
        self._updating = True
        try:
            self.table.setRowCount(len(self._masks))
            for r, mask in enumerate(self._masks):
                cells = [mask.name, mask.kind, str(len(mask.points))]
                for c, text in enumerate(cells):
                    item = QTableWidgetItem(text)
                    if c != 0:
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.table.setItem(r, c, item)
                mirror = QTableWidgetItem()
                mirror.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                mirror.setCheckState(Qt.CheckState.Checked if mask.mirror else Qt.CheckState.Unchecked)
                self.table.setItem(r, 3, mirror)
                colour = QTableWidgetItem(mask.color)
                colour.setFlags(colour.flags() & ~Qt.ItemFlag.ItemIsEditable)
                colour.setBackground(QColor(mask.color))
                self.table.setItem(r, 4, colour)
                visible = QTableWidgetItem()
                visible.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                visible.setCheckState(Qt.CheckState.Checked if mask.visible else Qt.CheckState.Unchecked)
                self.table.setItem(r, 5, visible)
        finally:
            self._updating = False

    # ---------------------------------------------------------- actions
    def _next_color(self) -> str:
        return DEFAULT_COLORS[len(self._masks) % len(DEFAULT_COLORS)]

    def _import_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Mask CSV", "",
                                              "CSV files (*.csv *.txt);;All files (*)")
        if not path:
            return
        try:
            mask = read_mask_csv(path)
        except (OSError, ValueError) as e:
            QMessageBox.critical(self, "Import Failed", str(e))
            return
        mask.color = self._next_color()
        editor = MaskPointsDialog(mask, self)        # confirm kind / mirror / name
        if editor.exec() != QDialog.DialogCode.Accepted:
            return
        self._masks.append(editor.mask())
        self._fill()
        self._emit()

    def _add_points(self):
        mask = SpecMask(name=f"Mask {len(self._masks) + 1}", color=self._next_color(),
                        points=[(0.0, 0.0), (30.0, -20.0), (90.0, -30.0)])
        editor = MaskPointsDialog(mask, self)
        if editor.exec() != QDialog.DialogCode.Accepted:
            return
        self._masks.append(editor.mask())
        self._fill()
        self._emit()

    def _edit_current(self):
        r = self.table.currentRow()
        if r < 0 or r >= len(self._masks):
            return
        editor = MaskPointsDialog(self._masks[r], self)
        if editor.exec() == QDialog.DialogCode.Accepted:
            self._fill()
            self._emit()

    def _remove_current(self):
        r = self.table.currentRow()
        if 0 <= r < len(self._masks):
            del self._masks[r]
            self._fill()
            self._emit()

    def _load_set(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Mask Set", "", "Mask set (*.json);;All files (*)")
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as handle:
                self._masks = masks_from_json(handle.read())
        except (OSError, ValueError, TypeError) as e:
            QMessageBox.critical(self, "Load Failed", str(e))
            return
        self._fill()
        self._emit()

    def _save_set(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Mask Set", "masks.json",
                                              "Mask set (*.json);;All files (*)")
        if not path:
            return
        if not path.lower().endswith('.json'):
            path += '.json'
        try:
            with open(path, 'w', encoding='utf-8') as handle:
                handle.write(masks_to_json(self._masks))
        except OSError as e:
            QMessageBox.critical(self, "Save Failed", str(e))

    def _cell_changed(self, row, col):
        if self._updating or row >= len(self._masks):
            return
        mask = self._masks[row]
        item = self.table.item(row, col)
        if col == 0:
            mask.name = item.text().strip() or mask.name
        elif col == 3:
            mask.mirror = item.checkState() == Qt.CheckState.Checked
        elif col == 5:
            mask.visible = item.checkState() == Qt.CheckState.Checked
        else:
            return
        self._emit()

    def _cell_double_clicked(self, row, col):
        if row >= len(self._masks):
            return
        if col == 4:
            color = QColorDialog.getColor(QColor(self._masks[row].color), self, "Mask colour")
            if color.isValid():
                self._masks[row].color = color.name()
                self._fill()
                self._emit()
        elif col in (1, 2):
            self.table.setCurrentCell(row, col)
            self._edit_current()
