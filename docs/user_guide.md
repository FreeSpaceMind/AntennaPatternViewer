# AntennaPatternViewer User Guide

This is the complete panel-by-panel reference guide for AntennaPatternViewer (APV). For installation instructions and a quick start tutorial, see [Getting Started](getting_started.md).

> **Rendering note:** This document uses LaTeX math notation. GitHub and most Markdown renderers with MathJax/KaTeX support will display equations correctly. If you are reading this in a plain text editor, the raw LaTeX source is included inline.

---

## Table of Contents

1. [Application Layout](#application-layout)
2. [Icon Sidebar](#icon-sidebar)
3. [Pattern Strip](#pattern-strip)
4. [File Manager Panel (Panel 0)](#file-manager-panel-panel-0)
5. [View Panel (Panel 1)](#view-panel-panel-1)
6. [Processing Panel (Panel 2)](#processing-panel-panel-2)
7. [Analysis Panel (Panel 3)](#analysis-panel-panel-3)
8. [Export Panel (Panel 4)](#export-panel-panel-4)
9. [Center Dock Widgets](#center-dock-widgets)
10. [Keyboard Shortcuts](#keyboard-shortcuts)
11. [Glossary](#glossary)
12. [Related Documentation](#related-documentation)

---

## Application Layout

The application window is divided into two main regions: a **left panel area** and a set of **center dock widgets**.

```
+----------+---------------------------------------+
|          |        Pattern Strip                   |
|  Icon    +---------------------------------------+
|  Side-   |                                       |
|  bar     |  Active Panel                         |
|          |  (Files / View / Processing /          |
|  [Files] |   Analysis / Export)                   |
|  [View]  |                                       |
|  [Proc]  |                                       |
|  [Anlys] |                                       |
|  [Exprt] |                                       |
+----------+---------------------------------------+
           | 2D Plot | 3D Plot | Data Display | NF |
           +---------------------------------------+
```

### Left Side

| Element | Description |
|---------|-------------|
| **Icon Sidebar** | Vertical strip of 5 icon buttons for switching between panels |
| **Pattern Strip** | Horizontal bar above the active panel showing all loaded patterns |
| **Stacked Panels** | One panel visible at a time, selected by the Icon Sidebar |

### Center / Right Side

Four tabbed dock widgets that can be rearranged, floated, or stacked:

| Dock | Description |
|------|-------------|
| **2D Plot** | Primary visualization: 1D cuts and 2D polar plots (matplotlib) |
| **3D Plot** | 3D radiation pattern visualization (placeholder) |
| **Data Display** | Tabular view of the pattern data |
| **Near Field** | Near-field E/H component visualization (populated after SWE near-field calculation) |

All center panels are Qt dock widgets. You can drag their title bars to rearrange, float them as independent windows, or stack them as tabs.

---

## Icon Sidebar

The Icon Sidebar is the narrow vertical strip on the far left of the window. It contains five buttons that switch the visible panel:

| Index | Icon | Name | Tooltip |
|-------|------|------|---------|
| 0 | Files | `files` | Files -- Browse and load patterns |
| 1 | View | `view` | View -- Plot settings and display options |
| 2 | Processing | `processing` | Processing -- Pattern modifications |
| 3 | Analysis | `analysis` | Analysis -- SWE and near field calculations |
| 4 | Export | `export` | Export -- Save patterns and plots |

Only one panel is visible at a time. Clicking a sidebar icon immediately switches the panel.

> **Embedded mode:** When APV is embedded inside another application (e.g., UmbraAntennaDesigner), the first panel slot can be replaced with a custom widget. See [Getting Started -- Custom First Panel](getting_started.md#custom-first-panel).

---

## Pattern Strip

The Pattern Strip is a horizontal scrollable bar that sits above the active panel. It displays all loaded patterns as clickable **chips**.

### Chip States

| Visual Indicator | Meaning |
|-----------------|---------|
| Blue background, bold text, checkmark prefix | **Active** pattern (displayed in plots, available for processing) |
| Blue border, diamond prefix | In the **comparison set** |
| Checkmark + diamond | Active **and** in the comparison set |
| Plain chip | Loaded but neither active nor in comparison |

### Interactions

| Action | Result |
|--------|--------|
| **Left-click** a chip | Sets that pattern as the active pattern |
| **Right-click** a chip | Opens context menu (see below) |
| **Click the `+` button** | Opens a file dialog to load additional patterns |

### Context Menu

Right-clicking a pattern chip provides:

- **Set as Active** -- Make this the active pattern (hidden if already active)
- **Add to Comparison** / **Remove from Comparison** -- Toggle membership in the comparison set
- **Unload Pattern** -- Remove the pattern from the session entirely

---

## File Manager Panel (Panel 0)

The File Manager is the default first panel. It provides a complete file browsing and loading interface.

### Toolbar

At the top of the panel, a toolbar contains:

| Control | Description |
|---------|-------------|
| **Open Files...** button | Opens a standard OS file dialog filtered to supported formats |
| **Recent** dropdown | Shows up to 10 recently opened files; click to reload. Includes a "Clear Recent Files" option at the bottom |
| **Filter** text box | Filters the file tree in real time. Supports partial name matching (e.g., typing `horn` shows only files containing "horn" in the name) |

### Path Breadcrumb

Below the toolbar is a clickable breadcrumb navigation bar showing the current directory path. Each path segment is a button; clicking it navigates the file tree to that directory.

### Quick Access Sidebar

On the left side of the file browser area, a Quick Access panel provides fast navigation:

| Section | Contents |
|---------|----------|
| **Default locations** | Home (`~`), Desktop, Documents |
| **Favorites** | User-added directories, marked with a star icon |
| **Recent locations** | Directories derived from recently opened files |

**Managing Favorites:**

- Click **+ Add Current Folder** at the bottom to bookmark the current directory.
- **Right-click** a favorite entry and select **Remove from Favorites** to delete it.
- Favorites persist across sessions via `QSettings`.

**Navigation:** Double-click any Quick Access item to navigate the file tree to that location.

### File Tree Browser

The main file browser uses a `QFileSystemModel`-backed tree view. It shows only supported file types:

| Extension | Format |
|-----------|--------|
| `*.cut` | GRASP/TICRA cut file |
| `*.ffd` | NSI far-field data |
| `*.npz` | NumPy pattern archive (native format) |
| `*.sph` | TICRA spherical wave coefficients |
| `*.atams` | ATAMS measurement file |

**Interactions:**

| Action | Result |
|--------|--------|
| **Double-click a file** | Loads the pattern immediately |
| **Double-click a folder** | Navigates into that directory |
| **Select multiple files + click Load Selected** | Loads all selected files. Use Ctrl+click or Shift+click for multi-selection |

### File Preview Bar

Below the file tree, a preview bar displays metadata for the currently selected file:

- **File name** (bold)
- **File type** (e.g., "GRASP cut file", "NSI far-field data")
- **File size** (in B, KB, or MB)
- **Last modified date**

### Drag-and-Drop Support

You can drag pattern files from your OS file manager directly onto the File Manager panel. Supported file types are automatically recognized and loaded.

### Format-Specific Import Dialogs

#### CUT File Import

CUT files do not contain frequency metadata. When loading a `.cut` file, a dialog prompts for:

| Field | Description | Default |
|-------|-------------|---------|
| **Start Frequency** | Lower frequency bound in GHz | 1.000 GHz |
| **End Frequency** | Upper frequency bound in GHz | 1.000 GHz |

If the CUT file contains multiple cuts (multiple frequencies), they are linearly spaced between the start and end frequencies.

#### ATAMS File Import

ATAMS measurement files may have non-uniform theta grids (different theta samples per phi cut). A dialog presents:

- **Interpolate to uniform theta grid** checkbox
  - **Checked:** Interpolates all phi cuts to a common uniform theta grid based on the nominal azimuth values from the file header. This enables all processing operations that require uniform theta grids.
  - **Unchecked:** Preserves the raw per-phi theta positions as measured. Some processing operations (e.g., translate, MARS) will be unavailable.

#### SPH File Import

SPH files contain TICRA spherical wave expansion coefficients. On import:

1. The SWE coefficients are read via `read_ticra_sph()`.
2. A far-field pattern is computed from the coefficients via `create_pattern_from_swe()`.
3. The SWE coefficient data is stored on the pattern object (`pattern.swe`) for later use in the Analysis panel (near-field evaluation, re-export).

### Recent Files Persistence

Recent files, favorite directories, and the last browsed directory are persisted across application sessions using Qt's `QSettings` mechanism. Up to 10 recent files and 5 recent locations are stored.

---

## View Panel (Panel 1)

The View Panel controls how the active pattern is visualized in the 2D and 3D plot widgets.

### Frequency Selection

A multi-select list widget showing all frequencies in the active pattern (displayed as `{freq} MHz`).

| Control | Description |
|---------|-------------|
| **Frequency list** | Click to select a single frequency; Ctrl+click or Shift+click for multiple |
| **Select All** button | Selects all frequencies |
| **Clear All** button | Deselects all frequencies |

If no frequency is explicitly selected, the first frequency is used by default.

### Phi Angle Selection

A multi-select list widget showing all phi angles in the active pattern (displayed as `{phi}` in degrees).

| Control | Description |
|---------|-------------|
| **Phi list** | Click to select; Ctrl+click or Shift+click for multiple |
| **Select All** button | Selects all phi angles |
| **Clear All** button | Deselects all phi angles |

If no phi angle is explicitly selected, the first phi angle is used by default.

### Plot Settings

| Control | Options | Description |
|---------|---------|-------------|
| **Format** | `1D Cut`, `2D Polar` | Selects whether to plot Cartesian 1D cuts or a 2D polar color map |
| **Value** | `Gain`, `Phase`, `Axial Ratio` | The quantity to plot on the y-axis (1D) or as color (2D) |
| **Component** | `Co-pol`, `Cross-pol`, `E-theta`, `E-phi` | Which field component to display |
| **Show Cross-Pol** | Checkbox | When checked, overlays the cross-polarization component on the same axes as the main component |
| **Unwrap Phase** | Checkbox | When checked and plotting phase, removes $2\pi$ discontinuities by applying `numpy.unwrap` along the theta axis |

#### Component mapping

The component dropdown maps to internal field accessors:

| Display Name | Internal Key | Description |
|-------------|-------------|-------------|
| Co-pol | `e_co` | Co-polarization (depends on current polarization setting) |
| Cross-pol | `e_cx` | Cross-polarization |
| E-theta | `e_theta` | Theta component of the electric field |
| E-phi | `e_phi` | Phi component of the electric field |

### Statistics Group

When multiple phi cuts are selected, statistical analysis can be performed across them.

| Control | Description |
|---------|-------------|
| **Enable Statistics Plot** | Checkbox. When enabled, plots the selected statistic across all selected phi cuts instead of individual cuts |
| **Show Min/Max Range** | Checkbox (default: on). When enabled alongside statistics, shades the region between the minimum and maximum values across all phi cuts |
| **Statistic** | Dropdown: `mean`, `median`, `rms`, `percentile`, `std` |
| **Percentile Range** | Visible only when `percentile` is selected. Two spin boxes: lower % (default 25%) and upper % (default 75%). The shaded band shows the inter-percentile range |

#### Statistic definitions

Given $N$ selected phi cuts with gain values $G_1(\theta), G_2(\theta), \ldots, G_N(\theta)$ at each theta angle:

| Statistic | Formula |
|-----------|---------|
| **Mean** | $\bar{G}(\theta) = \frac{1}{N}\sum_{i=1}^{N} G_i(\theta)$ |
| **Median** | Middle value of the sorted set $\{G_1(\theta), \ldots, G_N(\theta)\}$ |
| **RMS** | $G_\text{rms}(\theta) = \sqrt{\frac{1}{N}\sum_{i=1}^{N} G_i^2(\theta)}$ |
| **Std** | $\sigma(\theta) = \sqrt{\frac{1}{N}\sum_{i=1}^{N}(G_i(\theta) - \bar{G}(\theta))^2}$ |
| **Percentile** | The $p$-th percentile of $\{G_1(\theta), \ldots, G_N(\theta)\}$ for the given lower/upper bounds |

### Pattern Comparison Group

| Control | Description |
|---------|-------------|
| **Enable Multi-Pattern Plot** | Checkbox (default: on). When enabled and comparison patterns exist, overlays them on the same axes as the active pattern |
| **Status label** | Shows compatibility information between the active pattern and comparison set |

**Status label color coding:**

| Color | Meaning |
|-------|---------|
| **Green** | All comparison patterns have identical frequency and phi angle dimensions -- fully compatible |
| **Orange** | Partial compatibility -- shows count of common frequencies and common phi angles |
| **Gray** | No patterns in comparison set |

---

## Processing Panel (Panel 2)

The Processing Panel provides controls for modifying the active pattern data. All processing operations are applied non-destructively: the pipeline always starts from the original pattern and re-applies all enabled transforms in order.

### Processing Pipeline Order

When multiple processing steps are enabled simultaneously, they are applied in this fixed order:

1. Coordinate format transformation
2. Amplitude normalization
3. Boresight normalization
4. Theta origin shift (measurement correction)
5. Phi origin shift (measurement correction)
6. Phase center translation
7. MARS (measurement correction)
8. Rotation (antenna orientation)

Measurement corrections run first, in the frame the data was measured in. Rotation runs last, after the phase center has been moved to the origin, because a rotation is only as accurate as the sampling and a pattern whose phase center is far from the origin varies quickly in phase between samples.

### Measurement Correction versus Rotation

Two groups on this panel move the pattern around in angle, and they are for different jobs:

| | Origin Shift (Measurement Correction) | Rotation (Antenna Orientation) |
|---|---|---|
| **Purpose** | Undo a positioner or mounting offset so that the measured $\theta = 0$, $\phi = 0$ line up with the antenna's true boresight and reference plane | Point the antenna somewhere other than $+z$, as it will be mounted |
| **What it does** | Re-labels the measured angle axes: the $\phi$ shift renumbers the cuts, the $\theta$ shift slides each $\phi$ cut along its own $\theta$ axis | Rigid 3D rotation of the whole pattern about the origin, field vectors included |
| **Is it a rotation of the antenna?** | No. Every cut is shifted along a different great circle, so the result is not a rigid rotation and the boresight does not land at a definite $(\theta_0, \phi_0)$ | Yes |
| **Typical magnitude** | A fraction of a degree to a few degrees | Any angle |
| **Library call** | `shift_theta_origin`, `shift_phi_origin` | `rotate` |

If you want to see how the pattern looks with the antenna tilted, use **Rotation**. If the measured pattern peak is a little off $\theta = 0$ because of how the antenna sat on the positioner, use **Origin Shift**.

### Polarization

| Control | Options |
|---------|---------|
| **Polarization** combo box | `Theta`, `Phi`, `X (Ludwig-3)`, `Y (Ludwig-3)`, `RHCP`, `LHCP` |

Changing the polarization converts the pattern's field components to the selected basis. The co-pol and cross-pol definitions follow from the chosen polarization:

| Selection | Co-pol | Cross-pol |
|-----------|--------|-----------|
| Theta | $E_\theta$ | $E_\phi$ |
| Phi | $E_\phi$ | $E_\theta$ |
| X (Ludwig-3) | $E_x$ | $E_y$ |
| Y (Ludwig-3) | $E_y$ | $E_x$ |
| RHCP | $E_R = \frac{1}{\sqrt{2}}(E_\theta - jE_\phi)$ | $E_L = \frac{1}{\sqrt{2}}(E_\theta + jE_\phi)$ |
| LHCP | $E_L = \frac{1}{\sqrt{2}}(E_\theta + jE_\phi)$ | $E_R = \frac{1}{\sqrt{2}}(E_\theta - jE_\phi)$ |

The Ludwig-3 transformation is:

$$E_x = E_\theta \cos\phi - E_\phi \sin\phi$$

$$E_y = E_\theta \sin\phi + E_\phi \cos\phi$$

### Coordinate Format

| Control | Description |
|---------|-------------|
| **Format** combo box | `Central` or `Sided` |
| **Dual sphere status** label | Shows detection message if data spans phi 0--360 degrees |
| **Split** button | Splits a dual-sphere measurement into two separate patterns |
| **Average** button | Splits and averages the two spheres into one pattern |

#### Central vs. Sided Coordinates

- **Central** format: Theta ranges symmetrically about boresight, e.g., $\theta \in [-90^\circ, 90^\circ]$.
- **Sided** format: Theta ranges from 0 to the maximum angle, e.g., $\theta \in [0^\circ, 180^\circ]$.

Coordinate format is auto-detected on load. The rule is: if $\theta_\text{min} < -0.5^\circ$, the format is central; otherwise it is sided.

#### Dual Sphere Processing

Some antenna measurements cover the full sphere by measuring phi from 0 to 360 degrees. APV detects this as a "dual sphere" measurement when phi spans 0--360 degrees.

- **Split** separates the data into:
  - **Sphere 1**: $\phi \in [0^\circ, 180^\circ]$ (kept as-is)
  - **Sphere 2**: $\phi \in [180^\circ, 360^\circ]$, remapped to $[0^\circ, 180^\circ]$, with theta flipped and field components negated

  The physical basis is that a measurement at $(\theta, \phi + 180^\circ)$ observes the same far-field direction as $(-\theta, \phi)$, with a sign change in the field components.

- **Average** performs the split and then averages the two resulting patterns element-wise, reducing measurement noise.

### Normalization

| Control | Description |
|---------|-------------|
| **Amplitude** checkbox + combo | Enables amplitude normalization with method: `Peak`, `Boresight`, or `Mean` |
| **Normalize at Boresight** checkbox | Forces all phi cuts to the same amplitude and phase at $\theta = 0$ |

#### Amplitude Normalization

Given the total power pattern $P(\theta, \phi) = |E_\text{co}|^2 + |E_\text{cx}|^2$, the normalization factor $P_\text{ref}$ is computed per frequency:

| Method | Reference |
|--------|-----------|
| **Peak** | $P_\text{ref} = \max_{\theta,\phi} P(\theta, \phi)$ |
| **Boresight** | $P_\text{ref} = P(\theta_0, \phi_0)$ where $\theta_0$ and $\phi_0$ are the angles closest to zero |
| **Mean** | $P_\text{ref} = \frac{1}{N_\theta N_\phi} \sum_{\theta,\phi} P(\theta, \phi)$ |

All field components are divided by $\sqrt{P_\text{ref}}$, so the normalized gain in dB at the reference point is 0 dB.

#### Boresight Normalization

When enabled, each phi cut is individually scaled so that all cuts have the same amplitude and phase at boresight ($\theta = 0$). The algorithm:

1. Converts to Ludwig-3 $(E_x, E_y)$ components.
2. Computes the boresight value $E_x(\theta=0, \phi_i)$ for each phi cut $i$.
3. The reference amplitude is the **median** magnitude across all phi cuts: $|E_x|_\text{ref} = \text{median}_i \{|E_x(\theta=0, \phi_i)|\}$.
4. The reference phase is taken from the first phi cut.
5. Each phi cut is scaled by a complex factor to match the reference amplitude and phase at boresight.

This is useful for correcting systematic per-cut gain and phase offsets in measured data.

### Origin Shift (Measurement Correction)

| Control | Range | Step | Description |
|---------|-------|------|-------------|
| **Theta** checkbox + spinbox | $[-180^\circ, 180^\circ]$ | $0.1^\circ$ | Shifts the theta origin of every $\phi$ cut by the specified offset (interpolated along the cut) |
| **Phi** checkbox + spinbox | $[-180^\circ, 180^\circ]$ | $0.1^\circ$ | Adds the offset to the $\phi$ coordinate of every cut |

This is a measurement correction for positioner or mounting offsets, not a rotation of the antenna (see *Measurement Correction versus Rotation* above). The theta shift is carried out in central format, where each cut is a closed circle and wraps instead of clipping, and the result is mapped back onto the pattern's own grid, so it behaves the same whether the pattern is displayed in sided or central format. The checkbox enables/disables the shift. The spinbox value is applied live when the checkbox is enabled; changing the spinbox value while enabled immediately updates the pattern.

### Rotation (Antenna Orientation)

| Control | Range | Description |
|---------|-------|-------------|
| **Apply** checkbox | | Enables the rotation; angle changes are applied live while checked |
| **$\alpha$** | $[-180^\circ, 180^\circ]$ | Azimuth about $y$; $+\alpha$ tilts the boresight toward $+x$ ($\phi = 0^\circ$) |
| **$\beta$** | $[-180^\circ, 180^\circ]$ | Elevation about $x$; $+\beta$ tilts the boresight toward $+y$ ($\phi = 90^\circ$) |
| **$\gamma$** | $[-180^\circ, 180^\circ]$ | Roll about $z$, from $+x$ toward $+y$ |
| **Interpolation** | Linear / Cubic | Cubic is more accurate on coarse grids but slower |

The rotation is $R = R_y(\alpha)\,R_x(-\beta)\,R_z(\gamma)$ applied to the antenna: roll first, then elevation, then azimuth. The status line shows where the original boresight lands, $\theta_0 = \arccos(\cos\alpha\cos\beta)$, $\phi_0 = \operatorname{atan2}(\sin\beta, \sin\alpha\cos\beta)$. The rotated pattern is resampled on the pattern's own grid, in its own coordinate format, so directions that rotate outside a partial-sphere measurement come back as zero. See *Isometric Rotation* under Pattern Operations in the Theory section for the details.

### Phase Center

The phase center is the point in 3D space from which the antenna's radiation appears to originate. Translating the coordinate origin to the phase center flattens the far-field phase pattern.

| Control | Description |
|---------|-------------|
| **Theta** spinbox | The half-cone angle (0--90 degrees) over which to optimize the phase center. Default: 45 degrees |
| **Freq** combo | Frequency at which to compute the phase center |
| **Find** button | Runs the phase center optimization algorithm and populates the X, Y, Z fields |
| **X, Y, Z** spinboxes | Manual phase center coordinates in millimeters. Range: $\pm 1000$ mm. Precision: 0.01 mm |
| **Apply Phase Center Shift** checkbox | When enabled, applies the translation to the pattern |
| **Result label** | Shows the found phase center coordinates |

#### Phase Center Translation Formula

The phase shift applied to translate the coordinate origin by $(\Delta x, \Delta y, \Delta z)$ is:

$$\Delta\Phi(\theta, \phi) = k \left( \Delta x \cos\phi \sin\theta + \Delta y \sin\phi \sin\theta + \Delta z \cos\theta \right)$$

where $k = 2\pi / \lambda$ is the wavenumber at the operating frequency, and $\lambda = c / f$ is the wavelength. The translation is applied independently to both $E_\theta$ and $E_\phi$ components:

$$E'_\theta(\theta, \phi) = |E_\theta| \cdot e^{j(\angle E_\theta + \Delta\Phi)}$$

$$E'_\phi(\theta, \phi) = |E_\phi| \cdot e^{j(\angle E_\phi + \Delta\Phi)}$$

#### Phase Center Finding Algorithm

The **Find** button uses `scipy.optimize.basinhopping` to minimize the phase variation over the specified cone angle and all phi cuts at the selected frequency. The cost function minimizes the standard deviation of the phase pattern after translation.

> **Tip:** A smaller theta angle (e.g., 10--20 degrees) finds the phase center relevant to the main beam. A larger angle (e.g., 45--60 degrees) finds a global best-fit phase center. The X/Y coordinates are typically near zero for rotationally symmetric antennas; the Z coordinate represents the axial offset.

### MARS (Mathematical Absorber Reflection Suppression)

| Control | Description |
|---------|-------------|
| **Apply** checkbox | Enables/disables MARS processing |
| **Max Extent** spinbox | Maximum radial extent of the antenna under test, in meters. Range: 0.001--10.0 m. Precision: 0.001 m. Default: 0.5 m |
| **Taper** spinbox | Number of mode orders above $n_\text{max}$ over which the filter rolls off with a raised cosine. 0 (default) is a brick wall. Range: 0--100 |

Changing either value while **Apply** is checked re-applies the filter.

MARS suppresses room reflections and scattering artifacts in measured antenna patterns by filtering each great-circle phi cut in the cylindrical mode domain (far-field MARS). The algorithm:

1. For each frequency, compute the wavenumber $k = 2\pi f / c$.
2. Determine the maximum mode order: $n_\text{max} = \lfloor k \cdot a \rfloor$, where $a$ is the maximum radial extent.
3. Decompose each phi cut (a closed circle in theta, central format) into Fourier modes.
4. Retain modes with index $|n| \leq n_\text{max}$ in full, roll off over the next **Taper** orders, and zero out the rest.
5. Reconstruct the filtered pattern.

The physical rationale is that a source of maximum extent $a$ can only radiate modes up to order $n \approx ka$. Modes beyond this order are due to measurement artifacts (reflections, diffraction from the test range).

A pattern whose theta cuts do not span a full circle (a sector from a far-field or compact range, or a sided hemisphere) is zero-padded to a full circle before filtering, which is the sector processing of far-field MARS. Expect ringing near the sector edges; the library logs a warning naming them.

> **Guideline:** Set **Max Extent** to the physical radius of the antenna under test (including any feed structure or support), measured from the origin the pattern is referred to. Apply the phase center translation first so that the antenna is centred; the pipeline runs Phase Center before MARS for this reason. Too small a value over-smooths the pattern; too large a value retains artifacts.

A brick-wall mode filter (Taper 0) spreads the residual of a removed reflection along the whole cut with slowly decaying sidelobes. A taper of a few to ten orders confines that residual at the cost of retaining slightly more of the reflection. See the FarFieldSpherical pattern operations documentation for the weights and measured trade-off.

---

## Analysis Panel (Panel 3)

The Analysis Panel provides three capabilities: **Spherical Wave Expansion (SWE)** for modal decomposition, **Near Field Evaluation** from SWE coefficients, and **Cross-Polarization Metrics** for evaluating a reflector feed over its illumination cone.

### Spherical Wave Expansion (SWE) Section

SWE decomposes a far-field pattern into spherical mode coefficients $Q_1^{smn}$ and $Q_2^{smn}$, where $s$ is the polarization index, $m$ is the azimuthal order, and $n$ is the polar degree.

| Control | Description |
|---------|-------------|
| **Frequencies** list | Check one or more frequencies at which to compute SWE coefficients; all are checked by default |
| **Select All / Clear All** | Quickly change the SWE frequency selection |
| **Source radius r** | Radius in meters of the minimum sphere enclosing the antenna sources; used to compute the physical maximum mode order |
| **NMAX: Auto** checkbox | When checked, the physical maximum is computed from the source radius and frequency. When unchecked, the spinbox (range 1--500) truncates the result to a manual limit |
| **MMAX: Auto** checkbox | When checked, the physical maximum is computed automatically. When unchecked, the spinbox (range 0--500) truncates the result to a manual limit |
| **Calculate SWE Coefficients** button | Starts the SWE calculation in a background thread (the GUI remains responsive) |

#### SWE Mode Indices

- **NMAX** (maximum polar degree $n$): Controls the angular resolution. Higher values capture finer angular features. The auto value is typically derived from the theta sampling: $N_\text{max} \approx N_\theta - 1$.
- **MMAX** (maximum azimuthal order $|m|$): Controls the phi-direction resolution. The auto value is derived from the phi sampling: $M_\text{max} \approx N_\phi / 2$.

#### Results Display

After a successful calculation, the results text area shows:

| Field | Description |
|-------|-------------|
| **Frequency** | The frequency at which coefficients were computed (in GHz) |
| **MMAX, NMAX** | The mode indices used |
| **Total coefficients** | Number of $Q_1$ + $Q_2$ coefficients |
| **Total power** | $P_\text{total} = \sum_{n,m} \left( |Q_1^{nm}|^2 + |Q_2^{nm}|^2 \right)$ |

#### Power Per Mode Plot

Below the results, a two-subplot figure is displayed:

1. **Top: Cumulative Power vs. $n$**
   - Plots the cumulative fraction of total power as a function of polar mode order $n$.
   - A dashed red line marks the 99.9% threshold.
   - This plot shows how quickly the power converges with increasing $n$. A sharp rise to 99.9% indicates the pattern is well-sampled.

2. **Bottom: Relative Power per $|m|$**
   - Bar chart of power per azimuthal index $|m|$, in dB relative to total power.
   - Shows which azimuthal modes carry significant power. A rotationally symmetric antenna will have most power concentrated at low $|m|$ values.

#### Background Computation

The SWE calculation runs in a dedicated `QThread` (via `SWEWorker`) to prevent the GUI from freezing. During computation:

- The button text changes to "Calculating..."
- The button is disabled to prevent duplicate calculations
- The results area shows the current frequency and overall progress
- On completion, results for every selected frequency are displayed and stored on the pattern object at `pattern.swe[frequency]`

If the pattern was loaded from a `.sph` file, SWE data is already available and displayed immediately without requiring re-calculation.

### Near Field Evaluation Section

After SWE coefficients have been calculated (or loaded from a `.sph` file), the near field can be evaluated on arbitrary surfaces.

| Control | Description |
|---------|-------------|
| **Surface Type** combo | `Spherical Surface` or `Planar Surface` |
| **Calculate Near Field** button | Starts the near-field evaluation (enabled only after SWE data exists) |

#### Spherical Surface Parameters

| Parameter | Range | Default | Description |
|-----------|-------|---------|-------------|
| **Radius** | 0.001--10.0 m | 0.05 m | Radius of the evaluation sphere |
| **Theta Points** | 10--361 | 91 | Number of theta samples from $0^\circ$ to $180^\circ$ |
| **Phi Points** | 10--361 | 91 | Number of phi samples from $0^\circ$ to $360^\circ$ |

The near field is evaluated at each $(r, \theta, \phi)$ grid point using the SWE `near_field()` method, which computes all six components: $E_r$, $E_\theta$, $E_\phi$, $H_r$, $H_\theta$, $H_\phi$.

#### Planar Surface Parameters

| Parameter | Range | Default | Description |
|-----------|-------|---------|-------------|
| **X Extent** | 0.01--10.0 m | 0.5 m | Half-width in the x-direction (total width is $2 \times$ extent) |
| **Y Extent** | 0.01--10.0 m | 0.5 m | Half-width in the y-direction |
| **Z Distance** | 0.001--10.0 m | 0.1 m | Distance of the evaluation plane from the origin along z |
| **X Points** | 10--501 | 51 | Number of x samples |
| **Y Points** | 10--501 | 51 | Number of y samples |

For planar evaluation, the Cartesian grid points $(x, y, z)$ are converted to spherical coordinates $(r, \theta, \phi)$ before calling the SWE near-field computation.

#### Near Field Results

After computation, the results text area shows:

- Surface type (spherical or planar)
- Grid dimensions and extents
- The near-field data is emitted via the `nearfield_calculated` signal, which populates the **Near Field** dock widget in the center area

### Cross-Polarization Metrics Section

Evaluates the feed cross-polarization requirements defined in *Cross-Polarization Metrics for a Reflector Feed* on the **processed** pattern (the one currently displayed), so a polarization or coordinate-format change on the Processing panel is reflected in the results. The definitions are in the Theory section under Analysis Functions.

| Control | Description |
|---------|-------------|
| **Illumination half-angle $\theta_e$** | Half-angle of the cone subtended by the reflector at the feed (1--90$^\circ$, default 35$^\circ$). All metrics are integrated or searched over $0 \le \theta \le \theta_e$ |
| **Max azimuthal order** | Highest azimuthal order $n$ retained in the cross-pol mode spectrum (0--12, default 6). Must not exceed the Nyquist order of the $\phi$ grid |
| **Check against requirements** | When checked, the requirement fields below are enabled and the results are colored by pass/fail |
| **XPD_int $\ge$** | Minimum integrated XPD in dB (default 20) |
| **n = 0 level $\ge$** | Minimum $n = 0$ cross-pol level in dB (default 40) |
| **Bands (GHz)** | Comma-separated `lo-hi` pairs in GHz (default `8-11, 13-15`). Frequencies outside these bands are reported but excluded from pass/fail. Leave blank to treat every frequency as in band |
| **Compute Cross-Pol Metrics** | Runs the computation (milliseconds; no background thread) |
| **Export CSV** | Writes the last result to CSV, one row per frequency, with a column per azimuthal mode |

The pattern must cover a full 360$^\circ$ in $\phi$ on a uniform grid (a duplicated endpoint such as $-180/+180$ is handled), and $\theta$ must be uniformly spaced inside the cone. A half-plane measurement ($\phi$ 0--180 in sided form) cannot be evaluated; the error message in the summary line says which condition failed.

#### Results Table

One row per frequency; all values in dB.

| Column | Meaning |
|--------|---------|
| **f (GHz)** | Frequency |
| **In band** | `Yes`/`No` when requirement checking is on, otherwise a dash |
| **Edge taper** | $\phi$-averaged co-pol amplitude at $\theta_e$ relative to peak. Sanity check on the feed / illumination-angle pairing; about $-10$ to $-13$ dB for a typical design |
| **XPD_int** | Integrated XPD: co- to cross-polarized power ratio over the cone. Requirement 2 |
| **n=0 level** | Peak co-pol amplitude over the azimuthally symmetric ($n = 0$) component of the cross-pol field, worst case over the cone. Requirement 1 |
| **Worst point XPD** | Minimum over the cone of co/cross at the same angle. Conventional and pessimistic; for comparison only |
| **Peak xpol** | Peak co-pol over the peak cross-pol in the cone. The datasheet-style number; for comparison only |

When requirement checking is on, the **XPD_int** and **n=0 level** cells show the margin to the limit in parentheses and are colored green (pass) or red (fail). The summary line below the table reports the worst in-band values and an overall PASS/FAIL; without checking, it reports the worst values over all frequencies.

The $n = 0$ level of a horn-only, azimuthally symmetric simulation sits at the solver's numerical floor (typically 65--80 dB) and is not representative of the assembled feed.

---

## Export Panel (Panel 4)

The Export Panel saves the current pattern to various file formats.

### Export Options

| Control | Options | Description |
|---------|---------|-------------|
| **File Type** | `NPZ`, `CUT`, `FFD`, `SPH`, `CSV`, `PKL` | Output format (see table below) |
| **Frequency** | `All frequencies` / `Selected only` | Export all frequency points or only the frequencies selected in the View panel |
| **Processing** | `With processing` / `Raw data` | Export the processed pattern (with all enabled transforms applied) or the original unmodified data |
| **Export...** button | Opens a save dialog to choose the output file path |

### File Formats

| Format | Extension | Description | Notes |
|--------|-----------|-------------|-------|
| **NPZ** | `.npz` | NumPy archive | Native format preserving all metadata. Recommended for archival |
| **CUT** | `.cut` | GRASP/TICRA cut file | Standard exchange format for antenna simulation tools |
| **FFD** | `.ffd` | NSI far-field data | Standard format for NSI near-field measurement systems |
| **SPH** | `.sph` | TICRA spherical wave expansion | Exports SWE coefficients. **Requires** SWE to be calculated first in the Analysis panel |
| **CSV** | `.csv` | Comma-separated values | Human-readable tabular export for external analysis |
| **PKL** | `.pkl` | Matplotlib figure pickle | Saves the current 2D plot figure as a Python pickle. Can be reopened in matplotlib for further editing |

### Format-Specific Notes

**SPH Export:** This format exports spherical wave expansion coefficients, not raw field data. You must first calculate SWE coefficients in the Analysis panel. "All frequencies" writes every calculated frequency block to one `.sph` file; "Selected only" writes the calculated frequencies selected in the View panel. If SWE data is not available, the export will fail with an error message directing you to the Analysis panel.

**PKL Export:** This saves the `matplotlib.figure.Figure` object from the 2D plot widget. To reload:

```python
import pickle
import matplotlib.pyplot as plt

with open("my_plot.pkl", "rb") as f:
    fig = pickle.load(f)
fig.show()
plt.show()
```

**Selected Frequency:** For far-field formats, when "Selected only" is chosen, the first frequency selected in the View panel is exported. For SPH, all selected frequencies with calculated SWE data are written. If no frequency is selected, the first available frequency is used.

---

## Center Dock Widgets

### 2D Plot

The primary visualization widget, powered by matplotlib. It renders either 1D Cartesian cuts or 2D polar color maps depending on the Format selection in the View panel.

**Features:**

- Standard matplotlib navigation toolbar (zoom, pan, home, save figure)
- Automatic axis labeling based on the selected value type and component
- Multi-frequency overlay when multiple frequencies are selected
- Cross-pol overlay when "Show Cross-Pol" is enabled
- Statistics overlay with optional min/max shading
- Multi-pattern comparison overlay when enabled

**1D Cut Mode:**

- X-axis: Theta angle (degrees)
- Y-axis: Gain (dBi), Phase (degrees), or Axial Ratio (dB) depending on Value selection
- Each selected phi angle is plotted as a separate trace
- Legend identifies each trace by phi angle, frequency, and/or pattern name

**2D Polar Mode:**

- Polar coordinate plot with theta as the radial axis and phi as the angular axis
- Color represents the selected value (gain, phase, or axial ratio)
- Colorbar indicates the value range

**Plot strip:** the row under the canvas holds Grid, Legend, Normalize, Smooth (2D only), the axis limit fields, Reset Scale, Export Plot Data and Style…. Axis limits are remembered per loaded pattern and survive processing toggles, so a MARS on/off comparison keeps its scale.

### Plot Style Dialog

**Style…** on the plot strip opens a floating, non-modal dialog. It takes no room from the layout, can be moved beside the plot, and every edit applies live. There is one style per plot format (1D cut, 2D polar, near field); the dialog shows which one it is editing.

| Tab | Controls |
|-----|----------|
| **Text** | Title, X label, Y label, colorbar label (each blank = the plotting default); font family; sizes for title, axis labels, tick labels and legend (Auto = default) |
| **Axes & Grid** | Major tick step for X and Y (radial on the polar view); minor grid; grid line style and opacity; polar zero location and direction; dark background; figure and axes colours |
| **Legend & Lines** | Legend location (including outside right), columns, frame; line width for every trace; colour cycle (tab10, Set1, viridis, …) |
| **Series** | One row per trace on screen: legend label, colour (double-click to pick), width, style and visibility. Overrides are keyed by the trace's original label, so they persist across replots and processing changes |

The header offers built-in presets (Default, Publication, Presentation, Dark); applying a preset keeps your per-trace edits. **Save…** and **Load…** exchange a style as JSON so a group can share a house style; **Reset** returns the current format to the plotting defaults. Styles are remembered between sessions.

Legend and grid *visibility* stay on the plot strip; the dialog controls how they look.

### Exporting a Figure

The 2D dock's export opens a small dialog: file and format (PNG, PDF, SVG, JPEG, TIFF), width and height in inches, resolution in dpi, transparent background, and margin trimming. PDF and SVG are vector formats and are what a publication wants; the size in inches decides how large the fonts appear on the page. The figure is resized only for the write and the on-screen canvas is unchanged. The current plot style is applied, so what you see is what is exported.

### 3D Plot

Reserved for future implementation. Currently displays a placeholder message.

### Data Display

A tabular view showing the raw numerical data of the active pattern. Displays field component values for the selected frequency, theta, and phi angles.

### Near Field

Displays the results of a near-field calculation performed from the Analysis panel. Shows E-field and H-field component magnitudes on the specified evaluation surface (spherical or planar).

This tab is populated only after clicking **Calculate Near Field** in the Analysis panel with valid SWE data.

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `F1` | Open help documentation |
| `Shift+F1` | Context-sensitive help for the current panel |

---

## Glossary

| Term | Definition |
|------|------------|
| **Active pattern** | The pattern currently displayed in the plots and available for processing. Shown with a checkmark and blue highlight in the Pattern Strip |
| **Boresight** | The direction $\theta = 0$ (the antenna's main axis) |
| **Central format** | Coordinate system where theta is symmetric about boresight, e.g., $\theta \in [-90^\circ, 90^\circ]$ |
| **Co-pol** | The desired polarization component of the antenna |
| **Comparison set** | A group of patterns overlaid on the same plot axes for comparison |
| **Cross-pol** | The undesired orthogonal polarization component |
| **Dual sphere** | A measurement where phi spans 0--360 degrees, effectively capturing two hemispheres |
| **Ludwig-3** | A polarization definition where co-pol is aligned with the antenna's principal plane: $E_x = E_\theta \cos\phi - E_\phi \sin\phi$ |
| **MARS** | Mathematical Absorber Reflection Suppression -- a spatial filtering technique to remove measurement artifacts |
| **NMAX** | Maximum polar mode index (degree) in the spherical wave expansion |
| **MMAX** | Maximum azimuthal mode index (order) in the spherical wave expansion |
| **Phase center** | The effective point of radiation origin, where the far-field phase pattern is approximately constant |
| **Sided format** | Coordinate system where theta goes from 0 to a maximum angle, e.g., $\theta \in [0^\circ, 180^\circ]$ |
| **SWE** | Spherical Wave Expansion -- decomposition of a field into spherical harmonic modes |

---

## Related Documentation

- [Getting Started](getting_started.md) -- Installation, quick start, and application layout overview
- [FarFieldSpherical: Coordinate Systems](../../FarFieldSpherical/docs/coordinate_systems.md) -- Theory of central vs. sided coordinate formats
- [FarFieldSpherical: Polarization](../../FarFieldSpherical/docs/polarization.md) -- Polarization basis conversions (theta/phi, Ludwig-3, circular)
- [FarFieldSpherical: Pattern Operations](../../FarFieldSpherical/docs/pattern_operations.md) -- Detailed algorithms for translate, normalize, MARS, etc.
- [Spherical Wave Expansion: SWE Theory](../../spherical_wave_expansion/docs/swe_theory.md) -- Mathematical foundations of spherical mode decomposition and near-field evaluation
