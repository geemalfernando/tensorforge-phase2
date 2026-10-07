# Phase 2 submission evidence

Complete means verified with recorded evidence; a file or implementation alone is insufficient.

| Requirement | Current evidence | Remaining action |
| --- | --- | --- |
| End-to-end front end | Dashboard with single and batch workflows; desktop/mobile checks passed | Publish and verify a live demo URL |
| Official OpenAPI contract | Required endpoint paths implemented | Obtain `tensorforge-phase2-openapi-v2.yaml`; compare exact fields, enums, statuses, authorization, errors, and async size limits |
| Official JSON Schemas | Application checks and API tests exist | Obtain organizer `schemas/` and bundle; validate all request/response variants, including team consistency |
| API key privacy and reliability | `.env` ignored/excluded from image; configured key tested; 64 concurrent rounds of valid/invalid auth and health passed locally; public health | Configure the exact key on hosting; keep it unchanged for the evaluation window; repeat concurrent checks publicly |
| Large evaluation batch | Local 2,001-ticket submit/poll/results/order/delete passed using configured key; worker supports up to 5,000 | Record 2,001–5,000-ticket public-host evidence |
| Offline container startup | Dockerfile includes saved artifact and port-8000 startup | Start Docker daemon, build, then verify network-disabled runtime and documented single-command startup |
| Hosted batch endpoint | Local API available | Provision hosting with persistent `/app/data`; one API process per SQLite store; test public authenticated endpoint |
| GitHub repository | Local Git repository initialized; private GitHub publication in progress | Verify remote main branch and reviewer access |
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
