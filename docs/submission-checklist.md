# Phase 2 submission evidence

Complete means verified with recorded evidence; a file or implementation alone is insufficient.

| Requirement | Current evidence | Remaining action |
| --- | --- | --- |
| End-to-end front end | Live dashboard at `https://tensorforge-phase2.vercel.app/`; the floating Demo button opens the judge checklist and key-gated API console | Refresh the walkthrough to show the judge console |
| Official OpenAPI contract | Supplied v2.1.0 saved as `tensorforge-phase2-openapi-v2.yaml`; 39 focused API/contract tests pass; matching contract served by `/docs` | Repeat full schema and async-job checks against the deployed service |
| Official JSON Schemas | Exact organizer standalone schemas and draft-2020-12 bundle downloaded from Drive; contract responses and all 800 validation predictions checked against the bundle | Repeat on the public host |
| API key privacy and reliability | `.env` ignored/excluded from image; exact key tested against hosted synchronous batch; judge console stores the entered key in page memory only; public health | Keep the exact key unchanged and active through the evaluation window; repeat concurrent checks publicly |
| Large evaluation batch | Local 5,000-ticket ordered results passed while health/live predictions stayed responsive; container also passed 2,001 tickets offline | Record 2,001–5,000-ticket public-host evidence and reference-hardware checks |
| Offline container startup | Built `tensorforge-phase2:drive-2.0`; published-port health ready in 1.414 s; 100-ticket sync and 2,001-ticket async passed with network disabled; evidence in `artifacts/drive_container_verification.json` | Repeat on reference hardware; GitHub CI previously returned startup_failure before jobs started |
| Hosted batch endpoint | Production `/predict/batch` passed public-health, missing-key `401`, and valid-key `200` checks; full route list is shown in the judge console | Repeat deployed schema validation and 2,001–5,000-ticket async-job evidence |
| GitHub repository | Private repository published at the URL below; main branch verified | Grant judges repository access |
| Video | A 15:26 local walkthrough recording exists; it predates the new judge console and is git-ignored | Refresh to show the Demo checklist/console, upload to YouTube unlisted, and verify access |
| Report | `docs/report.md` and five-page `docs/report.pdf` draft with reproduced metrics | Update with final public-host evidence/URLs and keep within five pages |
| Training/evaluation evidence | Drive-trained v2.1.0 artifact, dataset checksums, frozen configuration, saved model comparisons, 75/25 scores, and diagnostics | Keep judges' holdout unseen; describe synthetic-data and language-coverage limitations |

## Final links

- Live demo: https://tensorforge-phase2.vercel.app/
- Evaluation API base URL: https://tensorforge-phase2.vercel.app
- GitHub repository: https://github.com/geemalfernando/tensorforge-phase2 (private; judges require access)
- Local verified image: `tensorforge-phase2:drive-2.0` (registry publishing pending)
- Unlisted video: pending refresh and upload
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
