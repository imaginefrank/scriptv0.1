"""State management for archetype beats, clips, and runtime checks."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .archetypes import Archetype, BeatSlot

FIFTEEN_MINUTES = 15 * 60


@dataclass
class ClipSelection:
    clip_id: str
    in_point: float
    out_point: float

    def duration(self) -> float:
        return max(0.0, self.out_point - self.in_point)


@dataclass
class BeatState:
    slot: BeatSlot
    text: str = ""
    clip: Optional[ClipSelection] = None
    operator_approved: bool = False

    def spoken_runtime(self) -> float:
        words = len(self.text.split())
        return words / 2.5

    def clip_runtime(self) -> float:
        return self.clip.duration() if self.clip else 0.0

    def total_runtime(self) -> float:
        return self.spoken_runtime() + self.clip_runtime()


@dataclass
class ScriptState:
    """Aggregated state for a scripted segment."""

    archetype: Archetype
    beats: Dict[str, BeatState] = field(default_factory=dict)

    @classmethod
    def from_archetype(cls, archetype: Archetype) -> "ScriptState":
        beats = {slot.name: BeatState(slot=slot) for slot in archetype.slots}
        return cls(archetype=archetype, beats=beats)

    def set_text(self, slot_name: str, text: str) -> None:
        self._require_slot(slot_name)
        self.beats[slot_name].text = text.strip()

    def set_clip(self, slot_name: str, clip_id: str, in_point: float, out_point: float) -> None:
        self._require_slot(slot_name)
        self.beats[slot_name].clip = ClipSelection(clip_id=clip_id, in_point=in_point, out_point=out_point)

    def approve_transition(self, slot_name: str) -> None:
        self._require_slot(slot_name)
        self.beats[slot_name].operator_approved = True

    def continuity_notes(self) -> List[str]:
        notes: List[str] = []
        setup = self.beats.get("Setup")
        clip = self.beats.get("Clip")
        if setup and clip:
            if not setup.text:
                notes.append("Setup text is empty; establish context before rolling clip.")
            if not clip.text and not clip.clip:
                notes.append("Clip beat has no footage or narration; confirm source.")
            if clip.clip and clip.clip.clip_id.lower() not in setup.text.lower():
                notes.append(
                    "Setup should reference the upcoming clip (id or subject) to prime the transition."
                )
            if setup.text and clip.text and setup.text.split()[-1].lower() == clip.text.split()[0].lower():
                notes.append("Setup and Clip share connective phrasing; transition should feel seamless.")
            if clip.clip is None:
                notes.append("Clip segment has no selected footage; choose a source clip and in/out.")
            if not clip.operator_approved:
                notes.append("Operator gate pending: approve the Clip transition when ready.")
        return notes

    def runtime_summary(self) -> Tuple[float, Dict[str, float]]:
        per_beat: Dict[str, float] = {}
        cumulative = 0.0
        for slot in self.archetype.slots:
            beat = self.beats[slot.name]
            cumulative += beat.total_runtime()
            per_beat[slot.name] = beat.total_runtime()
        return cumulative, per_beat

    def over_budget_beats(self) -> List[str]:
        cumulative = 0.0
        flagged: List[str] = []
        for slot in self.archetype.slots:
            beat = self.beats[slot.name]
            cumulative += beat.total_runtime()
            if cumulative > FIFTEEN_MINUTES:
                flagged.append(slot.name)
        return flagged

    def _require_slot(self, slot_name: str) -> None:
        if slot_name not in self.beats:
            raise KeyError(f"Slot '{slot_name}' not in current archetype")
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

