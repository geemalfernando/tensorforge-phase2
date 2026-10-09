"""Vercel Queues subscriber for durable batch classification."""
from pathlib import Path

from starlette.concurrency import run_in_threadpool
from vercel.queue import subscribe

from app.jobs import JobManager
from app.model import MODEL_PATH, TicketModel


@subscribe(topic="tensorforge-batch-jobs")
async def process_batch_job(message: dict[str, str]) -> None:
    job_id = message.get("job_id")
    if not job_id:
        raise ValueError("Queue message is missing job_id.")

    model = TicketModel.load(MODEL_PATH)
    manager = JobManager(model, str(Path("data") / "jobs.sqlite3"))
    try:
        await run_in_threadpool(manager._run_job, job_id)
    finally:
        manager.close()
