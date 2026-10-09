# Vercel + Supabase deployment

This project can deploy the dashboard and FastAPI application in one Vercel project. Supabase PostgreSQL stores async batch jobs, dashboard sessions, and support tickets; Vercel Queues delivers batch jobs to a separate Python subscriber. SQLite and the local worker remain available for development.

## 1. Link the project

1. Push the repository to a Git provider and import it into Vercel.
2. Choose the **Services** preset and keep the project root set to the repository root (not `frontend/`). The checked-in `vercel.json` defines a Vite `frontend` service and a FastAPI `app` service, then sends API paths to FastAPI and the remaining paths to the frontend. Python runtime dependencies are declared in both `pyproject.toml` (for Vercel Queues/Python builds) and `requirements.txt` (for local/Docker use); keep the pinned lists synchronized. The Python service uses Vercel's automatic dependency installation and bundle optimization; do not override its install command.
3. Vercel builds each service independently. The Vite service writes its deployment assets to `dist`; local builds continue to generate `app/static/ui`.
4. Enable Vercel Queues for the project. The subscriber in `app/batch_worker.py` is registered in `pyproject.toml`; the SDK uses Vercel's deployment identity for queue calls.

## 2. Configure Supabase PostgreSQL

Create a Supabase project, then copy its **Transaction pooler** connection string from **Connect**. Use this URL as `DATABASE_URL` in Vercel. Transaction mode is intended for serverless connections; the app disables prepared statements for compatibility. Do not use a frontend variable such as `VITE_DATABASE_URL`.

The app creates its three tables (`jobs`, `dashboard_sessions`, and `support_tickets`) when the API starts. Keep the default Supabase database role in the URL so it can create these tables. The PostgreSQL connection is opened only for each short operation and then closed, leaving connection pooling to Supabase.

## 3. Set Vercel environment variables

Add the following under **Project Settings → Environment Variables** for Production (and Preview if needed):

| Variable | Value |
| --- | --- |
| `API_KEY` | The current organizer-issued evaluation key |
| `SUPPORT_PASSWORD` | A unique support-console password |
| `DATABASE_URL` | Supabase **Transaction pooler** connection URI |

Optionally set `AUTO_APPROVE_CONFIDENCE`. Do not prefix any server secret with `VITE_`; those variables are embedded in the public browser bundle. Do not paste secrets into chat, source control, or the Vercel build command.

Redeploy after adding or changing environment variables.

## 4. Verify

After deployment, check `/health`, open the dashboard, and submit a small async job through `/docs` or the batch workbench. Confirm it reaches `succeeded`, then check paged results. The API and queue consumer use the same Supabase database, so state persists across function instances and cold starts.

## Limits and availability

- Supabase Free projects can pause after a period of inactivity; resume the project before judging if it has paused.
- Vercel Queues and the Python runtime are platform features whose availability, function-duration limits, and usage quotas depend on the current Vercel plan. Confirm the project can enable Queues and run the configured 300-second functions before relying on it for evaluation.
- Vercel Hobby is intended for personal, non-commercial use. Review the current plan terms and usage limits.
- Free tiers are not an uptime/SLA guarantee. Keep the local Docker deployment available as a fallback.
