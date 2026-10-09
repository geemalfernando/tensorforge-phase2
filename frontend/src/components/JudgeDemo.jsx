import { useState } from "react";
import { serviceUrl } from "../lib/api";

const SAMPLE_TICKET = {
  ticket_id: "JUDGE-DEMO-001",
  channel: "chat",
  text: "My food order is late and has not arrived.",
};
const SAMPLE_BATCH = {
  tickets: [
    SAMPLE_TICKET,
    {
      ticket_id: "JUDGE-DEMO-002",
      channel: "email",
      subject: "Lost property",
      text: "I left my bag in the car after my ride.",
    },
  ],
};
const SAMPLE_JOB = {
  tickets: [
    SAMPLE_TICKET,
    {
      ticket_id: "JUDGE-JOB-002",
      channel: "chat",
      text: "The driver is refusing to stop and I feel unsafe.",
    },
    {
      ticket_id: "JUDGE-JOB-003",
      channel: "call_transcript",
      text: "An item was missing from my meal.",
    },
  ],
};

async function callApi(path, apiKey, { method = "GET", body, headers = {} } = {}) {
  const response = await fetch(serviceUrl(path), {
    method,
    headers: {
      ...(apiKey ? { "X-API-Key": apiKey } : {}),
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
      ...headers,
    },
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  });
  const text = await response.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { response: text };
    }
  }
  return { status: response.status, data, retryAfter: response.headers.get("Retry-After") };
}

function ResponsePanel({ response }) {
  if (!response) return null;
  return (
    <section className="panel overflow-hidden" aria-live="polite">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-4 py-3">
        <div>
          <p className="kicker">Latest response</p>
          <p className="mt-1 font-mono text-xs text-slate-500">
            {response.method} {response.path}
          </p>
        </div>
        <span className={`status-pill ${response.status >= 400 ? "text-rose-700" : "text-teal-800"}`}>
          HTTP {response.status}
        </span>
      </div>
      {response.retryAfter && (
        <p className="px-4 pt-3 text-xs text-slate-500">
          Retry-After: {response.retryAfter} seconds
        </p>
      )}
      <pre className="max-h-96 overflow-auto whitespace-pre-wrap break-words p-4 text-xs leading-relaxed text-slate-700">
        {response.data === null
          ? "No response body (204 No Content)."
          : JSON.stringify(response.data, null, 2)}
      </pre>
    </section>
  );
}

function EndpointCard({ title, description, children }) {
  return (
    <section className="panel space-y-4 p-5 sm:p-6">
      <div>
        <p className="kicker">Judge endpoint</p>
        <h2 className="mt-2 text-lg font-bold">{title}</h2>
        <p className="mt-2 text-sm leading-relaxed text-slate-500">{description}</p>
      </div>
      {children}
    </section>
  );
}

