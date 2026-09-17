"""
Non-modal Plot Style dialog.

Edits a PlotStyle live: every change emits ``style_changed`` and the plot
widget re-applies the style to the current axes. The dialog floats, so it
takes no room from the layout and can sit next to the plot while you work.
"""
from __future__ import annotations

from typing import List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox, QColorDialog, QComboBox, QDialog, QDoubleSpinBox, QFileDialog,
    QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QSpinBox, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
    QHeaderView,
)

from ..plot_style import (COLOR_CYCLES, LEGEND_LOCATIONS, LINE_STYLES, PRESETS,
                          PlotStyle, SeriesStyle, preset)

FONT_FAMILIES = ['', 'sans-serif', 'serif', 'monospace', 'DejaVu Sans', 'Arial',
                 'Times New Roman', 'Helvetica']


class _OptionalSpin(QDoubleSpinBox):
    """A spin box whose minimum reads 'Auto' and maps to None."""

    def __init__(self, lo, hi, step=1.0, decimals=1, parent=None):
        super().__init__(parent)
        self.setRange(lo - step, hi)
        self.setSingleStep(step)
        self.setDecimals(decimals)
        self.setSpecialValueText("Auto")
        self.setValue(self.minimum())

    def value_or_none(self) -> Optional[float]:
        return None if self.value() <= self.minimum() else float(self.value())

    def set_value_or_none(self, value):
        self.setValue(self.minimum() if value is None else float(value))


