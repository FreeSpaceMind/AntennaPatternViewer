"""
File manager widget for browsing, loading, and managing multiple pattern instances.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFileDialog, QMessageBox,
    QInputDialog, QMenu, QSplitter, QTreeView,
    QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QSpinBox,
    QDoubleSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QDir
from PyQt6.QtGui import QIcon, QColor, QFileSystemModel
from pathlib import Path
import time

from farfield_spherical import read_cut, read_ffd, load_pattern_npz
from ..pattern_instance import PatternInstance

class CutFileDialog(QDialog):
    """Dialog for getting frequency information for .cut files."""
    
    def __init__(self, filename, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Import {filename}")
        self.setup_ui()
    
    def setup_ui(self):
        layout = QFormLayout(self)
        
        # Frequency start
        self.freq_start_spin = QDoubleSpinBox()
        self.freq_start_spin.setRange(0.001, 1000.0)
        self.freq_start_spin.setValue(1.0)
        self.freq_start_spin.setSuffix(" GHz")
        self.freq_start_spin.setDecimals(3)
        layout.addRow("Start Frequency:", self.freq_start_spin)
        
        # Frequency end
        self.freq_end_spin = QDoubleSpinBox()
        self.freq_end_spin.setRange(0.001, 1000.0)
        self.freq_end_spin.setValue(1.0)
        self.freq_end_spin.setSuffix(" GHz")
        self.freq_end_spin.setDecimals(3)
        layout.addRow("End Frequency:", self.freq_end_spin)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
    
    def get_frequencies(self):
        """Return frequencies in Hz."""
        return (
            self.freq_start_spin.value() * 1e9,
            self.freq_end_spin.value() * 1e9
        )
    
class FileManagerWidget(QWidget):
    """
    File manager widget for pattern loading and management.
    
    Features:
    - File browser for selecting patterns
    - Imported patterns list
    - Load/unload controls
    - Active pattern selection
    - Comparison set management
    - Pattern renaming
    """
    
    def __init__(self, data_model, parent=None):
        super().__init__(parent)
        self.data_model = data_model
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        """Setup the file manager UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Create main horizontal splitter for browser/buttons/imported
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side: File Browser
        browser_widget = self.create_browser_panel()
        main_splitter.addWidget(browser_widget)
        
        # Center: Load/Unload buttons
        button_widget = self.create_button_panel()
        main_splitter.addWidget(button_widget)
        
        # Right side: Imported Patterns
        imported_widget = self.create_imported_panel()
        main_splitter.addWidget(imported_widget)
        
        # Set splitter proportions
        main_splitter.setStretchFactor(0, 2)  # Browser gets more space
        main_splitter.setStretchFactor(1, 0)  # Buttons minimal
        main_splitter.setStretchFactor(2, 2)  # Imported list gets more space
        
        layout.addWidget(main_splitter)
        
        # Add comparison panel below (collapsible)
        comparison_panel = self.create_comparison_panel()
        layout.addWidget(comparison_panel)
    
    def create_browser_panel(self) -> QWidget:
        """Create the file browser panel."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Title
        title = QLabel("<b>Browser</b>")
        layout.addWidget(title)
        
        # File system model and tree view
        self.file_model = QFileSystemModel()
        self.file_model.setRootPath(QDir.homePath())
        
        # Set name filters for pattern files
        self.file_model.setNameFilters(["*.cut", "*.ffd", "*.npz", "*.sph"])
        self.file_model.setNameFilterDisables(False)
        
        self.file_tree = QTreeView()
        self.file_tree.setModel(self.file_model)
        self.file_tree.setRootIndex(self.file_model.index(QDir.homePath()))
        
        # Configure tree view
        self.file_tree.setSelectionMode(QTreeView.SelectionMode.ExtendedSelection)
        self.file_tree.setColumnWidth(0, 250)
        
        layout.addWidget(self.file_tree)
        
        return widget
    
    def create_button_panel(self) -> QWidget:
        """Create the load/unload button panel."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.addStretch()
        
        # Load button (right arrow)
        self.load_btn = QPushButton("→")
        self.load_btn.setToolTip("Load selected file(s)")
        self.load_btn.setMaximumWidth(50)
        self.load_btn.clicked.connect(self.load_selected_files)
        layout.addWidget(self.load_btn)
        
        layout.addSpacing(10)
        
        # Unload button (left arrow)
        self.unload_btn = QPushButton("←")
        self.unload_btn.setToolTip("Unload selected pattern(s)")
        self.unload_btn.setMaximumWidth(50)
        self.unload_btn.clicked.connect(self.unload_selected_patterns)
        layout.addWidget(self.unload_btn)
        
        layout.addStretch()
        
        return widget
    
    def create_imported_panel(self) -> QWidget:
        """Create the imported patterns panel."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Title
        title = QLabel("<b>Imported Patterns</b>")
        layout.addWidget(title)
        
        # Imported patterns list
        self.imported_list = QListWidget()
        self.imported_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.imported_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.imported_list.customContextMenuRequested.connect(self.show_context_menu)
        self.imported_list.itemDoubleClicked.connect(self.on_item_double_clicked)
        layout.addWidget(self.imported_list)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.set_active_btn = QPushButton("Set Active")
        self.set_active_btn.clicked.connect(self.set_active_pattern)
        button_layout.addWidget(self.set_active_btn)
        
        self.add_comparison_btn = QPushButton("Add to Comparison")
        self.add_comparison_btn.clicked.connect(self.add_to_comparison)
        button_layout.addWidget(self.add_comparison_btn)
        
        layout.addLayout(button_layout)
        
        return widget
    
    def create_comparison_panel(self) -> QWidget:
        """Create the collapsible comparison panel."""
        from antenna_pattern_viewer.widgets.collapsible_group import CollapsibleGroupBox
        
        # Create collapsible group (starts collapsed by default)
        self.comparison_group = CollapsibleGroupBox("Comparison Set")
        
        # Comparison list
        self.comparison_list = QListWidget()
        self.comparison_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.comparison_list.setMaximumHeight(150)
        self.comparison_group.addWidget(self.comparison_list)
        
        # Remove button
        self.remove_comparison_btn = QPushButton("Remove from Comparison")
        self.remove_comparison_btn.clicked.connect(self.remove_from_comparison)
        self.comparison_group.addWidget(self.remove_comparison_btn)
        
        return self.comparison_group

    def connect_signals(self):
        """Connect signals."""
        self.data_model.instances_changed.connect(self.refresh_imported_list)
        self.data_model.active_instance_changed.connect(self.on_active_changed)
        self.data_model.comparison_set_changed.connect(self.on_comparison_changed)
    
    def load_selected_files(self):
        """Load selected file(s) from browser."""
        selected_indexes = self.file_tree.selectedIndexes()
        if not selected_indexes:
            return
        
        # Get unique file paths (multiple columns selected)
        file_paths = set()
        for index in selected_indexes:
            if index.column() == 0:  # Only process name column
                file_path = Path(self.file_model.filePath(index))
                if file_path.is_file():
                    file_paths.add(file_path)
        
        # Load each file
        for file_path in file_paths:
            self.load_pattern_file(file_path)
    
    def load_pattern_file(self, file_path: Path):
        """Load a pattern file and create an instance."""
        try:
            # Determine file type and load
            suffix = file_path.suffix.lower()
            
            if suffix == '.cut':
                # Get frequency information from user
                dialog = CutFileDialog(file_path.name, self)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    freq_start, freq_end = dialog.get_frequencies()
                    pattern = read_cut(str(file_path), freq_start, freq_end)
                else:
                    return  # User cancelled
                    
            elif suffix == '.ffd':
                pattern = read_ffd(str(file_path))
                
            elif suffix == '.npz':
                pattern, _ = load_pattern_npz(str(file_path))
                
            elif suffix == '.sph':
                # Read SWE and convert directly to pattern
                from farfield_spherical.io.readers import read_ticra_sph
                from farfield_spherical.io.swe_utils import create_pattern_from_swe
                
                swe = read_ticra_sph(str(file_path))
                pattern = create_pattern_from_swe(swe)
                    
            else:
                raise ValueError(f"Unsupported file format: {suffix}")
            
            # Create instance
            instance = PatternInstance(
                pattern=pattern,
                source_file=file_path,
                display_name=file_path.name,
                load_timestamp=time.time()
            )
            
            # Add to model
            self.data_model.add_instance(instance)
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Load Error",
                f"Failed to load {file_path.name}:\n{str(e)}"
            )

    def unload_selected_patterns(self):
        """Unload selected pattern(s) from imported list."""
        selected_items = self.imported_list.selectedItems()
        if not selected_items:
            return
        
        for item in selected_items:
            instance_id = item.data(Qt.ItemDataRole.UserRole)
            self.data_model.remove_instance(instance_id)
    
    def refresh_imported_list(self):
        """Refresh the imported patterns list."""
        self.imported_list.clear()
        
        active_id = self.data_model.get_active_instance()
        active_id = active_id.instance_id if active_id else None
        
        comparison_ids = {inst.instance_id for inst in self.data_model.get_comparison_instances()}
        
        for instance in self.data_model.get_all_instances():
            item = QListWidgetItem(instance.display_name)
            item.setData(Qt.ItemDataRole.UserRole, instance.instance_id)
            
            # Mark active pattern
            if instance.instance_id == active_id:
                font = item.font()
                font.setBold(True)
                item.setFont(font)
                item.setBackground(QColor(200, 230, 255))
                item.setText(f"✓ {instance.display_name}")
            
            # Mark comparison patterns
            if instance.instance_id in comparison_ids:
                item.setForeground(QColor(0, 100, 200))
            
            self.imported_list.addItem(item)
        
        # Also refresh comparison list
        self.refresh_comparison_list()

    def refresh_comparison_list(self):
        """Refresh the comparison set list."""
        self.comparison_list.clear()
        
        comparison_instances = self.data_model.get_comparison_instances()
        
        for instance in comparison_instances:
            item = QListWidgetItem(instance.display_name)
            item.setData(Qt.ItemDataRole.UserRole, instance.instance_id)
            self.comparison_list.addItem(item)
        
        # Update group title with count
        count = len(comparison_instances)
        self.comparison_group.setTitle(f"Comparison Set ({count})")

    def remove_from_comparison(self):
        """Remove selected patterns from comparison set."""
        # Get selection from comparison list if it has focus
        if self.comparison_list.hasFocus():
            selected_items = self.comparison_list.selectedItems()
        else:
            # Otherwise use imported list selection
            selected_items = self.imported_list.selectedItems()
        
        for item in selected_items:
            instance_id = item.data(Qt.ItemDataRole.UserRole)
            self.data_model.remove_from_comparison(instance_id)
    
    def set_active_pattern(self):
        """Set selected pattern as active."""
        selected_items = self.imported_list.selectedItems()
        if not selected_items:
            return
        
        # Use first selected
        item = selected_items[0]
        instance_id = item.data(Qt.ItemDataRole.UserRole)
        self.data_model.set_active_instance(instance_id)
    
    def add_to_comparison(self):
        """Add selected patterns to comparison set."""
        selected_items = self.imported_list.selectedItems()
        for item in selected_items:
            instance_id = item.data(Qt.ItemDataRole.UserRole)
            self.data_model.add_to_comparison(instance_id)

    def show_context_menu(self, pos):
        """Show context menu for imported pattern."""
        item = self.imported_list.itemAt(pos)
        if not item:
            return
        
        menu = QMenu(self)
        
        rename_action = menu.addAction("Rename")
        duplicate_action = menu.addAction("Duplicate")
        menu.addSeparator()
        delete_action = menu.addAction("Delete")
        
        action = menu.exec(self.imported_list.mapToGlobal(pos))
        
        instance_id = item.data(Qt.ItemDataRole.UserRole)
        
        if action == rename_action:
            self.rename_pattern(instance_id)
        elif action == duplicate_action:
            self.duplicate_pattern(instance_id)
        elif action == delete_action:
            self.data_model.remove_instance(instance_id)
    
    def rename_pattern(self, instance_id: str):
        """Rename a pattern instance."""
        instance = self.data_model.get_instance(instance_id)
        if not instance:
            return
        
        new_name, ok = QInputDialog.getText(
            self,
            "Rename Pattern",
            "Enter new name:",
            text=instance.display_name
        )
        
        if ok and new_name:
            self.data_model.rename_instance(instance_id, new_name)
    
    def duplicate_pattern(self, instance_id: str):
        """Duplicate a pattern instance."""
        instance = self.data_model.get_instance(instance_id)
        if not instance:
            return
        
        # Ask for new name
        new_name, ok = QInputDialog.getText(
            self,
            "Duplicate Pattern",
            "Enter name for duplicate:",
            text=f"{instance.display_name} (copy)"
        )
        
        if ok and new_name:
            new_instance = instance.clone(new_name)
            self.data_model.add_instance(new_instance)
    
    def on_item_double_clicked(self, item):
        """Handle double-click on imported pattern."""
        instance_id = item.data(Qt.ItemDataRole.UserRole)
        self.data_model.set_active_instance(instance_id)
    
    def on_active_changed(self, instance):
        """Handle active instance change."""
        self.refresh_imported_list()
    
    def on_comparison_changed(self, instance_ids):
        """Handle comparison set change."""
        self.refresh_comparison_list()
        self.refresh_imported_list()