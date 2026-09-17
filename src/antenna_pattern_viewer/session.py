"""
Session files: everything needed to reopen a comparison tomorrow.

A session is JSON holding the loaded files with the options they were read
with, each instance's processing state, view settings and comparison
membership, the active instance, the plot styles, the specification masks,
the plot strip settings and the window geometry. Patterns themselves are
not stored; they are re-read from their files on load.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import numpy as np

from .plot_style import PlotStyle
from .spec_mask import SpecMask

logger = logging.getLogger(__name__)

SESSION_VERSION = 1
SESSION_SUFFIX = '.apvsession'


def _jsonable(value):
    """Convert numpy scalars/arrays and tuples so json can write them."""
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, np.ndarray):
        return [_jsonable(v) for v in value.tolist()]
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, Path):
        return str(value)
    return value


# ------------------------------------------------------------------ collect

def collect_session(main_window) -> Dict[str, Any]:
    """Snapshot the application state into a plain dictionary."""
    from .widgets.plot_widget import PlotWidget
    from .widgets.view_panel import ViewPanel

    model = main_window.data_model
    active = model.get_active_instance()
    if active is not None:
        # The model holds the live state for the active instance; the copy
        # on the instance is only refreshed when the selection changes.
        active.processing_state = dict(model._processing_state)
        active.view_params = dict(model.get_all_view_params())

    comparison_ids = {inst.instance_id for inst in model.get_comparison_instances()}
    instances = []
    for inst in model.get_all_instances():
        instances.append({
            'source_file': str(inst.source_file) if inst.source_file else None,
            'display_name': inst.display_name,
            'load_options': _jsonable(getattr(inst, 'load_options', {}) or {}),
            'processing_state': _jsonable(inst.processing_state or {}),
            'view_params': _jsonable(inst.view_params or {}),
            'in_comparison': inst.instance_id in comparison_ids,
            'active': active is not None and inst.instance_id == active.instance_id,
            'notes': getattr(inst, 'notes', ''),
        })

    plot_widget = main_window.findChild(PlotWidget)
    view_panel = main_window.findChild(ViewPanel)
    data = {
        'version': SESSION_VERSION,
        'instances': instances,
        'view_params': _jsonable(model.get_all_view_params()),
        'view_panel': _jsonable(view_panel.get_current_parameters()) if view_panel else {},
        'plot_styles': {key: style.to_dict() for key, style in plot_widget.styles.items()}
                       if plot_widget else {},
        'masks': [m.to_dict() for m in plot_widget.masks] if plot_widget else [],
        'plot_strip': plot_widget.strip_state() if plot_widget else {},
        'window_geometry': bytes(main_window.saveGeometry().toHex()).decode('ascii'),
        'window_state': bytes(main_window.saveState().toHex()).decode('ascii'),
    }
    return data


def write_session(path, data: Dict[str, Any]) -> Path:
    path = Path(path)
    if path.suffix.lower() != SESSION_SUFFIX:
        path = path.with_suffix(SESSION_SUFFIX)
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(data, handle, indent=2)
    return path


def read_session(path) -> Dict[str, Any]:
    with open(path, 'r', encoding='utf-8') as handle:
        data = json.load(handle)
    if not isinstance(data, dict) or 'instances' not in data:
        raise ValueError("Not a session file")
    version = int(data.get('version', 0))
    if version > SESSION_VERSION:
        raise ValueError(f"Session version {version} is newer than this viewer supports")
    return data


# ------------------------------------------------------------------ restore

def restore_session(main_window, data: Dict[str, Any],
                    on_done: Optional[Callable[[List[str]], None]] = None):
    """
    Rebuild the application state from ``data``.

    The pattern files are re-read in the background; the per-instance state
    is applied once they arrive. ``on_done`` receives the list of files that
    could not be loaded (their entries are skipped).
    """
    from .widgets.file_manager_widget import FileManagerWidget
    from .widgets.plot_widget import PlotWidget
    from .widgets.view_panel import ViewPanel

    model = main_window.data_model
    file_manager = main_window.findChild(FileManagerWidget)
    plot_widget = main_window.findChild(PlotWidget)
    view_panel = main_window.findChild(ViewPanel)

    # Window and plot settings do not depend on the files
    geometry = data.get('window_geometry')
    if geometry:
        from PyQt6.QtCore import QByteArray
        main_window.restoreGeometry(QByteArray.fromHex(geometry.encode('ascii')))
    state = data.get('window_state')
    if state:
        from PyQt6.QtCore import QByteArray
        main_window.restoreState(QByteArray.fromHex(state.encode('ascii')))
    if plot_widget is not None:
        for key, style_data in (data.get('plot_styles') or {}).items():
            if key in plot_widget.styles:
                plot_widget.styles[key] = PlotStyle.from_dict(style_data)
        plot_widget._save_styles()
        plot_widget.set_masks([SpecMask.from_dict(m) for m in data.get('masks') or []])
        plot_widget.apply_strip_state(data.get('plot_strip') or {})

    # Drop what is loaded now: a session replaces the workspace
    for inst in list(model.get_all_instances()):
        model.remove_instance(inst.instance_id)

    entries = [e for e in data.get('instances', []) if e.get('source_file')]
    missing = [e['source_file'] for e in entries if not Path(e['source_file']).exists()]
    entries = [e for e in entries if Path(e['source_file']).exists()]

    def finish(loaded):
        """``loaded``: list of (path, instance) in the order they arrived."""
        by_path: Dict[str, list] = {}
        for path, inst in loaded:
            by_path.setdefault(str(Path(path)), []).append(inst)
        active_id = None
        states = {}
        for entry in entries:
            queue = by_path.get(str(Path(entry['source_file'])))
            if not queue:
                continue
            inst = queue.pop(0)
            inst.display_name = entry.get('display_name') or inst.display_name
            inst.notes = entry.get('notes', '')
            inst.view_params = dict(entry.get('view_params') or {})
            inst.processed_pattern = None
            states[inst.instance_id] = dict(entry.get('processing_state') or {})
            if entry.get('in_comparison'):
                model.add_to_comparison(inst.instance_id)
            if entry.get('active'):
                active_id = inst.instance_id
        if active_id is None and loaded:
            active_id = loaded[0][1].instance_id
        # Switching saves the outgoing instance's live (default) state onto
        # it, so the restored states go on after the switch: the active one
        # through the model, the others onto their instances for when they
        # are activated or compared.
        if active_id is not None:
            model.set_active_instance(active_id)
        for inst in model.get_all_instances():
            state = states.get(inst.instance_id)
            if state is None:
                continue
            if inst.instance_id == active_id:
                model.set_processing_state(state)
            else:
                # JSON turned tuples into lists; the live state keeps tuples
                # (the MARS pair, the rotation) so the pipeline cache keys match.
                inst.processing_state = {k: tuple(v) if isinstance(v, list) else v
                                         for k, v in state.items()}
                inst.processed_pattern = None
        if view_panel is not None:
            view_panel.apply_parameters(data.get('view_panel') or {})
        if on_done is not None:
            on_done(missing)

    if not entries:
        finish([])
        return
    if file_manager is None:
        raise RuntimeError("No file manager to load the session's files with")
    file_manager.load_files_with_options(
        [(Path(e['source_file']), e.get('load_options') or {}) for e in entries],
        on_finished=finish)
