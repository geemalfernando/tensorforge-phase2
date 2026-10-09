# TensorForge 2.0 — Phase 2 report draft

**Submission status:** local prototype with supplied OpenAPI checks and offline container verification. Public hosting, reference-hardware checks, and video recording are pending. Exact organizer JSON Schemas downloaded from Drive are checked locally. Update this draft with final deployment evidence.

## 1. Problem and solution

RideEat support messages arrive through chat, email, and call transcripts in English, Sinhala, Tamil, transliterated text, and mixed scripts. The prototype predicts a primary issue category, optional secondary issue, urgency, and support team. A React dashboard adapted from ResolveX supports intake, live operations, support review, model inspection, and JSON batches; the service also exposes synchronous and asynchronous evaluation APIs.

Classification runs locally using trained TF-IDF pipelines with logistic regression and a calibrated linear SVM. No LLM, remote model, model download, or paid inference API is used at runtime. The evaluation API key authenticates requests to our own service; it is not a model-provider credential.

## 2. Architecture and design decisions

FastAPI serves the dashboard, public `/health`, and protected prediction/job endpoints. The configured `API_KEY` is compared with the supplied `X-API-Key` or bearer token using a constant-time comparison. A missing configuration denies protected access. The regular dashboard uses a same-origin server bridge that supplies the configured key internally, so it never sends that server key to the browser. The separate Judge demo asks the evaluator to enter their own key, verifies it through `/auth/verify`, and keeps it in page memory only for direct endpoint calls; it is not saved to browser storage and is cleared on sign-out. Deployment must preserve the judges' exact supplied key throughout evaluation.

The service validates requests before inference, preserves batch ordering, and echoes supplied ticket IDs. Synchronous batches support 1–100 tickets. The supplied v2.1.0 contract confirms that async jobs accept 1–5,000 tickets, including the large evaluation range above 2,000. CPU-bound synchronous inference runs in a thread pool so it does not directly block the HTTP event loop.

SQLite persists job state and results. One worker processes jobs in chunks of 100; at most four jobs are active or queued. The API supports status polling, pageable results, idempotency keys, cancellation/discard, and 24-hour retention checked when results are accessed. Interrupted jobs are marked failed after a restart. Run one API process per job store and mount persistent storage for hosting. Queue limits return a retryable response rather than allowing unbounded job submissions.

The container builds the React UI in a Node stage, copies the compiled UI and pre-trained artifact, and installs dependencies at build time. Its startup command serves port 8000. The built image became reachable through a published port in 1.414 seconds. A second container with networking disabled passed health, authenticated single prediction, a 100-ticket synchronous batch, and a 2,001-ticket async job. The image contains the model and supplied OpenAPI document; it excludes `.env`. These checks used Docker Desktop, not the organizers' reference hardware.

## 3. Training and development

The supplied dataset has 4,000 training examples and 800 validation examples. Input features include channel, optional language, subject, and message text; ticket IDs are excluded. Language is passed as an optional hint at inference. Text is normalized to Unicode NFC. Word 1–2 grams capture lexical phrases while character n-grams support scripts, spelling variants, and transliteration.

All three pipelines were fitted afresh on the downloaded Drive CSVs, which are byte-for-byte identical to the previous local dataset. Checksums and archive provenance are saved. A first candidate selected on an internal training split reduced validation category accuracy to 60.88%; it was rejected. Further development comparisons are retained in `artifacts/training_experiments.json`; the selected settings are frozen in `configs/training.json`.

Primary category uses balanced logistic regression with `C=100`, word 1–2 and boundary-aware character 2–6 grams. Secondary category uses a linear SVM (`C=1`) with three-fold sigmoid calibration. Urgency uses balanced logistic regression (`C=40`). Secondary/urgency preprocessing normalizes spacing, masks synthetic references and removes explicitly quoted past correspondence. Secondary and urgency cutoffs are 0.2 and 0.3. Narrow precedence rules and the fixed routing map enforce competition semantics. Every pipeline is trained with seed 42.

Reproduce the held-out evaluation and final refit with `python scripts/train_model.py` or set `RETRAIN = True` in `notebooks/tensorforge_model_report.ipynb` and run it. The deterministic split takes 75% of `train.csv` for fitting and 25% for testing, stratified by primary category. The existing `validation.csv` is not used for the test score; it is included with `train.csv` only when refitting the final deployment artifact. The notebook shows scores, per-class metrics, language breakdowns, and visual diagnostics.

**Evaluation limitation:** the held-out results below measure only this synthetic workshop dataset. The judges' unseen holdout remains the independent evaluation. Sinhala/Tamil content has not received independent native-speaker review; strong dataset scores do not establish real-world reliability.

## 4. Evaluation and findings

Current artifact: `tf-phase2-drive-2.1.0`.

| Output | 25% test accuracy | Macro-F1 |
| --- | ---: | ---: |
| Primary category | 99.00% | 98.92% |
| Secondary category | 99.80% | 98.84% |
| Urgency | 99.90% | 99.71% |

In the held-out fold, the model correctly classified all 150 `delivery_delay` tickets, with no `delivery_delay` → `lost_item` errors; 48 of 50 `lost_item` tickets were correct, with one predicted as `delivery_delay`. The notebook also checks clear delayed-order and left-property examples. Confidence below 0.5 or three or fewer message words triggers a human-review recommendation. Ambiguous short messages still need clarification. Confidence is the model probability for the returned primary label, including after any rule override; it is not independently calibrated.

Automated API tests exercise authorization on prediction/job routes, input errors, output structure, issue precedence, ordering, idempotency, job status, pagination, and deletion. Contract tests validate responses against the supplied schemas. The local full test run after retraining passed 46 tests; one Vercel Queue SDK integration test was deselected because that dependency is unavailable in the current Python 3.8 environment. Public-host verification remains pending.

Held-out primary-category accuracy by language: English 98.31% (356 tickets), mixed 100% (23), Sinhala 100% (198), Singlish 99.61% (255), Tamil 100% (146), and Tanglish 86.36% (22). The small groups, particularly mixed and Tanglish, have substantial uncertainty. These synthetic-data results do not establish real-world reliability.

## 5. Submission and operational plan

Before submission: repeat schema checks publicly, repeat checks on reference hardware, deploy the verified image with persistent job storage and the exact evaluation key, test through the public URL, grant judges repository access, record the 15-minute walkthrough as an unlisted YouTube video, and update the maximum-five-page report PDF. Use `docs/submission-checklist.md` to record evidence and final URLs. No public-host or independent-holdout claims should be made until verified.
