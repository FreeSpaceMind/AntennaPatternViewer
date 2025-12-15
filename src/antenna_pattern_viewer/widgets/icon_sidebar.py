"""
Icon sidebar widget for panel navigation.

Provides a vertical strip of icon buttons for switching between panels.
This widget is designed to be reusable across different applications.

Usage:
    # Default configuration (Files, View, Processing, Analysis, Export)
    sidebar = IconSidebar()

    # Custom first panel
    sidebar = IconSidebar(first_panel={"icon": "🔧", "tooltip": "Generator - Configure pattern"})

    # Fully custom panels
    panels = [
        {"icon": "🔧", "tooltip": "Generator"},
        {"icon": "👁", "tooltip": "View"},
        {"icon": "📤", "tooltip": "Export"},
    ]
    sidebar = IconSidebar(panels=panels)
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QButtonGroup, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, Qt, QSize
from PyQt6.QtGui import QIcon
from typing import List, Dict, Optional


# Default panel configurations
DEFAULT_PANELS = [
    {"icon": "📁", "tooltip": "Files - Browse and load patterns", "name": "files"},
    {"icon": "👁", "tooltip": "View - Plot settings and display options", "name": "view"},
    {"icon": "⚙️", "tooltip": "Processing - Pattern modifications", "name": "processing"},
    {"icon": "📊", "tooltip": "Analysis - SWE and near field calculations", "name": "analysis"},
    {"icon": "📤", "tooltip": "Export - Save patterns and plots", "name": "export"},
]


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

    Args:
        panels: List of panel configurations. Each dict should have:
            - "icon": str - The icon text/emoji to display
            - "tooltip": str - Tooltip text for the button
            - "name": str (optional) - Name identifier for the panel
        first_panel: Dict to override just the first panel configuration.
            If provided, replaces the first entry in DEFAULT_PANELS.
        parent: Parent widget
    """

    # Signal emitted when panel selection changes
    panel_changed = pyqtSignal(int)

    # Panel indices (for default configuration)
    PANEL_FIRST = 0  # Custom/Files panel
    PANEL_VIEW = 1
    PANEL_PROCESSING = 2
    PANEL_ANALYSIS = 3
    PANEL_EXPORT = 4

    def __init__(
        self,
        panels: Optional[List[Dict[str, str]]] = None,
        first_panel: Optional[Dict[str, str]] = None,
        parent=None
    ):
        super().__init__(parent)
        self.buttons: List[IconButton] = []

        # Determine panel configuration
        if panels is not None:
            self.panel_configs = panels
        elif first_panel is not None:
            # Use default panels but replace first one
            self.panel_configs = [first_panel] + DEFAULT_PANELS[1:]
        else:
            self.panel_configs = DEFAULT_PANELS.copy()

        self.setup_ui()

    def setup_ui(self):
        """Setup the sidebar UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Create button group for exclusive selection
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)

        # Create buttons from configuration
        for idx, config in enumerate(self.panel_configs):
            btn = IconButton(config["icon"], config["tooltip"])
            self.buttons.append(btn)
            self.button_group.addButton(btn, idx)
            layout.addWidget(btn)

        layout.addStretch()

        # Connect signal
        self.button_group.idClicked.connect(self.on_button_clicked)

        # Set default selection
        if self.buttons:
            self.buttons[0].setChecked(True)

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

    def get_panel_name(self, index: int) -> Optional[str]:
        """Get the name of a panel by index."""
        if 0 <= index < len(self.panel_configs):
            return self.panel_configs[index].get("name")
        return None

    def panel_count(self) -> int:
        """Get the number of panels."""
        return len(self.panel_configs)
