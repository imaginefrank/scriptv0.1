"""Toolkit loader and selection utilities."""
from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

CATEGORY_NAMES: List[str] = [
    "Storyboarding",
    "Visual Contrast",
    "Timing",
    "Wordplay",
    "Absurdity",
    "Metaphor",
    "Character",
    "Physical Comedy",
    "Irony",
    "Satire",
    "Parody",
    "Hyperbole",
    "Deadpan",
    "Improvisation",
    "Misdirection",
    "Callbacks",
    "Breaking the Fourth Wall",
    "Meta",
    "Props",
    "Music",
    "Silence",
    "Lighting",
]


@dataclass(frozen=True)
class Tool:
    name: str
    category: str
    core_principle: str
    tags: List[str]
    examples: List[str]


@dataclass
class Toolkit:
    tools: List[Tool]
    categories: List[str]
    by_category: Dict[str, List[Tool]]
    by_tag: Dict[str, List[Tool]]

    def as_dict(self) -> Dict[str, object]:
        return {
            "categories": self.categories,
            "tools": [tool.__dict__ for tool in self.tools],
        }


_DEF_EXAMPLES = [
    "Translate the concept into a storyboard panel that exaggerates the visual gag.",
    "Lean into the most literal interpretation for comedic contrast.",
    "Layer a second reveal that undercuts the first punchline.",
    "Let the silence linger just long enough to become the joke.",
]

_DEF_CORE = [
    "Push the idea until the audience anticipates the turn, then bend it once more.",
    "Treat visuals like verbs—every frame should act on the joke.",
    "Reward rewatching with small, nested payoffs.",
]


def _build_tool(index: int) -> Tool:
    category = CATEGORY_NAMES[index % len(CATEGORY_NAMES)]
    variant = (index % 15) + 1
    core_principle = f"{category} discipline #{(index % 7) + 1}: {_DEF_CORE[index % len(_DEF_CORE)]}"
    tags = [category.lower().replace(" ", "-"), "phase1", "visual", f"variant-{(index % 5) + 1}"]
    examples = [f"{category} example {variant:03d}: {_DEF_EXAMPLES[index % len(_DEF_EXAMPLES)]}"]
    return Tool(
        name=f"{category} Tool {variant:03d}",
        category=category,
        core_principle=core_principle,
        tags=tags,
        examples=examples,
    )


def load_toolkit() -> Toolkit:
    tools: List[Tool] = [_build_tool(i) for i in range(329)]
    by_category: Dict[str, List[Tool]] = {category: [] for category in CATEGORY_NAMES}
    by_tag: Dict[str, List[Tool]] = {}

    for tool in tools:
        by_category[tool.category].append(tool)
        for tag in tool.tags:
            by_tag.setdefault(tag, []).append(tool)

    return Toolkit(tools=tools, categories=CATEGORY_NAMES, by_category=by_category, by_tag=by_tag)


def _score_tool(tool: Tool, requested_tags: Iterable[str], texture_tags: Iterable[str]) -> float:
    tag_set = set(tag.lower() for tag in requested_tags)
    texture_set = set(tag.lower() for tag in texture_tags)
    overlap = len(tag_set.intersection(tool.tags))
    texture_overlap = len(texture_set.intersection(tool.tags))
    visual_bonus = 0.5 if "visual" in tool.tags else 0
    return overlap * 2 + texture_overlap + visual_bonus


def select_tools(
    toolkit: Toolkit,
    tags: Sequence[str] | None = None,
    visual_texture: str | None = None,
    contrarian: bool = False,
    limit: int = 8,
    fallback_mix: int = 5,
) -> List[Tool]:
    requested_tags = list(tags or [])
    texture_tags = (visual_texture or "").replace(",", " ").split()

    scored = [
        (tool, _score_tool(tool, requested_tags, texture_tags))
        for tool in toolkit.tools
    ]
    scored.sort(key=lambda pair: pair[1], reverse=True)

    if contrarian:
        midpoint = len(scored) // 2
        contrarian_pool = scored[midpoint: midpoint + (limit * 2)]
        random.shuffle(contrarian_pool)
        selected = [tool for tool, _ in contrarian_pool[:limit]]
    else:
        selected = [tool for tool, score in scored if score > 0][:limit]

    used_categories = {tool.category for tool in selected}
    if len(selected) < fallback_mix:
        for category in toolkit.categories:
            if len(selected) >= fallback_mix:
                break
            if category in used_categories:
                continue
            selected.append(toolkit.by_category[category][0])
            used_categories.add(category)

    return selected


def save_selection(selection: List[Tool], path: Path) -> None:
    payload = {
        "toolkit_selection": [tool.__dict__ for tool in selection],
    }
    path.write_text(json.dumps(payload, indent=2))
