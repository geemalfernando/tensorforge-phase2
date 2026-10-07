# ResolveX × TensorForge — Support Intelligence

A multilingual RideEat support-ticket classifier, API, and React dashboard adapted from your ResolveX system. Ticket intake, live operations, support review, batch inference, and a model lab share the same trained backend. The classifier is a locally trained TF-IDF + logistic-regression model; predictions do not call an LLM or any external service.

## Start the API and dashboard

Python 3.8+ is supported. Install dependencies, train the bundled workshop data, then start the service:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
python scripts/train_model.py
npm ci --prefix frontend
npm run build --prefix frontend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

For local development, put `API_KEY` in `.env`. It is loaded automatically, ignored by Git, and excluded from the Docker build. Deployment environment variables take precedence over values in `.env`.

Open <http://localhost:8000> for the dashboard or <http://localhost:8000/docs> for the API explorer. `GET /health` is public. All inference and batch-job endpoints return `401` until `API_KEY` is set, and accept either `X-API-Key` or `Authorization: Bearer <your-team-key>`. The API never has a default key. The dashboard automatically uses the configured server key through its same-origin demo bridge. The key is never returned to the browser or saved in browser storage.

The organizer’s supplied OpenAPI v2.1.0 contract is saved in `tensorforge-phase2-openapi-v2.yaml`. `/openapi.json` and `/docs` use the matching `app/openapi.json`, which is bundled in the container. The API specification version is independent of the trained model version.

## Docker

The image contains the trained model artifact, so no training data, network access, or model download is needed at runtime.

```bash
docker build -t tensorforge-mvp .
docker run -p 8000:8000 -e API_KEY='<your-team-key>' tensorforge-mvp
```

`/health` works without a key. Provide the evaluation key to Docker through `-e API_KEY=...`; do not copy it into the image or commit it to the repository. The SQLite job database is stored at `/app/data/jobs.sqlite3`; mount a persistent volume at `/app/data` if batch jobs need to survive container replacement. Run one API process per SQLite job store.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Public readiness and loaded model version |
| `POST` | `/auth/verify` | Verify API access without submitting a ticket |
| `POST` | `/predict` | Classify one ticket |
| `POST` | `/predict/batch` | Classify 1–100 tickets synchronously |
| `POST` | `/batch/jobs` | Queue 1–5,000 tickets for async classification |
| `GET` | `/batch/jobs/{job_id}` | Poll job status and progress |
| `GET` | `/batch/jobs/{job_id}/results` | Fetch stable, pageable results after success |
| `DELETE` | `/batch/jobs/{job_id}` | Cancel or discard a job |

### Dashboard workflows

The ResolveX-style workspace has five views: Ticket intake, Live operations, Support queue, Batch workbench, and Model lab. Intake supports chat, email subject/body, and call transcripts. Predictions enter the current browser session queue. Urgent and low-confidence tickets enter support review; an agent can confirm the team or record a routing override with a reason. Review decisions are session demo state, reset on refresh, and leave canonical model predictions unchanged.

The batch workbench loads JSON, processes 1–100 tickets synchronously or 101–5,000 asynchronously, polls progress, supports cancellation, and downloads all results. Its preview shows up to 100 rows. The model lab reads actual loaded classifier classes and saved validation metrics from the server.

The browser calls `/dashboard/api/...`; the server supplies its configured key internally. There is no API-key prompt or browser secret. Direct judging routes require the exact evaluation key. See [ResolveX adaptation details](docs/resolvex-adaptation.md) for source provenance and the three-model replacement.

For frontend development, run `npm run dev --prefix frontend` alongside the API, and open the URL printed by Vite. Rebuild with `npm run build --prefix frontend` to update the UI served by FastAPI. Node is needed only to build the UI; Docker handles this in its build stage.

Request examples:

