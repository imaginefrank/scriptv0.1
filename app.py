import json
from pathlib import Path
from typing import Dict, List, Optional

from flask import Flask, jsonify, request

STATE_PATH = Path("workspace_state.json")
DEFAULT_STATE = {"beats": []}


app = Flask(__name__, static_folder="static", static_url_path="/static")


def load_state() -> Dict:
    if not STATE_PATH.exists():
        STATE_PATH.write_text(json.dumps(DEFAULT_STATE, indent=2))
    with STATE_PATH.open() as f:
        return json.load(f)


def save_state(state: Dict) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2))


def generate_variants(beat_text: str, context: Optional[str], persona: str, tool: Optional[str]) -> List[Dict]:
    base_context = context or "(no prior context)"
    prompts = [
        {
            "label": "safe_anchor",
            "prompt": f"Safe/Anchor system prompt using persona '{persona}' with context: {base_context}",
        },
        {
            "label": "tool_heavy",
            "prompt": f"Tool-forward prompt for {tool or 'unspecified tool'} with context: {base_context}",
        },
        {
            "label": "wildcard",
            "prompt": f"Wildcard exploratory prompt with persona '{persona}' and context: {base_context}",
        },
    ]

    variants = []
    for idx, prompt in enumerate(prompts, start=1):
        suffix = tool or "general tooling"
        text = (
            f"[{prompt['label'].replace('_', ' ').title()}] "
            f"Persona: {persona}. Tool: {suffix}. Context: {base_context}. Draft: {beat_text}"
        )
        variants.append(
            {
                "id": f"v{idx}",
                "type": prompt["label"],
                "system_prompt": prompt["prompt"],
                "text": text,
            }
        )
    return variants


def summarize(text: str) -> str:
    if not text:
        return ""
    clean_text = " ".join(text.split())
    return (clean_text[:120] + "…") if len(clean_text) > 120 else clean_text


def resolve_selected_text(beat: Dict) -> Optional[str]:
    if beat.get("manual_override"):
        return beat.get("final_text")

    if beat.get("final_text"):
        return beat.get("final_text")

    variant_id = beat.get("selected_variant")
    if variant_id:
        for variant in beat.get("variants", []):
            if variant["id"] == variant_id:
                return variant["text"]
    return None


def propagate_contexts(beats: List[Dict]) -> None:
    previous_text: Optional[str] = None
    previous_summary: Optional[str] = None

    for beat in beats:
        beat["context"] = previous_text or previous_summary
        summary = beat.get("summary") or summarize(beat.get("text", ""))
        beat["summary"] = summary

        selected_text = resolve_selected_text(beat)
        previous_text = selected_text
        previous_summary = summary


def chain_context(beats: List[Dict]) -> List[Dict]:
    chained: List[Dict] = []
    previous_text: Optional[str] = None
    previous_summary: Optional[str] = None

    for beat in beats:
        context = previous_text or previous_summary
        persona = beat.get("persona") or "Anchor"
        tool = beat.get("tool")

        variants = generate_variants(beat.get("text", ""), context, persona, tool)
        summary = beat.get("summary") or summarize(beat.get("text", ""))

        chained_beat = {
            "id": beat.get("id") or f"beat_{len(chained) + 1}",
            "title": beat.get("title") or f"Beat {len(chained) + 1}",
            "text": beat.get("text", ""),
            "context": context,
            "persona": persona,
            "tool_usage": tool,
            "variants": variants,
            "selected_variant": beat.get("selected_variant"),
            "final_text": beat.get("final_text"),
            "summary": summary,
            "manual_override": beat.get("manual_override", False),
            "operator_choice": beat.get("operator_choice"),
        }

        selected_text = resolve_selected_text(chained_beat)
        previous_text = selected_text
        previous_summary = summary
        chained.append(chained_beat)

    return chained


@app.route("/api/job", methods=["POST"])
def create_job():
    payload = request.get_json(force=True)
    beats = payload.get("beats", [])

    chained_beats = chain_context(beats)
    state = load_state()
    state["beats"] = chained_beats
    propagate_contexts(state["beats"])
    save_state(state)

    return jsonify({"beats": chained_beats})


@app.route("/api/state", methods=["GET"])
def get_state():
    return jsonify(load_state())


@app.route("/api/beats/<beat_id>/select", methods=["POST"])
def select_variant(beat_id: str):
    payload = request.get_json(force=True)
    variant_id = payload.get("variant_id")
    state = load_state()

    for beat in state.get("beats", []):
        if beat.get("id") == beat_id:
            beat["selected_variant"] = variant_id
            beat["manual_override"] = False
            beat["operator_choice"] = "variant"
            variant_text = None
            for variant in beat.get("variants", []):
                if variant["id"] == variant_id:
                    variant_text = variant["text"]
                    break
            beat["final_text"] = variant_text
            beat["summary"] = beat.get("summary") or summarize(variant_text or "")
            break

    propagate_contexts(state.get("beats", []))
    save_state(state)
    return jsonify(state)


@app.route("/api/beats/<beat_id>/reject_all", methods=["POST"])
def reject_all(beat_id: str):
    payload = request.get_json(force=True)
    operator_text = payload.get("operator_text", "")
    state = load_state()

    for beat in state.get("beats", []):
        if beat.get("id") == beat_id:
            beat["manual_override"] = True
            beat["operator_choice"] = "manual_override"
            beat["final_text"] = operator_text
            beat["selected_variant"] = None
            beat["summary"] = summarize(operator_text)
            break

    propagate_contexts(state.get("beats", []))
    save_state(state)
    return jsonify(state)


@app.route("/")
def index():
    return app.send_static_file("index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
