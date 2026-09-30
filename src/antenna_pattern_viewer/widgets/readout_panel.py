"""
A compact, collapsible readout under the plot strip for marker, mask and
cursor text. Fixed height with a scrollbar, so many traces cannot push the
plot off the screen; a toggle collapses it to one line.
"""
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QHBoxLayout, QPlainTextEdit, QToolButton, QVBoxLayout, QWidget


class ReadoutPanel(QWidget):
    MAX_HEIGHT = 84

    def __init__(self, parent=None):
        super().__init__(parent)
        self._text = ""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        self.toggle = QToolButton()
        self.toggle.setCheckable(True)
        self.toggle.setStyleSheet("QToolButton { border: none; font-size: 9pt; color: #444; }")
        self.toggle.toggled.connect(self._apply_collapsed)
        header.addWidget(self.toggle)
        header.addStretch()
        layout.addLayout(header)
        self.box = QPlainTextEdit()
        self.box.setReadOnly(True)
        self.box.setMaximumHeight(self.MAX_HEIGHT)
        self.box.setStyleSheet("font-size: 9pt; color: #444; background: transparent; border: none;")
        self.box.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self.box)
        collapsed = False
        try:
            collapsed = QSettings('AntennaPatternViewer', 'PlotStyle').value('readout/collapsed', False, type=bool)
        except Exception:
            pass
        self.toggle.setChecked(bool(collapsed))
        self._apply_collapsed(bool(collapsed))

    # -- QLabel-like interface the plot widget and tests use ----------------
    def text(self) -> str:
        return self._text

    def setText(self, text: str):
        self._text = text or ""
        self.box.setPlainText(self._text)
        self._update_header()

    def _update_header(self):
        lines = [l for l in self._text.splitlines() if l.strip()]
        first = lines[0] if lines else ""
        if self.toggle.isChecked():
            summary = first[:110] + ("…" if len(first) > 110 else "")
            more = f"  (+{len(lines) - 1} more)" if len(lines) > 1 else ""
            self.toggle.setText(f"▸ Readout: {summary}{more}")
        else:
            self.toggle.setText(f"▾ Readout ({len(lines)} line{'s' if len(lines) != 1 else ''})")

    def _apply_collapsed(self, collapsed: bool):
        self.box.setVisible(not collapsed)
        self._update_header()
        try:
            QSettings('AntennaPatternViewer', 'PlotStyle').setValue('readout/collapsed', bool(collapsed))
        except Exception:
            pass
