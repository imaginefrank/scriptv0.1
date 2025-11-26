"""Minimal FastAPI app to expose toolkit and comedic angle orchestration."""
from __future__ import annotations

from pathlib import Path
from typing import List

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from app.toolkit import load_toolkit, select_tools
from app.angles import generate_comedic_angles
from app import state as workspace_state

app = FastAPI(title="Toolkit Loader")


@app.get("/toolkit")
def get_toolkit():
    toolkit = load_toolkit()
    return toolkit.as_dict()


@app.post("/select")
def post_select(payload: dict):
    toolkit = load_toolkit()
    selected = select_tools(
        toolkit,
        tags=payload.get("tags", []),
        visual_texture=payload.get("visual_texture"),
        contrarian=payload.get("contrarian", False),
    )
    state = workspace_state.record_selection([tool.__dict__ for tool in selected])
    return {"selected": [tool.__dict__ for tool in selected], "state": state}


@app.post("/angles")
def post_angles(payload: dict, background_tasks: BackgroundTasks):
    toolkit = load_toolkit()
    selection = select_tools(
        toolkit,
        tags=payload.get("tags", []),
        visual_texture=payload.get("visual_texture"),
        contrarian=payload.get("contrarian", False),
    )

    role = payload.get("role") or "Creator"
    context = payload.get("context") or ""
    contrarian = payload.get("contrarian", False)

    def _generate_and_store():
        angles = generate_comedic_angles(role, context, selection, contrarian=contrarian)
        workspace_state.record_angles([angle.as_dict() for angle in angles])

    background_tasks.add_task(_generate_and_store)
    return {"message": "Angle generation enqueued", "count": len(selection)}


@app.get("/workspace-state")
def get_workspace_state():
    return workspace_state.load_state()


@app.post("/angles/{angle_id}/choose")
def choose_angle(angle_id: str):
    state = workspace_state.choose_angle(angle_id)
    return state


@app.post("/angles/{angle_id}/override")
def override_angle(angle_id: str, payload: dict):
    new_text = payload.get("angle")
    if not new_text:
        raise HTTPException(status_code=400, detail="New angle text required")
    state = workspace_state.override_angle(angle_id, new_text)
    return state


@app.get("/")
def ui_root():
    index_path = Path("static/index.html")
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="UI not found")
    return FileResponse(index_path)


@app.get("/ui")
def ui_page():
    return ui_root()


