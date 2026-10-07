import json
import logging
import os
import sqlite3
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

from app.model import MODEL_VERSION, TicketModel

logger = logging.getLogger(__name__)
MAX_ACTIVE_JOBS = 4
RETENTION = timedelta(hours=24)
CHUNK_SIZE = 100


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def timestamp(value: datetime) -> str:
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


class JobManager:
    def __init__(self, model: TicketModel, db_path: Optional[str] = None) -> None:
        self.model = model
        self.db_path = Path(db_path or os.environ.get("JOB_DB_PATH", "data/jobs.sqlite3"))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="batch-job")
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(str(self.db_path), timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    idempotency_key TEXT UNIQUE,
                    status TEXT NOT NULL,
                    total INTEGER NOT NULL,
                    processed INTEGER NOT NULL,
                    tickets_json TEXT NOT NULL,
                    results_json TEXT,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    expires_at TEXT,
                    error_json TEXT,
                    model_version TEXT
                )
                """
            )
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(jobs)")}
            if "model_version" not in columns:
                connection.execute("ALTER TABLE jobs ADD COLUMN model_version TEXT")
            # Preserve the generating model when serving retained results after retraining.
            for row in connection.execute("SELECT job_id, results_json FROM jobs WHERE model_version IS NULL"):
                predictions = json.loads(row["results_json"]) if row["results_json"] else []
                version = predictions[0].get("model_version", MODEL_VERSION) if predictions else MODEL_VERSION
                connection.execute("UPDATE jobs SET model_version=? WHERE job_id=?", (version, row["job_id"]))
            now = utc_now()
            expiry = timestamp(now + RETENTION)
            connection.execute(
                """
                UPDATE jobs
                SET status='failed', finished_at=?, expires_at=?,
                    error_json=?
                WHERE status IN ('queued', 'running')
                """,
                (
                    timestamp(now),
                    expiry,
                    json.dumps(
                        {
                            "code": "interrupted",
                            "message": "Service restarted while the job was running.",
                        }
                    ),
                ),
            )

    def close(self) -> None:
        self.executor.shutdown(wait=False)

    def submit(
        self, tickets: List[Dict[str, Any]], idempotency_key: Optional[str]
    ) -> Tuple[Dict[str, Any], bool]:
        with self.lock:
            with self._connect() as connection:
                if idempotency_key:
                    existing = connection.execute(
                        "SELECT * FROM jobs WHERE idempotency_key=?",
                        (idempotency_key,),
                    ).fetchone()
                    if existing is not None:
                        return self._status_from_row(existing), True

                active = connection.execute(
                    "SELECT COUNT(*) FROM jobs WHERE status IN ('queued', 'running')"
                ).fetchone()[0]
                if active >= MAX_ACTIVE_JOBS:
                    return {}, False

                job_id = str(uuid.uuid4())
                created_at = timestamp(utc_now())
                connection.execute(
                    """
                    INSERT INTO jobs (
                        job_id, idempotency_key, status, total, processed,
                        tickets_json, created_at, model_version
                    ) VALUES (?, ?, 'queued', ?, 0, ?, ?, ?)
                    """,
                    (
                        job_id,
                        idempotency_key,
                        len(tickets),
                        json.dumps(tickets, ensure_ascii=False),
                        created_at,
                        MODEL_VERSION,
                    ),
                )
                row = connection.execute(
                    "SELECT * FROM jobs WHERE job_id=?", (job_id,)
                ).fetchone()
                status = self._status_from_row(row)

            self.executor.submit(self._run_job, job_id)
            return status, True

    def _status_from_row(self, row: sqlite3.Row) -> Dict[str, Any]:
        error = json.loads(row["error_json"]) if row["error_json"] else None
        return {
            "job_id": row["job_id"],
            "status": row["status"],
            "total": row["total"],
            "processed": row["processed"],
            "created_at": row["created_at"],
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "expires_at": row["expires_at"],
            "model_version": row["model_version"] or MODEL_VERSION,
            "error": error,
        }

    def _get_row(self, job_id: str) -> Optional[sqlite3.Row]:
        with self._connect() as connection:
            return connection.execute(
                "SELECT * FROM jobs WHERE job_id=?", (job_id,)
            ).fetchone()

    def get_status(self, job_id: str) -> Tuple[Optional[Dict[str, Any]], bool]:
        row = self._get_row(job_id)
        if row is None:
            return None, False
        if row["expires_at"] and row["expires_at"] <= timestamp(utc_now()):
            self._discard_expired_data(job_id)
            return None, True
        return self._status_from_row(row), False

    def get_results(
        self, job_id: str, offset: int, limit: Optional[int]
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        row = self._get_row(job_id)
        if row is None:
            return None, "not_found"
        if row["expires_at"] and row["expires_at"] <= timestamp(utc_now()):
            self._discard_expired_data(job_id)
            return None, "expired"
        if row["status"] != "succeeded" or row["results_json"] is None:
            return None, "not_ready"
        predictions = json.loads(row["results_json"])
        page_limit = len(predictions) if limit is None else limit
        end = min(offset + page_limit, len(predictions))
        next_offset = end if end < len(predictions) else None
        return (
            {
                "job_id": row["job_id"],
                "status": "succeeded",
                "total": len(predictions),
                "offset": offset,
                "limit": page_limit,
                "next_offset": next_offset,
                "model_version": row["model_version"] or MODEL_VERSION,
                "predictions": predictions[offset:end],
            },
            "ok",
        )

    def _discard_expired_data(self, job_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE jobs
                SET tickets_json='[]', results_json=NULL, idempotency_key=NULL
                WHERE job_id=?
                """,
                (job_id,),
            )

    def delete(self, job_id: str) -> bool:
        with self.lock, self._connect() as connection:
            row = connection.execute("SELECT status FROM jobs WHERE job_id=?", (job_id,)).fetchone()
            if row is None:
                return False
            if row["status"] in {"queued", "running"}:
                finished = utc_now()
                connection.execute(
                    """
                    UPDATE jobs SET status='cancelled', finished_at=?, expires_at=?,
                        tickets_json='[]', results_json=NULL
                    WHERE job_id=?
                    """,
                    (timestamp(finished), timestamp(finished + RETENTION), job_id),
                )
                return True
            cursor = connection.execute("DELETE FROM jobs WHERE job_id=?", (job_id,))
            return cursor.rowcount > 0

    def _run_job(self, job_id: str) -> None:
        with self.lock, self._connect() as connection:
            row = connection.execute(
                "SELECT status, tickets_json FROM jobs WHERE job_id=?", (job_id,)
            ).fetchone()
            if row is None or row["status"] != "queued":
                return
            connection.execute(
                "UPDATE jobs SET status='running', started_at=? WHERE job_id=?",
                (timestamp(utc_now()), job_id),
            )
            tickets = json.loads(row["tickets_json"])

        predictions: List[Dict[str, Any]] = []
        try:
            for start in range(0, len(tickets), CHUNK_SIZE):
                with self.lock:
                    current = self._get_row(job_id)
                    if current is None or current["status"] != "running":
                        return
                predictions.extend(
                    self.model.predict_many(tickets[start : start + CHUNK_SIZE])
                )
                with self.lock, self._connect() as connection:
                    current = connection.execute(
                        "SELECT status FROM jobs WHERE job_id=?", (job_id,)
                    ).fetchone()
                    if current is None or current["status"] != "running":
                        return
                    connection.execute(
                        "UPDATE jobs SET processed=? WHERE job_id=?",
                        (len(predictions), job_id),
                    )

            finished = utc_now()
            with self.lock, self._connect() as connection:
                current = connection.execute(
                    "SELECT status FROM jobs WHERE job_id=?", (job_id,)
                ).fetchone()
                if current is None or current["status"] != "running":
                    return
                connection.execute(
                    """
                    UPDATE jobs
                    SET status='succeeded', processed=?, results_json=?,
                        finished_at=?, expires_at=?, tickets_json='[]'
                    WHERE job_id=?
                    """,
                    (
                        len(predictions),
                        json.dumps(predictions, ensure_ascii=False),
                        timestamp(finished),
                        timestamp(finished + RETENTION),
                        job_id,
                    ),
                )
        except Exception:
            logger.exception("Batch job %s failed during classification", job_id)
            finished = utc_now()
            with self.lock, self._connect() as connection:
                connection.execute(
                    """
                    UPDATE jobs
                    SET status='failed', finished_at=?, expires_at=?, error_json=?,
                        tickets_json='[]', results_json=NULL
                    WHERE job_id=? AND status='running'
                    """,
                    (
                        timestamp(finished),
                        timestamp(finished + RETENTION),
                        json.dumps(
                            {
                                "code": "classification_failed",
                                "message": "The batch classification job failed.",
                            }
                        ),
                        job_id,
                    ),
                )
