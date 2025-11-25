"""Archetype definitions for scripted beats and timings."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class BeatSlot:
    """A slot in an archetype with a suggested duration and description."""

    name: str
    suggested_duration_sec: int
    guidance: str


@dataclass(frozen=True)
class Archetype:
    """An archetype with a name and ordered beat slots."""

    name: str
    slots: List[BeatSlot]
    description: str


def _heroic_insight() -> Archetype:
    return Archetype(
        name="Heroic Insight",
        description="Opens with context, uses a compelling clip, and lands a takeaway.",
        slots=[
            BeatSlot(
                name="Setup",
                suggested_duration_sec=120,
                guidance="Set location, stakes, and who is on camera.",
            ),
            BeatSlot(
                name="Clip",
                suggested_duration_sec=420,
                guidance="The main footage or interview driving the story.",
            ),
            BeatSlot(
                name="Reflection",
                suggested_duration_sec=180,
                guidance="Narrated reflection or call to action to close the segment.",
            ),
        ],
    )


def _conflict_resolution() -> Archetype:
    return Archetype(
        name="Conflict & Resolution",
        description="Contrasts a problem clip with a visual solution, with a bridge between.",
        slots=[
            BeatSlot(
                name="Setup",
                suggested_duration_sec=90,
                guidance="State the problem, tease the footage that proves it.",
            ),
            BeatSlot(
                name="Clip",
                suggested_duration_sec=360,
                guidance="Primary clip that visualizes the conflict.",
            ),
            BeatSlot(
                name="Bridge",
                suggested_duration_sec=90,
                guidance="Voiceover that links into the resolution visuals.",
            ),
            BeatSlot(
                name="Resolution",
                suggested_duration_sec=240,
                guidance="Show the fix; reinforce key lines with visuals and ambient audio.",
            ),
        ],
    )


def _micro_doc() -> Archetype:
    return Archetype(
        name="Micro Doc",
        description="Lean docu-style piece with intro, primary beat, and outro tag.",
        slots=[
            BeatSlot(
                name="Setup",
                suggested_duration_sec=75,
                guidance="Identity, stakes, and why the viewer should care.",
            ),
            BeatSlot(
                name="Clip",
                suggested_duration_sec=330,
                guidance="Core vérité clip; include b-roll notes for texture.",
            ),
            BeatSlot(
                name="Tag",
                suggested_duration_sec=90,
                guidance="Sponsor tag or CTA; includes graphic/text overlay cues.",
            ),
        ],
    )


ALL_ARCHETYPES: Dict[str, Archetype] = {
    archetype.name: archetype
    for archetype in (_heroic_insight(), _conflict_resolution(), _micro_doc())
}


def available_archetypes() -> List[str]:
    """Return the list of archetype names."""

    return list(ALL_ARCHETYPES)


def get_archetype(name: str) -> Archetype:
    """Fetch an archetype by name, raising if it is not defined."""

    if name not in ALL_ARCHETYPES:
        raise KeyError(f"Archetype '{name}' is not defined")
    return ALL_ARCHETYPES[name]
