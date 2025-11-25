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
