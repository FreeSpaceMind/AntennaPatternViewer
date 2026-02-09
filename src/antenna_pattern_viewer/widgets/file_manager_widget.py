"""
File manager widget for browsing, loading, and managing multiple pattern instances.

Redesigned with improved UX:
- Vertical stacked layout for better space utilization
- Quick access sidebar with favorites and recent locations
- Path breadcrumb navigation
- Search/filter functionality
- File preview panel
- Drag-and-drop support
- Standard file open dialog
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFileDialog, QMessageBox,
    QMenu, QSplitter, QTreeView, QLineEdit,
    QDialog, QDialogButtonBox, QFormLayout, QDoubleSpinBox,
    QToolButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QDir, QSettings
from PyQt6.QtGui import QColor, QFileSystemModel, QDragEnterEvent, QDropEvent
from pathlib import Path
import time
import os

from farfield_spherical import read_cut, read_ffd, load_pattern_npz, read_atams
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


class AtamsFileDialog(QDialog):
    """Dialog for ATAMS file import options."""

    def __init__(self, filename, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Import {filename}")
        self.setup_ui()

    def setup_ui(self):
        from PyQt6.QtWidgets import QCheckBox

        layout = QFormLayout(self)

        # Info label
        info = QLabel(
            "ATAMS files contain per-phi theta grids (non-uniform).\n"
            "You can optionally interpolate to a uniform grid."
        )
        info.setWordWrap(True)
        layout.addRow(info)

        # Interpolate checkbox
        self.interpolate_check = QCheckBox("Interpolate to uniform theta grid")
        self.interpolate_check.setToolTip(
            "If checked, interpolates to the nominal azimuth values from the file header.\n"
            "If unchecked, preserves the actual measured positions (per-phi theta grids)."
        )
        layout.addRow(self.interpolate_check)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_interpolate(self):
        """Return whether to interpolate to uniform grid."""
        return self.interpolate_check.isChecked()


class PathBreadcrumb(QWidget):
    """Clickable breadcrumb path navigation."""

    path_clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(2)
        self.current_path = ""

    def set_path(self, path: str):
        """Update breadcrumb to show given path."""
        self.current_path = path

        # Clear existing buttons
        while self.layout.count():
            child = self.layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Parse path into components
        path_obj = Path(path)
        parts = list(path_obj.parts)

        # Build breadcrumb buttons
        accumulated_path = ""
        for i, part in enumerate(parts):
            if i == 0:
                accumulated_path = part
                if not accumulated_path.endswith(os.sep):
                    accumulated_path += os.sep
            else:
                accumulated_path = str(Path(accumulated_path) / part)

            btn = QToolButton()
            btn.setText(part if part != os.sep else "/")
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
            btn.setAutoRaise(True)
            btn.setProperty("path", accumulated_path)
            btn.clicked.connect(self._on_button_clicked)
            self.layout.addWidget(btn)

            # Add separator except for last
            if i < len(parts) - 1:
                sep = QLabel(">")
                sep.setStyleSheet("color: gray; padding: 0 2px;")
                self.layout.addWidget(sep)

        self.layout.addStretch()

    def _on_button_clicked(self):
        btn = self.sender()
        if btn:
            path = btn.property("path")
            self.path_clicked.emit(path)


class QuickAccessItem(QListWidgetItem):
    """List item for quick access locations."""

    def __init__(self, name: str, path: str, icon_char: str = ""):
        display = f"{icon_char} {name}" if icon_char else name
        super().__init__(display)
        self.setData(Qt.ItemDataRole.UserRole, path)
        self.setToolTip(path)


class FileManagerWidget(QWidget):
    """
    Redesigned file manager widget for pattern loading and management.

    Features:
    - Toolbar with Open dialog and Recent files
    - Quick access sidebar with favorites
    - Path breadcrumb navigation
    - Search/filter functionality
    - File preview panel
    - Drag-and-drop support
    - Loaded patterns management
    - Comparison set management
    """

    # Settings keys
    SETTINGS_RECENT_FILES = "file_manager/recent_files"
    SETTINGS_FAVORITES = "file_manager/favorites"
    SETTINGS_LAST_DIR = "file_manager/last_directory"
    MAX_RECENT_FILES = 10
    MAX_RECENT_LOCATIONS = 5

    SUPPORTED_EXTENSIONS = ["*.cut", "*.ffd", "*.npz", "*.sph", "*.atams"]
    FILE_FILTER = "Pattern Files (*.cut *.ffd *.npz *.sph *.atams);;All Files (*)"

    def __init__(self, data_model, parent=None):
        super().__init__(parent)
        self.data_model = data_model
        self.settings = QSettings("AntennaPatternViewer", "FileManager")
        self.recent_files = []
        self.recent_locations = []
        self.favorites = []

        self.load_settings()
        self.setup_ui()
        self.connect_signals()
        self.setAcceptDrops(True)

    def load_settings(self):
        """Load saved settings."""
        self.recent_files = self.settings.value(self.SETTINGS_RECENT_FILES, []) or []
        self.favorites = self.settings.value(self.SETTINGS_FAVORITES, []) or []
        last_dir = self.settings.value(self.SETTINGS_LAST_DIR, QDir.homePath())
        self.current_directory = last_dir if Path(last_dir).exists() else QDir.homePath()

        # Extract recent locations from recent files
        self._update_recent_locations()

    def save_settings(self):
        """Save settings."""
        self.settings.setValue(self.SETTINGS_RECENT_FILES, self.recent_files)
        self.settings.setValue(self.SETTINGS_FAVORITES, self.favorites)
        self.settings.setValue(self.SETTINGS_LAST_DIR, self.current_directory)

    def _update_recent_locations(self):
        """Update recent locations from recent files."""
        locations = []
        for f in self.recent_files:
            dir_path = str(Path(f).parent)
            if dir_path not in locations:
                locations.append(dir_path)
        self.recent_locations = locations[:self.MAX_RECENT_LOCATIONS]

    def setup_ui(self):
        """Setup the file manager UI with new vertical layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # === TOOLBAR ===
        toolbar = self.create_toolbar()
        main_layout.addWidget(toolbar)

        # === PATH BREADCRUMB ===
        self.breadcrumb = PathBreadcrumb()
        self.breadcrumb.path_clicked.connect(self.navigate_to_path)
        self.breadcrumb.set_path(self.current_directory)
        main_layout.addWidget(self.breadcrumb)

        # === MAIN BROWSER AREA (Splitter) ===
        browser_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Quick Access Panel (left)
        quick_access = self.create_quick_access_panel()
        browser_splitter.addWidget(quick_access)

        # File List Panel (right)
        file_panel = self.create_file_list_panel()
        browser_splitter.addWidget(file_panel)

        browser_splitter.setStretchFactor(0, 1)
        browser_splitter.setStretchFactor(1, 3)
        browser_splitter.setSizes([150, 400])

        main_layout.addWidget(browser_splitter, stretch=2)

        # === FILE PREVIEW ===
        self.preview_label = QLabel("Select a file to see details")
        self.preview_label.setStyleSheet("""
            QLabel {
                background-color: palette(base);
                border: 1px solid palette(mid);
                border-radius: 3px;
                padding: 5px;
                color: palette(text);
            }
        """)
        self.preview_label.setMaximumHeight(50)
        main_layout.addWidget(self.preview_label)

        # Note: Loaded Patterns and Comparison sections moved to PatternStrip widget

    def create_toolbar(self) -> QWidget:
        """Create toolbar with Open, Recent, and Search."""
        toolbar = QWidget()
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Open Files button
        self.open_btn = QPushButton("Open Files...")
        self.open_btn.setToolTip("Open file dialog to select pattern files")
        self.open_btn.clicked.connect(self.open_file_dialog)
        layout.addWidget(self.open_btn)

        # Recent Files dropdown
        self.recent_btn = QToolButton()
        self.recent_btn.setText("Recent")
        self.recent_btn.setToolTip("Recently opened files")
        self.recent_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.recent_menu = QMenu(self)
        self.recent_btn.setMenu(self.recent_menu)
        self._update_recent_menu()
        layout.addWidget(self.recent_btn)

        layout.addStretch()

        # Search/Filter box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Filter files...")
        self.search_box.setClearButtonEnabled(True)
        self.search_box.setMaximumWidth(200)
        self.search_box.textChanged.connect(self.filter_files)
        layout.addWidget(self.search_box)

        return toolbar

    def create_quick_access_panel(self) -> QWidget:
        """Create quick access sidebar."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Title
        title = QLabel("<b>Quick Access</b>")
        layout.addWidget(title)

        # Quick access list
        self.quick_access_list = QListWidget()
        self.quick_access_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.quick_access_list.customContextMenuRequested.connect(self.show_quick_access_menu)
        self.quick_access_list.itemDoubleClicked.connect(self.on_quick_access_clicked)
        layout.addWidget(self.quick_access_list)

        # Add favorites button
        add_fav_btn = QPushButton("+ Add Current Folder")
        add_fav_btn.setToolTip("Add current folder to favorites")
        add_fav_btn.clicked.connect(self.add_current_to_favorites)
        layout.addWidget(add_fav_btn)

        self._refresh_quick_access()

        return widget

    def _refresh_quick_access(self):
        """Refresh quick access list."""
        self.quick_access_list.clear()

        # Add default locations
        home = QDir.homePath()
        desktop = str(Path(home) / "Desktop")
        documents = str(Path(home) / "Documents")

        # Default locations section
        self.quick_access_list.addItem(QuickAccessItem("Home", home, "~"))
        if Path(desktop).exists():
            self.quick_access_list.addItem(QuickAccessItem("Desktop", desktop, "~"))
        if Path(documents).exists():
            self.quick_access_list.addItem(QuickAccessItem("Documents", documents, "~"))

        # Separator
        sep_item = QListWidgetItem("--- Favorites ---")
        sep_item.setFlags(Qt.ItemFlag.NoItemFlags)
        sep_item.setForeground(QColor(128, 128, 128))
        self.quick_access_list.addItem(sep_item)

        # Favorites
        for fav in self.favorites:
            if Path(fav).exists():
                name = Path(fav).name or fav
                self.quick_access_list.addItem(QuickAccessItem(name, fav, "★"))

        # Recent locations separator
        if self.recent_locations:
            sep_item2 = QListWidgetItem("--- Recent ---")
            sep_item2.setFlags(Qt.ItemFlag.NoItemFlags)
            sep_item2.setForeground(QColor(128, 128, 128))
            self.quick_access_list.addItem(sep_item2)

            for loc in self.recent_locations:
                if Path(loc).exists():
                    name = Path(loc).name or loc
                    self.quick_access_list.addItem(QuickAccessItem(name, loc, ""))

    def create_file_list_panel(self) -> QWidget:
        """Create file browser list panel."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # File system model
        self.file_model = QFileSystemModel()
        self.file_model.setRootPath(self.current_directory)
        self.file_model.setNameFilters(self.SUPPORTED_EXTENSIONS)
        self.file_model.setNameFilterDisables(False)

        # File tree view
        self.file_tree = QTreeView()
        self.file_tree.setModel(self.file_model)
        self.file_tree.setRootIndex(self.file_model.index(self.current_directory))
        self.file_tree.setSelectionMode(QTreeView.SelectionMode.ExtendedSelection)
        self.file_tree.setColumnWidth(0, 200)

        # Hide unnecessary columns for cleaner look
        self.file_tree.setColumnHidden(2, True)  # Type

        # Connect selection change for preview
        self.file_tree.selectionModel().selectionChanged.connect(self.on_file_selection_changed)
        self.file_tree.doubleClicked.connect(self.on_file_double_clicked)

        layout.addWidget(self.file_tree)

        # Load button
        load_layout = QHBoxLayout()
        load_layout.addStretch()

        self.load_btn = QPushButton("Load Selected")
        self.load_btn.setToolTip("Load selected pattern files")
        self.load_btn.clicked.connect(self.load_selected_files)
        load_layout.addWidget(self.load_btn)

        layout.addLayout(load_layout)

        return widget

    def connect_signals(self):
        """Connect data model signals."""
        # Note: Pattern management moved to PatternStrip widget
        pass

    # === FILE OPERATIONS ===

    def open_file_dialog(self):
        """Open standard file dialog."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Open Pattern Files",
            self.current_directory,
            self.FILE_FILTER
        )

        if files:
            # Update current directory
            self.current_directory = str(Path(files[0]).parent)
            self.breadcrumb.set_path(self.current_directory)
            self.file_tree.setRootIndex(self.file_model.index(self.current_directory))
            self.save_settings()

            # Load each file
            for file_path in files:
                self.load_pattern_file(Path(file_path))

    def load_selected_files(self):
        """Load selected files from browser."""
        selected_indexes = self.file_tree.selectedIndexes()
        if not selected_indexes:
            return

        # Get unique file paths
        file_paths = set()
        for index in selected_indexes:
            if index.column() == 0:
                file_path = Path(self.file_model.filePath(index))
                if file_path.is_file():
                    file_paths.add(file_path)

        for file_path in file_paths:
            self.load_pattern_file(file_path)

    def load_pattern_file(self, file_path: Path):
        """Load a pattern file and create an instance."""
        try:
            suffix = file_path.suffix.lower()

            if suffix == '.cut':
                dialog = CutFileDialog(file_path.name, self)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    freq_start, freq_end = dialog.get_frequencies()
                    pattern = read_cut(str(file_path), freq_start, freq_end)
                else:
                    return

            elif suffix == '.ffd':
                pattern = read_ffd(str(file_path))

            elif suffix == '.npz':
                pattern, _ = load_pattern_npz(str(file_path))

            elif suffix == '.sph':
                from farfield_spherical.io.readers import read_ticra_sph
                from farfield_spherical.io.swe_utils import create_pattern_from_swe

                swe = read_ticra_sph(str(file_path))
                pattern = create_pattern_from_swe(swe)

            elif suffix == '.atams':
                dialog = AtamsFileDialog(file_path.name, self)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    interpolate = dialog.get_interpolate()
                    pattern = read_atams(str(file_path), interpolate=interpolate)
                else:
                    return

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

            # Update recent files
            self._add_to_recent(str(file_path))

        except Exception as e:
            QMessageBox.critical(
                self,
                "Load Error",
                f"Failed to load {file_path.name}:\n{str(e)}"
            )

    def _add_to_recent(self, file_path: str):
        """Add file to recent files list."""
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
        self.recent_files.insert(0, file_path)
        self.recent_files = self.recent_files[:self.MAX_RECENT_FILES]
        self._update_recent_locations()
        self._update_recent_menu()
        self._refresh_quick_access()
        self.save_settings()

    def _update_recent_menu(self):
        """Update the recent files menu."""
        self.recent_menu.clear()

        if not self.recent_files:
            action = self.recent_menu.addAction("No recent files")
            action.setEnabled(False)
            return

        for file_path in self.recent_files:
            path = Path(file_path)
            if path.exists():
                action = self.recent_menu.addAction(f"{path.name}  ({path.parent})")
                action.setData(file_path)
                action.triggered.connect(self._on_recent_file_clicked)

        self.recent_menu.addSeparator()
        clear_action = self.recent_menu.addAction("Clear Recent Files")
        clear_action.triggered.connect(self._clear_recent_files)

    def _on_recent_file_clicked(self):
        """Handle click on recent file."""
        action = self.sender()
        if action:
            file_path = action.data()
            if file_path and Path(file_path).exists():
                self.load_pattern_file(Path(file_path))

    def _clear_recent_files(self):
        """Clear recent files list."""
        self.recent_files = []
        self.recent_locations = []
        self._update_recent_menu()
        self._refresh_quick_access()
        self.save_settings()


    # === NAVIGATION ===

    def navigate_to_path(self, path: str):
        """Navigate file browser to path."""
        if Path(path).exists():
            self.current_directory = path
            self.breadcrumb.set_path(path)
            self.file_tree.setRootIndex(self.file_model.index(path))
            self.save_settings()

    def on_quick_access_clicked(self, item: QListWidgetItem):
        """Handle double-click on quick access item."""
        path = item.data(Qt.ItemDataRole.UserRole)
        if path and Path(path).exists():
            self.navigate_to_path(path)

    def on_file_double_clicked(self, index):
        """Handle double-click on file tree item."""
        file_path = Path(self.file_model.filePath(index))

        if file_path.is_dir():
            # Navigate into directory
            self.navigate_to_path(str(file_path))
        elif file_path.is_file():
            # Load the file
            self.load_pattern_file(file_path)

    def filter_files(self, text: str):
        """Filter files by search text."""
        if text:
            # Add wildcard for partial matching
            filters = [f"*{text}*{ext[1:]}" for ext in self.SUPPORTED_EXTENSIONS]
            self.file_model.setNameFilters(filters)
        else:
            self.file_model.setNameFilters(self.SUPPORTED_EXTENSIONS)

    # === FILE PREVIEW ===

    def on_file_selection_changed(self, selected, deselected):
        """Update preview when file selection changes."""
        indexes = self.file_tree.selectedIndexes()

        if not indexes:
            self.preview_label.setText("Select a file to see details")
            return

        # Get first selected file (column 0)
        for index in indexes:
            if index.column() == 0:
                file_path = Path(self.file_model.filePath(index))
                if file_path.is_file():
                    self._update_preview(file_path)
                    return

        self.preview_label.setText("Select a file to see details")

    def _update_preview(self, file_path: Path):
        """Update the preview label with file info."""
        try:
            stat = file_path.stat()
            size = stat.st_size
            modified = time.strftime("%Y-%m-%d %H:%M", time.localtime(stat.st_mtime))

            # Format size
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size / (1024 * 1024):.2f} MB"

            ext_info = {
                '.cut': 'GRASP cut file',
                '.ffd': 'NSI far-field data',
                '.npz': 'NumPy pattern archive',
                '.sph': 'TICRA spherical wave expansion',
                '.atams': 'ATAMS measurement file'
            }
            file_type = ext_info.get(file_path.suffix.lower(), 'Unknown type')

            self.preview_label.setText(
                f"<b>{file_path.name}</b>  |  {file_type}  |  {size_str}  |  Modified: {modified}"
            )
        except Exception:
            self.preview_label.setText(f"<b>{file_path.name}</b>")

    # === QUICK ACCESS / FAVORITES ===

    def add_current_to_favorites(self):
        """Add current directory to favorites."""
        if self.current_directory not in self.favorites:
            self.favorites.append(self.current_directory)
            self._refresh_quick_access()
            self.save_settings()

    def show_quick_access_menu(self, pos):
        """Show context menu for quick access items."""
        item = self.quick_access_list.itemAt(pos)
        if not item:
            return

        path = item.data(Qt.ItemDataRole.UserRole)
        if not path:
            return

        # Only show remove option for favorites
        if path in self.favorites:
            menu = QMenu(self)
            remove_action = menu.addAction("Remove from Favorites")
            action = menu.exec(self.quick_access_list.mapToGlobal(pos))

            if action == remove_action:
                self.favorites.remove(path)
                self._refresh_quick_access()
                self.save_settings()

    # === DRAG AND DROP ===

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter."""
        if event.mimeData().hasUrls():
            # Check if any URLs are supported files
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    path = Path(url.toLocalFile())
                    if path.suffix.lower() in ['.cut', '.ffd', '.npz', '.sph', '.atams']:
                        event.acceptProposedAction()
                        return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        """Handle file drop."""
        for url in event.mimeData().urls():
            if url.isLocalFile():
                path = Path(url.toLocalFile())
                if path.suffix.lower() in ['.cut', '.ffd', '.npz', '.sph', '.atams']:
                    self.load_pattern_file(path)
        event.acceptProposedAction()

    # Note: Pattern management functions moved to PatternStrip widget
