"""
Setup script for antenna-pattern-viewer package.

This setup.py is provided for backward compatibility with older build tools.
Modern installations should use pyproject.toml directly with:
    pip install .
"""

from setuptools import setup, find_packages

# Read long description from README
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="antenna-pattern-viewer",
    version="1.0.0",
    author="Justin Long",
    author_email="justinwlong1@gmail.com",
    description="GUI application for visualizing antenna far-field patterns",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/antenna-pattern-viewer",
    project_urls={
        "Bug Tracker": "https://github.com/yourusername/antenna-pattern-viewer/issues",
        "Documentation": "https://antenna-pattern-viewer.readthedocs.io",
        "Source Code": "https://github.com/yourusername/antenna-pattern-viewer",
    },
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Visualization",
    ],
    python_requires=">=3.9",
    install_requires=[
        "farfield-spherical>=1.0.0",
        "PyQt6>=6.4.0",
        "matplotlib>=3.5.0",
        "numpy>=1.21.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-qt>=4.0.0",
            "pytest-cov>=3.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "antenna-pattern-viewer=antenna_pattern_viewer.__main__:main",
        ],
        "gui_scripts": [
            "antenna-pattern-viewer-gui=antenna_pattern_viewer.__main__:main",
        ],
    },
    keywords="antenna pattern viewer GUI visualization PyQt6",
)