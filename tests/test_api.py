import json
import re
import time

import pytest
from app import main
from app.model import MODEL_VERSION
def headers():
    return {"X-API-Key": "test-evaluation-key"}


def ticket(ticket_id="TF-TEST-1", text="The driver is late with my food"):
    return {"ticket_id": ticket_id, "channel": "chat", "subject": "", "text": text}


def test_health_is_public_and_dashboard_assets_load(client):
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert health.json()["model_version"] == MODEL_VERSION
    assert "TensorForge" in client.get("/").text
    stylesheet = re.search(r'href="([^\"]+\.css)"', client.get("/").text).group(1)
    assert client.get(stylesheet).status_code == 200


def test_vercel_origin_cors_and_dashboard_api_proxy(client, monkeypatch):
    origin = "https://tensorforge-demo.vercel.app"
    monkeypatch.setenv("DASHBOARD_ORIGINS", origin)
    preflight = client.options(
        "/dashboard/api/predict",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-tensorforge-dashboard",
        },
    )
    assert preflight.status_code == 204
    assert preflight.headers["access-control-allow-origin"] == origin
    assert preflight.headers["access-control-allow-credentials"] == "true"

    prediction = client.post(
        "/dashboard/api/predict",
        headers={
            "Origin": origin,
            "Sec-Fetch-Site": "cross-site",
            "X-TensorForge-Dashboard": "1",
        },
        json=ticket(),
    )
    assert prediction.status_code == 200
    assert prediction.headers["access-control-allow-origin"] == origin

    denied = client.options(
        "/dashboard/api/predict",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert denied.status_code == 403


def test_dashboard_reports_three_real_models_without_secrets(client):
    result = client.get("/dashboard/models")
    assert result.status_code == 200
    value = result.json()
    assert [item["id"] for item in value["models"]] == ["category", "secondary_category", "is_urgent"]
    assert all(item["loaded"] for item in value["models"])
    assert value["training_examples"] == 4000
    assert len(value["routes"]) == 11
    assert "test-evaluation-key" not in result.text


def test_auth_happens_before_content_type_and_json_validation(client):
    unauthorized = client.post("/predict", content="{", headers={"Content-Type": "text/plain"})
    assert unauthorized.status_code == 401
    assert unauthorized.json()["error"]["code"] == "unauthorized"
    assert unauthorized.headers["www-authenticate"] == "Bearer"

    malformed = client.post(
        "/predict",
        content="{",
        headers={**headers(), "Content-Type": "application/json"},
    )
    assert malformed.status_code == 400
    assert malformed.json()["error"]["code"] == "malformed_json"


def test_verify_access_checks_key_without_classifying(client, monkeypatch):
    assert client.post("/auth/verify").status_code == 401
    assert client.post("/auth/verify", headers={"X-API-Key": "wrong"}).status_code == 401
    verified = client.post("/auth/verify", headers=headers())
    assert verified.status_code == 200
    assert verified.json() == {"status": "authenticated"}
    assert verified.headers["cache-control"] == "no-store"
    assert "test-evaluation-key" not in verified.text
    assert client.post("/auth/verify", headers={"Authorization": "Bearer test-evaluation-key"}).status_code == 200
    monkeypatch.delenv("API_KEY")
    assert client.post("/auth/verify", headers=headers()).status_code == 401


def test_vercel_batch_submission_publishes_an_idempotent_queue_message(client, monkeypatch):
    import vercel.queue

    manager = main.jobs
    assert manager is not None
    monkeypatch.setattr(manager, "queue_mode", True)
    monkeypatch.setattr(
        manager,
        "submit",
        lambda tickets, key: (
            {"job_id": "queue-job", "status": "queued", "total": len(tickets)},
            True,
        ),
    )
    messages = []

    async def send(topic, payload, idempotency_key=None):
        messages.append((topic, payload, idempotency_key))

    monkeypatch.setattr(vercel.queue, "send", send)
    response = client.post(
        "/batch/jobs",
        json={"tickets": [ticket("queue-ticket")]},
        headers={**headers(), "Idempotency-Key": "queue-request"},
    )

    assert response.status_code == 202
    assert messages == [
        ("tensorforge-batch-jobs", {"job_id": "queue-job"}, "queue-job")
    ]


def test_predictions_stay_closed_when_api_key_is_unset(client, monkeypatch):
    monkeypatch.delenv("API_KEY")
    response = client.post(
        "/predict",
        json={"channel": "chat", "text": "Please check my delivery"},
        headers={"X-API-Key": "test-evaluation-key"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_bearer_auth_and_content_type_and_size_errors(client):
    authorized = client.post(
        "/predict",
        json={"channel": "chat", "text": "My meal is late"},
        headers={"Authorization": "Bearer test-evaluation-key"},
    )
    assert authorized.status_code == 200

    unsupported = client.post(
        "/predict",
        content="{}",
        headers={**headers(), "Content-Type": "text/plain"},
    )
    assert unsupported.status_code == 415
    assert unsupported.json()["error"]["code"] == "unsupported_media_type"

    oversized = client.post(
        "/predict",
        content=json.dumps({"channel": "chat", "text": "x" * (1024 * 1024)}),
        headers={**headers(), "Content-Type": "application/json"},
    )
    assert oversized.status_code == 413


def test_single_prediction_shape_and_request_id_echo(client):
    response = client.post(
        "/predict",
        json=ticket(),
        headers={**headers(), "X-Request-ID": "request-abc"},
    )
    assert response.status_code == 200
    prediction = response.json()
    assert prediction["ticket_id"] == "TF-TEST-1"
    assert prediction["category"] in {
        "payment_refund",
        "ride_trip_issue",
        "lost_item",
        "order_missing_wrong",
        "delivery_delay",
        "food_quality",
        "account_promo",
        "safety_conduct",
        "app_technical",
        "general_inquiry",
        "spam_irrelevant",
    }
    assert prediction["team"]
    assert prediction["model_version"] == MODEL_VERSION
    assert 0 <= prediction["confidence"] <= 1
    assert prediction["secondary_category"] != prediction["category"]
    assert response.headers["x-request-id"] == "request-abc"


@pytest.mark.parametrize(
    ("text", "expected_category", "expected_secondary", "urgent"),
    [
        (
            "order eka late, refund ekak denna",
            "delivery_delay",
            "payment_refund",
            False,
        ),
        (
            "என் ஆர்டர்ல ஒரு ஐட்டம் வரல, பணம் திருப்பி தாங்க",
            "order_missing_wrong",
            "payment_refund",
            False,
        ),
        (
            "the driver took a wrong turn and is not stopping the car, I am scared",
            "safety_conduct",
            None,
            True,
        ),
    ],
)
def test_documented_issue_precedence(client, text, expected_category, expected_secondary, urgent):
    response = client.post(
        "/predict",
        json={"channel": "chat", "text": text},
        headers=headers(),
    )
    assert response.status_code == 200
    prediction = response.json()
    assert prediction["category"] == expected_category
    assert prediction["secondary_category"] == expected_secondary
    assert prediction["is_urgent"] is urgent


def test_resolved_safety_history_does_not_override_the_current_issue(client):
    response = client.post(
        "/predict",
        json={
            "channel": "chat",
            "text": (
                "The driver was not stopping and I was scared, but that issue was already "
                "resolved. Now my order arrived with a missing item."
            ),
        },
        headers=headers(),
    )
    assert response.status_code == 200
    assert response.json()["category"] == "order_missing_wrong"


def test_invalid_ticket_returns_structured_validation_error(client):
    response = client.post(
        "/predict",
        json={"channel": "fax", "text": "  "},
        headers=headers(),
    )
    assert response.status_code == 422
    details = response.json()["error"]["details"]
    assert {detail["field"] for detail in details} >= {"channel", "text"}


def test_batch_is_atomic_and_preserves_ticket_order(client):
    response = client.post(
        "/predict/batch",
        json={"tickets": [ticket("first"), ticket("second", "My bag is missing from the car")]},
        headers=headers(),
    )
    assert response.status_code == 200
    result = response.json()
    assert [item["ticket_id"] for item in result["predictions"]] == ["first", "second"]
    assert result["meta"]["count"] == 2
    assert result["meta"]["model_version"] == MODEL_VERSION


def test_short_ambiguous_singlish_ticket_is_flagged_for_review(client):
    response = client.post("/predict", json=ticket(text="badu nati una"), headers=headers())
    assert response.status_code == 200
    assert response.json()["needs_human_review"] is True
    assert response.json()["is_urgent"] is False

    invalid = client.post(
        "/predict/batch",
        json={"tickets": [ticket("same"), ticket("same", "   ")]},
        headers=headers(),
    )
    assert invalid.status_code == 422
    assert [item["index"] for item in invalid.json()["error"]["details"]] == [1, 1]


def test_async_job_idempotency_status_paging_and_delete(client):
    payload = {"tickets": [ticket("async-a"), ticket("async-b", "My account login code does not work")]}
    submitted = client.post(
        "/batch/jobs",
        json=payload,
        headers={**headers(), "Idempotency-Key": "retryable-request"},
    )
    assert submitted.status_code == 202
    job_id = submitted.json()["job_id"]
    assert submitted.headers["location"] == "/batch/jobs/{}".format(job_id)

    retried = client.post(
        "/batch/jobs",
        json=payload,
        headers={**headers(), "Idempotency-Key": "retryable-request"},
    )
    assert retried.status_code == 202
    assert retried.json()["job_id"] == job_id

    deadline = time.monotonic() + 10
    status = client.get("/batch/jobs/{}".format(job_id), headers=headers())
    while status.json()["status"] in {"queued", "running"} and time.monotonic() < deadline:
        time.sleep(0.02)
        status = client.get("/batch/jobs/{}".format(job_id), headers=headers())
    assert status.json()["status"] == "succeeded"
    assert status.json()["processed"] == 2

    page = client.get(
        "/batch/jobs/{}/results?offset=0&limit=1".format(job_id),
        headers=headers(),
    )
    assert page.status_code == 200
    assert page.json()["next_offset"] == 1
    assert page.json()["predictions"][0]["ticket_id"] == "async-a"
    assert client.delete("/batch/jobs/{}".format(job_id), headers=headers()).status_code == 204
    assert client.get("/batch/jobs/{}".format(job_id), headers=headers()).status_code == 404


def test_unknown_routes_return_json(client):
    response = client.get("/not-a-route")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert "error" in response.json()


@pytest.mark.parametrize("method,path", [
    ("post", "/predict"),
    ("post", "/predict/batch"),
    ("post", "/batch/jobs"),
    ("get", "/batch/jobs/unknown"),
    ("get", "/batch/jobs/unknown/results"),
    ("delete", "/batch/jobs/unknown"),
])
def test_all_prediction_and_job_routes_require_the_exact_key(client, method, path):
    for supplied in ({}, {"X-API-Key": "wrong-key"}):
        response = getattr(client, method)(path, headers=supplied)
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"


def test_key_survives_whitespace_and_either_equivalent_header(client, monkeypatch):
    monkeypatch.setenv("API_KEY", "test-evaluation-key\n")
    accepted = [
        {"X-API-Key": "test-evaluation-key"},
        {"X-API-Key": " test-evaluation-key "},
        {"Authorization": "Bearer test-evaluation-key"},
        {"Authorization": "bearer   test-evaluation-key"},
        {"X-API-Key": "", "Authorization": "Bearer test-evaluation-key"},
        {"X-API-Key": "stale-key", "Authorization": "Bearer test-evaluation-key"},
        {"X-API-Key": "test-evaluation-key", "Authorization": "Bearer stale-key"},
    ]
    for supplied in accepted:
        assert client.post("/predict", json=ticket(), headers=supplied).status_code == 200, supplied
    rejected = [
        {"X-API-Key": ""},
        {"Authorization": "Bearer"},
        {"Authorization": "Basic test-evaluation-key"},
        {"X-API-Key": "test-evaluation-key-extra"},
    ]
    for supplied in rejected:
        response = client.post("/predict", json=ticket(), headers=supplied)
        assert response.status_code == 401, supplied
        assert response.json()["error"]["code"] == "unauthorized"


def test_key_is_accepted_under_concurrent_load(client):
    from concurrent.futures import ThreadPoolExecutor

    def call(index):
        auth = headers() if index % 2 else {"Authorization": "Bearer test-evaluation-key"}
        return client.post("/predict", json=ticket("LOAD-{}".format(index)), headers=auth).status_code

    with ThreadPoolExecutor(max_workers=16) as pool:
        statuses = list(pool.map(call, range(200)))
    assert statuses == [200] * 200


def test_dashboard_uses_server_key_without_returning_it(client):
    status = client.get("/dashboard/status")
    assert status.json() == {"configured": True}
    assert status.headers["cache-control"] == "no-store"
    browser_headers = {"X-TensorForge-Dashboard": "1", "Origin": "http://testserver"}
    response = client.post("/dashboard/api/predict", json=ticket(), headers=browser_headers)
    assert response.status_code == 200
    assert response.json()["ticket_id"] == "TF-TEST-1"
    assert response.headers["cache-control"] == "no-store"
    batch = client.post("/dashboard/api/predict/batch", json={"tickets": [ticket()]}, headers=browser_headers)
    assert batch.status_code == 200
    assert batch.json()["meta"]["count"] == 1
    html = client.get("/")
    script = re.search(r'src="([^\"]+\.js)"', html.text).group(1)
    javascript = client.get(script)
    assert javascript.status_code == 200
    for resource in (status, response, batch, html, javascript):
        assert "test-evaluation-key" not in resource.text
    assert 'id="api-key"' not in client.get("/").text
    assert client.post("/predict", json=ticket()).status_code == 401


def test_dashboard_access_rejects_cross_site_and_missing_configuration(client, monkeypatch):
    path = "/dashboard/api/predict"
    assert client.post(path, json=ticket()).status_code == 403
    assert client.post(path, json=ticket(), headers={"X-TensorForge-Dashboard": "1", "Origin": "https://other.example"}).status_code == 403
    assert client.post(path, json=ticket(), headers={"X-TensorForge-Dashboard": "1", "Sec-Fetch-Site": "cross-site"}).status_code == 403
    assert client.get("/dashboard/api/health", headers={"X-TensorForge-Dashboard": "1"}).status_code == 404
    monkeypatch.delenv("API_KEY")
    assert client.get("/dashboard/status").json() == {"configured": False}
    response = client.post(path, json=ticket(), headers={"X-TensorForge-Dashboard": "1"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "access_not_configured"
