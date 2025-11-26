from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, validator
from starlette.requests import Request

app = FastAPI(title="Cluster Ingestion Service")
templates = Jinja2Templates(directory=Path(__file__).resolve().parent / "templates")

STATE_FILE = Path(__file__).resolve().parent.parent / "workspace_state.json"
STATE_FILE.parent.mkdir(parents=True, exist_ok=True)


class RepresentativeClip(BaseModel):
    clip_id: str = Field(..., description="Identifier for the clip")
    transcript: str = Field("", description="Transcript content")
    title: Optional[str] = Field(None, description="Optional clip title")
    url: Optional[str] = Field(None, description="Playback URL")
    thumbnail_url: Optional[str] = Field(None, description="Preview image URL")
    is_garbled: bool = Field(False, description="Flag when transcript is unusable")

    def transcript_is_missing(self) -> bool:
        return not self.transcript.strip()


class ClusterPayload(BaseModel):
    cluster_id: str = Field(..., description="Unique identifier for the cluster")
    title: str = Field(..., description="Readable title for the cluster")
    growth_percentage: float = Field(..., ge=0, description="Growth percentage over baseline")
    total_views: int = Field(..., ge=0, description="Total views across clips")
    acceleration_index: float = Field(..., ge=0, description="Momentum indicator")
    sentiment_score: float = Field(..., ge=-1, le=1, description="Average sentiment score")
    visual_tags: List[str] = Field(default_factory=list, description="Visual elements identified in the cluster")
    transcript_summary: Optional[str] = Field("", description="Summary derived from transcripts")
    engagement_rate: Optional[float] = Field(None, ge=0, description="Engagement ratio for the cluster")
    fact_card: Optional[str] = Field("", description="Source fact card content")
    representative_clips: List[RepresentativeClip] = Field(
        default_factory=list, description="Clips that represent the cluster"
    )

    @validator("visual_tags", pre=True, always=True)
    def dedupe_visual_tags(cls, value: List[str]) -> List[str]:
        if value is None:
            return []
        deduped = []
        for tag in value:
            normalized = tag.strip()
            if normalized and normalized.lower() not in {t.lower() for t in deduped}:
                deduped.append(normalized)
        return deduped

    @validator("representative_clips", pre=True, always=True)
    def ensure_clips_list(cls, value: Optional[List[RepresentativeClip]]) -> List[RepresentativeClip]:
        return value or []


GROWTH_THRESHOLD = 20.0
TOTAL_VIEWS_THRESHOLD = 50_000
ACCELERATION_THRESHOLD = 1.2
SENTIMENT_GATE = -0.1


def detect_market_movement(cluster: ClusterPayload) -> bool:
    metrics_pass = (
        cluster.growth_percentage >= GROWTH_THRESHOLD
        and cluster.total_views >= TOTAL_VIEWS_THRESHOLD
        and cluster.acceleration_index >= ACCELERATION_THRESHOLD
    )
    sentiment_pass = cluster.sentiment_score >= SENTIMENT_GATE
    return metrics_pass and sentiment_pass


def derive_visual_texture(cluster: ClusterPayload) -> dict:
    aggregated_tags = sorted({tag.strip() for tag in cluster.visual_tags if tag.strip()})
    cues = []
    if cluster.transcript_summary:
        sentences = [s.strip() for s in cluster.transcript_summary.split(".") if s.strip()]
        cues = sentences[:3]
    engagement_notes = []
    if cluster.engagement_rate is not None:
        engagement_notes.append(f"Engagement rate: {cluster.engagement_rate:.2f}")
    engagement_notes.append(f"Total views: {cluster.total_views:,}")
    engagement_notes.append(f"Acceleration index: {cluster.acceleration_index:.2f}")
    return {
        "visual_tags": aggregated_tags,
        "transcript_cues": cues,
        "engagement_notes": engagement_notes,
    }


def neutralize_fact_card(fact_card: Optional[str]) -> Optional[str]:
    if not fact_card:
        return None
    sentences = [s.strip() for s in fact_card.split(".") if s.strip()]
    neutralized = []
    biased_markers = {"should", "must", "terrible", "amazing", "shocking"}
    for sentence in sentences:
        words = sentence.split()
        filtered_words = [word for word in words if word.lower().strip(",") not in biased_markers]
        cleaned = " ".join(filtered_words)
        if cleaned:
            neutralized.append(cleaned)
    if not neutralized:
        return None
    return ". ".join(neutralized) + "."


def evaluate_validation(cluster: ClusterPayload) -> dict:
    missing_clips = len(cluster.representative_clips) == 0
    garbled_transcripts = any(
        clip.is_garbled or clip.transcript_is_missing() for clip in cluster.representative_clips
    )
    prompts = []
    if missing_clips:
        prompts.append("No representative clips provided. Add at least one clip or skip this cluster.")
    if garbled_transcripts:
        prompts.append(
            "One or more transcripts are garbled or missing. Repair the transcript or mark the clip to skip."
        )
    return {
        "missing_representative_clips": missing_clips,
        "garbled_transcripts": garbled_transcripts,
        "operator_prompts": prompts,
    }


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {"clusters": [], "history": []}
    with STATE_FILE.open("r", encoding="utf-8") as handle:
        try:
            return json.load(handle)
        except json.JSONDecodeError:
            return {"clusters": [], "history": []}