class PlotStyleDialog(QDialog):
    style_changed = pyqtSignal(object)      # PlotStyle for the current plot format

    SERIES_COLUMNS = ('Trace', 'Legend label', 'Colour', 'Width', 'Style', 'Visible')

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Plot Style")
        self.setModal(False)
        self.setWindowFlag(Qt.WindowType.Tool, True)
        self.setMinimumWidth(460)
        self._style = PlotStyle()
        self._format_label = ''
        self._updating = False
        self._series_labels: List[str] = []
        self._build_ui()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        self.format_label = QLabel("")
        self.format_label.setStyleSheet("color: #666;")
        header.addWidget(self.format_label)
        header.addStretch()
        header.addWidget(QLabel("Preset:"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(list(PRESETS))
        self.preset_combo.setToolTip("Replace the current style with a built-in preset")
        header.addWidget(self.preset_combo)
        self.apply_preset_btn = QPushButton("Apply")
        header.addWidget(self.apply_preset_btn)
        layout.addLayout(header)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._text_tab(), "Text")
        self.tabs.addTab(self._axes_tab(), "Axes && Grid")
        self.tabs.addTab(self._legend_tab(), "Legend && Lines")
        self.tabs.addTab(self._series_tab(), "Series")
        layout.addWidget(self.tabs)

        buttons = QHBoxLayout()
        self.load_btn = QPushButton("Load…")
        self.load_btn.setToolTip("Load a style saved as JSON")
        self.save_btn = QPushButton("Save…")
        self.save_btn.setToolTip("Save this style as JSON to share or reuse")
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setToolTip("Back to the plotting defaults for this plot format")
        self.close_btn = QPushButton("Close")
        for b in (self.load_btn, self.save_btn, self.reset_btn):
            buttons.addWidget(b)
        buttons.addStretch()
        buttons.addWidget(self.close_btn)
        layout.addLayout(buttons)

        self.apply_preset_btn.clicked.connect(self._apply_preset)
        self.load_btn.clicked.connect(self._load)
        self.save_btn.clicked.connect(self._save)
        self.reset_btn.clicked.connect(self._reset)
        self.close_btn.clicked.connect(self.hide)

    def _text_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self.title_edit = QLineEdit(); self.title_edit.setPlaceholderText("Auto")
        self.xlabel_edit = QLineEdit(); self.xlabel_edit.setPlaceholderText("Auto")
        self.ylabel_edit = QLineEdit(); self.ylabel_edit.setPlaceholderText("Auto")
        self.cbar_edit = QLineEdit(); self.cbar_edit.setPlaceholderText("Auto (2D polar only)")
        form.addRow("Title:", self.title_edit)
        form.addRow("X label:", self.xlabel_edit)
        form.addRow("Y label:", self.ylabel_edit)
        form.addRow("Colorbar label:", self.cbar_edit)

        self.font_combo = QComboBox(); self.font_combo.setEditable(True)
        self.font_combo.addItems(FONT_FAMILIES)
        self.font_combo.setToolTip("Blank keeps matplotlib's default font")
        form.addRow("Font family:", self.font_combo)
        self.title_size = _OptionalSpin(4, 48)
        self.label_size = _OptionalSpin(4, 48)
        self.tick_size = _OptionalSpin(4, 48)
        self.legend_size = _OptionalSpin(4, 48)
        form.addRow("Title size:", self.title_size)
        form.addRow("Axis label size:", self.label_size)
        form.addRow("Tick label size:", self.tick_size)
        form.addRow("Legend size:", self.legend_size)

        for edit in (self.title_edit, self.xlabel_edit, self.ylabel_edit, self.cbar_edit):
            edit.editingFinished.connect(self._emit)
        self.font_combo.currentTextChanged.connect(self._emit)
        for spin in (self.title_size, self.label_size, self.tick_size, self.legend_size):
            spin.valueChanged.connect(self._emit)
        return w

    def _axes_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self.x_step = _OptionalSpin(0.1, 360, step=5.0)
        self.y_step = _OptionalSpin(0.1, 1000, step=5.0)
        self.x_step.setToolTip("Degrees between major x ticks (1D) — Auto lets matplotlib choose")
        self.y_step.setToolTip("Units between major y ticks; radial ticks on the 2D polar view")
        form.addRow("X tick step:", self.x_step)
        form.addRow("Y tick step:", self.y_step)

        self.grid_minor = QCheckBox("Show minor grid")
        self.grid_style = QComboBox(); self.grid_style.addItems(LINE_STYLES)
        self.grid_alpha = QDoubleSpinBox(); self.grid_alpha.setRange(0.05, 1.0)
        self.grid_alpha.setSingleStep(0.05); self.grid_alpha.setValue(0.5)
        form.addRow("", self.grid_minor)
        form.addRow("Grid line style:", self.grid_style)
        form.addRow("Grid opacity:", self.grid_alpha)

        self.polar_zero = QComboBox(); self.polar_zero.addItems(['N', 'E', 'S', 'W'])
        self.polar_zero.setToolTip("Where phi = 0 sits on the 2D polar view")
        self.polar_cw = QCheckBox("Phi increases clockwise (antenna convention)")
        form.addRow("Polar zero:", self.polar_zero)
        form.addRow("", self.polar_cw)

        self.dark_check = QCheckBox("Dark background")
        self.fig_color_btn = QPushButton("Figure colour…")
        self.axes_color_btn = QPushButton("Axes colour…")
        self.clear_colors_btn = QPushButton("Default colours")
        row = QHBoxLayout()
        for b in (self.fig_color_btn, self.axes_color_btn, self.clear_colors_btn):
            row.addWidget(b)
        form.addRow("", self.dark_check)
        form.addRow("Background:", row)

        for spin in (self.x_step, self.y_step, self.grid_alpha):
            spin.valueChanged.connect(self._emit)
        self.grid_minor.toggled.connect(self._emit)
        self.grid_style.currentTextChanged.connect(self._emit)
        self.polar_zero.currentTextChanged.connect(self._emit)
        self.polar_cw.toggled.connect(self._emit)
        self.dark_check.toggled.connect(self._emit)
        self.fig_color_btn.clicked.connect(lambda: self._pick_color('figure_color'))
        self.axes_color_btn.clicked.connect(lambda: self._pick_color('axes_color'))
        self.clear_colors_btn.clicked.connect(self._clear_colors)
        return w

    def _legend_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self.legend_loc = QComboBox(); self.legend_loc.addItems(LEGEND_LOCATIONS)
        self.legend_cols = QSpinBox(); self.legend_cols.setRange(1, 8)
        self.legend_frame = QCheckBox("Draw legend frame"); self.legend_frame.setChecked(True)
        form.addRow("Legend location:", self.legend_loc)
        form.addRow("Legend columns:", self.legend_cols)
        form.addRow("", self.legend_frame)

        self.line_width = _OptionalSpin(0.2, 10, step=0.25, decimals=2)
        self.line_width.setToolTip("Width for every trace; per-trace widths on the Series tab win")
        self.color_cycle = QComboBox(); self.color_cycle.addItems(COLOR_CYCLES)
        self.color_cycle.setToolTip("Colour sequence for the traces; applied on the next replot")
        form.addRow("Line width:", self.line_width)
        form.addRow("Colour cycle:", self.color_cycle)

        self.legend_loc.currentTextChanged.connect(self._emit)
        self.legend_cols.valueChanged.connect(self._emit)
        self.legend_frame.toggled.connect(self._emit)
        self.line_width.valueChanged.connect(self._emit)
        self.color_cycle.currentTextChanged.connect(self._emit)
        return w

    def _series_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        hint = QLabel("Per-trace overrides. Edits are keyed by the trace's original label, so "
                      "they persist across replots. Double-click a cell to edit.")
        hint.setWordWrap(True); hint.setStyleSheet("color: #666;")
        layout.addWidget(hint)
        self.series_table = QTableWidget(0, len(self.SERIES_COLUMNS))
        self.series_table.setHorizontalHeaderLabels(self.SERIES_COLUMNS)
        self.series_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.series_table.verticalHeader().setVisible(False)
        layout.addWidget(self.series_table)
        row = QHBoxLayout()
        self.series_clear_btn = QPushButton("Clear overrides")
        row.addWidget(self.series_clear_btn); row.addStretch()
        layout.addLayout(row)
        self.series_table.cellChanged.connect(self._series_cell_changed)
        self.series_table.cellDoubleClicked.connect(self._series_cell_double_clicked)
        self.series_clear_btn.clicked.connect(self._clear_series)
        return w

    # ------------------------------------------------------------- state
    def set_style(self, style: PlotStyle, format_label: str = ''):
        """Show ``style`` in the controls without emitting."""
        self._style = style.copy()
        self._format_label = format_label
        self.format_label.setText(f"Editing: {format_label}" if format_label else "")
        self._updating = True
        try:
            s = self._style
            self.title_edit.setText(s.title or '')
            self.xlabel_edit.setText(s.xlabel or '')
            self.ylabel_edit.setText(s.ylabel or '')
            self.cbar_edit.setText(s.colorbar_label or '')
            self.font_combo.setCurrentText(s.font_family or '')
            self.title_size.set_value_or_none(s.title_size)
            self.label_size.set_value_or_none(s.label_size)
            self.tick_size.set_value_or_none(s.tick_size)
            self.legend_size.set_value_or_none(s.legend_size)
            self.x_step.set_value_or_none(s.x_tick_step)
            self.y_step.set_value_or_none(s.y_tick_step)
            self.grid_minor.setChecked(s.grid_minor)
            self.grid_style.setCurrentText(s.grid_linestyle or '-')
            self.grid_alpha.setValue(s.grid_alpha)
            self.polar_zero.setCurrentText(s.polar_zero_location or 'N')
            self.polar_cw.setChecked(s.polar_clockwise)
            self.dark_check.setChecked(s.dark)
            self.legend_loc.setCurrentText(s.legend_loc or 'best')
            self.legend_cols.setValue(max(1, int(s.legend_columns)))
            self.legend_frame.setChecked(s.legend_frame)
            self.line_width.set_value_or_none(s.line_width)
            self.color_cycle.setCurrentText(s.color_cycle or 'default')
            self._fill_series_table()
        finally:
            self._updating = False

    def style(self) -> PlotStyle:
        return self._style.copy()

    def set_series(self, labels: List[str]):
        """Refresh the Series tab with the traces currently on the plot."""
        self._series_labels = list(labels)
        self._updating = True
        try:
            self._fill_series_table()
        finally:
            self._updating = False

    # ---------------------------------------------------------- collect
    def _collect(self) -> PlotStyle:
        s = self._style
        text = lambda edit: (edit.text().strip() or None)
        s.title = text(self.title_edit)
        s.xlabel = text(self.xlabel_edit)
        s.ylabel = text(self.ylabel_edit)
        s.colorbar_label = text(self.cbar_edit)
        s.font_family = self.font_combo.currentText().strip() or None
        s.title_size = self.title_size.value_or_none()
        s.label_size = self.label_size.value_or_none()
        s.tick_size = self.tick_size.value_or_none()
        s.legend_size = self.legend_size.value_or_none()
        s.x_tick_step = self.x_step.value_or_none()
        s.y_tick_step = self.y_step.value_or_none()
        s.grid_minor = self.grid_minor.isChecked()
        s.grid_linestyle = self.grid_style.currentText()
        s.grid_alpha = float(self.grid_alpha.value())
        s.polar_zero_location = self.polar_zero.currentText()
        s.polar_clockwise = self.polar_cw.isChecked()
        s.dark = self.dark_check.isChecked()
        s.legend_loc = self.legend_loc.currentText()
        s.legend_columns = int(self.legend_cols.value())
        s.legend_frame = self.legend_frame.isChecked()
        s.line_width = self.line_width.value_or_none()
        s.color_cycle = self.color_cycle.currentText()
        return s

    def _emit(self, *_args):
        if self._updating:
            return
        self._collect()
        self.style_changed.emit(self._style.copy())

    # ----------------------------------------------------------- actions
    def _apply_preset(self):
        chosen = preset(self.preset_combo.currentText())
        chosen.series = self._style.series      # presets do not touch per-trace edits
        self.set_style(chosen, self._format_label)
        self.style_changed.emit(self._style.copy())

    def _reset(self):
        self.set_style(PlotStyle(), self._format_label)
        self.style_changed.emit(self._style.copy())

    def _load(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Plot Style", "",
                                              "Plot style (*.json);;All files (*)")
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as handle:
                loaded = PlotStyle.from_json(handle.read())
        except (OSError, ValueError, TypeError) as e:
            QMessageBox.critical(self, "Load Failed", f"Could not read the style:\n{e}")
            return
        self.set_style(loaded, self._format_label)
        self.style_changed.emit(self._style.copy())

    def _save(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Plot Style", "plot_style.json",
                                              "Plot style (*.json);;All files (*)")
        if not path:
            return
        if not path.lower().endswith('.json'):
            path += '.json'
        try:
            with open(path, 'w', encoding='utf-8') as handle:
                handle.write(self._collect().to_json())
        except OSError as e:
            QMessageBox.critical(self, "Save Failed", f"Could not write the style:\n{e}")

    def _pick_color(self, attribute: str):
        current = getattr(self._style, attribute) or ('#ffffff' if not self._style.dark else '#1e1e1e')
        color = QColorDialog.getColor(QColor(current), self, "Choose colour")
        if color.isValid():
            setattr(self._style, attribute, color.name())
            self._emit()

    def _clear_colors(self):
        self._style.figure_color = None
        self._style.axes_color = None
        self._emit()

    # ------------------------------------------------------------ series
    def _fill_series_table(self):
        table = self.series_table
        table.blockSignals(True)
        try:
            table.setRowCount(len(self._series_labels))
            for row, label in enumerate(self._series_labels):
                override = self._style.series.get(label, SeriesStyle())
                cells = [
                    label,
                    override.label or '',
                    override.color or '',
                    '' if override.linewidth is None else f"{override.linewidth:g}",
                    override.linestyle or '',
                ]
                for col, value in enumerate(cells):
                    item = QTableWidgetItem(value)
                    if col in (0, 2):      # colour is picked with a dialog
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    if col == 2 and override.color:
                        item.setBackground(QColor(override.color))
                    table.setItem(row, col, item)
                visible = QTableWidgetItem()
                visible.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                visible.setCheckState(Qt.CheckState.Checked if override.visible
                                      else Qt.CheckState.Unchecked)
                table.setItem(row, 5, visible)
        finally:
            table.blockSignals(False)

    def _series_cell_changed(self, row: int, col: int):
        if self._updating or row >= len(self._series_labels):
            return
        key = self._series_labels[row]
        override = self._style.series.setdefault(key, SeriesStyle())
        item = self.series_table.item(row, col)
        value = item.text().strip() if item is not None else ''
        if col == 1:
            override.label = value or None
        elif col == 2:
            override.color = value or None
        elif col == 3:
            try:
                override.linewidth = float(value) if value else None
            except ValueError:
                override.linewidth = None
        elif col == 4:
            override.linestyle = value if value in LINE_STYLES else None
        elif col == 5:
            override.visible = item.checkState() == Qt.CheckState.Checked
        if override == SeriesStyle():
            del self._style.series[key]
        self.style_changed.emit(self._style.copy())

    def _series_cell_double_clicked(self, row: int, col: int):
        if col != 2 or row >= len(self._series_labels):
            return
        key = self._series_labels[row]
        current = self._style.series.get(key, SeriesStyle()).color or '#1f77b4'
        color = QColorDialog.getColor(QColor(current), self, f"Colour for {key}")
        if color.isValid():
            self.series_table.item(row, col).setText(color.name())   # triggers cellChanged

    def _clear_series(self):
        self._style.series.clear()
        self._fill_series_table()
        self.style_changed.emit(self._style.copy())
