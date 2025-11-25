"""Workspace state helpers."""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Dict, List
import json
import time

STATE_PATH = Path("workspace_state.json")


def load_state(path: Path = STATE_PATH) -> Dict:
    if not path.exists():
        return {"toolkit_selection": [], "angles": []}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return {"toolkit_selection": [], "angles": []}


def persist_state(state: Dict, path: Path = STATE_PATH) -> None:
    path.write_text(json.dumps(state, indent=2))


def record_selection(tools: List[Dict], path: Path = STATE_PATH) -> Dict:
    state = load_state(path)
    state["toolkit_selection"] = [tool for tool in tools]
    state.setdefault("selection_log", []).append({
        "timestamp": time.time(),
        "tools": tools,
    })
    persist_state(state, path)
    return state


def record_angles(angles: List[Dict], path: Path = STATE_PATH) -> Dict:
    state = load_state(path)
    state["angles"] = angles
    state.setdefault("angle_log", []).append({
        "timestamp": time.time(),
        "angles": angles,
    })
    persist_state(state, path)
    return state


def choose_angle(angle_id: str, path: Path = STATE_PATH) -> Dict:
    state = load_state(path)
    for angle in state.get("angles", []):
        if angle.get("id") == angle_id:
            angle["status"] = "selected"
            break
    persist_state(state, path)
    return state


def override_angle(angle_id: str, new_text: str, path: Path = STATE_PATH) -> Dict:
    state = load_state(path)
    for angle in state.get("angles", []):
        if angle.get("id") == angle_id:
            angle["angle"] = new_text
            angle["status"] = "overridden"
            break
    persist_state(state, path)
    return state

