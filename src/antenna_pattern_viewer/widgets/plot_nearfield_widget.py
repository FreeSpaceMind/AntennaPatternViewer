from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import numpy as np


class PlotNearFieldWidget(QWidget):
    """Widget for displaying near field patterns."""
    
    def __init__(self, data_model, parent=None):
        super().__init__(parent)
        self.data_model = data_model
        self.near_field_data = None
        
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        # Component selector
        component_layout = QHBoxLayout()
        component_layout.addWidget(QLabel("Field Component:"))
        self.component_combo = QComboBox()
        self.component_combo.currentTextChanged.connect(self.update_plot)
        component_layout.addWidget(self.component_combo)
        component_layout.addStretch()
        
        layout = QVBoxLayout()
        layout.addLayout(component_layout)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        self.setLayout(layout)
    
    def plot_near_field(self, near_field_data):
        """Store near field data and plot."""
        self.near_field_data = near_field_data
        
        # Compute Cartesian components if planar
        if not near_field_data.get('is_spherical', True):
            self._compute_cartesian_components()
        
        # Update component list
        self._update_component_list()
        
        # Plot
        self.update_plot()
    
    def _compute_cartesian_components(self):
        """Compute Cartesian field components from spherical."""
        from swe.core import spherical_to_cartesian_field, cartesian_to_spherical
        
        # Get grid
        x = self.near_field_data['x']
        y = self.near_field_data['y']
        X, Y = np.meshgrid(x, y, indexing='ij')
        Z = np.full_like(X, self.near_field_data['z_distance'])
        
        # Convert to spherical for coordinate transformation
        r, theta, phi = cartesian_to_spherical(X.ravel(), Y.ravel(), Z.ravel())
        
        # Get spherical components
        E_r = self.near_field_data['E_r'].ravel()
        E_theta = self.near_field_data['E_theta'].ravel()
        E_phi = self.near_field_data['E_phi'].ravel()
        
        H_r = self.near_field_data['H_r'].ravel()
        H_theta = self.near_field_data['H_theta'].ravel()
        H_phi = self.near_field_data['H_phi'].ravel()
        
        # Convert to Cartesian
        E_x, E_y, E_z = spherical_to_cartesian_field(E_r, E_theta, E_phi, theta, phi)
        H_x, H_y, H_z = spherical_to_cartesian_field(H_r, H_theta, H_phi, theta, phi)
        
        # Store as grid
        shape = X.shape
        self.near_field_data['E_x'] = E_x.reshape(shape)
        self.near_field_data['E_y'] = E_y.reshape(shape)
        self.near_field_data['E_z'] = E_z.reshape(shape)
        self.near_field_data['H_x'] = H_x.reshape(shape)
        self.near_field_data['H_y'] = H_y.reshape(shape)
        self.near_field_data['H_z'] = H_z.reshape(shape)
    
    def _total_magnitude(self, field):
        """
        Total |E| or |H| on the grid.

        The data dictionary can hold both the spherical triad and, for a planar
        cut, the Cartesian one. They describe the same vector, so summing both
        would double the power and report 3 dB high; the Cartesian triad is
        preferred when present.
        """
        cartesian = [f'{field}_x', f'{field}_y', f'{field}_z']
        spherical = [f'{field}_r', f'{field}_theta', f'{field}_phi']
        keys = cartesian if all(k in self.near_field_data for k in cartesian) else spherical
        magnitude_sq = sum(np.abs(self.near_field_data[k]) ** 2
                           for k in keys if k in self.near_field_data)
        return np.sqrt(magnitude_sq)

    def _update_component_list(self):
        """Update available components based on data."""
        self.component_combo.blockSignals(True)
        self.component_combo.clear()
        
        # Add all available components
        components = ['|E|', '|H|']
        for key in ['E_x', 'E_y', 'E_z', 'E_theta', 'E_phi', 'E_r',
                    'H_x', 'H_y', 'H_z', 'H_theta', 'H_phi', 'H_r']:
            if key in self.near_field_data:
                components.append(key)
        
        self.component_combo.addItems(components)
        self.component_combo.blockSignals(False)
    
    def update_plot(self):
        """Update the plot with selected component."""
        if self.near_field_data is None:
            return

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        component = self.component_combo.currentText()
        is_spherical = self.near_field_data.get('is_spherical', True)

        # Get coordinate arrays based on data type
        if is_spherical:
            x = self.near_field_data['phi']
            y = self.near_field_data['theta']
            xlabel = 'Phi (deg)'
            ylabel = 'Theta (deg)'
        else:
            x = self.near_field_data['x']
            y = self.near_field_data['y']
            xlabel = 'X (m)'
            ylabel = 'Y (m)'

        # Get field data
        if component in ('|E|', '|H|'):
            field_data = self._total_magnitude(component[1])
        else:
            field_data = np.abs(self.near_field_data[component])

        # Convert to dB
        magnitude_db = 20 * np.log10(field_data + 1e-10)

        # The grids are built with indexing='ij', so rows are the first
        # coordinate (x, or theta). pcolormesh takes the coordinate arrays
        # explicitly, which keeps the orientation right for non-square and
        # asymmetric grids; imshow would show the transpose.
        mesh_x, mesh_y = np.meshgrid(x, y, indexing='ij')
        im = ax.pcolormesh(mesh_x, mesh_y, magnitude_db, cmap='jet', shading='auto')
        ax.set_aspect('equal' if not is_spherical else 'auto')

        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_title(f'Near Field Pattern: {component}')
        self.figure.colorbar(im, ax=ax, label='Magnitude (dB)')

        self.canvas.draw()
    
    def clear(self):
        """Clear the plot."""
        self.figure.clear()
        self.canvas.draw()