```bash
curl http://localhost:8000/predict \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: your-team-key' \
  -d '{"ticket_id":"TF-1048","channel":"chat","text":"mage order eka late, refund ekak denna"}'

curl http://localhost:8000/predict/batch \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: your-team-key' \
  -d '{"tickets":[{"ticket_id":"TF-1048","channel":"chat","text":"Order is late"}]}'
```

The API validates the full batch before returning any predictions, preserves input order, echoes ticket IDs, and returns JSON errors for malformed, invalid, oversized, unauthorized, and unknown-route requests. Async jobs accept 1–5,000 tickets and support idempotency keys, a one-running-plus-three-queued limit, persisted status/results, cancellation, restart marking, and 24-hour result retention (above the contract’s six-hour minimum). Deleting a queued/running job retains its `cancelled` status; deleting a finished job discards it.

## Model and evaluation

Training uses only `channel`, `subject`, and `text`, not ticket IDs or the supplied language label. The primary-category feature pipeline combines word 1–2 grams with boundary-aware character 2–6 grams and balanced class weights to handle English, Sinhala/Tamil scripts, transliteration, typos, and mixed-script text. Separate classifiers predict primary category, secondary category (including a no-secondary class), and urgency. Validation-tuned probability cutoffs improve urgent-issue and secondary-issue recall, and narrow deterministic precedence rules enforce the documented safety, late-delivery/refund, and missing-item/refund policies. Team routing is derived from the fixed API category map.

```bash
python scripts/train_model.py
```

The script trains on `datasets/train.csv`, evaluates `datasets/validation.csv`, writes `artifacts/model.joblib`, and records accuracy and macro-F1 in `artifacts/evaluation_metrics.json`. Model `tf-phase2-baseline-1.2.1` scores validation category accuracy **0.6288** (macro-F1 **0.6495**), secondary-category accuracy **0.9550** (macro-F1 **0.6922**), and urgency accuracy **0.9750** (macro-F1 **0.9264**). This validation split informed model and threshold selection, so these are development scores rather than independent test scores. Review the full metrics before deployment; the supplied multilingual dataset is synthetic, and the dataset notes caution that its Sinhala/Tamil content has not had independent native-speaker review.

Run `python scripts/evaluate_model.py` to reproduce scores for the saved model and write per-category, per-language, and confusion breakdowns to `artifacts/evaluation_breakdown.json`.

Predictions with primary confidence below 0.5 set `needs_human_review` to `true`. Confidence is the model probability for the returned primary category; it has not been independently calibrated.

## Phase 2 submission

Track verified requirements and missing evidence in [the submission checklist](docs/submission-checklist.md). A [report draft](docs/report.md) and [15-minute video outline](docs/video-walkthrough.md) are available. Contract tests validate responses against the supplied OpenAPI’s embedded schemas and check its prose consistency rules. OpenAPI 3.0 `nullable` is translated for the JSON Schema validator. The separate organizer `schemas/` bundle has not been provided, so validation against that bundle remains pending. Public hosting and video recording are separate deliverables.

## Tests

```bash
pytest -q
```

Browser workflow verification (against a running local service):

```bash
npx --prefix frontend playwright install chromium
BASE_URL=http://127.0.0.1:8000 node scripts/verify_dashboard.cjs
```

This checks intake, review, urgent routing, single/synchronous/2,001-ticket async inference, ordered download, three-model status, and mobile layout.

The 31 tests include validation against the supplied OpenAPI's embedded schemas and consistency rules. Reproduce container checks with:

```bash
docker build -t tensorforge-mvp .
python scripts/verify_container.py --image tensorforge-mvp
```

The verification script loads `.env`, checks published-port readiness within 120 seconds, then runs inference, a 100-ticket batch, and a 2,001-ticket job in a separate container with `--network none`. It removes its temporary containers and never prints the API key. Saved local evidence is in `artifacts/container_verification.json` and `artifacts/contract_job_verification.json`; these are development-machine results, not reference-hardware or hosted measurements.
