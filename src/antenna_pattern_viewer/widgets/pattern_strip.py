"""
Pattern strip widget showing loaded patterns as clickable chips.

Always visible at the top of the left panel, provides quick access to
switch between patterns and manage the comparison set.
"""
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QScrollArea, QMenu,
    QSizePolicy, QFileDialog
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor
from pathlib import Path


class PatternChip(QPushButton):
    """Clickable chip representing a loaded pattern."""

    def __init__(self, instance_id: str, display_name: str, parent=None):
        super().__init__(parent)
        self.instance_id = instance_id
        self.display_name = display_name
        self.is_active = False
        self.in_comparison = False

        self.setText(display_name)
        self.setToolTip(display_name)
        self.setCheckable(False)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.update_style()

    def set_active(self, active: bool):
        """Set whether this pattern is the active one."""
        self.is_active = active
        self.update_display()

    def set_in_comparison(self, in_comparison: bool):
        """Set whether this pattern is in the comparison set."""
        self.in_comparison = in_comparison
        self.update_display()

    def update_display(self):
        """Update the display text and style based on state."""
        prefix = ""
        if self.is_active:
            prefix += "✓ "
        if self.in_comparison and not self.is_active:
            prefix += "◆ "
        elif self.in_comparison and self.is_active:
            # Both active and in comparison
            prefix = "✓◆ "

        self.setText(f"{prefix}{self.display_name}")
        self.update_style()

    def update_style(self):
        """Update the button style based on state."""
        if self.is_active:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #cce5ff;
                    border: 1px solid #99caff;
                    border-radius: 10px;
                    padding: 4px 8px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #b3d9ff;
                }
            """)
        elif self.in_comparison:
            self.setStyleSheet("""
                QPushButton {
                    background-color: palette(button);
                    border: 1px solid #0064c8;
                    border-radius: 10px;
                    padding: 4px 8px;
                    color: #0064c8;
                }
                QPushButton:hover {
                    background-color: palette(midlight);
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: palette(button);
                    border: 1px solid palette(mid);
                    border-radius: 10px;
                    padding: 4px 8px;
                }
                QPushButton:hover {
                    background-color: palette(midlight);
                }
            """)


class PatternStrip(QWidget):
    """
    Horizontal strip showing loaded patterns as clickable chips.

    Features:
    - Shows all loaded patterns
    - Active pattern highlighted with checkmark and blue background
    - Comparison patterns marked with diamond
    - Left-click to set active
    - Right-click context menu for actions
    - [+] button to open file dialog
    """

    # Signals
    pattern_selected = pyqtSignal(str)  # Emits instance_id
    add_pattern_requested = pyqtSignal()  # Request to open file dialog

    def __init__(self, data_model, parent=None):
        super().__init__(parent)
        self.data_model = data_model
        self.chips: dict[str, PatternChip] = {}

        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        """Setup the strip UI."""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 2, 0, 2)
        main_layout.setSpacing(0)

        # Scroll area for pattern chips
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setFixedHeight(36)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)

        # Container for chips
        self.chips_container = QWidget()
        self.chips_layout = QHBoxLayout(self.chips_container)
        self.chips_layout.setContentsMargins(4, 0, 4, 0)
        self.chips_layout.setSpacing(4)
        self.chips_layout.addStretch()

        self.scroll_area.setWidget(self.chips_container)
        main_layout.addWidget(self.scroll_area)

        # Add button
        self.add_btn = QPushButton("+")
        self.add_btn.setToolTip("Load pattern file")
        self.add_btn.setFixedSize(28, 28)
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: palette(button);
                border: 1px solid palette(mid);
                border-radius: 14px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: palette(midlight);
            }
        """)
        self.add_btn.clicked.connect(self.add_pattern_requested.emit)
        main_layout.addWidget(self.add_btn)

        # Set size policy
        self.setFixedHeight(40)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def connect_signals(self):
        """Connect to data model signals."""
        self.data_model.instances_changed.connect(self.refresh_chips)
        self.data_model.active_instance_changed.connect(self.on_active_changed)
        self.data_model.comparison_set_changed.connect(self.on_comparison_changed)

    def refresh_chips(self):
        """Refresh the pattern chips from data model."""
        # Get current state
        instances = self.data_model.get_all_instances()
        active_instance = self.data_model.get_active_instance()
        active_id = active_instance.instance_id if active_instance else None
        comparison_ids = {inst.instance_id for inst in self.data_model.get_comparison_instances()}

        # Remove old chips
        for chip in list(self.chips.values()):
            self.chips_layout.removeWidget(chip)
            chip.deleteLater()
        self.chips.clear()

        # Remove stretch
        while self.chips_layout.count():
            item = self.chips_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Create new chips
        for instance in instances:
            chip = PatternChip(instance.instance_id, instance.display_name)
            chip.set_active(instance.instance_id == active_id)
            chip.set_in_comparison(instance.instance_id in comparison_ids)

            # Connect signals
            chip.clicked.connect(lambda checked, iid=instance.instance_id: self.on_chip_clicked(iid))
            chip.customContextMenuRequested.connect(
                lambda pos, iid=instance.instance_id: self.show_context_menu(pos, iid)
            )

            self.chips[instance.instance_id] = chip
            self.chips_layout.addWidget(chip)

        # Add stretch at end
        self.chips_layout.addStretch()

    def on_chip_clicked(self, instance_id: str):
        """Handle chip click - set as active."""
        self.data_model.set_active_instance(instance_id)
        self.pattern_selected.emit(instance_id)

    def on_active_changed(self, instance):
        """Handle active instance change."""
        active_id = instance.instance_id if instance else None

        for iid, chip in self.chips.items():
            chip.set_active(iid == active_id)

    def on_comparison_changed(self, comparison_ids: list):
        """Handle comparison set change."""
        comparison_set = set(comparison_ids)

        for iid, chip in self.chips.items():
            chip.set_in_comparison(iid in comparison_set)

    def show_context_menu(self, pos, instance_id: str):
        """Show context menu for a pattern chip."""
        chip = self.chips.get(instance_id)
        if not chip:
            return

        menu = QMenu(self)

        # Set Active action
        active_instance = self.data_model.get_active_instance()
        if not active_instance or active_instance.instance_id != instance_id:
            set_active_action = menu.addAction("Set as Active")
            set_active_action.triggered.connect(
                lambda: self.data_model.set_active_instance(instance_id)
            )

        # Comparison actions
        comparison_ids = {inst.instance_id for inst in self.data_model.get_comparison_instances()}
        if instance_id in comparison_ids:
            remove_comp_action = menu.addAction("Remove from Comparison")
            remove_comp_action.triggered.connect(
                lambda: self.data_model.remove_from_comparison(instance_id)
            )
        else:
            add_comp_action = menu.addAction("Add to Comparison")
            add_comp_action.triggered.connect(
                lambda: self.data_model.add_to_comparison(instance_id)
            )

        menu.addSeparator()

        # Unload action
        unload_action = menu.addAction("Unload Pattern")
        unload_action.triggered.connect(
            lambda: self.data_model.remove_instance(instance_id)
        )

        # Show menu at chip position
        menu.exec(chip.mapToGlobal(pos))
