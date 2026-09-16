# AntennaPatternViewer Architecture Guide

This document describes the internal architecture of AntennaPatternViewer for developers
who need to understand, extend, or embed the application. It covers the MVC pattern,
signal flow, processing pipeline, multi-pattern management, and step-by-step instructions
for adding new features.

## Table of Contents

- [Package Structure](#package-structure)
- [MVC Architecture Overview](#mvc-architecture-overview)
- [Model: PatternDataModel](#model-patterndatamodel)
  - [Signals](#signals)
  - [Processing Pipeline](#processing-pipeline)
  - [View Parameters](#view-parameters)
  - [Multi-Pattern Management](#multi-pattern-management)
- [View: Widget Classes](#view-widget-classes)
  - [AntennaPatternWidget (Top Level)](#antennapatternwidget-top-level)
  - [Plot Widgets](#plot-widgets)
  - [Panel Widgets](#panel-widgets)
- [Controller: LeftPanelWidget](#controller-leftpanelwidget)
  - [Signal Routing](#signal-routing)
  - [Handler Pattern](#handler-pattern)
- [Signal Flow Walkthrough](#signal-flow-walkthrough)
  - [Loading a Pattern](#loading-a-pattern)
  - [Applying a Processing Step](#applying-a-processing-step)
  - [Changing View Parameters](#changing-view-parameters)
- [PatternInstance and Multi-Pattern Support](#patterninstance-and-multi-pattern-support)
- [Background Workers](#background-workers)
- [Embeddability](#embeddability)
- [How To: Add a New Processing Step](#how-to-add-a-new-processing-step)
- [How To: Add a New Plot Type](#how-to-add-a-new-plot-type)
- [Coordinate Format and Dual Sphere](#coordinate-format-and-dual-sphere)
- [Dependencies](#dependencies)

---

## Package Structure

```
src/antenna_pattern_viewer/
|
|-- __init__.py                  # Public API: AntennaPatternWidget, PatternDataModel, plot_pattern_cut
|-- antenna_pattern_widget.py    # QMainWindow - top-level embeddable widget with dock layout
|-- data_model.py                # PatternDataModel - central data model (the "M" in MVC)
|-- pattern_instance.py          # PatternInstance dataclass - loaded pattern with settings
|-- plotting.py                  # Standalone plotting functions (plot_pattern_cut, etc.)
|
|-- widgets/
|   |-- __init__.py
|   |-- left_panel_widget.py     # LeftPanelWidget - controller: icon sidebar + stacked panels
|   |-- icon_sidebar.py          # IconSidebar - vertical icon navigation strip
|   |-- pattern_list_widget.py   # PatternListWidget - collapsible pattern list
|   |-- file_manager_widget.py   # FileManagerWidget - file browser with quick access
|   |-- view_panel.py            # ViewPanel - frequency/phi selection, plot settings
|   |-- processing_panel.py      # ProcessingPanel - pattern processing controls
|   |-- analysis_panel.py        # AnalysisPanel - SWE and near field calculations
|   |-- export_widget.py         # ExportWidget - pattern and plot export
|   |-- plot_2d_widget.py        # Plot2DWidget - matplotlib 2D pattern plots
|   |-- plot_3d_widget.py        # Plot3DWidget - 3D visualization
|   |-- plot_nearfield_widget.py # PlotNearFieldWidget - near field visualization
|   |-- data_display_widget.py   # DataDisplayWidget - tabular data view
|   |-- plot_widget.py           # PlotWidget - reusable matplotlib canvas wrapper
|
|-- workers/
|   |-- __init__.py
|   |-- swe_worker.py            # SWEWorker - QThread for background SWE calculation
|
|-- dialogs/
    |-- __init__.py
```

---

## MVC Architecture Overview

AntennaPatternViewer follows a Model-View-Controller (MVC) pattern adapted for PyQt6's
signal-slot mechanism. The boundaries between the three roles are:

```
+-------------------------------------------------------------------+
|                      AntennaPatternWidget                         |
|                      (QMainWindow shell)                          |
|                                                                   |
|  +------------+   signals    +----------------------------+       |
|  |            |  -------->>  |                            |       |
|  |   MODEL    |              |          VIEWS             |       |
|  | DataModel  |  <<--------  |  Plot2D, Plot3D, Data,     |       |
|  |            |   (reads)    |  NearField, ViewPanel       |       |
|  +-----^------+              +----------------------------+       |
|        |                                                          |
|        | set_*() calls                                            |
|        |                                                          |
|  +-----+-------------------+                                      |
|  |     CONTROLLER          |                                      |
|  |  LeftPanelWidget        |                                      |
|  |    |-- ProcessingPanel  |  (emits signals with user input)     |
|  |    |-- ViewPanel        |  (emits parameters_changed)          |
|  |    |-- AnalysisPanel    |                                      |
|  |    |-- ExportWidget     |                                      |
|  |    +-- FileManager      |                                      |
|  +-------------------------+                                      |
+-------------------------------------------------------------------+
```

**Model** (`PatternDataModel`): Holds all state -- the current pattern, original pattern,
processing state, view parameters, and loaded instances. Emits signals when state changes.

**View** (Plot widgets, DataDisplayWidget): Receive a reference to the data model,
connect to its signals, and redraw when notified. Views never modify the model directly.

**Controller** (`LeftPanelWidget`): Receives user interaction signals from panel widgets
(ProcessingPanel, ViewPanel, etc.), translates them into data model method calls, and
triggers view refreshes.

---

## Model: PatternDataModel

**File:** `src/antenna_pattern_viewer/data_model.py`

`PatternDataModel` is a `QObject` subclass that serves as the single source of truth.
Every widget receives a reference to the same `PatternDataModel` instance, created in
`AntennaPatternWidget.__init__()`:

```python
class AntennaPatternWidget(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data_model = PatternDataModel()
        # All child widgets receive self.data_model
```

### Signals

The data model emits the following signals to notify widgets of state changes:

| Signal | Payload | When Emitted |
|---|---|---|
| `pattern_loaded` | `FarFieldSpherical` or `None` | New pattern loaded via `set_pattern()` or `set_active_instance()` |
| `pattern_modified` | `FarFieldSpherical` | Processing applied via `apply_processing()` |
| `view_parameters_changed` | `dict` | View params updated via `set_view_param()` or `update_view_params()` |
| `processing_applied` | `str` (processing name) | A processing step was toggled (e.g. `"phase_center_translation"`) |
| `instances_changed` | (none) | Instance added or removed |
| `active_instance_changed` | `PatternInstance` or `None` | Active instance switched |
| `comparison_set_changed` | `list[str]` (instance IDs) | Comparison set modified |

Widgets connect to these signals in their `connect_signals()` methods:

```python
class Plot2DWidget(QWidget):
    def connect_signals(self):
        self.data_model.pattern_loaded.connect(self.on_pattern_changed)
        self.data_model.pattern_modified.connect(self.on_pattern_changed)
        self.data_model.view_parameters_changed.connect(self.on_view_params_changed)
        self.data_model.comparison_set_changed.connect(self.on_comparison_changed)
```

### Processing Pipeline

The data model maintains two pattern references:

- `_original_pattern` -- the unprocessed pattern as loaded from disk
- `_pattern` -- the current (possibly processed) pattern

All processing operations are stored declaratively in `_processing_state`:

```python
_processing_state = {
    'phase_center_translation': None,   # [x, y, z] list in meters, or None
    'mars': None,                       # (max_extent_m, taper_orders), or None
    'coordinate_format': None,          # 'central', 'sided', or None (keep original)
    'theta_origin_shift': None,         # float in degrees, or None
    'phi_origin_shift': None,           # float in degrees, or None
    'amplitude_normalization': None,    # 'peak', 'boresight', 'mean', or None
    'boresight_normalization': False,   # bool
}
```

When any processing parameter changes, `apply_processing()` re-runs the entire pipeline
from a fresh copy of `_original_pattern`. This avoids accumulated floating-point errors
from stacking transforms:

```python
def apply_processing(self):
    """Apply all enabled processing operations to the original pattern."""
    if self._original_pattern is None:
        return

    # Always start from a clean copy
    processed = self._original_pattern.copy()

    # 1. Coordinate format (central/sided)
    if self._processing_state['coordinate_format'] is not None:
        processed.transform_coordinates(self._processing_state['coordinate_format'])

    # 2. Amplitude normalization (peak/boresight/mean)
    if self._processing_state['amplitude_normalization'] is not None:
        processed.normalize_amplitude(self._processing_state['amplitude_normalization'])

    # 3. Boresight normalization
    if self._processing_state['boresight_normalization']:
        processed.normalize_at_boresight()

    # 4. Theta origin shift
    if self._processing_state['theta_origin_shift'] is not None:
        processed.shift_theta_origin(self._processing_state['theta_origin_shift'])

    # 5. Phi origin shift
    if self._processing_state['phi_origin_shift'] is not None:
        processed.shift_phi_origin(self._processing_state['phi_origin_shift'])

    # 6. Phase center translation
    if self._processing_state['phase_center_translation'] is not None:
        translation = np.array(self._processing_state['phase_center_translation'])
        processed.translate(translation)

    # 7. MARS algorithm
    if self._processing_state['mars'] is not None:
        max_extent, taper = self._processing_state['mars']
        processed.apply_mars(max_extent, taper=taper)

    self._pattern = processed
    self.pattern_modified.emit(processed)
```

**Order matters.** Coordinate format conversion must happen before origin shifts (which
operate on theta/phi values), and MARS must be applied last since it modifies the
frequency-domain data.

Each processing step has a corresponding `set_*()` method that updates the state,
re-runs the pipeline, and emits `processing_applied`:

```python
def set_phase_center_translation(self, translation: Optional[list]):
    """Enable or disable phase center translation.
    Args: translation: [x, y, z] in meters, or None to disable
    """
    self._processing_state['phase_center_translation'] = translation
    self.apply_processing()
    self.processing_applied.emit("phase_center_translation")
```

### View Parameters

View parameters control how patterns are displayed (which frequencies, phi cuts, plot
type, etc.) without modifying the underlying pattern data:

```python
_view_params = {
    'selected_frequencies': [],    # List of frequency values (Hz)
    'selected_phi': [],            # List of phi angle values (degrees)
    'selected_theta': [],          # List of theta angle values (degrees)
    'plot_type': '1d_cut',         # '1d_cut' or '2d_polar'
    'component': 'e_co',           # 'e_co', 'e_cx', 'e_theta', 'e_phi'
    'value_type': 'gain',          # 'gain', 'phase', 'axial_ratio'
    'normalize': False,            # Normalize peak to 0 dB
    'unwrap_phase': True,          # Unwrap phase discontinuities
    'statistics_enabled': False,   # Enable statistics mode
    'statistic_type': 'mean',      # 'mean', 'median', 'rms', 'percentile', 'std'
}
```

View params can be read and written individually or in bulk:

```python
# Read
freq = data_model.get_view_param('selected_frequencies')

# Write single
data_model.set_view_param('plot_type', '2d_polar')

# Write multiple (emits view_parameters_changed once)
data_model.update_view_params({
    'selected_frequencies': [10e9],
    'selected_phi': [0.0, 90.0],
})
```

### Multi-Pattern Management

The data model supports loading multiple patterns simultaneously for comparison:

```
PatternDataModel
  |-- _instances: Dict[str, PatternInstance]       # All loaded patterns
  |-- _active_instance_id: str                     # Currently displayed pattern
  |-- _comparison_instance_ids: Set[str]           # Patterns overlaid on plots
```

Key operations:

```python
# Add a loaded pattern
instance = PatternInstance(pattern=pattern, source_file=Path("my_file.cut"))
data_model.add_instance(instance)   # First instance auto-becomes active

# Switch active pattern (saves/restores view_params per instance)
data_model.set_active_instance(instance_id)

# Manage comparison overlay
data_model.add_to_comparison(instance_id)
data_model.remove_from_comparison(instance_id)

# Query
active = data_model.get_active_instance()        # -> PatternInstance
all_inst = data_model.get_all_instances()          # -> List[PatternInstance]
comp = data_model.get_comparison_instances()       # -> List[PatternInstance]
compat = data_model.get_comparison_compatibility() # -> dict with compatibility info
```

When switching active instances, the data model automatically saves the current
`_view_params` to the outgoing instance and restores them from the incoming instance:

```python
def set_active_instance(self, instance_id: str):
    # Save current view params to old active instance
    if self._active_instance_id:
        old_instance = self._instances.get(self._active_instance_id)
        if old_instance:
            old_instance.view_params = self._view_params.copy()

    # Set new active and restore its view params
    self._active_instance_id = instance_id
    instance = self._instances[instance_id]
    if instance.view_params:
        self._view_params.update(instance.view_params)
        self.view_parameters_changed.emit(self._view_params)

    # Load the pattern
    self.set_pattern(instance.pattern, file_path=...)
    self.active_instance_changed.emit(instance)
```

---

## View: Widget Classes

### AntennaPatternWidget (Top Level)

**File:** `src/antenna_pattern_viewer/antenna_pattern_widget.py`

The top-level `QMainWindow` that assembles the entire UI using Qt dock widgets:

```
+------------------------------------------------------------------+
|  AntennaPatternWidget (QMainWindow)                              |
|                                                                  |
|  +--------------+  +----------------------------------------+   |
|  | Left Panel   |  |  Tabbed Center Area                    |   |
|  | (Dock)       |  |  +---+ +---+ +------+ +----------+    |   |
|  |              |  |  |2D | |3D | |Data  | |NearField |    |   |
|  | [Icon Bar]   |  |  |   | |   | |      | |          |    |   |
|  | [Panel Stack]|  |  +---+ +---+ +------+ +----------+    |   |
|  |              |  |                                        |   |
|  +--------------+  +----------------------------------------+   |
|  [Status Bar                                                ]   |
+------------------------------------------------------------------+
```

The dock layout is created in `setup_docks()`:

```python
def setup_docks(self):
    # Create plot widgets
    self.plot_2d = Plot2DWidget(self.data_model)
    self.plot_3d = Plot3DWidget(self.data_model)
    self.plot_nearfield = PlotNearFieldWidget(self.data_model)
    self.data_display = DataDisplayWidget(self.data_model)

    # Create left panel (controller)
    self.left_panel = LeftPanelWidget(
        self.data_model,
        plot_widget=self.plot_2d.plot_widget
    )

    # Arrange: left panel on left, tabbed plots on right
    self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.left_panel_dock)
    self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.plot_2d_dock)
    self.tabifyDockWidget(self.plot_2d_dock, self.plot_3d_dock)
    self.tabifyDockWidget(self.plot_2d_dock, self.data_dock)
    self.tabifyDockWidget(self.plot_2d_dock, self.plot_nearfield_dock)
```

### Plot Widgets

All plot widgets follow the same pattern: receive `data_model`, connect to signals,
redraw on notification.

```python
class Plot2DWidget(QWidget):
    def __init__(self, data_model, parent=None):
        super().__init__(parent)
        self.data_model = data_model
        self.setup_ui()
        self.connect_signals()

    def connect_signals(self):
        self.data_model.pattern_loaded.connect(self.on_pattern_changed)
        self.data_model.pattern_modified.connect(self.on_pattern_changed)
        self.data_model.view_parameters_changed.connect(self.on_view_params_changed)

    def on_pattern_changed(self, pattern):
        """Redraw when pattern data changes."""
        self.plot_widget.current_pattern = pattern
        if pattern is None:
            self.plot_widget.clear_plot()
            return
        self.update_plot_from_model()

    def on_view_params_changed(self, params):
        """Redraw when view settings change."""
        if self.plot_widget.current_pattern is not None:
            self.update_plot_from_model()

    def update_plot_from_model(self):
        """Read view params from data_model and replot."""
        params = self.data_model._view_params
        frequencies = params.get('selected_frequencies', [])
        phi_angles = params.get('selected_phi', [])
        plot_type = params.get('plot_type', '1d_cut')
        # ... extract remaining params and call plotting functions
```

### Panel Widgets

Panel widgets are stacked inside the LeftPanelWidget and provide user controls:

| Panel | Purpose | Key Signals |
|---|---|---|
| `FileManagerWidget` | Browse and load pattern files | (loads via data_model directly) |
| `ViewPanel` | Frequency/phi selection, plot format, statistics | `parameters_changed` |
| `ProcessingPanel` | Processing toggles and parameters | `apply_phase_center_signal`, `apply_mars_signal`, `coordinate_format_changed`, etc. |
| `AnalysisPanel` | SWE calculation, near field evaluation | `nearfield_calculated` |
| `ExportWidget` | Save patterns and plots to disk | `export_completed` |

---

## Controller: LeftPanelWidget

**File:** `src/antenna_pattern_viewer/widgets/left_panel_widget.py`

The LeftPanelWidget is the central controller that wires user interactions to model
operations. Its layout combines an icon sidebar for navigation with a stacked widget
containing the five panels:

```
+----------+----------------------+
|          | PatternListWidget    |
| Icon     +----------------------+
| Sidebar  | QStackedWidget       |
|          |  [0] FileManager     |
|  Files   |  [1] ViewPanel       |
|  View    |  [2] ProcessingPanel |
|  Proc    |  [3] AnalysisPanel   |
|  Anlys   |  [4] ExportWidget    |
|  Export  |                      |
+----------+----------------------+
```

### Signal Routing

The `connect_signals()` method is the central wiring point. It connects each
ProcessingPanel signal to a handler method:

```python
def connect_signals(self):
    # Icon sidebar -> panel stack navigation
    self.icon_sidebar.panel_changed.connect(self.panel_stack.setCurrentIndex)

    # View panel -> data model
    self.view_panel.parameters_changed.connect(self.on_view_params_changed)

    # Processing panel -> data model (via handler methods)
    self.processing_panel.apply_phase_center_signal.connect(self.on_apply_phase_center)
    self.processing_panel.apply_mars_signal.connect(self.on_apply_mars)
    self.processing_panel.polarization_changed.connect(self.on_polarization_changed)
    self.processing_panel.coordinate_format_changed.connect(self.on_coordinate_format_changed)
    self.processing_panel.shift_theta_origin_signal.connect(self.on_shift_theta_origin)
    self.processing_panel.shift_phi_origin_signal.connect(self.on_shift_phi_origin)
    self.processing_panel.normalize_amplitude_signal.connect(self.on_normalize_amplitude)
    self.processing_panel.normalize_boresight_signal.connect(self.on_normalize_boresight)
    self.processing_panel.split_spheres_signal.connect(self.on_split_spheres)
    self.processing_panel.average_spheres_signal.connect(self.on_average_spheres)

    # Analysis panel -> forward nearfield signal
    self.analysis_panel.nearfield_calculated.connect(self.nearfield_calculated.emit)
```

### Handler Pattern

Every processing handler follows the same three-step pattern:

1. Call `data_model.set_*()` (which internally calls `apply_processing()` and emits `pattern_modified`)
2. Call `processing_panel.on_pattern_loaded(data_model.pattern)` to update the processing panel UI
3. Emit `view_parameters_changed` to trigger plot refreshes

```python
def on_apply_phase_center(self, x, y, z, frequency):
    """Handle phase center translation toggle."""
    if self.data_model.original_pattern is None:
        return
    try:
        is_checked = self.processing_panel.apply_phase_center_check.isChecked()
        if is_checked:
            self.data_model.set_phase_center_translation([x, y, z])
        else:
            self.data_model.set_phase_center_translation(None)

        # Step 2: Update processing panel with new pattern state
        self.processing_panel.on_pattern_loaded(self.data_model.pattern)
        # Step 3: Trigger view refresh
        self.data_model.view_parameters_changed.emit(self.data_model._view_params)
    except Exception as e:
        logger.error(f"Failed to toggle phase center: {e}", exc_info=True)
```

This pattern ensures that:
- The model is always the source of truth (step 1)
- The processing panel UI reflects the processed pattern (step 2)
- All plot widgets redraw with the new data (step 3)

---

## Signal Flow Walkthrough

### Loading a Pattern

When a user loads a file, the following sequence occurs:

```
User double-clicks file in FileManagerWidget
  |
  v
FileManagerWidget reads file -> creates FarFieldSpherical
  |
  v
FileManagerWidget creates PatternInstance(pattern=..., source_file=...)
  |
  v
data_model.add_instance(instance)
  |
  +-- (if first instance) --> data_model.set_active_instance(id)
  |                               |
  |                               +-- Saves old view_params to outgoing instance
  |                               +-- Restores view_params from new instance
  |                               +-- data_model.set_pattern(pattern)
  |                               |       |
  |                               |       +-- Resets _processing_state
  |                               |       +-- Sets _original_pattern = pattern
  |                               |       +-- Sets _pattern = pattern
  |                               |       +-- Emits pattern_loaded(pattern)
  |                               |               |
  |                               |               +---> ViewPanel.on_pattern_loaded()
  |                               |               |         (populates freq/phi lists)
  |                               |               +---> ProcessingPanel.on_pattern_loaded()
  |                               |               |         (updates polarization, coord format)
  |                               |               +---> Plot2DWidget.on_pattern_changed()
  |                               |               |         (triggers replot)
  |                               |               +---> DataDisplayWidget.on_pattern_loaded()
  |                               |                         (populates table)
  |                               |
  |                               +-- Emits active_instance_changed(instance)
  |                               +-- Emits pattern_loaded(pattern)
  |
  +-- Emits instances_changed()
          |
          +---> PatternListWidget updates list display
```

### Applying a Processing Step

Example: user toggles the "Apply Phase Center Shift" checkbox.

```
ProcessingPanel: apply_phase_center_check toggled by user
  |
  v
ProcessingPanel.on_apply_phase_center_toggled()
  |  reads x, y, z from spinboxes and frequency from combo
  v
ProcessingPanel.apply_phase_center_signal.emit(x, y, z, freq)
  |
  v
LeftPanelWidget.on_apply_phase_center(x, y, z, freq)
  |
  +-- data_model.set_phase_center_translation([x, y, z])
  |       |
  |       +-- Updates _processing_state['phase_center_translation']
  |       +-- Calls apply_processing()
  |       |       |
  |       |       +-- processed = _original_pattern.copy()
  |       |       +-- Applies all enabled transforms in order (1-7)
  |       |       +-- _pattern = processed
  |       |       +-- Emits pattern_modified(processed)
  |       |               |
  |       |               +---> Plot2DWidget.on_pattern_changed(processed)
  |       |               +---> Plot3DWidget.on_pattern_changed(processed)
  |       |               +---> DataDisplayWidget updates
  |       |
  |       +-- Emits processing_applied("phase_center_translation")
  |
  +-- processing_panel.on_pattern_loaded(data_model.pattern)
  |       (updates panel UI to reflect processed pattern state)
  |
  +-- data_model.view_parameters_changed.emit(data_model._view_params)
          |
          +---> Plot2DWidget.on_view_params_changed() -> replot
          +---> Plot3DWidget.on_view_params_changed() -> replot
```

### Changing View Parameters

When the user selects different frequencies or changes the plot format:

```
ViewPanel: user selects new frequencies in the list widget
  |
  v
QListWidget.itemSelectionChanged -> ViewPanel.parameters_changed.emit()
  |
  v
LeftPanelWidget.on_view_params_changed()
  |
  +-- params = view_panel.get_current_parameters()
  |       (reads all UI controls into a dict)
  |
  +-- data_model.update_view_params(params)
  |       |
  |       +-- Merges params into _view_params
  |       +-- Emits view_parameters_changed(params)
  |               |
  |               +---> Plot2DWidget.on_view_params_changed(params)
  |               |         reads data_model._view_params
  |               |         calls update_plot_from_model()
  |               +---> Plot3DWidget.on_view_params_changed(params)
  |               +---> DataDisplayWidget updates
```

---

## PatternInstance and Multi-Pattern Support

**File:** `src/antenna_pattern_viewer/pattern_instance.py`

Each loaded file creates a `PatternInstance` dataclass:

```python
@dataclass
class PatternInstance:
    instance_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    pattern: Any = None                              # FarFieldSpherical object
    source_file: Optional[Path] = None
    display_name: str = ""                           # Shown in pattern list
    view_params: Dict[str, Any] = field(default_factory=dict)
    processing_history: list = field(default_factory=list)
    load_timestamp: Optional[float] = None
    notes: str = ""
```

Key behaviors:
- `display_name` defaults to the filename if not provided
- `view_params` stores the per-instance view settings, saved/restored when switching
- `clone()` creates a copy with a new UUID (useful for "duplicate pattern" features)
- `processing_history` tracks which operations have been applied (for dual sphere splits, etc.)

The `PatternListWidget` displays all loaded instances and allows the user to:
- Click to set active
- Check a box to add to the comparison set
- Right-click for rename/remove/clone actions
- Click [+] to open a file dialog

---

## Background Workers

**File:** `src/antenna_pattern_viewer/workers/swe_worker.py`

Long-running computations use `QThread` to avoid freezing the GUI:

```python
class SWEWorker(QThread):
    finished = pyqtSignal(object)   # Emits SWE object when done
    error = pyqtSignal(str)         # Emits error message
    progress = pyqtSignal(str)      # Emits progress messages

    def __init__(self, pattern, frequency, nmax=None, mmax=None):
        super().__init__()
        self.pattern = pattern
        self.frequency = frequency
        self.nmax = nmax
        self.mmax = mmax

    def run(self):
        try:
            self.progress.emit("Calculating spherical modes...")
            swe = self.pattern.calculate_spherical_modes(
                frequency=self.frequency,
                nmax=self.nmax,
                mmax=self.mmax
            )
            self.finished.emit(swe)
        except Exception as e:
            self.error.emit(str(e))
```

Usage from AnalysisPanel:

```python
self.swe_worker = SWEWorker(pattern, frequency, nmax=nmax)
self.swe_worker.finished.connect(self.on_swe_finished)
self.swe_worker.error.connect(self.on_swe_error)
self.swe_worker.progress.connect(self.on_swe_progress)
self.swe_worker.start()
```

---

## Embeddability

`AntennaPatternWidget` is designed to be embedded in larger applications.

### Basic Embedding

```python
from antenna_pattern_viewer import AntennaPatternWidget

# Embed as a widget in your application
viewer = AntennaPatternWidget(parent=your_main_window)
your_layout.addWidget(viewer)

# Load a pattern programmatically
from farfield_spherical import read_pattern
pattern = read_pattern("my_antenna.cut")
viewer.data_model.set_pattern(pattern, file_path="my_antenna.cut")
```

### Custom First Panel

The left panel's first slot (normally the FileManager) can be replaced with a custom
widget. This is useful when the viewer is embedded in a tool that generates patterns
rather than loading them from files:

```python
from antenna_pattern_viewer.widgets.left_panel_widget import LeftPanelWidget

# Create your custom panel
generator_widget = MyPatternGeneratorWidget(data_model)

# Create left panel with custom first panel
left_panel = LeftPanelWidget(
    data_model,
    first_panel_widget=generator_widget,
    first_panel_config={
        "icon": "wrench_icon",
        "tooltip": "Generator - Create patterns",
        "name": "generator"
    },
    show_pattern_strip=False,   # Hide the pattern list if not needed
)
```

### Controlling the Viewer Programmatically

```python
# Navigate panels
viewer.show_files_panel()
viewer.show_controls_panel()
viewer.show_analysis_panel()
viewer.show_export_panel()

# Access the data model
viewer.data_model.set_view_param('plot_type', '2d_polar')
viewer.data_model.set_phase_center_translation([0.0, 0.0, 0.01])

# Listen for events
viewer.pattern_loaded.connect(my_callback)
viewer.status_message.connect(my_status_bar.showMessage)
```

---

## How To: Add a New Processing Step

This section walks through adding a hypothetical "Taper Window" processing step.

### Step 1: Add to `_processing_state` in `data_model.py`

Add the new key to both `__init__` and `set_pattern` (which resets state):

```python
# In __init__:
self._processing_state = {
    # ... existing keys ...
    'taper_window': None,   # 'hanning', 'hamming', or None
}

# In set_pattern:
self._processing_state = {
    # ... existing keys ...
    'taper_window': None,
}
```

### Step 2: Add `set_*()` method in `data_model.py`

```python
def set_taper_window(self, window_type: Optional[str]):
    """Enable or disable taper window.
    Args: window_type: 'hanning', 'hamming', or None to disable
    """
    self._processing_state['taper_window'] = window_type
    self.apply_processing()
    self.processing_applied.emit("taper_window")
```

### Step 3: Add the transform in `apply_processing()`

Insert it in the correct position in the pipeline (after existing steps, before MARS):

```python
def apply_processing(self):
    # ... existing steps 1-6 ...

    # 7. Taper window (new)
    if self._processing_state['taper_window'] is not None:
        processed.apply_taper(self._processing_state['taper_window'])

    # 8. MARS (was step 7, now step 8)
    if self._processing_state['mars'] is not None:
        max_extent, taper = self._processing_state['mars']
        processed.apply_mars(max_extent, taper=taper)

    self._pattern = processed
    self.pattern_modified.emit(processed)
```

### Step 4: Add signal in `ProcessingPanel`

```python
class ProcessingPanel(QWidget):
    # Existing signals...
    apply_taper_signal = pyqtSignal(str)  # window_type
```

### Step 5: Add UI controls in `ProcessingPanel.setup_ui()`

```python
# === TAPER WINDOW ===
taper_group = QGroupBox("Taper Window")
taper_layout = QHBoxLayout(taper_group)
self.apply_taper_check = QCheckBox("Apply")
self.apply_taper_check.toggled.connect(self.on_apply_taper_toggled)
taper_layout.addWidget(self.apply_taper_check)
self.taper_combo = QComboBox()
self.taper_combo.addItems(["Hanning", "Hamming"])
taper_layout.addWidget(self.taper_combo)
layout.addWidget(taper_group)
```

Add the event handler:

```python
def on_apply_taper_toggled(self, checked):
    if not self.current_pattern:
        return
    window_type = self.taper_combo.currentText().lower() if checked else ""
    self.apply_taper_signal.emit(window_type)
```

### Step 6: Add handler in `LeftPanelWidget`

Connect the signal in `connect_signals()`:

```python
self.processing_panel.apply_taper_signal.connect(self.on_apply_taper)
```

Implement the handler:

```python
def on_apply_taper(self, window_type):
    """Handle taper window toggle."""
    if self.data_model.original_pattern is None:
        return
    try:
        is_checked = self.processing_panel.apply_taper_check.isChecked()
        if is_checked and window_type:
            self.data_model.set_taper_window(window_type)
        else:
            self.data_model.set_taper_window(None)

        self.processing_panel.on_pattern_loaded(self.data_model.pattern)
        self.data_model.view_parameters_changed.emit(self.data_model._view_params)
    except Exception as e:
        logger.error(f"Failed to toggle taper: {e}", exc_info=True)
```

### Summary of Files Changed

| File | Change |
|---|---|
| `data_model.py` | Add to `_processing_state`, add `set_taper_window()`, add step in `apply_processing()` |
| `processing_panel.py` | Add signal, UI controls, event handler |
| `left_panel_widget.py` | Connect signal, implement handler |

---

## How To: Add a New Plot Type

Plot widgets connect to data model signals and read `_view_params` to determine what to
draw. To add a new plot type:

1. Create a new widget class inheriting from `QWidget`
2. Accept `data_model` in the constructor
3. Connect to `pattern_loaded`, `pattern_modified`, and `view_parameters_changed`
4. Implement `update_plot_from_model()` that reads `data_model._view_params`
5. Add the widget as a new dock in `AntennaPatternWidget.setup_docks()`

Example skeleton:

```python
class PlotSmithWidget(QWidget):
    def __init__(self, data_model, parent=None):
        super().__init__(parent)
        self.data_model = data_model
        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.canvas = FigureCanvas(Figure())
        layout.addWidget(self.canvas)

    def connect_signals(self):
        self.data_model.pattern_loaded.connect(self.on_pattern_changed)
        self.data_model.pattern_modified.connect(self.on_pattern_changed)
        self.data_model.view_parameters_changed.connect(self.on_view_params_changed)

    def on_pattern_changed(self, pattern):
        if pattern is not None:
            self.update_plot_from_model()

    def on_view_params_changed(self, params):
        self.update_plot_from_model()

    def update_plot_from_model(self):
        params = self.data_model._view_params
        pattern = self.data_model.pattern
        # ... draw smith chart ...
```

Then in `antenna_pattern_widget.py`:

```python
def setup_docks(self):
    # ... existing docks ...
    self.plot_smith_dock = QDockWidget("Smith Chart", self)
    self.plot_smith = PlotSmithWidget(self.data_model)
    self.plot_smith_dock.setWidget(self.plot_smith)
    self.tabifyDockWidget(self.plot_2d_dock, self.plot_smith_dock)
```

---

## Coordinate Format and Dual Sphere

### Coordinate Format Detection

Antenna patterns can be stored in two coordinate conventions:

- **Central format:** theta ranges from negative to positive (e.g., -90 to +90),
  phi ranges from 0 to 180. The sign of theta indicates which hemisphere.
- **Sided format:** theta ranges from 0 to 180, phi ranges from 0 to 360. The full
  sphere is covered by phi wrapping around.

Detection heuristic:

```python
theta_min = np.min(pattern.theta_angles)
if theta_min < -0.5:
    format = 'central'
else:
    format = 'sided'
```

The `coordinate_format` processing step converts between these conventions via
`FarFieldSpherical.transform_coordinates()`.

**Important:** The `transform_coordinates` method has a guard
`np.max(phi) > 185` to skip conversion for dual sphere data that already spans
the full phi range.

### Dual Sphere Detection and Splitting

Some antenna measurements capture two hemispheres in a single file with phi spanning
0 to 360 degrees even in central-format data.

- **Detection:** `detect_dual_sphere(pattern)` checks if phi spans 0-360 (works
  regardless of theta format)
- **Splitting:** `split_dual_sphere(pattern)` separates the data:
  - phi 0-180 becomes sphere 1 (as-is)
  - phi 180-360 becomes sphere 2 (phi remapped to 0-180, fields negated, theta flipped)
- **Physics:** A measurement at (theta, phi+180) observes the same physical direction as
  (-theta, phi), with field sign negation from the coordinate transformation.

The dual sphere UI is integrated into the ProcessingPanel's coordinate format group.
When a dual sphere is detected, "Split" and "Average" buttons are enabled. These
operations create new PatternInstance objects (they do not modify the original).

---

## Dependencies

| Package | Role | Required |
|---|---|---|
| **PyQt6** | GUI framework (widgets, signals, layout) | Yes |
| **FarFieldSpherical** | Pattern data structure and operations (read/write, transforms, SWE) | Yes |
| **matplotlib** | 2D plotting, polar plots, statistics plots | Yes |
| **numpy** | Numerical operations on pattern arrays | Yes |
| **SphericalWaveExpansion (swe)** | Spherical wave expansion analysis | Optional (AnalysisPanel) |
| **scipy** | Interpolation for 2D polar plots, spec masks | Optional (some plot features) |

Both `FarFieldSpherical` and `AntennaPatternViewer` are installed in editable mode
(`pip install -e`), so source changes take effect on application restart without
reinstallation.
