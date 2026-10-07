# TensorForge 2.0 — Phase 2 report draft

**Submission status:** local prototype with supplied OpenAPI checks and offline container verification. Public hosting, reference-hardware checks, and video recording are pending. Exact organizer JSON Schemas downloaded from Drive are checked locally. Update this draft with final deployment evidence.

## 1. Problem and solution

RideEat support messages arrive through chat, email, and call transcripts in English, Sinhala, Tamil, transliterated text, and mixed scripts. The prototype predicts a primary issue category, optional secondary issue, urgency, and support team. A React dashboard adapted from ResolveX supports intake, live operations, support review, model inspection, and JSON batches; the service also exposes synchronous and asynchronous evaluation APIs.

Classification runs locally using trained TF-IDF pipelines with logistic regression and a calibrated linear SVM. No LLM, remote model, model download, or paid inference API is used at runtime. The evaluation API key authenticates requests to our own service; it is not a model-provider credential.

## 2. Architecture and design decisions

FastAPI serves the dashboard, public `/health`, and protected prediction/job endpoints. The configured `API_KEY` is compared with the supplied `X-API-Key` or bearer token using a constant-time comparison. A missing configuration denies protected access. The public demo dashboard uses a same-origin server bridge that supplies the configured key internally. No key is sent to the browser, and no key-entry prompt is shown. Direct prediction/job endpoints continue to require the exact key. Deployment must preserve the judges' exact supplied key throughout evaluation.

The service validates requests before inference, preserves batch ordering, and echoes supplied ticket IDs. Synchronous batches support 1–100 tickets. The supplied v2.1.0 contract confirms that async jobs accept 1–5,000 tickets, including the large evaluation range above 2,000. CPU-bound synchronous inference runs in a thread pool so it does not directly block the HTTP event loop.

SQLite persists job state and results. One worker processes jobs in chunks of 100; at most four jobs are active or queued. The API supports status polling, pageable results, idempotency keys, cancellation/discard, and 24-hour retention checked when results are accessed. Interrupted jobs are marked failed after a restart. Run one API process per job store and mount persistent storage for hosting. Queue limits return a retryable response rather than allowing unbounded job submissions.

The container builds the React UI in a Node stage, copies the compiled UI and pre-trained artifact, and installs dependencies at build time. Its startup command serves port 8000. The built image became reachable through a published port in 1.414 seconds. A second container with networking disabled passed health, authenticated single prediction, a 100-ticket synchronous batch, and a 2,001-ticket async job. The image contains the model and supplied OpenAPI document; it excludes `.env`. These checks used Docker Desktop, not the organizers' reference hardware.

## 3. Training and development

The supplied dataset has 4,000 training examples and 800 validation examples. Input features include channel, subject, and message text; ticket IDs and supplied language labels are excluded. Text is normalized to Unicode NFC. Word 1–2 grams capture lexical phrases while character n-grams support scripts, spelling variants, and transliteration.

All three pipelines were fitted afresh on the downloaded Drive CSVs, which are byte-for-byte identical to the previous local dataset. Checksums and archive provenance are saved. A first candidate selected on an internal training split reduced validation category accuracy to 60.88%; it was rejected. Further development comparisons are retained in `artifacts/training_experiments.json`; the selected settings are frozen in `configs/training.json`.

Primary category uses balanced logistic regression with `C=100`, word 1–2 and boundary-aware character 2–6 grams. Secondary category uses a linear SVM (`C=1`) with three-fold sigmoid calibration. Urgency uses balanced logistic regression (`C=40`). Secondary/urgency preprocessing normalizes spacing, masks synthetic references and removes explicitly quoted past correspondence. Secondary and urgency cutoffs are 0.2 and 0.3. Narrow precedence rules and the fixed routing map enforce competition semantics. Every pipeline is trained with seed 42.

Reproduce fresh fits with `python scripts/train_model.py`; reproduce primary comparisons with `python scripts/compare_training.py --target category`. Evaluation also validates all 800 predictions against the organizer's exact draft-2020-12 bundle. The earlier baseline scored 62.88% category accuracy and 92.64% urgency macro-F1; the new artifact scores 63.00% and 93.13%. Gains are small, and secondary scores are unchanged.

**Validation limitation:** development validation informed the final configuration and thresholds. These are development scores, not independent test results. The judges' unseen holdout supplies the independent evaluation. The dataset is synthetic and its Sinhala/Tamil content has not received independent native-speaker review. Retraining does not establish real-world reliability.

## 4. Evaluation and findings

Current artifact: `tf-phase2-drive-2.0.0`.

| Output | Validation accuracy | Macro-F1 |
| --- | ---: | ---: |
| Primary category | 63.00% | 65.04% |
| Secondary category | 95.50% | 69.22% |
| Urgency | 97.50% | 93.13% |

Primary categorization remains the main quality limitation. Secondary accuracy alone can conceal weak performance on uncommon secondary labels; macro-F1 therefore accompanies accuracy. Confidence below 0.5 or three or fewer message words triggers a human-review recommendation. The user example “badu nati una” predicts lost_item at 31.6% confidence and is flagged for review. Confidence is the model probability for the returned primary label, including after any rule override; it is not independently calibrated.

Automated API tests exercise authorization on every prediction/job route, input errors, output structure, issue precedence, ordering, idempotency, job status, pagination, and deletion. Desktop/mobile browser checks exercise automatic server access, classification, urgent review queues, routing decisions, batch downloads, three-model status, and a 2,001-ticket async job. A local 2,001-ticket job passed submission, polling, complete ordered results, and deletion using the configured key. Another local check passed 64 rounds of valid-key, invalid-key, and health requests with eight concurrent workers. All 33 API/contract tests pass, including the supplied YAML’s embedded schemas and consistency rules, malformed JSON, multilingual examples, batch independence, queue limits, cancellation, expiry, and interrupted restart state. A 5,000-ticket local job completed with ordered results while health and live predictions remained responsive; recorded timings are development-machine measurements. Exact organizer draft-2020-12 schema checks pass; public-host verification remains pending.

Saved-artifact primary accuracy by language: en 53.93% (280 tickets), mixed 55.00% (20 tickets), si 46.25% (160 tickets), singlish 90.50% (200 tickets), ta 61.67% (120 tickets), tanglish 65.00% (20 tickets). Small groups have substantial uncertainty. The largest confusion is order_missing_wrong as payment_refund (32 tickets). Better native-script and short-message labeled examples are priorities; this run does not establish real-world reliability.

## 5. Submission and operational plan

Before submission: repeat schema checks publicly, repeat checks on reference hardware, deploy the verified image with persistent job storage and the exact evaluation key, test through the public URL, grant judges repository access, record the 15-minute walkthrough as an unlisted YouTube video, and update the maximum-five-page report PDF. Use `docs/submission-checklist.md` to record evidence and final URLs. No public-host or independent-holdout claims should be made until verified.
