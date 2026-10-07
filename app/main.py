import hmac
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.concurrency import run_in_threadpool
from dotenv import load_dotenv

from app.jobs import JobManager
from app.model import MODEL_PATH, MODEL_VERSION, TicketModel

load_dotenv()

logger = logging.getLogger("tensorforge")
CHANNELS = {"email", "chat", "call_transcript"}
BODY_LIMITS = {
    "/predict": 1 * 1024 * 1024,
    "/predict/batch": 5 * 1024 * 1024,
    "/batch/jobs": 25 * 1024 * 1024,
}
model: Optional[TicketModel] = None
jobs: Optional[JobManager] = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    global model, jobs
    model = TicketModel.load(MODEL_PATH)
    jobs = JobManager(model)
    yield
    if jobs is not None:
        jobs.close()
    jobs = None
    model = None


app = FastAPI(
    title="TensorForge 2.0 | RideEat Support Intelligence",
    version=MODEL_VERSION,
    description="Multilingual support-ticket classification trained on the supplied RideEat dataset.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
)
app.mount(
    "/static",
    StaticFiles(directory=str(Path(__file__).parent / "static")),
    name="static",
)


@app.middleware("http")
async def echo_request_id(request: Request, call_next):
    response = await call_next(request)
    request_id = request.headers.get("X-Request-ID")
    if (
        request_id
        and len(request_id) <= 128
        and all(32 <= ord(character) <= 126 for character in request_id)
    ):
        response.headers["X-Request-ID"] = request_id
    return response


def error_response(
    status_code: int,
    code: str,
    message: str,
    details: Optional[List[Dict[str, Any]]] = None,
    headers: Optional[Dict[str, str]] = None,
) -> JSONResponse:
    error: Dict[str, Any] = {"code": code, "message": message}
    if details:
        error["details"] = details
    return JSONResponse(
        status_code=status_code,
        content={"error": error},
        headers=headers,
    )


@app.exception_handler(StarletteHTTPException)
async def json_http_error(_: Request, exc: StarletteHTTPException):
    status = exc.status_code
    if status == 404:
        code, message = "not_found", "The requested resource was not found."
    elif status == 405:
        code, message = "method_not_allowed", "The HTTP method is not supported for this route."
    else:
        code, message = "http_error", str(exc.detail)
    return error_response(status, code, message, headers=exc.headers)


