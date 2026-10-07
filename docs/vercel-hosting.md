# Vercel hosting assessment

The user selected Vercel as the existing hosting platform. The saved local credential returned HTTP 403 from Vercel's account API, so account access has not been established and no deployment has been created.

Vercel supports FastAPI, but the current application needs a persistent SQLite job store and a process-level background worker. Vercel Functions have a read-only filesystem except for `/tmp`, and instances are isolated. Moving the job database to `/tmp` would not provide a durable, shared job store. The platform also caps function request/response payloads at 4.5 MB, below this application's 25 MB async request limit. The supplied OpenAPI contract confirms a 25 MB async request limit, which exceeds the Vercel Function payload cap.

Sources: [FastAPI support](https://vercel.com/docs/frameworks/backend/fastapi), [runtime/filesystem behavior](https://vercel.com/docs/functions/runtimes), [function payload limits](https://vercel.com/docs/functions/limitations).

Two architectures can be evaluated:

1. Host the dashboard on Vercel and deploy the existing Docker API on a persistent container host. Give judges the direct backend URL; validate the dashboard/API connection after both deployments. This retains the existing trained artifact and job engine.
2. Adapt the API for Vercel with durable external job storage and a supported queue/worker system, then re-test the full contract. This requires provisioned services, credentials, job-engine changes, and confirmation that evaluation payload sizes fit the platform limits.

Next steps: authenticate the Vercel account locally (`npx vercel login`), choose the backend architecture and account, obtain the missing organizer YAML/schemas, and perform end-to-end public-host verification. Do not label a dashboard-only deployment as a complete evaluation solution.
