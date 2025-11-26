from __future__ import annotations

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
