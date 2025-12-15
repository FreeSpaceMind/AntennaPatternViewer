"""
Icon sidebar widget for panel navigation.

Provides a vertical strip of icon buttons for switching between panels.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QButtonGroup, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, Qt, QSize
from PyQt6.QtGui import QIcon


class IconButton(QPushButton):
    """Custom icon button for the sidebar."""

    def __init__(self, icon_text: str, tooltip: str, parent=None):
        super().__init__(parent)
        self.setText(icon_text)
        self.setToolTip(tooltip)
        self.setCheckable(True)
        self.setFixedSize(40, 40)
        self.setStyleSheet("""
            QPushButton {
                border: none;
                border-radius: 4px;
                font-size: 18px;
                background-color: transparent;
            }
            QPushButton:hover {
                background-color: palette(midlight);
            }
            QPushButton:checked {
                background-color: palette(highlight);
                color: palette(highlighted-text);
            }
        """)


class IconSidebar(QWidget):
    """
    Vertical icon sidebar for panel navigation.

    Emits panel_changed signal with panel index when user clicks an icon.
    """

    # Signal emitted when panel selection changes
    panel_changed = pyqtSignal(int)

    # Panel indices
    PANEL_FILES = 0
    PANEL_CONTROLS = 1
    PANEL_ANALYSIS = 2
    PANEL_EXPORT = 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Setup the sidebar UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Create button group for exclusive selection
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)

        # Create icon buttons
        self.files_btn = IconButton("📁", "Files - Browse and load patterns")
        self.controls_btn = IconButton("⚙️", "Controls - View and processing settings")
        self.analysis_btn = IconButton("📊", "Analysis - SWE and near field calculations")
        self.export_btn = IconButton("📤", "Export - Save patterns and plots")

        # Add buttons to group with IDs matching panel indices
        self.button_group.addButton(self.files_btn, self.PANEL_FILES)
        self.button_group.addButton(self.controls_btn, self.PANEL_CONTROLS)
        self.button_group.addButton(self.analysis_btn, self.PANEL_ANALYSIS)
        self.button_group.addButton(self.export_btn, self.PANEL_EXPORT)

        # Add to layout
        layout.addWidget(self.files_btn)
        layout.addWidget(self.controls_btn)
        layout.addWidget(self.analysis_btn)
        layout.addWidget(self.export_btn)
        layout.addStretch()

        # Connect signal
        self.button_group.idClicked.connect(self.on_button_clicked)

        # Set default selection
        self.files_btn.setChecked(True)

        # Fixed width for sidebar
        self.setFixedWidth(48)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

    def on_button_clicked(self, button_id: int):
        """Handle button click."""
        self.panel_changed.emit(button_id)

    def set_current_panel(self, index: int):
        """Programmatically set the current panel."""
        button = self.button_group.button(index)
        if button:
            button.setChecked(True)

    def current_panel(self) -> int:
        """Get the currently selected panel index."""
        return self.button_group.checkedId()
