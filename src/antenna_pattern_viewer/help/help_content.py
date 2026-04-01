"""
Help content configuration for AntennaPatternViewer.

Defines navigation structure and resolves documentation files from multiple packages:
- AntennaPatternViewer docs/
- FarFieldSpherical docs/
- SphericalWaveExpansion docs/
"""

import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)

# Documentation directories from each package
# Resolved lazily to handle missing packages gracefully

def _get_apv_docs_dir() -> Path:
    """Get APV docs directory."""
    return Path(__file__).parent.parent.parent.parent / "docs"


def _get_farfield_docs_dir() -> Optional[Path]:
    """Get FarFieldSpherical docs directory via package path."""
    try:
        import farfield_spherical
        pkg_dir = Path(farfield_spherical.__file__).parent
        docs_dir = pkg_dir.parent.parent / "docs"
        if docs_dir.exists():
            return docs_dir
    except (ImportError, AttributeError):
        pass

    # Fallback: try relative path from APV
    fallback = Path(__file__).parent.parent.parent.parent.parent.parent / "FarFieldSpherical" / "docs"
    if fallback.exists():
        return fallback
    return None


def _get_swe_docs_dir() -> Optional[Path]:
    """Get SphericalWaveExpansion docs directory via package path."""
    try:
        import swe
        pkg_dir = Path(swe.__file__).parent
        docs_dir = pkg_dir.parent / "docs"
        if docs_dir.exists():
            return docs_dir
    except (ImportError, AttributeError):
        pass

    # Fallback: try relative path from APV
    fallback = Path(__file__).parent.parent.parent.parent.parent.parent / "spherical_wave_expansion" / "docs"
    if fallback.exists():
        return fallback
    return None


# Navigation structure: List of (category_name, [(item_name, file_path), ...])
# file_path is a key used by get_document_path() to resolve the actual file
HELP_NAVIGATION: List[Tuple[str, List[Tuple[str, Optional[str]]]]] = [
    ("Getting Started", [
        ("Getting Started", "apv:getting_started.md"),
    ]),

    ("User Guide", [
        ("User Guide", "apv:user_guide.md"),
    ]),

    ("Theory", [
        ("Coordinate Systems", "ffs:coordinate_systems.md"),
        ("Polarization", "ffs:polarization.md"),
        ("Pattern Operations", "ffs:pattern_operations.md"),
        ("Analysis Functions", "ffs:analysis.md"),
        ("Spherical Wave Expansion", "swe:swe_theory.md"),
    ]),

    ("Developer Guide", [
        ("Architecture", "apv:architecture.md"),
    ]),
]

# Map panel indices to relevant help sections for context-sensitive help
PANEL_HELP_MAP: Dict[int, str] = {
    0: "apv:getting_started.md",       # Files panel
    1: "apv:user_guide.md",            # View panel
    2: "ffs:pattern_operations.md",    # Processing panel
    3: "swe:swe_theory.md",            # Analysis panel
    4: "apv:user_guide.md",            # Export panel
}


def get_document_path(doc_key: str) -> Optional[Path]:
    """
    Resolve a document key to a filesystem path.

    Document keys use a prefix to identify the source package:
    - "apv:" -> AntennaPatternViewer docs/
    - "ffs:" -> FarFieldSpherical docs/
    - "swe:" -> SphericalWaveExpansion docs/

    Args:
        doc_key: Document key (e.g., "ffs:coordinate_systems.md")

    Returns:
        Full Path to the file, or None if not found
    """
    if ":" in doc_key:
        prefix, filename = doc_key.split(":", 1)
    else:
        prefix, filename = "apv", doc_key

    if prefix == "apv":
        docs_dir = _get_apv_docs_dir()
        if docs_dir:
            path = docs_dir / filename
            if path.exists():
                return path

    elif prefix == "ffs":
        docs_dir = _get_farfield_docs_dir()
        if docs_dir:
            path = docs_dir / filename
            if path.exists():
                return path

    elif prefix == "swe":
        docs_dir = _get_swe_docs_dir()
        if docs_dir:
            path = docs_dir / filename
            if path.exists():
                return path

    return None


def load_document(doc_key: str) -> str:
    """
    Load documentation content from file.

    Args:
        doc_key: Document key (e.g., "ffs:coordinate_systems.md")

    Returns:
        File content as string, or error message if not found
    """
    path = get_document_path(doc_key)

    if path is not None:
        try:
            return path.read_text(encoding='utf-8')
        except Exception as e:
            return f"Error reading file: {e}"

    return f"Document not found: {doc_key}"


def get_all_documents() -> List[Tuple[str, str, str]]:
    """
    Get list of all documents for search indexing.

    Returns:
        List of (doc_key, title, category) tuples
    """
    documents = []
    for category, items in HELP_NAVIGATION:
        for title, doc_key in items:
            if doc_key is not None:
                documents.append((doc_key, title, category))
    return documents


def get_all_doc_dirs() -> List[Path]:
    """
    Get all documentation directories that exist.

    Returns:
        List of Path objects to docs directories
    """
    dirs = []
    apv = _get_apv_docs_dir()
    if apv and apv.exists():
        dirs.append(apv)

    ffs = _get_farfield_docs_dir()
    if ffs:
        dirs.append(ffs)

    swe = _get_swe_docs_dir()
    if swe:
        dirs.append(swe)

    return dirs
