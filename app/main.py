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
