# scriptv0.1

This prototype loads a 329-tool creative toolkit, scores Phase 1 picks by tags/visual texture, and generates comedic angles that can be reviewed and overridden from a lightweight UI.

## Running the API/UI
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Start the FastAPI server:
   ```bash
   uvicorn main:app --reload
   ```
3. Open [http://localhost:8000/ui](http://localhost:8000/ui) to review picks and angles.

## Key endpoints
- `POST /select` — Select tools by tags/visual texture with optional contrarian mix; saves to `workspace_state.json`.
- `POST /angles` — Enqueue comedic angle generation (role/context/tool/core principle/example baked into prompts); results persisted with risk scores.
- `POST /angles/{id}/choose` — Mark an angle as the chosen one.
- `POST /angles/{id}/override` — Override an angle with operator-provided copy.
- `GET /workspace-state` — Inspect saved selections and angles.

## State
Generated selections and angles are stored in `workspace_state.json` so operators can review and iterate.
