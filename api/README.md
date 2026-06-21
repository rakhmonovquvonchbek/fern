# Fern API (Cloud Run)

FastAPI backend for shared Claude extraction with Firestore rate limiting.

## Local dev (rate limit test)

```bash
cd api
pip install -r requirements.txt
export FERN_LOCAL_RATE_LIMIT=memory
export ANTHROPIC_API_KEY=sk-ant-...
uvicorn main:app --port 8080
```

## Deploy

```bash
chmod +x deploy.sh
./deploy.sh
```

Requires `gcloud` CLI and secret `fern-anthropic-key` in Secret Manager.

After deploy, set `api_url` in `~/.fern/config.json`.

## Rate limits

Two layers on `POST /extract`:

1. **Per install_id:** 3 free lifetime audits, max 1 per day
2. **Per IP:** max 10 requests per day (abuse prevention)

Returns HTTP 429 with upgrade instructions when exceeded.

## Endpoints

- `POST /extract` — batch email extraction
- `POST /ping` — optional anonymous telemetry
- `GET /health` — health check
