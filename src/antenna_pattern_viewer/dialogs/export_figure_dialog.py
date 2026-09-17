"""
Export options for the figure on screen: size, resolution, format and
background. Vector formats (SVG, PDF) are what a publication wants; the
size in inches is what decides how large the fonts look on the page.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                             QDoubleSpinBox, QFileDialog, QFormLayout, QHBoxLayout,
                             QLineEdit, QPushButton, QSpinBox, QVBoxLayout)

FORMATS = {'PNG image (*.png)': 'png', 'PDF (vector) (*.pdf)': 'pdf',
           'SVG (vector) (*.svg)': 'svg', 'JPEG image (*.jpg)': 'jpg',
           'TIFF image (*.tif)': 'tif'}


class ExportFigureDialog(QDialog):
    def __init__(self, figure, parent=None, default_name='pattern_plot'):
        super().__init__(parent)
        self.setWindowTitle("Export Figure")
        self._figure = figure
        width, height = figure.get_size_inches()

        layout = QVBoxLayout(self)
        form = QFormLayout()
        path_row = QHBoxLayout()
        self.path_edit = QLineEdit(f"{default_name}.png")
        self.browse_btn = QPushButton("Browse…")
        path_row.addWidget(self.path_edit); path_row.addWidget(self.browse_btn)
        form.addRow("File:", path_row)

        self.format_combo = QComboBox(); self.format_combo.addItems(list(FORMATS))
        form.addRow("Format:", self.format_combo)
        self.width_spin = QDoubleSpinBox(); self.width_spin.setRange(1, 40)
        self.width_spin.setDecimals(2); self.width_spin.setSuffix(" in"); self.width_spin.setValue(width)
        self.height_spin = QDoubleSpinBox(); self.height_spin.setRange(1, 40)
        self.height_spin.setDecimals(2); self.height_spin.setSuffix(" in"); self.height_spin.setValue(height)
        form.addRow("Width:", self.width_spin)
        form.addRow("Height:", self.height_spin)
        self.dpi_spin = QSpinBox(); self.dpi_spin.setRange(50, 1200); self.dpi_spin.setValue(300)
        form.addRow("Resolution:", self.dpi_spin)
        self.transparent = QCheckBox("Transparent background")
        self.tight = QCheckBox("Trim margins (bbox tight)"); self.tight.setChecked(True)
        form.addRow("", self.transparent)
        form.addRow("", self.tight)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save
                                   | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.browse_btn.clicked.connect(self._browse)
        self.format_combo.currentTextChanged.connect(self._sync_extension)

    def _browse(self):
        path, chosen = QFileDialog.getSaveFileName(self, "Export Figure", self.path_edit.text(),
                                                   ";;".join(FORMATS))
        if path:
            self.path_edit.setText(path)
            if chosen in FORMATS:
                self.format_combo.setCurrentText(chosen)

    def _sync_extension(self, text):
        ext = FORMATS.get(text)
        current = self.path_edit.text().strip()
        if ext and current:
            self.path_edit.setText(str(Path(current).with_suffix(f".{ext}")))

    def options(self) -> dict:
        ext = FORMATS[self.format_combo.currentText()]
        path = Path(self.path_edit.text().strip())
        if path.suffix.lower().lstrip('.') != ext:
            path = path.with_suffix(f".{ext}")
        return {
            'path': str(path), 'format': ext,
            'size': (float(self.width_spin.value()), float(self.height_spin.value())),
            'dpi': int(self.dpi_spin.value()),
            'transparent': self.transparent.isChecked(),
            'bbox_inches': 'tight' if self.tight.isChecked() else None,
        }


def save_figure(figure, options: dict) -> Optional[str]:
    """
    Write ``figure`` with the dialog's options and return the path.

    The figure is resized for the export and restored afterwards so the
    on-screen canvas is unchanged.
    """
    original = figure.get_size_inches().copy()
    try:
        figure.set_size_inches(*options['size'])
        figure.savefig(options['path'], dpi=options['dpi'], format=options['format'],
                       transparent=options['transparent'], bbox_inches=options['bbox_inches'],
                       facecolor=figure.get_facecolor() if not options['transparent'] else 'none')
    finally:
        figure.set_size_inches(*original)
    return options['path']
