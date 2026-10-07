# TensorForge 2.0 — Support Intelligence MVP

A multilingual RideEat support-ticket classifier, API, and browser dashboard. The classifier is a locally trained TF-IDF + logistic-regression model; predictions do not call an LLM or any external service.

## Start the API and dashboard

Python 3.8+ is supported. Install dependencies, train the bundled workshop data, then start the service:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
python scripts/train_model.py
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

For local development, put `API_KEY` in `.env`. It is loaded automatically, ignored by Git, and excluded from the Docker build. Deployment environment variables take precedence over values in `.env`.

Open <http://localhost:8000> for the dashboard or <http://localhost:8000/docs> for the API explorer. `GET /health` is public. All inference and batch-job endpoints return `401` until `API_KEY` is set, and accept either `X-API-Key` or `Authorization: Bearer <your-team-key>`. The API never has a default key. The dashboard keeps a key in memory for the current tab only; it does not save it to local storage.

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

The single-ticket tab supports chat, email subject/body, and call transcripts. Use the batch workbench to load or paste a JSON request: up to 100 tickets run synchronously, while 101–5,000 use the async job API with progress polling, cancellation, and JSON download. The browser requests the API key when the tab is connected; it is intentionally not embedded in dashboard code or copied from server environment into the browser.

The dashboard verifies a key before showing it as connected. Session counters track classified, urgent, and review-recommended tickets in the current tab. Batch results include a preview of up to 100 rows with urgent and human-review filters; JSON download includes the full batch. Counters reset on reload or with Reset counters. Ctrl/Cmd+Enter submits the selected workbench.

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

The API validates the full batch before returning any predictions, preserves input order, echoes ticket IDs, and returns JSON errors for malformed, invalid, oversized, unauthorized, and unknown-route requests. Async jobs support idempotency keys, a one-running-plus-three-queued limit, persisted status/results, cancellation, restart marking, and 24-hour result retention.

## Model and evaluation

Training uses only `channel`, `subject`, and `text`, not ticket IDs or the supplied language label. The primary-category feature pipeline combines word 1–2 grams with boundary-aware character 2–6 grams and balanced class weights to handle English, Sinhala/Tamil scripts, transliteration, typos, and mixed-script text. Separate classifiers predict primary category, secondary category (including a no-secondary class), and urgency. Validation-tuned probability cutoffs improve urgent-issue and secondary-issue recall, and narrow deterministic precedence rules enforce the documented safety, late-delivery/refund, and missing-item/refund policies. Team routing is derived from the fixed API category map.

```bash
python scripts/train_model.py
```

The script trains on `datasets/train.csv`, evaluates `datasets/validation.csv`, writes `artifacts/model.joblib`, and records accuracy and macro-F1 in `artifacts/evaluation_metrics.json`. Model `tf-phase2-baseline-1.2.1` scores validation category accuracy **0.6288** (macro-F1 **0.6495**), secondary-category accuracy **0.9550** (macro-F1 **0.6922**), and urgency accuracy **0.9750** (macro-F1 **0.9264**). This validation split informed model and threshold selection, so these are development scores rather than independent test scores. Review the full metrics before deployment; the supplied multilingual dataset is synthetic, and the dataset notes caution that its Sinhala/Tamil content has not had independent native-speaker review.

Run `python scripts/evaluate_model.py` to reproduce scores for the saved model and write per-category, per-language, and confusion breakdowns to `artifacts/evaluation_breakdown.json`.

## Phase 2 submission

Track verified requirements and missing evidence in [the submission checklist](docs/submission-checklist.md). A [report draft](docs/report.md) and [15-minute video outline](docs/video-walkthrough.md) are available. Official OpenAPI/schema compliance is pending receipt of the organizer's contract files; the application's generated `/docs` is not a replacement for them. Public hosting, video recording, and report PDF export are separate deliverables.

## Tests

```bash
pytest -q
```
