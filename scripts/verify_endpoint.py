"""Smoke-test a chosen deployment; this does not replace official schema validation."""
import argparse
import json
import os
import time
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from dotenv import load_dotenv


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Trusted service URL receiving the configured API key")
    parser.add_argument("--job-size", type=int, default=2001, choices=range(2001, 5001), metavar="2001..5000")
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()
    load_dotenv()
    key = os.environ.get("API_KEY")
    if not key:
        parser.error("Set API_KEY in the environment or .env; it is never printed.")
    base = args.base_url.rstrip("/")

    def request(path, payload=None, authenticated=True, method=None):
        headers = {"Content-Type": "application/json"}
        if authenticated:
            headers["X-API-Key"] = key
        req = Request(base + path, data=json.dumps(payload).encode() if payload is not None else None,
                      headers=headers, method=method)
        # Disable redirects so credentials stay on the explicitly chosen service.
        with build_opener(NoRedirect()).open(req, timeout=60) as response:
            body = response.read()
            return json.loads(body) if body else None

    assert request("/health", authenticated=False)["status"] == "ok"
    sample = {"ticket_id": "SMOKE-1", "channel": "chat", "text": "My food order is late"}
    try:
        request("/predict", sample, authenticated=False)
    except HTTPError as error:
        assert error.code == 401
    else:
        raise AssertionError("Prediction endpoint accepted a request without a key")
    assert request("/predict", sample)["ticket_id"] == "SMOKE-1"
    assert request("/predict/batch", {"tickets": [sample]})["meta"]["count"] == 1
    tickets = [dict(sample, ticket_id="SMOKE-{}".format(i)) for i in range(args.job_size)]
    job = request("/batch/jobs", {"tickets": tickets})["job_id"]
    try:
        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            status = request("/batch/jobs/" + job)
            if status["status"] == "succeeded":
                break
            assert status["status"] in ("queued", "running"), "Job failed"
            time.sleep(2)
        else:
            raise TimeoutError("Job did not complete within the configured timeout")
        result = request("/batch/jobs/" + job + "/results?limit=5000")
        assert [p["ticket_id"] for p in result["predictions"]] == [t["ticket_id"] for t in tickets]
        print("Passed: public health, unauthorized access rejection, authenticated predictions, and {} ordered async results.".format(args.job_size))
    finally:
        request("/batch/jobs/" + job, method="DELETE")


if __name__ == "__main__":
    main()