def persist_state(state: dict) -> None:
    with STATE_FILE.open("w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2, ensure_ascii=False)


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    state = load_state()
    return templates.TemplateResponse("dashboard.html", {"request": request, "state": state})


@app.get("/state")
async def get_state():
    return load_state()


class ClusterIngestionRequest(BaseModel):
    clusters: List[ClusterPayload]


@app.post("/ingest-clusters")
async def ingest_clusters(payload: ClusterIngestionRequest):
    if not payload.clusters:
        raise HTTPException(status_code=400, detail="No clusters provided")

    state = load_state()
    now = datetime.utcnow().isoformat() + "Z"
    ingested_clusters = []

    for cluster in payload.clusters:
        validation = evaluate_validation(cluster)
        market_movement = detect_market_movement(cluster)
        visual_texture = derive_visual_texture(cluster)
        neutral_fact_card = neutralize_fact_card(cluster.fact_card)

        cluster_record = {
            "cluster_id": cluster.cluster_id,
            "title": cluster.title,
            "metrics": {
                "growth_percentage": cluster.growth_percentage,
                "total_views": cluster.total_views,
                "acceleration_index": cluster.acceleration_index,
                "sentiment_score": cluster.sentiment_score,
            },
            "market_movement_flag": market_movement,
            "visual_texture": visual_texture,
            "neutral_fact_card": neutral_fact_card,
            "validation": validation,
            "representative_clips": [clip.dict() for clip in cluster.representative_clips],
            "ingested_at": now,
        }
        ingested_clusters.append(cluster_record)
        state["clusters"].append(cluster_record)
        state["history"].append(
            {
                "cluster_id": cluster.cluster_id,
                "ingested_at": now,
                "market_movement_flag": market_movement,
                "visual_texture": visual_texture,
                "neutral_fact_card": neutral_fact_card,
                "validation": validation,
            }
        )

    persist_state(state)
    return {"ingested": ingested_clusters, "count": len(ingested_clusters)}


@app.get("/clusters/{cluster_id}")
async def get_cluster(cluster_id: str):
    state = load_state()
    for cluster in state.get("clusters", []):
        if cluster.get("cluster_id") == cluster_id:
            return cluster
    raise HTTPException(status_code=404, detail="Cluster not found")
import copy
import json
import threading
import uuid
from datetime import datetime
from pathlib import Path
from queue import Queue
from typing import Any, Dict, List

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

STATE_PATH = Path("workspace_state.json")


def utc_now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)


class WorkspaceStateManager:
    def __init__(self, state_path: Path) -> None:
        self.state_path = state_path
        self.lock = threading.Lock()
        self.state: Dict[str, Any] = {}
        self._ensure_state()

    def _ensure_state(self) -> None:
        if self.state_path.exists():
            self.state = json.loads(self.state_path.read_text())
            return

        clips = [p.name for p in Path("app/static/clips").glob("*") if p.is_file()]
        self.state = {
            "version": 1,
            "updated_at": utc_now(),
            "document": {"title": "", "summary": "", "content": ""},
            "overrides": {"title": False, "summary": False, "content": True},
            "scratchpad": "",
            "variants": [],
            "polish_history": [],
            "clips": clips,
            "history": [],
        }
        self._write_state()

    def _write_state(self) -> None:
        self.state_path.write_text(json.dumps(self.state, indent=2))

    def get_state(self) -> Dict[str, Any]:
        with self.lock:
            return copy.deepcopy(self.state)

    def _bump_version(self, note: str) -> None:
        self.state.setdefault("history", []).append(
            {"version": self.state.get("version", 1), "updated_at": self.state.get("updated_at"), "note": note}
        )
        self.state["version"] = self.state.get("version", 1) + 1
        self.state["updated_at"] = utc_now()

    def update_document(self, title: str, summary: str, content: str, overrides: Dict[str, bool]) -> None:
        with self.lock:
            self.state["document"].update({"title": title, "summary": summary, "content": content})
            self.state["overrides"] = overrides
            self._bump_version("document updated")
            self._write_state()

    def update_scratchpad(self, scratchpad: str) -> None:
        with self.lock:
            self.state["scratchpad"] = scratchpad
            self._bump_version("scratchpad updated")
            self._write_state()

    def append_variant(self, variant: Dict[str, Any]) -> None:
        with self.lock:
            self.state.setdefault("variants", []).append(variant)
            self._bump_version("variant generated")
            self._write_state()

    def add_polish(self, variant_id: str, text: str) -> None:
        with self.lock:
            for variant in self.state.get("variants", []):
                if variant["id"] == variant_id:
                    variant.setdefault("polished", []).append(text)
                    break
            self.state.setdefault("polish_history", []).append(
                {"variant_id": variant_id, "text": text, "polished_at": utc_now()}
            )
            self._bump_version("polish drafted")
            self._write_state()