def _authorize(request: Request) -> Optional[JSONResponse]:
    expected = os.environ.get("API_KEY")
    if not expected:
        return error_response(
            401,
            "unauthorized",
            "Missing API key. Send X-API-Key or Authorization Bearer.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    supplied = request.headers.get("X-API-Key")
    authorization = request.headers.get("Authorization", "")
    if supplied is None and authorization.lower().startswith("bearer "):
        supplied = authorization[7:].strip()
    keys_match = supplied is not None and hmac.compare_digest(
        supplied.encode("utf-8"), expected.encode("utf-8")
    )
    if not keys_match:
        return error_response(
            401,
            "unauthorized",
            "Missing API key. Send X-API-Key or Authorization Bearer."
            if supplied is None
            else "Invalid API key.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return None


async def _read_json(request: Request, limit: int) -> Tuple[Optional[Any], Optional[JSONResponse]]:
    content_type = request.headers.get("content-type", "")
    if content_type.split(";", 1)[0].strip().lower() != "application/json":
        return None, error_response(
            415,
            "unsupported_media_type",
            "Content-Type must be application/json.",
        )

    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > limit:
                return None, error_response(
                    413, "payload_too_large", "Request body exceeds the maximum allowed size."
                )
        except ValueError:
            return None, error_response(
                400, "malformed_json", "Content-Length header must be an integer."
            )

    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > limit:
            return None, error_response(
                413, "payload_too_large", "Request body exceeds the maximum allowed size."
            )
    try:
        return json.loads(body), None
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, error_response(400, "malformed_json", "Request body is not valid JSON.")


def _validate_ticket(ticket: Any, require_id: bool = False) -> List[Dict[str, str]]:
    details: List[Dict[str, str]] = []
    if not isinstance(ticket, dict):
        return [{"field": "ticket", "issue": "must be an object"}]

    if require_id and "ticket_id" not in ticket:
        details.append({"field": "ticket_id", "issue": "is required"})
    if "ticket_id" in ticket:
        value = ticket["ticket_id"]
        if not isinstance(value, str):
            details.append({"field": "ticket_id", "issue": "must be a string"})
        elif len(value) > 64:
            details.append({"field": "ticket_id", "issue": "must be at most 64 characters"})

    channel = ticket.get("channel")
    if not isinstance(channel, str):
        details.append({"field": "channel", "issue": "is required and must be a string"})
    elif channel not in CHANNELS:
        details.append(
            {"field": "channel", "issue": "must be one of email, chat, call_transcript"}
        )

    subject = ticket.get("subject", "")
    if not isinstance(subject, str):
        details.append({"field": "subject", "issue": "must be a string"})
    elif len(subject) > 500:
        details.append({"field": "subject", "issue": "must be at most 500 characters"})

    text = ticket.get("text")
    if not isinstance(text, str):
        details.append({"field": "text", "issue": "is required and must be a string"})
    elif not text.strip():
        details.append(
            {"field": "text", "issue": "must contain at least one non-whitespace character"}
        )
    elif len(text) > 10000:
        details.append({"field": "text", "issue": "must be at most 10000 characters"})
    return details


def _validate_many(payload: Any, maximum: int) -> Tuple[Optional[List[Dict[str, Any]]], List[Dict[str, Any]]]:
    if not isinstance(payload, dict) or "tickets" not in payload:
        return None, [{"field": "tickets", "issue": "is required"}]
    tickets = payload["tickets"]
    if not isinstance(tickets, list):
        return None, [{"field": "tickets", "issue": "must be an array"}]
    if not 1 <= len(tickets) <= maximum:
        return None, [
            {"field": "tickets", "issue": "must contain between 1 and {} items".format(maximum)}
        ]

    details: List[Dict[str, Any]] = []
    seen_ids = set()
    for index, ticket in enumerate(tickets):
        item_details = _validate_ticket(ticket, require_id=True)
        if isinstance(ticket, dict) and isinstance(ticket.get("ticket_id"), str):
            ticket_id = ticket["ticket_id"]
            if ticket_id in seen_ids:
                item_details.append(
                    {"field": "ticket_id", "issue": "duplicate of an earlier item"}
                )
            seen_ids.add(ticket_id)
        details.extend(dict(item, index=index) for item in item_details)
    return tickets, details


def _prediction_model() -> Optional[TicketModel]:
    return model


def _job_manager() -> Optional[JobManager]:
    return jobs


@app.get("/", include_in_schema=False)
async def dashboard():
    return FileResponse(str(Path(__file__).parent / "static" / "index.html"))


@app.post("/auth/verify")
async def verify_access(request: Request):
    unauthorized = _authorize(request)
    if unauthorized is not None:
        return unauthorized
    return JSONResponse(content={"status": "authenticated"}, headers={"Cache-Control": "no-store"})


@app.get("/health", tags=["Core"])
async def health():
    current_model = _prediction_model()
    if current_model is None:
        return JSONResponse(
            status_code=503,
            content={"status": "loading", "model_version": None, "model_loaded": False},
        )
    return {"status": "ok", "model_version": MODEL_VERSION, "model_loaded": True}


@app.post("/predict", tags=["Core"])
async def predict(request: Request):
    denied = _authorize(request)
    if denied is not None:
        return denied
    payload, failure = await _read_json(request, BODY_LIMITS["/predict"])
    if failure is not None:
        return failure
    details = _validate_ticket(payload)
    if details:
        return error_response(422, "validation_error", "Request failed validation.", details)
    current_model = _prediction_model()
    if current_model is None:
        return error_response(503, "model_not_ready", "The model is not loaded yet.")
    predictions = await run_in_threadpool(current_model.predict_many, [payload])
    return predictions[0]


@app.post("/predict/batch", tags=["Evaluation"])
async def predict_batch(request: Request):
    denied = _authorize(request)
    if denied is not None:
        return denied
    started = time.perf_counter()
    payload, failure = await _read_json(request, BODY_LIMITS["/predict/batch"])
    if failure is not None:
        return failure
    tickets, details = _validate_many(payload, 100)
    if details:
        return error_response(422, "validation_error", "Request failed validation.", details)
    current_model = _prediction_model()
    if current_model is None:
        return error_response(503, "model_not_ready", "The model is not loaded yet.")
    predictions = await run_in_threadpool(current_model.predict_many, tickets or [])
    return {
        "predictions": predictions,
        "meta": {
            "count": len(predictions),
            "model_version": MODEL_VERSION,
            "processing_time_ms": int((time.perf_counter() - started) * 1000),
        },
    }


@app.post("/batch/jobs", tags=["Evaluation"], status_code=202)
async def submit_batch_job(request: Request):
    denied = _authorize(request)
    if denied is not None:
        return denied
    payload, failure = await _read_json(request, BODY_LIMITS["/batch/jobs"])
    if failure is not None:
        return failure
    tickets, details = _validate_many(payload, 5000)
    if details:
        return error_response(422, "validation_error", "Request failed validation.", details)
    manager = _job_manager()
    if manager is None:
        return error_response(503, "service_not_ready", "The job service is not ready.")
    idempotency_key = request.headers.get("Idempotency-Key") or None
    if idempotency_key is not None and len(idempotency_key) > 128:
        return error_response(
            422,
            "validation_error",
            "Request failed validation.",
            [{"field": "Idempotency-Key", "issue": "must be at most 128 characters"}],
        )
    status, accepted = manager.submit(tickets or [], idempotency_key)
    if not accepted:
        return error_response(
            429,
            "too_many_jobs",
            "Job queue is full. Retry later.",
            headers={"Retry-After": "3"},
        )
    return JSONResponse(
        status_code=202,
        content=status,
        headers={"Location": "/batch/jobs/{}".format(status["job_id"]), "Retry-After": "2"},
    )


@app.get("/batch/jobs/{job_id}", tags=["Evaluation"])
async def get_batch_job(job_id: str, request: Request):
    denied = _authorize(request)
    if denied is not None:
        return denied
    manager = _job_manager()
    status, expired = manager.get_status(job_id) if manager else (None, False)
    if expired:
        return error_response(410, "job_expired", "Job results have expired.")
    if status is None:
        return error_response(404, "job_not_found", "No job with this id.")
    headers = {"Retry-After": "2"} if status["status"] in {"queued", "running"} else None
    return JSONResponse(content=status, headers=headers)


@app.delete("/batch/jobs/{job_id}", tags=["Evaluation"], status_code=204)
async def delete_batch_job(job_id: str, request: Request):
    denied = _authorize(request)
    if denied is not None:
        return denied
    manager = _job_manager()
    if manager is None or not manager.delete(job_id):
        return error_response(404, "job_not_found", "No job with this id.")
    return Response(status_code=204)


@app.get("/batch/jobs/{job_id}/results", tags=["Evaluation"])
async def get_batch_job_results(job_id: str, request: Request):
    denied = _authorize(request)
    if denied is not None:
        return denied
    try:
        offset = int(request.query_params.get("offset", "0"))
        limit_value = request.query_params.get("limit")
        limit = int(limit_value) if limit_value is not None else None
    except ValueError:
        return error_response(
            422,
            "validation_error",
            "Request failed validation.",
            [{"field": "offset/limit", "issue": "must be an integer"}],
        )
    if offset < 0 or (limit is not None and not 1 <= limit <= 5000):
        return error_response(
            422,
            "validation_error",
            "Request failed validation.",
            [{"field": "offset/limit", "issue": "is outside the allowed range"}],
        )
    manager = _job_manager()
    result, state = (
        manager.get_results(job_id, offset, limit)
        if manager
        else (None, "not_found")
    )
    if state == "not_found":
        return error_response(404, "job_not_found", "No job with this id.")
    if state == "expired":
        return error_response(410, "job_expired", "Job results have expired.")
    if state == "not_ready":
        return error_response(
            409,
            "job_not_ready",
            "Job results are available once the job has succeeded.",
        )
    return result


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)
