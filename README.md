# Antenna Pattern Viewer

A PyQt6-based GUI application for visualizing and analyzing antenna far-field patterns.

## Overview

**Antenna Pattern Viewer** provides a comprehensive graphical interface for working with antenna far-field patterns. The application features a dockable widget architecture, allowing users to customize their workspace by rearranging, floating, or hiding different panels.

## Features

- **Dockable Interface**: All panels can be moved, resized, floated, or hidden
- **Multiple File Formats**: Support for GRASP .cut, NSI .ffd, TICRA .sph, and NPZ files
- **Interactive Visualization**: Real-time 2D pattern plots with zoom, pan, and export
- **Pattern Processing**: 
  - Phase center translation
  - Polarization conversion
  - Pattern rotation (MARS)
  - Amplitude scaling
- **Analysis Tools**:
  - Phase center calculation
  - Axial ratio analysis
  - Directivity computation
  - Spherical wave expansion (coming soon)
- **Flexible Views**:
  - Multiple frequency selection
  - Arbitrary cut angle selection
  - Gain, phase, and axial ratio plotting
  - Statistical analysis across cuts
- **Embeddable**: Can be used as a standalone app or embedded in larger applications

## Installation

### Prerequisites

- Python 3.9 or higher
- FarFieldSpherical package installed

### From Source

```bash
git clone https://github.com/yourusername/antenna-pattern-viewer.git
cd antenna-pattern-viewer
pip install -e .
```

### Dependencies

The package automatically installs:
- `farfield-spherical>=1.0.0` - Core pattern library
- `PyQt6>=6.4.0` - GUI framework
- `matplotlib>=3.5.0` - Plotting library
- `numpy>=1.21.0` - Numerical computing

## Usage

### Standalone Application

Run as a standalone application:

```bash
antenna-pattern-viewer
```

Or:

```bash
python -m antenna_pattern_viewer
```

### Embedding in Other Applications

The `AntennaPatternWidget` can be embedded in larger PyQt applications:

```python
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget
from antenna_pattern_viewer import AntennaPatternWidget

app = QApplication([])

# Create a main window with tabs
main_window = QMainWindow()
tabs = QTabWidget()

# Embed antenna pattern viewer as a tab
pattern_viewer = AntennaPatternWidget()
tabs.addTab(pattern_viewer, "Antenna Patterns")

# Add other tabs to your application
# tabs.addTab(other_widget, "Other Tool")

main_window.setCentralWidget(tabs)
main_window.show()

app.exec()
```

### Programmatic Pattern Loading

```python
from antenna_pattern_viewer import AntennaPatternWidget
from farfield_spherical import read_cut

# Create widget
viewer = AntennaPatternWidget()

# Load pattern programmatically
pattern = read_cut('antenna.cut')
viewer.data_model.set_pattern(pattern, 'antenna.cut')

# Show the widget
viewer.show()
```

### Connecting to Signals

```python
viewer = AntennaPatternWidget()

# Connect to pattern loaded signal
def on_pattern_loaded(pattern):
    print(f"Pattern loaded with {len(pattern.frequencies)} frequencies")

viewer.pattern_loaded.connect(on_pattern_loaded)

# Connect to status messages
viewer.status_message.connect(print)
```

## User Interface

### Panels

The application consists of four dockable panels:

1. **Control Panel** (left): Contains three tabs
   - **View**: Select frequencies, angles, plot types, and display options
   - **Processing**: Apply phase center translation, rotation, polarization conversion
   - **Analysis**: Calculate phase centers, directivity, and spherical wave expansion

2. **2D View** (center-top): Interactive matplotlib plot with:
   - Zoom and pan controls
   - Grid and legend toggles
   - Axis limit controls
   - Normalization option
   - Export to PNG/PDF/SVG

3. **3D View** (center-bottom): 3D pattern visualization (coming soon)

4. **Data Display** (bottom): Shows pattern statistics and numerical data

### Menu Bar

- **File**
  - Open Pattern (Ctrl+O)
  - Save Pattern (Ctrl+S)
  - Export Plot (Ctrl+E)

- **View**
  - Toggle panels visibility
  - Reset layout to defaults

- **Help**
  - About

### Customizing the Layout

- **Move panels**: Drag panel title bar to new location
- **Float panels**: Drag panel outside main window
- **Hide panels**: Click × on panel or use View menu
- **Reset layout**: View → Reset Layout

## Supported File Formats

### Reading
- **GRASP .cut**: Standard GRASP10 cut file format
- **NSI .ffd**: Near-field Systems far-field data
- **TICRA .sph**: Spherical wave expansion coefficients
- **NPZ**: NumPy compressed format (native)

### Writing
- **NPZ**: Native format (recommended for Python workflows)
- **GRASP .cut**: Export to GRASP format
- **NSI .ffd**: Export to NSI format

## Keyboard Shortcuts

- `Ctrl+O`: Open pattern
- `Ctrl+S`: Save pattern
- `Ctrl+E`: Export plot
- `Ctrl+Q`: Quit application

## Development

### Project Structure

```
antenna_pattern_viewer/
├── src/
│   └── antenna_pattern_viewer/
│       ├── __init__.py
│       ├── __main__.py
│       ├── antenna_pattern_widget.py
│       ├── data_model.py
│       ├── widgets/
│       │   ├── control_panel_widget.py
│       │   ├── plot_2d_widget.py
│       │   ├── plot_3d_widget.py
│       │   ├── data_display_widget.py
│       │   ├── view_tab.py
│       │   ├── processing_tab.py
│       │   ├── analysis_tab.py
│       │   ├── plot_widget.py
│       │   └── collapsible_group.py
│       ├── workers/
│       │   └── swe_worker.py
│       └── dialogs/
│           └── nearfield_viewer.py
└── tests/
```

### Architecture

The application uses a **Model-View architecture**:

- **Data Model** (`PatternDataModel`): Central data store, emits signals on changes
- **Widgets**: Subscribe to model signals and update displays
- **Dockable Layout**: Each major component is a separate QDockWidget

This architecture ensures:
- All widgets stay synchronized automatically
- Easy to add new views of the same data
- Clean separation of concerns
- Simple to embed in other applications

## License

MIT License - see LICENSE file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Related Packages

- **FarFieldSpherical**: Core library for far-field pattern analysis (required dependency)

## Support

For bug reports and feature requests, please open an issue on GitHub.

## Changelog

### Version 1.0.0
- Initial release
- Dockable widget architecture
- Support for multiple file formats
- 2D pattern visualization
- Pattern processing tools
- Analysis capabilities
- Embeddable in other applications