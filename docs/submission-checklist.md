# Phase 2 submission evidence

Complete means verified with recorded evidence; a file or implementation alone is insufficient.

| Requirement | Current evidence | Remaining action |
| --- | --- | --- |
| End-to-end front end | Dashboard with single and batch workflows; desktop/mobile checks passed | Publish and verify a live demo URL |
| Official OpenAPI contract | Required endpoint paths implemented | Obtain `tensorforge-phase2-openapi-v2.yaml`; compare exact fields, enums, statuses, authorization, errors, and async size limits |
| Official JSON Schemas | Application checks and API tests exist | Obtain organizer `schemas/` and bundle; validate all request/response variants, including team consistency |
| API key privacy and reliability | `.env` ignored/excluded from image; configured key tested; 64 concurrent rounds of valid/invalid auth and health passed locally; public health | Configure the exact key on hosting; keep it unchanged for the evaluation window; repeat concurrent checks publicly |
| Large evaluation batch | Local 2,001-ticket submit/poll/results/order/delete passed using configured key; worker supports up to 5,000 | Record 2,001–5,000-ticket public-host evidence |
| Offline container startup | Dockerfile includes saved artifact and port-8000 startup; CI workflow passes local actionlint | Local Docker daemon is unavailable; GitHub CI returned startup_failure without jobs on two attempts. Resolve execution access and record an offline container pass |
| Hosted batch endpoint | Local API available | Provision hosting with persistent `/app/data`; one API process per SQLite store; test public authenticated endpoint |
| GitHub repository | Private repository published at the URL below; main branch verified | Give judges repository access |
| Video | `docs/video-walkthrough.md` contains a timed recording plan | Record 15 minutes; upload YouTube unlisted; verify viewing access |
| Report | `docs/report.md` and five-page `docs/report.pdf` draft with reproduced metrics | Update with completed evidence/URLs before final submission; re-export and recheck page limit |
| Training/evaluation evidence | Training script, saved artifact, aggregate metrics; detailed evaluation script | Save any future model experiments with configs and results; keep judges' holdout unseen |

## Final links

- Live demo: pending
- Evaluation API base URL: pending
- GitHub repository: https://github.com/geemalfernando/tensorforge-phase2 (private; judges require access)
- Image name/tag: pending
- Unlisted video: pending
- Report PDF: `docs/report.pdf` (draft)

## Container verification commands

```bash
docker build -t tensorforge-mvp .
# Normal required startup, with API_KEY already exported in the shell:
docker run --rm -p 8000:8000 -e API_KEY tensorforge-mvp
# Separate offline-runtime proof:
docker run --rm --network none -e API_KEY --name tensorforge-offline tensorforge-mvp
```

For the offline check, exercise `/health`, authenticated `/predict`, and job submission/poll/results from inside the container using `docker exec` and Python's standard-library HTTP client. An external browser cannot reach a container started with `--network none`. Never print the evaluation key or include it in screenshots, reports, repository files, or video.

After deployment, run `python scripts/verify_endpoint.py --base-url https://YOUR-TRUSTED-HOST` with the exact evaluation key configured in `.env` or `API_KEY`. This tests public health, authentication, single/synchronous prediction, and a 2,001-ticket async job, verifies result ordering, and discards the test job. Use `--job-size 5000` for the maximum-size check. This smoke test does not substitute for official schema validation.

The selected hosting platform is Vercel. See `docs/vercel-hosting.md`: saved account authentication returned HTTP 403, and the current persistent SQLite/background worker architecture needs an appropriate backend or adaptation before a complete deployment.
