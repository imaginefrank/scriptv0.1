"""Comedic angle generation and queue emulation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence
import itertools
import random
import uuid

from app.toolkit import Tool


@dataclass
class ComedicAngle:
    id: str
    prompt: str
    angle: str
    tool: Dict
    risk_score: float
    status: str = "suggested"

    def as_dict(self) -> Dict:
        return {
            "id": self.id,
            "prompt": self.prompt,
            "angle": self.angle,
            "tool": self.tool,
            "risk_score": round(self.risk_score, 3),
            "status": self.status,
        }


def _build_prompt(role: str, context: str, tool: Tool) -> str:
    return (
        f"Role: {role}\n"
        f"Context: {context}\n"
        f"Tool: {tool.name}\n"
        f"Core principle: {tool.core_principle}\n"
        f"Example: {tool.examples[0]}"
    )


def _risk_score(tool: Tool, context: str) -> float:
    edgy_tags = {"satire", "parody", "hyperbole", "breaking-the-fourth-wall"}
    bonus = 0.25 if edgy_tags.intersection(tool.tags) else 0
    length_penalty = min(len(context) / 500, 0.5)
    return min(1.0, 0.4 + bonus + length_penalty)


def generate_comedic_angles(
    role: str,
    context: str,
    tools: Sequence[Tool],
    count: int = 3,
    contrarian: bool = False,
) -> List[ComedicAngle]:
    angles: List[ComedicAngle] = []
    tool_cycle = itertools.cycle(tools)

    for _ in range(count):
        tool = next(tool_cycle)
        prompt = _build_prompt(role, context, tool)
        unexpected = " contrarian left-turn" if contrarian else ""
        angle_text = (
            f"Have {role} lean on {tool.name} to solve the problem with a{unexpected} twist: "
            f"{tool.core_principle.split(':', 1)[-1].strip()}"
        )
        risk = _risk_score(tool, context)
        angles.append(
            ComedicAngle(
                id=str(uuid.uuid4()),
                prompt=prompt,
                angle=angle_text,
                tool=tool.__dict__,
                risk_score=risk,
            )
        )

    return angles

