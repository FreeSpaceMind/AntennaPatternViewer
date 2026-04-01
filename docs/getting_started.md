# Getting Started with AntennaPatternViewer

## Overview

AntennaPatternViewer (APV) is a PyQt6-based GUI application for visualizing, processing, and analyzing antenna far-field radiation patterns. It is built on top of the [FarFieldSpherical](../../../FarFieldSpherical/docs/coordinate_systems.md) library and can optionally use the [SphericalWaveExpansion](../../../spherical_wave_expansion/docs/swe_theory.md) package for modal analysis.

APV can run as a standalone application or be embedded as a widget inside larger PyQt6 applications (e.g., UmbraAntennaDesigner).

---

## Installation

### Prerequisites

- Python 3.9 or higher
- PyQt6 >= 6.4.0
- FarFieldSpherical >= 1.0.0 (core pattern library)
- matplotlib >= 3.5.0
- numpy >= 1.21.0

### Install from Source

```bash
cd AntennaPatternViewer
pip install -e .
```

### Optional: Spherical Wave Expansion Support

To enable SWE analysis features (coefficient extraction, near-field evaluation):

```bash
cd spherical_wave_expansion
pip install -e .
```

---

## Launching the Application

### Standalone

```python
import sys
from PyQt6.QtWidgets import QApplication
from antenna_pattern_viewer import AntennaPatternWidget

app = QApplication(sys.argv)
viewer = AntennaPatternWidget()
viewer.show()
sys.exit(app.exec())
```

### Embedded in Another Application

```python
from antenna_pattern_viewer import AntennaPatternWidget

class MyMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.viewer = AntennaPatternWidget(parent=self)
        self.setCentralWidget(self.viewer)

        # Load a pattern programmatically
        from farfield_spherical import read_ffd
        pattern = read_ffd("my_antenna.ffd")
        self.viewer.data_model.set_pattern(pattern, file_path="my_antenna.ffd")
```

### Custom First Panel

The left panel's first slot (normally a file manager) can be replaced with a custom widget:

```python
my_generator = PatternGeneratorWidget(data_model)
left_panel = LeftPanelWidget(
    data_model,
    first_panel_widget=my_generator,
    first_panel_config={
        "icon": "wrench",
        "tooltip": "Generator - Create patterns",
        "name": "generator"
    },
    show_pattern_strip=False
)
```

---

## Supported File Formats

| Format | Extension | Description | Notes |
|--------|-----------|-------------|-------|
| **CUT** | `.cut` | GRASP/TICRA cut file | Prompts for frequency range on import |
| **FFD** | `.ffd` | NSI far-field data | Full frequency/angle data |
| **NPZ** | `.npz` | NumPy archive | Native format with full metadata |
| **SPH** | `.sph` | TICRA spherical wave coefficients | Converted to far-field on load |
| **ATAMS** | `.atams` | ATAMS measurement file | Option to interpolate non-uniform theta |
| **CSV** | `.csv` | Comma-separated values | Export only |

### Format-Specific Import Options

**CUT files**: Since CUT files do not contain frequency metadata, a dialog prompts for the start and end frequency (in GHz) before loading.

**ATAMS files**: ATAMS data may have non-uniform theta grids (different theta samples per phi cut). A dialog asks whether to interpolate to a uniform grid or preserve the raw per-phi sampling.

**SPH files**: Loaded via the SphericalWaveExpansion package. The SWE coefficients are used to compute a far-field pattern, and the coefficients are stored for later near-field evaluation.

---

## Application Layout

```
+----------+-------------------------------+
|          | Pattern Strip                 |
| Icon     +-------------------------------+
| Sidebar  | Stacked Panels:               |
|          |   [Files] [View] [Processing] |
|  Files   |   [Analysis] [Export]         |
|  View    |                               |
|  Proc    |                               |
|  Anlys   |                               |
|  Export  |                               |
+----------+-------------------------------+
           | 2D Plot | 3D Plot | Data | NF |
           +-------------------------------+
```

### Left Side

- **Icon Sidebar**: Vertical icon strip for switching between panels
- **Pattern Strip**: Horizontal bar showing loaded patterns, with controls for activating, comparing, and unloading patterns
- **Stacked Panels**: Only one panel visible at a time, selected by the icon sidebar

### Center / Right Side (Dockable)

- **2D Plot**: Primary 1D cut plots and 2D polar plots (matplotlib)
- **3D Plot**: 3D radiation pattern visualization
- **Data Display**: Tabular data view
- **Near Field**: Near-field visualization (populated after SWE near-field calculation)

All center panels are dockable Qt dock widgets that can be rearranged, floated, or tabified.

---

## Loading Your First Pattern

1. Click the **Files** icon in the sidebar (topmost icon)
2. Browse to your pattern file using the file tree, or click **Open Files...** to use a standard file dialog
3. Double-click a file or select it and click **Load Selected**
4. The pattern appears in the Pattern Strip and the 2D plot updates automatically

### Quick Loading Methods

- **Drag and drop**: Drag pattern files directly onto the file manager panel
- **Recent files**: Click the **Recent** dropdown to reload previously opened files
- **Favorites**: Add frequently used directories to the Quick Access panel
- **Programmatic**: Use `data_model.set_pattern(pattern)` from code

---

## Multi-Pattern Workflow

APV supports loading multiple patterns simultaneously for comparison:

1. Load multiple files — each appears as an entry in the Pattern Strip
2. Click a pattern name to make it the **active** pattern (displayed in plots, available for processing)
3. Right-click a pattern to add it to the **comparison set**
4. Enable **Multi-Pattern Plot** in the View panel to overlay comparison patterns on the same axes
5. Comparison compatibility is shown in the View panel (common frequencies, common phi angles)

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| F1 | Open help documentation |
| Shift+F1 | Context-sensitive help for current panel |

---

## Next Steps

- [User Guide](user_guide.md) — Complete panel-by-panel reference
- [Architecture Guide](architecture.md) — Developer guide to the MVC architecture
- [Coordinate Systems](../../FarFieldSpherical/docs/coordinate_systems.md) — Theory of coordinate formats
- [Polarization](../../FarFieldSpherical/docs/polarization.md) — Polarization conversions
- [Pattern Operations](../../FarFieldSpherical/docs/pattern_operations.md) — Processing algorithms
- [SWE Theory](../../spherical_wave_expansion/docs/swe_theory.md) — Spherical wave expansion algorithms
