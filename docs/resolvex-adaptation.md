# ResolveX adaptation for TensorForge

Source: https://github.com/geemalfernando/ResolveX, main at commit
`94d97edb632fc0ba5bd257dc2922443c8d733ec1`. A shallow clone was inspected locally.
The original repository is unchanged. This adaptation lives in tensorforge-phase2.

The React/Vite/Tailwind frontend reuses ResolveX's CSS, theme configuration,
header/navigation approach, support queue layout, and case decision/evidence layout.
`frontend/src/components/TicketPanel.jsx` adapts the CasePanel workflow to ticket review.

| ResolveX workflow | TensorForge replacement |
| --- | --- |
| Customer complaint | Multilingual ticket intake: chat, email, call transcript |
| Live operations | Session routing list with urgent/review/resolved filters |
| Support cases | Review queue, confirm team or record an override with a reason |
| Claim risk | Primary confidence and urgency signals for human review |
| Delivery model status | Three loaded ticket classifiers and development scores |
| Delivery-specific checks | Primary category, secondary category, urgency inference |

The ETA, fault, and claim-history models from ResolveX do not match this competition's
text classification task. They are replaced by the existing trained category,
secondary-category, and urgency TF-IDF pipelines (logistic regression and calibrated linear SVM). All three run
for every prediction. Training remains reproducible with scripts/train_model.py;
no delivery model, Gemini call, payment integration or Supabase dependency is needed.

The server loads API_KEY from the root .env; browser requests use the existing
same-origin dashboard bridge and never receive the secret. Judges use the exact
configured key directly on the specified routes. GET /health stays public.

The organizer contract, API schemas, fixed routing map, asynchronous SQLite jobs,
retention, idempotency and error formats stay in the Python service. Review decisions
are demo session state and do not change model predictions or judge results. Ticket
messages and decisions in the browser reset on refresh. Large API jobs persist in SQLite.

Build frontend: npm ci --prefix frontend && npm run build --prefix frontend.
FastAPI serves the compiled UI at /. Docker builds the frontend in a Node stage,
then bundles it with the model in the Python image; runtime needs no internet.

The organizer schemas are now bundled and checked. Public hosting and recording/uploading the
walkthrough remain outstanding submission deliverables. See submission-checklist.md.
