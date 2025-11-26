# scriptv0.1

FastAPI service for ingesting cluster data, deriving Phase 1 insights, and surfacing UI history.

## Running locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Endpoints

- `POST /ingest-clusters`: Ingest clusters using the schema defined in `app/main.py`, derive market movement flags, visual texture, and neutral fact cards, validate representative clips, and persist the results to `workspace_state.json`.
- `GET /state`: Returns the current persisted state and history.
- `GET /`: Renders a simple dashboard of the derived data.
- `GET /clusters/{cluster_id}`: Fetch an individual cluster entry.
# Workflow Drafting Sandbox

A FastAPI + HTMX-style server-rendered workspace for experimenting with Phase 1–5 creative flows: persisted JSON state, manual override editing, asynchronous AI job queue stubs, persistent scratchpad, local static media, and multi-variant drafting with regressive polish.

## Setup
1. Ensure Python 3.10+ is available.
2. (Recommended) Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install fastapi uvicorn jinja2 python-multipart
   ```

## Running the app
Start the development server from the repository root:
```bash
uvicorn app.main:app --reload --port 8000
```
Visit `http://localhost:8000` to access the UI.

## Features
- **JSON workspace persistence with versioning:** All edits are stored in `workspace_state.json`, with version increments and a human-readable history log.
- **Static media for clips:** Files under `app/static/clips/` are served via `/static/clips/...` and linked in the UI. Replace the placeholder `readme.txt` with your own clips.
- **Async job queue for AI generations:** Drafting and regressive polish jobs are queued in-memory and processed by a background worker; results are appended to variants and polish history on completion.
- **Manual overrides on editable fields:** Title, summary, and content fields respect override toggles to demonstrate human-in-the-loop control.
- **Persistent scratchpad sidebar:** Notes are stored alongside the workspace state and remain visible across page loads.
- **Token-cost footer:** An approximate token counter aggregates document, scratchpad, and variant text to highlight budget awareness.
- **Multi-variant drafting & regressive polish:** Queue multiple draft variants at once, then queue polish passes per variant to iteratively refine outputs.

## Data files
- `workspace_state.json`: persisted workspace state with history and version metadata.
- `app/static/clips/`: location for locally hosted media references.

## Notes
- The background worker is an in-memory stub intended to model asynchronous AI calls; restart the server to reset the job queue.
- The `/state` endpoint returns the current persisted JSON payload for inspection or integration.
