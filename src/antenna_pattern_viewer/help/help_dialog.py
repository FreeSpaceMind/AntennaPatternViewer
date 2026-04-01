"""
Help Dialog for AntennaPatternViewer.
Provides technical documentation with navigation, search, and LaTeX equation rendering.

Adapted from UmbraAntennaDesigner's help system. Loads documentation from
multiple packages (APV, FarFieldSpherical, SphericalWaveExpansion).
"""

import logging
from typing import Optional, List

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLineEdit, QPushButton, QSplitter, QLabel, QWidget, QFrame,
    QSizePolicy, QTextBrowser
)
from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QFont, QAction, QKeySequence

from .help_content import HELP_NAVIGATION, PANEL_HELP_MAP, load_document
from .markdown_renderer import MarkdownRenderer
from .help_search import HelpSearchIndex

logger = logging.getLogger(__name__)

# Try to import QWebEngineView for MathJax support
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    HAS_WEBENGINE = True
except ImportError:
    HAS_WEBENGINE = False
    logger.info("PyQt6-WebEngine not available. LaTeX equations will use fallback rendering.")


class HelpDialog(QDialog):
    """
    Help dialog with navigation tree, search, and LaTeX support.

    Features:
    - Hierarchical navigation tree
    - Full-text search across all documentation (APV + FFS + SWE)
    - LaTeX equation rendering via MathJax (requires PyQt6-WebEngine)
    - Navigation history (back/forward)
    - Context-sensitive help (jump to relevant panel docs)
    """

    navigate_requested = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None, initial_section: Optional[str] = None):
        """
        Initialize the help dialog.

        Args:
            parent: Parent widget
            initial_section: Optional doc key to show initially (e.g., "ffs:polarization.md")
        """
        super().__init__(parent)

        self.current_doc_key: Optional[str] = None
        self.history: List[str] = []
        self.history_index: int = -1
        self.search_index = HelpSearchIndex()
        self.renderer = MarkdownRenderer(enable_mathjax=HAS_WEBENGINE)

        self._setup_ui()
        self._populate_navigation()
        self._connect_signals()
        self._build_search_index()

        if initial_section:
            self.navigate_to(initial_section)
        else:
            self._show_home()

    def _setup_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("AntennaPatternViewer - Documentation")
        self.setMinimumSize(900, 650)
        self.resize(1100, 750)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # Header
        header = self._create_header()
        main_layout.addWidget(header)

        # Navigation toolbar
        toolbar = self._create_toolbar()
        main_layout.addWidget(toolbar)

        # Main content area
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Navigation tree
        self.nav_tree = QTreeWidget()
        self.nav_tree.setHeaderHidden(True)
        self.nav_tree.setMinimumWidth(220)
        self.nav_tree.setMaximumWidth(320)
        self.nav_tree.setFont(QFont("Segoe UI", 10))

        # Right: Content display
        if HAS_WEBENGINE:
            self.content_view = QWebEngineView()
            self.content_view.setMinimumWidth(550)
        else:
            self.content_view = QTextBrowser()
            self.content_view.setOpenExternalLinks(True)
            self.content_view.setMinimumWidth(550)
            self.content_view.setFont(QFont("Segoe UI", 10))

        splitter.addWidget(self.nav_tree)
        splitter.addWidget(self.content_view)
        splitter.setSizes([260, 820])

        main_layout.addWidget(splitter, stretch=1)

        # Footer
        footer = self._create_footer()
        main_layout.addWidget(footer)

        self._setup_shortcuts()

    def _create_header(self) -> QWidget:
        """Create header with title and search."""
        header = QFrame()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Documentation")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")

        search_layout = QHBoxLayout()
        search_layout.setSpacing(5)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search documentation...")
        self.search_box.setMinimumWidth(200)
        self.search_box.setMaximumWidth(300)

        self.search_button = QPushButton("Search")
        self.search_button.setMinimumWidth(70)

        search_layout.addWidget(QLabel("Search:"))
        search_layout.addWidget(self.search_box)
        search_layout.addWidget(self.search_button)

        layout.addWidget(title)
        layout.addStretch()
        layout.addLayout(search_layout)

        return header

    def _create_toolbar(self) -> QWidget:
        """Create navigation toolbar."""
        toolbar = QFrame()
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.back_button = QPushButton("< Back")
        self.back_button.setEnabled(False)
        self.back_button.setMinimumWidth(70)
        self.back_button.setToolTip("Go back (Alt+Left)")

        self.forward_button = QPushButton("Forward >")
        self.forward_button.setEnabled(False)
        self.forward_button.setMinimumWidth(70)
        self.forward_button.setToolTip("Go forward (Alt+Right)")

        self.home_button = QPushButton("Home")
        self.home_button.setMinimumWidth(60)
        self.home_button.setToolTip("Go to home page")

        self.breadcrumb_label = QLabel()
        self.breadcrumb_label.setStyleSheet("color: #666; font-style: italic;")

        layout.addWidget(self.back_button)
        layout.addWidget(self.forward_button)
        layout.addWidget(self.home_button)
        layout.addSpacing(20)
        layout.addWidget(self.breadcrumb_label)
        layout.addStretch()

        return toolbar

    def _create_footer(self) -> QWidget:
        """Create footer with status and close button."""
        footer = QFrame()
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(0, 0, 0, 0)

        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #666;")

        self.close_button = QPushButton("Close")
        self.close_button.setMinimumWidth(100)

        layout.addWidget(self.status_label)
        layout.addStretch()
        layout.addWidget(self.close_button)

        return footer

    def _setup_shortcuts(self):
        """Set up keyboard shortcuts."""
        back_action = QAction(self)
        back_action.setShortcut(QKeySequence("Alt+Left"))
        back_action.triggered.connect(self._go_back)
        self.addAction(back_action)

        forward_action = QAction(self)
        forward_action.setShortcut(QKeySequence("Alt+Right"))
        forward_action.triggered.connect(self._go_forward)
        self.addAction(forward_action)

        search_action = QAction(self)
        search_action.setShortcut(QKeySequence("Ctrl+F"))
        search_action.triggered.connect(lambda: self.search_box.setFocus())
        self.addAction(search_action)

    def _populate_navigation(self):
        """Populate the navigation tree."""
        self.nav_tree.clear()

        for category_name, items in HELP_NAVIGATION:
            category_item = QTreeWidgetItem([category_name])
            category_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'category'})
            category_item.setFont(0, QFont("Segoe UI", 10, QFont.Weight.Bold))

            for title, doc_key in items:
                if doc_key is None:
                    continue

                child_item = QTreeWidgetItem([title])
                child_item.setData(0, Qt.ItemDataRole.UserRole, {
                    'type': 'document',
                    'key': doc_key,
                    'title': title,
                    'category': category_name
                })
                category_item.addChild(child_item)

            self.nav_tree.addTopLevelItem(category_item)

        # Expand all categories
        for i in range(self.nav_tree.topLevelItemCount()):
            self.nav_tree.expandItem(self.nav_tree.topLevelItem(i))

    def _connect_signals(self):
        """Connect signals."""
        self.nav_tree.itemClicked.connect(self._on_tree_item_clicked)
        self.nav_tree.itemDoubleClicked.connect(self._on_tree_item_clicked)
        self.search_box.returnPressed.connect(self._perform_search)
        self.search_button.clicked.connect(self._perform_search)
        self.back_button.clicked.connect(self._go_back)
        self.forward_button.clicked.connect(self._go_forward)
        self.home_button.clicked.connect(self._show_home)
        self.close_button.clicked.connect(self.close)

        if not HAS_WEBENGINE:
            self.content_view.setOpenLinks(False)
            self.content_view.anchorClicked.connect(self._on_link_clicked)

    def _on_link_clicked(self, url: QUrl):
        """Handle clicks on internal links."""
        url_str = url.toString()
        if url_str.startswith('doc:'):
            doc_key = url_str[4:]
            self.navigate_to(doc_key)
        elif url_str.startswith('http://') or url_str.startswith('https://'):
            import webbrowser
            webbrowser.open(url_str)

    def _build_search_index(self):
        """Build the search index."""
        try:
            doc_count = self.search_index.build_index()
            self.status_label.setText(f"Indexed {doc_count} documents")
        except Exception as e:
            logger.error(f"Failed to build search index: {e}")
            self.status_label.setText("Search index build failed")

    def _on_tree_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle navigation tree item clicks."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        if data['type'] == 'category':
            if item.isExpanded():
                self.nav_tree.collapseItem(item)
            else:
                self.nav_tree.expandItem(item)
            return

        if data['type'] == 'document':
            self.navigate_to(data['key'])

    def navigate_to(self, doc_key: str):
        """
        Navigate to a specific document.

        Args:
            doc_key: Document key (e.g., "ffs:polarization.md")
        """
        content = load_document(doc_key)

        if content.startswith("Document not found:"):
            self._show_not_found(doc_key)
            return

        # Find title from navigation
        title = doc_key
        for category, items in HELP_NAVIGATION:
            for item_title, item_key in items:
                if item_key == doc_key:
                    title = item_title
                    self.breadcrumb_label.setText(f"{category} > {title}")
                    break

        html = self.renderer.render(content, title=title)

        if HAS_WEBENGINE:
            self.content_view.setHtml(html, QUrl("about:blank"))
        else:
            self.content_view.setHtml(html)

        self._add_to_history(doc_key)
        self.current_doc_key = doc_key
        self._highlight_tree_item(doc_key)

    def _show_not_found(self, doc_key: str):
        """Show placeholder for missing documents."""
        content = f"""
# Document Not Found

The requested document **{doc_key}** could not be loaded.

This may mean:
- The documentation file has not been created yet
- The package containing this documentation is not installed
- The file path has changed

## Available Documents

Use the navigation tree on the left to browse available documentation.
"""
        html = self.renderer.render(content, title="Not Found")

        if HAS_WEBENGINE:
            self.content_view.setHtml(html, QUrl("about:blank"))
        else:
            self.content_view.setHtml(html)

        self.breadcrumb_label.setText(f"Missing: {doc_key}")

    def _show_home(self):
        """Show the home page."""
        home_content = """
# AntennaPatternViewer Documentation

Welcome to the technical documentation for AntennaPatternViewer and its underlying libraries.

## Quick Navigation

Use the navigation tree on the left to browse documentation by topic, or use the search box to find specific content.

### Sections

- **Getting Started** — Installation, launching, supported file formats
- **User Guide** — Complete panel-by-panel reference for the GUI
- **Theory** — Coordinate systems, polarization, pattern operations, analysis, and spherical wave expansion
- **Developer Guide** — MVC architecture, signal flow, adding new features

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+F | Focus search box |
| Alt+Left | Go back |
| Alt+Right | Go forward |

## LaTeX Equations

This documentation includes LaTeX equations for mathematical formulas. For example, the far-field phase center translation:

$$
\\Delta\\phi = k(x\\cos\\phi\\sin\\theta + y\\sin\\phi\\sin\\theta + z\\cos\\theta)
$$

Where $k = 2\\pi f / c$ is the wavenumber.

> **NOTE:** Full LaTeX rendering requires PyQt6-WebEngine. Without it, equations are displayed as Unicode text.
"""
        html = self.renderer.render(home_content, title="Documentation Home")

        if HAS_WEBENGINE:
            self.content_view.setHtml(html, QUrl("about:blank"))
        else:
            self.content_view.setHtml(html)

        self.breadcrumb_label.setText("Home")
        self.current_doc_key = None

    # === HISTORY ===

    def _add_to_history(self, doc_key: str):
        """Add document to navigation history."""
        if self.history_index < len(self.history) - 1:
            self.history = self.history[:self.history_index + 1]

        if not self.history or self.history[-1] != doc_key:
            self.history.append(doc_key)
            self.history_index = len(self.history) - 1

        self._update_nav_buttons()

    def _update_nav_buttons(self):
        """Update back/forward button states."""
        self.back_button.setEnabled(self.history_index > 0)
        self.forward_button.setEnabled(self.history_index < len(self.history) - 1)

    def _go_back(self):
        """Navigate back in history."""
        if self.history_index > 0:
            self.history_index -= 1
            doc_key = self.history[self.history_index]
            self._navigate_without_history(doc_key)
            self._update_nav_buttons()

    def _go_forward(self):
        """Navigate forward in history."""
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            doc_key = self.history[self.history_index]
            self._navigate_without_history(doc_key)
            self._update_nav_buttons()

    def _navigate_without_history(self, doc_key: str):
        """Navigate without adding to history."""
        content = load_document(doc_key)

        if content.startswith("Document not found:"):
            self._show_not_found(doc_key)
            return

        title = doc_key
        for category, items in HELP_NAVIGATION:
            for item_title, item_key in items:
                if item_key == doc_key:
                    title = item_title
                    self.breadcrumb_label.setText(f"{category} > {title}")
                    break

        html = self.renderer.render(content, title=title)

        if HAS_WEBENGINE:
            self.content_view.setHtml(html, QUrl("about:blank"))
        else:
            self.content_view.setHtml(html)

        self.current_doc_key = doc_key
        self._highlight_tree_item(doc_key)

    def _highlight_tree_item(self, doc_key: str):
        """Highlight the corresponding item in the navigation tree."""
        self.nav_tree.clearSelection()

        for i in range(self.nav_tree.topLevelItemCount()):
            category_item = self.nav_tree.topLevelItem(i)
            for j in range(category_item.childCount()):
                child = category_item.child(j)
                data = child.data(0, Qt.ItemDataRole.UserRole)
                if data and data.get('key') == doc_key:
                    child.setSelected(True)
                    self.nav_tree.expandItem(category_item)
                    self.nav_tree.scrollToItem(child)
                    return

    # === SEARCH ===

    def _perform_search(self):
        """Perform search and display results."""
        query = self.search_box.text().strip()
        if not query:
            return

        results = self.search_index.search(query, max_results=20)

        if not results:
            self._show_no_results(query)
            return

        self._show_search_results(query, results)

    def _show_search_results(self, query: str, results: List):
        """Display search results with clickable links."""
        html_content = f'''
        <h1>Search Results</h1>
        <p>Found <strong>{len(results)}</strong> results for "<strong>{query}</strong>"</p>
        <hr>
        '''

        for doc_key, title, category, snippet, score in results:
            html_content += f'''
            <div style="margin-bottom: 20px; padding: 15px; background-color: #f8f9fa;
                        border-radius: 5px; border-left: 4px solid #2980b9;">
                <h3 style="margin-top: 0;">
                    <a href="doc:{doc_key}" style="color: #2c3e50; text-decoration: none;">{title}</a>
                </h3>
                <p style="color: #666; font-size: 90%; margin: 5px 0;"><em>{category}</em></p>
                <p style="margin: 10px 0;">{snippet}</p>
                <p style="margin: 0;">
                    <a href="doc:{doc_key}" style="color: #2980b9;">Open document &rarr;</a>
                </p>
            </div>
            '''

        html = self.renderer.render("", title=f"Search: {query}")
        html = html.replace('<body>', f'<body>{html_content}')

        if HAS_WEBENGINE:
            self.content_view.setHtml(html, QUrl("about:blank"))
        else:
            self.content_view.setHtml(html)

        self.breadcrumb_label.setText(f"Search: {query}")
        self.status_label.setText(f"Found {len(results)} results")

    def _show_no_results(self, query: str):
        """Display no results message."""
        content = f"""
# No Results Found

No documents matching "**{query}**" were found.

## Suggestions

- Try different keywords
- Use fewer or broader terms
- Check spelling

Use the navigation tree on the left to browse available documentation.
"""
        html = self.renderer.render(content, title="No Results")

        if HAS_WEBENGINE:
            self.content_view.setHtml(html, QUrl("about:blank"))
        else:
            self.content_view.setHtml(html)

        self.breadcrumb_label.setText(f"Search: {query}")
        self.status_label.setText("No results found")

    # === CONTEXT HELP ===

    @staticmethod
    def show_context_help(parent: QWidget, panel_index: int):
        """
        Show context-sensitive help for a specific panel.

        Args:
            parent: Parent widget
            panel_index: Index of the current sidebar panel
        """
        doc_key = PANEL_HELP_MAP.get(panel_index)
        dialog = HelpDialog(parent, initial_section=doc_key)
        dialog.exec()


def show_help_dialog(parent: Optional[QWidget] = None, section: Optional[str] = None):
    """
    Convenience function to show the help dialog.

    Args:
        parent: Parent widget
        section: Optional doc key to navigate to
    """
    dialog = HelpDialog(parent, initial_section=section)
    dialog.exec()
