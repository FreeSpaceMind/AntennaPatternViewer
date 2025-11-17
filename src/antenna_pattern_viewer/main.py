"""
Entry point for standalone Antenna Pattern Viewer application.
"""
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt


def main():
    """Launch the Antenna Pattern Viewer application."""
    
    # Enable high DPI display support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("Antenna Pattern Viewer")
    app.setOrganizationName("AntennaPatternViewer")
    
    # Import here to avoid issues with relative imports
    from antenna_pattern_viewer.antenna_pattern_widget import AntennaPatternWidget
    
    # Create and show main window
    main_window = AntennaPatternWidget()
    main_window.show()
    
    # Start event loop
    sys.exit(app.exec())


if __name__ == '__main__':
    main()