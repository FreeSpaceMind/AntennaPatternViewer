from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)


class SphFrequencyDialog(QDialog):
    """Dialog for selecting frequency blocks from a TICRA .sph file."""

    def __init__(self, filename, frequencies_hz, parent=None):
        super().__init__(parent)
        self._frequencies_hz = [float(freq) for freq in frequencies_hz]
        self.setWindowTitle(f"Import {Path(filename).name}")
        self._setup_ui(Path(filename).name)
        self._update_ok_state()

    def _setup_ui(self, filename):
        layout = QVBoxLayout(self)

        title = QLabel(filename)
        title.setWordWrap(True)
        layout.addWidget(title)

        self.frequency_list = QListWidget()
        for freq in self._frequencies_hz:
            item = QListWidgetItem(f"{freq / 1e9:.3f} GHz")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            item.setData(Qt.ItemDataRole.UserRole, freq)
            self.frequency_list.addItem(item)
        self.frequency_list.itemChanged.connect(self._update_ok_state)
        layout.addWidget(self.frequency_list)

        selection_row = QHBoxLayout()
        select_all = QPushButton("Select all")
        select_none = QPushButton("Select none")
        select_all.clicked.connect(self._select_all)
        select_none.clicked.connect(self._select_none)
        selection_row.addWidget(select_all)
        selection_row.addWidget(select_none)
        selection_row.addStretch(1)
        layout.addLayout(selection_row)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def _set_all(self, state):
        self.frequency_list.blockSignals(True)
        try:
            for index in range(self.frequency_list.count()):
                self.frequency_list.item(index).setCheckState(state)
        finally:
            self.frequency_list.blockSignals(False)
        self._update_ok_state()

    def _select_all(self):
        self._set_all(Qt.CheckState.Checked)

    def _select_none(self):
        self._set_all(Qt.CheckState.Unchecked)

    def _update_ok_state(self):
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            bool(self.selected_frequencies())
        )

    def selected_frequencies(self):
        selected = []
        for index in range(self.frequency_list.count()):
            item = self.frequency_list.item(index)
            if item.checkState() == Qt.CheckState.Checked:
                selected.append(float(item.data(Qt.ItemDataRole.UserRole)))
        return selected
