"""
Module entry point so that ``python -m antenna_pattern_viewer`` works and the
console scripts declared in the packaging metadata resolve.
"""
from .main import main

if __name__ == "__main__":
    main()