class JobQueue:
    def __init__(self, on_complete) -> None:
        self.queue: Queue = Queue()
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.on_complete = on_complete
        self.worker = threading.Thread(target=self._worker, daemon=True)
        self.worker.start()

    def _worker(self) -> None:
        while True:
            job = self.queue.get()
            if not job:
                continue
            job_id = job["id"]
            job["status"] = "running"
            self.jobs[job_id] = job
            payload = job.get("payload", {})

            if job["type"] == "draft":
                draft_text = self._draft_text(payload)
                job["result"] = draft_text
                job["status"] = "completed"
                self.on_complete("draft", job)
            elif job["type"] == "polish":
                polish_text = self._polish_text(payload)
                job["result"] = polish_text
                job["status"] = "completed"
                self.on_complete("polish", job)
            else:
                job["status"] = "unknown"

            self.queue.task_done()

    def _draft_text(self, payload: Dict[str, Any]) -> str:
        base = payload.get("base", "Draft")
        variant_idx = payload.get("index", 1)
        context = payload.get("context", "")
        return f"Variant {variant_idx}: {base.strip()}\nContext:\n{context.strip()}".strip()

    def _polish_text(self, payload: Dict[str, Any]) -> str:
        text = payload.get("text", "")
        notes = payload.get("notes", "Regressive polish")
        return f"Polished with notes: {notes}\n{text}"

    def enqueue(self, job_type: str, payload: Dict[str, Any]) -> str:
        job_id = str(uuid.uuid4())
        job = {
            "id": job_id,
            "type": job_type,
            "payload": payload,
            "status": "queued",
            "created_at": utc_now(),
        }
        self.jobs[job_id] = job
        self.queue.put(job)
        return job_id

    def list_jobs(self) -> List[Dict[str, Any]]:
        return sorted(self.jobs.values(), key=lambda j: j.get("created_at", ""), reverse=True)


manager = WorkspaceStateManager(STATE_PATH)
queue = JobQueue(on_complete=lambda kind, job: handle_completion(kind, job))

def handle_completion(kind: str, job: Dict[str, Any]) -> None:
    payload = job.get("payload", {})
    if kind == "draft":
        variant = {
            "id": job["id"],
            "text": job.get("result", ""),
            "created_at": job.get("created_at"),
            "prompt": payload.get("base", ""),
        }
        manager.append_variant(variant)
    elif kind == "polish":
        variant_id = payload.get("variant_id")
        manager.add_polish(variant_id=variant_id, text=job.get("result", ""))


app = FastAPI(title="Workflow Drafting")
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


def compute_token_cost(state: Dict[str, Any]) -> int:
    doc = state.get("document", {})
    total_text = " ".join([doc.get("title", ""), doc.get("summary", ""), doc.get("content", "")])
    total_text += " " + state.get("scratchpad", "")
    for variant in state.get("variants", []):
        total_text += " " + variant.get("text", "")
        for pol in variant.get("polished", []) if variant.get("polished") else []:
            total_text += " " + pol
    return approx_tokens(total_text)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    state = manager.get_state()
    token_cost = compute_token_cost(state)
    jobs = queue.list_jobs()
    clips = [p.name for p in Path("app/static/clips").glob("*") if p.is_file()]
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "state": state,
            "token_cost": token_cost,
            "jobs": jobs,
            "clips": clips,
        },
    )


@app.post("/update-document")
async def update_document(
    title: str = Form(""),
    summary: str = Form(""),
    content: str = Form(""),
    override_title: str | None = Form(None),
    override_summary: str | None = Form(None),
    override_content: str | None = Form(None),
):
    overrides = {
        "title": bool(override_title),
        "summary": bool(override_summary),
        "content": bool(override_content),
    }
    manager.update_document(title=title, summary=summary, content=content, overrides=overrides)
    return RedirectResponse("/", status_code=303)


@app.post("/update-scratchpad")
async def update_scratchpad(scratchpad: str = Form("")):
    manager.update_scratchpad(scratchpad)
    return RedirectResponse("/", status_code=303)


@app.post("/start-draft")
async def start_draft(
    base_prompt: str = Form(""),
    context: str = Form(""),
    variant_count: int = Form(1),
):
    for idx in range(1, max(1, variant_count) + 1):
        queue.enqueue(
            "draft",
            {
                "base": base_prompt,
                "context": context,
                "index": idx,
            },
        )
    return RedirectResponse("/", status_code=303)


@app.post("/start-polish")
async def start_polish(variant_id: str = Form(...), notes: str = Form("")):
    state = manager.get_state()
    variant_text = next((v["text"] for v in state.get("variants", []) if v["id"] == variant_id), "")
    queue.enqueue("polish", {"variant_id": variant_id, "text": variant_text, "notes": notes})
    return RedirectResponse("/", status_code=303)


@app.get("/state")
async def get_state():
    return manager.get_state()