export default function JudgeDemo({ apiKey, onAuthorize, onClear }) {
  const [candidate, setCandidate] = useState("");
  const [authBusy, setAuthBusy] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [response, setResponse] = useState(null);
  const [singleJson, setSingleJson] = useState(JSON.stringify(SAMPLE_TICKET, null, 2));
  const [batchJson, setBatchJson] = useState(JSON.stringify(SAMPLE_BATCH, null, 2));
  const [jobJson, setJobJson] = useState(JSON.stringify(SAMPLE_JOB, null, 2));
  const [jobId, setJobId] = useState("");
  const [idempotencyKey, setIdempotencyKey] = useState("");
  const [offset, setOffset] = useState("0");
  const [limit, setLimit] = useState("100");

  async function authenticate(event) {
    event.preventDefault();
    setAuthBusy(true);
    setError("");
    try {
      const result = await callApi("/auth/verify", candidate.trim(), {
        method: "POST",
        body: {},
      });
      setResponse({ method: "POST", path: "/auth/verify", ...result });
      if (result.status !== 200 || result.data?.status !== "authenticated") {
        setError(result.data?.error?.message || "The API key was not accepted.");
        return;
      }
      onAuthorize(candidate.trim());
      setCandidate("");
    } catch {
      setError("Could not reach the API. Check the service connection and try again.");
    } finally {
      setAuthBusy(false);
    }
  }

  async function execute(method, path, options = {}) {
    setBusy(true);
    setError("");
    try {
      const result = await callApi(path, apiKey, options);
      setResponse({ method, path, ...result });
      return result;
    } catch {
      setError("Could not reach the API. Check the service connection and try again.");
      return null;
    } finally {
      setBusy(false);
    }
  }

  async function submitJob(event) {
    event.preventDefault();
    let body;
    try {
      body = JSON.parse(jobJson);
    } catch {
      setError("Async job body must be valid JSON.");
      return;
    }
    const result = await execute("POST", "/batch/jobs", {
      method: "POST",
      body,
      headers: {
        ...(idempotencyKey.trim() ? { "Idempotency-Key": idempotencyKey.trim() } : {}),
      },
    });
    if (result?.status === 202 && result.data?.job_id) setJobId(result.data.job_id);
  }

  async function submitSingle(event) {
    event.preventDefault();
    let body;
    try {
      body = JSON.parse(singleJson);
    } catch {
      setError("Prediction body must be valid JSON.");
      return;
    }
    await execute("POST", "/predict", { method: "POST", body });
  }

  async function submitBatch(event) {
    event.preventDefault();
    let body;
    try {
      body = JSON.parse(batchJson);
    } catch {
      setError("Batch body must be valid JSON.");
      return;
    }
    await execute("POST", "/predict/batch", { method: "POST", body });
  }

  function chooseDemo(next) {
    setError("");
    setResponse(null);
    if (next === "health") void execute("GET", "/health");
    if (next === "auth") void execute("POST", "/auth/verify", { method: "POST", body: {} });
  }

  if (!apiKey) {
    return (
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(18rem,.7fr)]">
        <section className="panel p-5 sm:p-7">
          <p className="kicker">Evaluation access</p>
          <h2 className="mt-2 text-2xl font-bold">Sign in as judge</h2>
          <p className="mt-3 max-w-2xl text-sm leading-relaxed text-slate-500">
            Enter the API key issued for evaluation. The dashboard verifies it with
            <code className="mx-1 rounded bg-slate-100 px-1">POST /auth/verify</code>
            before unlocking the documented test controls.
          </p>
          <form onSubmit={authenticate} className="mt-6 space-y-4">
            <label className="block text-xs font-bold" htmlFor="judge-api-key">
              Evaluation API key
              <input
                id="judge-api-key"
                className="field font-mono"
                type="password"
                autoComplete="off"
                autoCapitalize="none"
                spellCheck={false}
                required
                value={candidate}
                onChange={(event) => setCandidate(event.target.value)}
                placeholder="Paste the key issued to your team"
              />
            </label>
            {error && <p role="alert" className="text-sm text-rose-700">{error}</p>}
            <button className="btn" disabled={authBusy || !candidate.trim()}>
              {authBusy ? "Verifying key…" : "Verify key & open demo"}
            </button>
          </form>
        </section>
        <aside className="panel p-5 sm:p-6">
          <p className="kicker">Key handling</p>
          <h2 className="mt-2 text-lg font-bold">Judge access only</h2>
          <ul className="mt-4 space-y-3 text-sm leading-relaxed text-slate-500">
            <li>The key is sent only to this API as an authorization header.</li>
            <li>It stays in page memory only and is not saved to browser storage.</li>
            <li>Use “Sign out” to clear it from the page.</li>
          </ul>
        </aside>
        <ResponsePanel response={response} />
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <section className="panel flex flex-wrap items-center justify-between gap-4 p-4 sm:p-5">
        <div>
          <p className="kicker">Judge authenticated</p>
          <h2 className="mt-1 text-lg font-bold">API evaluation console</h2>
          <p className="mt-1 text-xs text-slate-500">
            The key is held in memory only. Requests use the OpenAPI-defined endpoint paths and payloads.
          </p>
        </div>
        <button
          className="btn-secondary"
          onClick={() => {
            setResponse(null);
            setJobId("");
            onClear();
          }}
          disabled={busy}
        >
          Sign out & clear key
        </button>
      </section>

      {error && <p role="alert" className="rounded-2xl bg-rose-50 p-4 text-sm text-rose-800">{error}</p>}

      <section className="grid gap-3 sm:grid-cols-2">
        <button className="panel p-4 text-left transition hover:border-teal-300" onClick={() => chooseDemo("health")} disabled={busy}>
          <span className="kicker">Public readiness</span>
          <span className="mt-2 block font-mono text-sm font-bold">GET /health</span>
          <span className="mt-1 block text-xs text-slate-500">Check the hosted model version.</span>
        </button>
        <button className="panel p-4 text-left transition hover:border-teal-300" onClick={() => chooseDemo("auth")} disabled={busy}>
          <span className="kicker">Verify authorization</span>
          <span className="mt-2 block font-mono text-sm font-bold">POST /auth/verify</span>
          <span className="mt-1 block text-xs text-slate-500">Recheck the active evaluation key.</span>
        </button>
      </section>

      <div className="grid gap-5 lg:grid-cols-2">
        <EndpointCard title="Single ticket" description="POST /predict · Try one contract-shaped ticket.">
          <form onSubmit={submitSingle} className="space-y-3">
            <textarea className="field min-h-48 font-mono text-xs" aria-label="Single ticket request JSON" spellCheck={false} value={singleJson} onChange={(event) => setSingleJson(event.target.value)} />
            <button className="btn" disabled={busy}>{busy ? "Sending…" : "Send prediction"}</button>
          </form>
        </EndpointCard>
        <EndpointCard title="Synchronous batch" description="POST /predict/batch · Submit 1–100 tickets and inspect the ordered predictions.">
          <form onSubmit={submitBatch} className="space-y-3">
            <textarea className="field min-h-48 font-mono text-xs" aria-label="Judge batch request JSON" spellCheck={false} value={batchJson} onChange={(event) => setBatchJson(event.target.value)} />
            <button className="btn" disabled={busy}>{busy ? "Sending…" : "Run synchronous batch"}</button>
          </form>
        </EndpointCard>
        <EndpointCard title="Asynchronous batch job" description="POST /batch/jobs · Create a 1–5,000-ticket job. Supply an optional Idempotency-Key to make a retry safe.">
          <form onSubmit={submitJob} className="space-y-3">
            <textarea className="field min-h-40 font-mono text-xs" aria-label="Async job request JSON" spellCheck={false} value={jobJson} onChange={(event) => setJobJson(event.target.value)} />
            <label className="block text-xs font-bold">
              Idempotency-Key · optional
              <input className="field font-mono" maxLength={128} value={idempotencyKey} onChange={(event) => setIdempotencyKey(event.target.value)} placeholder="Unique retry key" />
            </label>
            <button className="btn" disabled={busy}>{busy ? "Submitting…" : "Submit async job"}</button>
          </form>
        </EndpointCard>
        <EndpointCard title="Poll, fetch, or cancel" description="Use the returned job_id to call the documented status, paged-results, and DELETE endpoints.">
          <label className="block text-xs font-bold">
            Job ID
            <input className="field font-mono" value={jobId} onChange={(event) => setJobId(event.target.value)} placeholder="Paste a job_id" />
          </label>
          <div className="grid gap-2 sm:grid-cols-2">
            <button className="btn-secondary" disabled={busy || !jobId.trim()} onClick={() => void execute("GET", `/batch/jobs/${encodeURIComponent(jobId.trim())}`)}>Poll status</button>
            <button className="btn-secondary" disabled={busy || !jobId.trim()} onClick={() => {
              const query = new URLSearchParams({ offset, limit });
              void execute("GET", `/batch/jobs/${encodeURIComponent(jobId.trim())}/results?${query}`);
            }}>Fetch results</button>
            <button className="btn-danger" disabled={busy || !jobId.trim()} onClick={() => void execute("DELETE", `/batch/jobs/${encodeURIComponent(jobId.trim())}`, { method: "DELETE" })}>Cancel / discard</button>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <label className="block text-xs font-bold">
              Results offset
              <input className="field" inputMode="numeric" value={offset} onChange={(event) => setOffset(event.target.value)} />
            </label>
            <label className="block text-xs font-bold">
              Results limit
              <input className="field" inputMode="numeric" value={limit} onChange={(event) => setLimit(event.target.value)} />
            </label>
          </div>
        </EndpointCard>
      </div>
      <ResponsePanel response={response} />
    </div>
  );
}
