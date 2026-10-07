"""Verify port binding and offline runtime of a built image without logging API_KEY."""
import argparse
import json
import os
import subprocess
import time
import uuid
from pathlib import Path
from urllib.request import urlopen

from dotenv import load_dotenv

RUNTIME_CHECK = r'''
import json, os, time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
assert not Path('/app/.env').exists()
assert json.loads(Path('/app/app/openapi.json').read_text())['info']['version'] == '2.1.0'
base = 'http://127.0.0.1:8000'
started = time.monotonic()
deadline = started + 120
while time.monotonic() < deadline:
    try:
        with urlopen(base + '/health', timeout=2) as r:
            health = json.load(r)
            assert health['status'] == 'ok'
        break
    except Exception:
        time.sleep(.1)
else:
    raise RuntimeError('Container did not become ready within 120 seconds')
def request(path, payload=None, authenticated=True):
    headers = {'Content-Type': 'application/json'}
    if authenticated:
        headers['X-API-Key'] = os.environ['API_KEY']
    req = Request(base + path, data=json.dumps(payload).encode() if payload is not None else None, headers=headers)
    with urlopen(req, timeout=60) as r:
        return json.load(r)
ticket = {'ticket_id': 'offline-check', 'channel': 'chat', 'text': 'My food order is late'}
try:
    request('/predict', ticket, authenticated=False)
except HTTPError as error:
    assert error.code == 401
    assert error.headers['WWW-Authenticate'] == 'Bearer'
else:
    raise AssertionError('Container inference is open without a key')
single = request('/predict', ticket)
assert single['model_version'] == health['model_version']
batch = request('/predict/batch', {'tickets': [dict(ticket, ticket_id=str(i)) for i in range(100)]})
assert batch['meta']['count'] == 100
assert [p['ticket_id'] for p in batch['predictions']] == [str(i) for i in range(100)]
job = request('/batch/jobs', {'tickets': [dict(ticket, ticket_id=str(i)) for i in range(2001)]})
deadline = time.monotonic() + 120
while time.monotonic() < deadline:
    status = request('/batch/jobs/' + job['job_id'])
    if status['status'] == 'succeeded':
        break
    assert status['status'] in ('queued', 'running')
    time.sleep(.1)
else:
    raise RuntimeError('Offline job did not complete')
result = request('/batch/jobs/' + job['job_id'] + '/results')
assert [p['ticket_id'] for p in result['predictions']] == [str(i) for i in range(2001)]
print(json.dumps({'model_version': health['model_version'], 'sync_batch_size': 100, 'async_job_size': 2001, 'offline_runtime_passed': True}))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="tensorforge-mvp")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    if not os.environ.get("API_KEY"):
        parser.error("Set API_KEY in .env or the environment; it is passed to Docker without being printed.")

    def docker(*arguments, **kwargs):
        return subprocess.check_output(["docker", *arguments], text=True, **kwargs).strip()

    evidence = {"image": args.image, "image_id": docker("image", "inspect", args.image, "--format", "{{.Id}}")}
    for mode in ("published-port", "offline"):
        name = "tensorforge-verify-" + uuid.uuid4().hex[:12]
        options = ["--network", "none"] if mode == "offline" else ["-p", "127.0.0.1::8000"]
        started = time.monotonic()
        try:
            docker("run", "-d", "--name", name, *options, "-e", "API_KEY", args.image)
            if mode == "published-port":
                port = docker("port", name, "8000/tcp")
                deadline = started + 120
                while time.monotonic() < deadline:
                    try:
                        with urlopen("http://" + port + "/health", timeout=2) as response:
                            assert json.load(response)["status"] == "ok"
                        break
                    except Exception:
                        time.sleep(.1)
                else:
                    raise RuntimeError("Published port did not become ready within 120 seconds")
                evidence["published_port_ready_seconds"] = round(time.monotonic() - started, 3)
            else:
                evidence.update(json.loads(docker("exec", "-i", name, "python", "-", input=RUNTIME_CHECK)))
        finally:
            subprocess.run(["docker", "rm", "-f", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
