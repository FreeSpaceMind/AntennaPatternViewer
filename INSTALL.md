# Installation Guide for AntennaPatternViewer

## Prerequisites

- Python 3.9 or higher
- pip (Python package installer)
- FarFieldSpherical package installed

## Quick Installation

### Step 1: Install FarFieldSpherical

The viewer depends on the FarFieldSpherical core library:

```bash
# If you have FarFieldSpherical source
cd ../FarFieldSpherical
pip install -e .

# Or from PyPI (when published)
pip install farfield-spherical
```

### Step 2: Install AntennaPatternViewer

```bash
cd AntennaPatternViewer
pip install -e .
```

### Step 3: Run the Application

```bash
antenna-pattern-viewer
```

Or:

```bash
python -m antenna_pattern_viewer
```

---

## Installation Methods

### 1. Development Installation (Recommended)

For development or if you want to modify the code:

```bash
# Clone/navigate to the repository
cd AntennaPatternViewer

# Install in editable mode
pip install -e .

# Or with dev dependencies
pip install -e ".[dev]"
```

Changes to the source code are immediately reflected without reinstalling.

### 2. Standard Installation from Source

```bash
cd AntennaPatternViewer
pip install .
```

### 3. Installation with Development Tools

```bash
pip install ".[dev]"
```

This installs additional tools:
- pytest (testing)
- pytest-qt (Qt testing)
- black (code formatting)
- flake8 (linting)

---

## Virtual Environment (Recommended)

Always use a virtual environment:

```bash
# Create virtual environment
python -m venv venv

# Activate it
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Install FarFieldSpherical
cd ../FarFieldSpherical
pip install -e .

# Install AntennaPatternViewer
cd ../AntennaPatternViewer
pip install -e .

# When done
deactivate
```

---

## Verifying Installation

### Test Import

```bash
python -c "from antenna_pattern_viewer import AntennaPatternWidget; print('Success!')"
```

### Test Application Launch

```bash
antenna-pattern-viewer
```

You should see the GUI window open.

### Test Embedding

```python
from PyQt6.QtWidgets import QApplication
from antenna_pattern_viewer import AntennaPatternWidget

app = QApplication([])
widget = AntennaPatternWidget()
widget.show()
print("Widget created successfully!")
# app.exec()  # Uncomment to run event loop
```

---

## Dependencies

The package automatically installs:

### Required Dependencies
- `farfield-spherical>=1.0.0` - Core pattern library
- `PyQt6>=6.4.0` - GUI framework
- `matplotlib>=3.5.0` - Plotting library  
- `numpy>=1.21.0` - Numerical computing

### Optional Development Dependencies
- `pytest>=7.0.0` - Testing framework
- `pytest-qt>=4.0.0` - Qt testing support
- `pytest-cov>=3.0.0` - Coverage reporting
- `black>=22.0.0` - Code formatting
- `flake8>=4.0.0` - Code linting

---

## Platform-Specific Notes

### Linux

May need to install Qt dependencies:

**Ubuntu/Debian:**
```bash
sudo apt-get install python3-pyqt6 python3-pyqt6.qtsvg
```

Or let pip install PyQt6:
```bash
pip install PyQt6
```

### macOS

PyQt6 should install cleanly via pip. If you encounter issues:

```bash
brew install qt6
pip install PyQt6
```

### Windows

PyQt6 typically works out of the box. If you need Visual C++ redistributables:

Download from: https://support.microsoft.com/en-us/help/2977003/

---

## Troubleshooting

### "No module named 'farfield_spherical'"

**Solution**: Install FarFieldSpherical first:
```bash
cd ../FarFieldSpherical
pip install -e .
```

### "No module named 'PyQt6'"

**Solution**: Install PyQt6:
```bash
pip install PyQt6
```

### "No module named 'antenna_pattern_viewer'"

**Solution**: Ensure you're in the right directory and install:
```bash
cd AntennaPatternViewer
pip install -e .
```

### Application doesn't launch / "antenna-pattern-viewer: command not found"

**Solutions**:

1. Make sure installation succeeded:
   ```bash
   pip list | grep antenna-pattern-viewer
   ```

2. Try running as module:
   ```bash
   python -m antenna_pattern_viewer
   ```

3. Reinstall:
   ```bash
   pip uninstall antenna-pattern-viewer
   pip install -e .
   ```

4. Check your PATH includes pip's script directory

### GUI appears but crashes when loading files

**Solution**: Check that FarFieldSpherical is installed and working:
```python
from farfield_spherical import read_cut
pattern = read_cut('test.cut')  # Use a real file
print(f"Loaded pattern: {len(pattern.frequencies)} frequencies")
```

### Import errors about widgets

**Solution**: Ensure all widget files have been migrated from the old package. Check the MIGRATION_GUIDE.md for the complete list.

### "matplotlib backend" errors

**Solution**: PyQt6 requires the Qt5Agg backend. This should be automatic, but you can force it:
```python
import matplotlib
matplotlib.use('Qt5Agg')
```

---

## Updating

To update to a newer version:

```bash
cd AntennaPatternViewer
git pull  # If using git
pip install --upgrade -e .
```

---

## Uninstalling

```bash
pip uninstall antenna-pattern-viewer
```

---

## Building Distribution Packages

To create installable wheel and source distributions:

```bash
# Install build tool
pip install build

# Build the package
python -m build

# This creates:
# dist/antenna_pattern_viewer-1.0.0-py3-none-any.whl
# dist/antenna-pattern-viewer-1.0.0.tar.gz
```

---

## Running Tests

If you installed with dev dependencies:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=antenna_pattern_viewer

# Run specific test file
pytest tests/test_antenna_pattern_viewer/test_widget.py
```

---

## Checking Installation

Run this comprehensive check:

```python
import sys

print("Python version:", sys.version)

try:
    import PyQt6
    print("✓ PyQt6 installed")
except ImportError:
    print("✗ PyQt6 missing")

try:
    import matplotlib
    print("✓ matplotlib installed")
except ImportError:
    print("✗ matplotlib missing")

try:
    import farfield_spherical
    print("✓ farfield-spherical installed")
except ImportError:
    print("✗ farfield-spherical missing")

try:
    import antenna_pattern_viewer
    print("✓ antenna-pattern-viewer installed")
except ImportError:
    print("✗ antenna-pattern-viewer missing")

print("\nAll checks passed! Ready to use.")
```

---

## Getting Help

If you encounter issues:

1. Check this troubleshooting guide
2. Verify all dependencies are installed
3. Check the GitHub Issues page
4. Run with verbose output:
   ```bash
   python -m antenna_pattern_viewer --verbose
   ```

---

## Next Steps

After installation:

1. Read the README.md for usage examples
2. Check MIGRATION_GUIDE.md if migrating from old package
3. Try loading a sample pattern file
4. Explore the dockable interface
5. Check out example scripts (if available)

---

## System Requirements

- **Python**: 3.9, 3.10, 3.11, or 3.12
- **RAM**: 2 GB minimum, 4 GB recommended
- **Display**: 1280x720 minimum resolution
- **OS**: Windows 10+, macOS 10.14+, Linux (most distributions)