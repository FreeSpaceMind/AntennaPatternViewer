from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import numpy as np
import logging

logger = logging.getLogger(__name__)


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
        
        logger.debug("PlotNearFieldWidget initialized")
    
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
        x = self.near_field_data['x']
        y = self.near_field_data['y']
        
        # Get field data
        if component == '|E|':
            # Total E-field magnitude
            E_mag_sq = 0
            for key in ['E_x', 'E_y', 'E_z']:
                if key in self.near_field_data:
                    E_mag_sq += np.abs(self.near_field_data[key])**2
            field_data = np.sqrt(E_mag_sq)
        elif component == '|H|':
            # Total H-field magnitude
            H_mag_sq = 0
            for key in ['H_x', 'H_y', 'H_z']:
                if key in self.near_field_data:
                    H_mag_sq += np.abs(self.near_field_data[key])**2
            field_data = np.sqrt(H_mag_sq)
        else:
            field_data = np.abs(self.near_field_data[component])
        
        # Convert to dB
        magnitude_db = 20 * np.log10(field_data + 1e-10)
        
        logger.info(f"Plotting {component}: range {np.min(magnitude_db):.2f} to {np.max(magnitude_db):.2f} dB")
        
        im = ax.imshow(magnitude_db, 
                      extent=[np.min(x), np.max(x), np.min(y), np.max(y)],
                      cmap='jet', 
                      aspect='equal',
                      origin='lower')
        
        ax.set_xlabel('X (m)')
        ax.set_ylabel('Y (m)')
        ax.set_title(f'Near Field Pattern: {component}')
        self.figure.colorbar(im, ax=ax, label='Magnitude (dB)')
        
        self.canvas.draw()
    
    def clear(self):
        """Clear the plot."""
        self.figure.clear()
        self.canvas.draw()