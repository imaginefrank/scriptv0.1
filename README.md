# Script Ops console

A collection of lightweight prototypes for managing scripted operations and creative drafting. The repository currently includes:

1. **Script Ops UI (static/Express)** — A single-page UI for phase-gated decisions, transcript management, clip previews, token estimates, and a simulated async queue (`index.html`, `app.js`, `style.css`, served by `server.js`).
2. **Workflow Drafting Sandbox (FastAPI)** — HTMX-style server-rendered workspace with persistent JSON state, async job queue stubs, manual overrides, scratchpad, and token-cost footer (`app/main.py`, templates under `app/templates`).
3. **Beat chaining API (Flask)** — Minimal API for chaining beat contexts and handling operator approvals or overrides (`app.py`).

## Running the Script Ops UI

```bash
npm install
npm start
```

The Express server hosts the static UI at http://localhost:3000 and persists beat versions in `workspace_state.json`.

## Running the Workflow Drafting Sandbox

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000 to access the workspace. Cluster ingestion views are available at http://localhost:8000/clusters.

## Running the Beat chaining API

```bash
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000 to work with the beat chaining endpoints or serve the static `index.html`.

## State files

- `workspace_state.json` — Shared workspace state for the Script Ops UI, FastAPI sandbox, and Flask beat chaining prototype.
- `cluster_state.json` — Cluster ingestion state for the FastAPI dashboard.

## Features at a glance

- Phase-gated navigation with explicit approvals.
- Transcript workspace with tags, summary, and sentiment sidebar.
- Token usage tracking and simulated async queue.
- Workflow drafting with persistent history, manual overrides, scratchpad, and regressive polish queue.
- Cluster ingestion that normalizes tags, checks validation gates, and renders a dashboard view.
