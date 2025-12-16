"""
Pattern list widget showing loaded patterns in a collapsible vertical list.

Replaces the horizontal chip strip with a more scalable list view that
handles many patterns better.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget,
    QListWidgetItem, QMenu, QSizePolicy, QAbstractItemView
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor, QBrush, QFont


class PatternListWidget(QWidget):
    """
    Collapsible list showing loaded patterns.

    Features:
    - Vertical list of patterns (handles many patterns well)
    - Collapsible to save space
    - Active pattern highlighted
    - Checkbox for comparison selection
    - Click to set active
    - Right-click context menu for actions
    - [+] button to open file dialog
    """

    # Signals (same as PatternStrip for compatibility)
    pattern_selected = pyqtSignal(str)  # Emits instance_id
    add_pattern_requested = pyqtSignal()  # Request to open file dialog

    # Height constants
    COLLAPSED_HEIGHT = 32
    EXPANDED_ROW_HEIGHT = 24
    MAX_VISIBLE_ROWS = 6

    def __init__(self, data_model, parent=None):
        super().__init__(parent)
        self.data_model = data_model
        self.is_expanded = True
        self._items: dict[str, QListWidgetItem] = {}

        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        """Setup the list UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header row with collapse button and add button
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(4, 2, 4, 2)
        header_layout.setSpacing(4)

        # Collapse/expand button
        self.collapse_btn = QPushButton("▼ Patterns")
        self.collapse_btn.setFlat(True)
        self.collapse_btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 2px 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: palette(midlight);
            }
        """)
        self.collapse_btn.clicked.connect(self.toggle_expanded)
        header_layout.addWidget(self.collapse_btn, 1)

        # Unload all button
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setToolTip("Unload all patterns")
        self.clear_btn.setFixedHeight(24)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: palette(button);
                border: 1px solid palette(mid);
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #ffcccc;
                border-color: #cc0000;
            }
        """)
        self.clear_btn.clicked.connect(self.unload_all_patterns)
        header_layout.addWidget(self.clear_btn)

        # Add button
        self.add_btn = QPushButton("+")
        self.add_btn.setToolTip("Load pattern file")
        self.add_btn.setFixedSize(24, 24)
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: palette(button);
                border: 1px solid palette(mid);
                border-radius: 12px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: palette(midlight);
            }
        """)
        self.add_btn.clicked.connect(self.add_pattern_requested.emit)
        header_layout.addWidget(self.add_btn)

        main_layout.addWidget(header)

        # Pattern list
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        self.list_widget.setStyleSheet("""
            QListWidget {
                border: 1px solid palette(mid);
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 4px;
            }
            QListWidget::item:selected {
                background-color: #cce5ff;
                color: black;
            }
            QListWidget::item:hover {
                background-color: palette(midlight);
            }
        """)
        main_layout.addWidget(self.list_widget)

        # Size policy
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.update_height()

    def connect_signals(self):
        """Connect to data model signals."""
        self.data_model.instances_changed.connect(self.refresh_list)
        self.data_model.active_instance_changed.connect(self.on_active_changed)
        self.data_model.comparison_set_changed.connect(self.on_comparison_changed)

    def toggle_expanded(self):
        """Toggle between expanded and collapsed states."""
        self.is_expanded = not self.is_expanded
        self.list_widget.setVisible(self.is_expanded)
        self.update_header()
        self.update_height()

    def update_header(self):
        """Update header button text."""
        count = len(self._items)
        if self.is_expanded:
            self.collapse_btn.setText(f"▼ Patterns ({count})")
        else:
            self.collapse_btn.setText(f"► Patterns ({count})")

    def update_height(self):
        """Update widget height based on expanded state and item count."""
        if not self.is_expanded:
            self.setFixedHeight(self.COLLAPSED_HEIGHT)
        else:
            # Calculate height based on number of items
            num_items = min(len(self._items), self.MAX_VISIBLE_ROWS)
            num_items = max(num_items, 1)  # At least 1 row
            list_height = num_items * self.EXPANDED_ROW_HEIGHT + 4
            total_height = self.COLLAPSED_HEIGHT + list_height
            self.setFixedHeight(total_height)

    def refresh_list(self):
        """Refresh the pattern list from data model."""
        # Get current state
        instances = self.data_model.get_all_instances()
        active_instance = self.data_model.get_active_instance()
        active_id = active_instance.instance_id if active_instance else None
        comparison_ids = {inst.instance_id for inst in self.data_model.get_comparison_instances()}

        # Clear and rebuild
        self.list_widget.clear()
        self._items.clear()

        for instance in instances:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, instance.instance_id)

            # Build display text with status indicators
            prefix = ""
            if instance.instance_id == active_id:
                prefix += "✓ "
            if instance.instance_id in comparison_ids:
                prefix += "◆ "

            item.setText(f"{prefix}{instance.display_name}")
            item.setToolTip(instance.display_name)

            # Style based on state
            self._apply_item_style(item, instance.instance_id == active_id,
                                  instance.instance_id in comparison_ids)

            self.list_widget.addItem(item)
            self._items[instance.instance_id] = item

        # Select active item
        if active_id and active_id in self._items:
            self._items[active_id].setSelected(True)

        self.update_header()
        self.update_height()

    def _apply_item_style(self, item: QListWidgetItem, is_active: bool, in_comparison: bool):
        """Apply styling to a list item based on its state."""
        font = QFont()

        if is_active:
            font.setBold(True)
            item.setBackground(QBrush(QColor("#cce5ff")))
        elif in_comparison:
            item.setForeground(QBrush(QColor("#0064c8")))
        else:
            item.setBackground(QBrush())
            item.setForeground(QBrush())

        item.setFont(font)

    def on_item_clicked(self, item: QListWidgetItem):
        """Handle item click - set as active."""
        instance_id = item.data(Qt.ItemDataRole.UserRole)
        if instance_id:
            self.data_model.set_active_instance(instance_id)
            self.pattern_selected.emit(instance_id)

    def unload_all_patterns(self):
        """Unload all patterns from the data model."""
        # Get all instance IDs first (can't modify dict while iterating)
        instance_ids = list(self._items.keys())
        for instance_id in instance_ids:
            self.data_model.remove_instance(instance_id)

    def on_active_changed(self, instance):
        """Handle active instance change."""
        active_id = instance.instance_id if instance else None
        comparison_ids = {inst.instance_id for inst in self.data_model.get_comparison_instances()}

        for iid, item in self._items.items():
            is_active = (iid == active_id)
            in_comparison = (iid in comparison_ids)

            # Update text prefix
            inst = self.data_model.get_instance(iid)
            if inst:
                prefix = ""
                if is_active:
                    prefix += "✓ "
                if in_comparison:
                    prefix += "◆ "
                item.setText(f"{prefix}{inst.display_name}")

            self._apply_item_style(item, is_active, in_comparison)

            if is_active:
                item.setSelected(True)

    def on_comparison_changed(self, comparison_ids: list):
        """Handle comparison set change."""
        comparison_set = set(comparison_ids)
        active_instance = self.data_model.get_active_instance()
        active_id = active_instance.instance_id if active_instance else None

        for iid, item in self._items.items():
            is_active = (iid == active_id)
            in_comparison = (iid in comparison_set)

            # Update text prefix
            inst = self.data_model.get_instance(iid)
            if inst:
                prefix = ""
                if is_active:
                    prefix += "✓ "
                if in_comparison:
                    prefix += "◆ "
                item.setText(f"{prefix}{inst.display_name}")

            self._apply_item_style(item, is_active, in_comparison)

    def show_context_menu(self, pos):
        """Show context menu for a pattern item."""
        item = self.list_widget.itemAt(pos)
        if not item:
            return

        instance_id = item.data(Qt.ItemDataRole.UserRole)
        if not instance_id:
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

        # Show menu
        menu.exec(self.list_widget.mapToGlobal(pos))
