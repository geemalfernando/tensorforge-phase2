# Phase 2 submission evidence

Complete means verified with recorded evidence; a file or implementation alone is insufficient.

| Requirement | Current evidence | Remaining action |
| --- | --- | --- |
| End-to-end front end | ResolveX-derived React dashboard: intake, operations, support review, batch workbench, model lab; automatic server-side key access | Publish and verify a live demo URL |
| Official OpenAPI contract | Supplied v2.1.0 saved as `tensorforge-phase2-openapi-v2.yaml`; 33 API/contract tests pass; matching contract served by `/docs` | Repeat contract checks against the deployed service |
| Official JSON Schemas | Exact organizer standalone schemas and draft-2020-12 bundle downloaded from Drive; contract responses and all 800 validation predictions checked against the bundle | Repeat on the public host |
| API key privacy and reliability | `.env` ignored/excluded from image; configured key tested; 64 concurrent rounds of valid/invalid auth and health passed locally; public health | Configure the exact key on hosting; keep it unchanged for the evaluation window; repeat concurrent checks publicly |
| Large evaluation batch | Local 5,000-ticket ordered results passed while health/live predictions stayed responsive; container also passed 2,001 tickets offline | Record 2,001–5,000-ticket public-host evidence and reference-hardware checks |
| Offline container startup | Built `tensorforge-phase2:drive-2.0`; published-port health ready in 1.414 s; 100-ticket sync and 2,001-ticket async passed with network disabled; evidence in `artifacts/drive_container_verification.json` | Repeat on reference hardware; GitHub CI previously returned startup_failure before jobs started |
| Hosted batch endpoint | Local API available | Provision hosting with persistent `/app/data`; one API process per SQLite store; test public authenticated endpoint |
| GitHub repository | Private repository published at the URL below; main branch verified | Give judges repository access |
| Video | `docs/video-walkthrough.md` contains a timed recording plan | Record 15 minutes; upload YouTube unlisted; verify viewing access |
| Report | `docs/report.md` and five-page `docs/report.pdf` draft with reproduced metrics | Update with completed evidence/URLs before final submission; re-export and recheck page limit |
| Training/evaluation evidence | Fresh Drive-trained artifact v2.0.0, dataset checksums, frozen configuration, saved model comparisons and detailed development scores | Save any future model experiments with configs and results; keep judges' holdout unseen |

## Final links

- Live demo: pending
- Evaluation API base URL: pending
- GitHub repository: https://github.com/geemalfernando/tensorforge-phase2 (private; judges require access)
- Local verified image: `tensorforge-phase2:drive-2.0` (registry publishing pending)
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

The selected hosting platform is Vercel. See `docs/vercel-hosting.md`: saved account authentication returned HTTP 403, and the current persistent SQLite/background worker architecture needs an appropriate backend or adaptation before a complete deployment. The supplied contract confirms the async request limit is 25 MB.
