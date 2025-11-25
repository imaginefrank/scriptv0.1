"""Interactive console UI for selecting archetypes, editing beats, and checking runtime."""
from __future__ import annotations

import sys

from .archetypes import available_archetypes, get_archetype
from .state import ScriptState


def prompt_archetype() -> ScriptState:
    names = available_archetypes()
    print("Available archetypes:")
    for idx, name in enumerate(names, start=1):
        print(f"  {idx}. {name}")
    while True:
        choice = input("Select archetype by number: ").strip()
        if not choice.isdigit() or int(choice) not in range(1, len(names) + 1):
            print("Invalid selection. Try again.")
            continue
        archetype = get_archetype(names[int(choice) - 1])
        print(f"Loaded archetype: {archetype.name} — {archetype.description}\n")
        return ScriptState.from_archetype(archetype)


def edit_text(state: ScriptState) -> None:
    slot_name = input("Enter beat name to edit text: ").strip()
    try:
        slot = state.beats[slot_name].slot
    except KeyError:
        print(f"Beat '{slot_name}' not found.\n")
        return
    print(f"Guidance for {slot.name}: {slot.guidance}")
    text = input("New text: ")
    state.set_text(slot_name, text)
    print(f"Updated text for {slot_name}.\n")


def select_clip(state: ScriptState) -> None:
    slot_name = input("Enter beat name to attach a clip: ").strip()
    if slot_name not in state.beats:
        print(f"Beat '{slot_name}' not found.\n")
        return
    clip_id = input("Clip id/slug: ").strip()
    try:
        in_point = float(input("In point (seconds): ").strip())
        out_point = float(input("Out point (seconds): ").strip())
    except ValueError:
        print("Invalid time entry.\n")
        return
    if out_point <= in_point:
        print("Out point must be greater than in point.\n")
        return
    state.set_clip(slot_name, clip_id, in_point, out_point)
    print(f"Clip set for {slot_name}: {clip_id} ({in_point:.2f}s - {out_point:.2f}s).\n")


def preview(state: ScriptState) -> None:
    view_mode = input("Preview mode (split/pip): ").strip().lower() or "split"
    divider = "|" if view_mode == "split" else "•"
    print("\nPreview with visual texture context:")
    for slot_name, beat in state.beats.items():
        clip_repr = (
            f"[{beat.clip.clip_id} {beat.clip.in_point:.1f}-{beat.clip.out_point:.1f}s]"
            if beat.clip
            else "[no clip selected]"
        )
        text_snippet = beat.text if beat.text else "<empty narration>"
        print(f"{slot_name:>8} {divider} {clip_repr} {divider} {text_snippet}")
    print()


def show_runtime(state: ScriptState) -> None:
    total, per_beat = state.runtime_summary()
    print("Runtime summary (spoken word-count/2.5 + clip durations):")
    for slot_name, runtime in per_beat.items():
        flag = " ⚠️" if slot_name in state.over_budget_beats() else ""
        print(f"  {slot_name:>10}: {runtime:6.1f}s{flag}")
    print(f"Total runtime: {total/60:.2f} minutes")
    if state.over_budget_beats():
        print("Over-budget beats (15-minute cap breached):", ", ".join(state.over_budget_beats()))
    print()


def continuity(state: ScriptState) -> None:
    notes = state.continuity_notes()
    if not notes:
        print("Continuity check: Setup flows into Clip and operator gate cleared.\n")
        return
    print("Continuity/transition guidance:")
    for note in notes:
        print(f" - {note}")
    print()


def approve_gate(state: ScriptState) -> None:
    slot_name = input("Enter beat to approve (usually 'Clip'): ").strip()
    if slot_name not in state.beats:
        print("Unknown beat.\n")
        return
    state.approve_transition(slot_name)
    print(f"Operator gate cleared for {slot_name}.\n")


def main() -> int:
    state = prompt_archetype()
    actions = {
        "1": ("Edit beat text", edit_text),
        "2": ("Select clip and in/out", select_clip),
        "3": ("Preview layout (split/PiP)", preview),
        "4": ("Show runtime + budget flags", show_runtime),
        "5": ("Continuity + operator gate", continuity),
        "6": ("Approve transition", approve_gate),
        "0": ("Exit", None),
    }

    while True:
        print("Actions:")
        for key, (label, _) in actions.items():
            print(f"  {key}. {label}")
        choice = input("Select action: ").strip()
        if choice == "0":
            return 0
        if choice not in actions:
            print("Invalid option.\n")
            continue
        _, handler = actions[choice]
        if handler:
            handler(state)


if __name__ == "__main__":
    sys.exit(main())
