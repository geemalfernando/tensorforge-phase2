import { useEffect, useMemo, useRef, useState } from "react";
import { api, label, download, sessionRequest, serviceUrl } from "./lib/api";
import TicketPanel from "./components/TicketPanel";
import Landing from "./components/Landing";
import FreshSurface, { Count, Words } from "./components/FreshSurface";

const NAV = [
  ["home", "⌂", "Home"],
  ["intake", "＋", "Ticket intake"],
  ["ops", "◈", "Live operations"],
  ["support", "◇", "Support queue"],
  ["batch", "▤", "Batch workbench"],
  ["models", "⌁", "Model lab"],
];
const PAGE_COPY = {
  intake: ["Ticket intake", "Every ticket. The right team.", "From customer message to a clear route. Three locally trained models identify the issue, the second concern, and the need for urgent attention."],
  ops: ["Live operations", "Every route, in one view.", "Follow ticket routing and review work across your current session."],
  support: ["Support queue", "A thoughtful second look.", "Review urgent or uncertain predictions and accept tickets and confirm the support team."],
  batch: ["Batch workbench", "Thousands of tickets. One run.", "Run a few tickets or an entire evaluation job. Track progress and export every prediction."],
  models: ["Model lab", "Meet the models.", "Inspect the three trained models, development scores, and the fixed support routes."],
};

function PageHero({ page }) {
  const [eyebrow, title, text] = PAGE_COPY[page];
  return (
    <section className="fresh-page-hero" data-spot>
      <div className="fresh-hero-deco" aria-hidden="true">
        <span className="fresh-hero-orbit" />
        <span className="fresh-hero-orbit orbit-two" />
        <span className="fresh-hero-spark">✳</span>
      </div>
      <div className="relative flex flex-wrap items-end justify-between gap-6">
        <div>
          <p className="fresh-hero-eyebrow"><span />{eyebrow} / Fresh Desk</p>
          <h1 key={page} aria-label={title}>
            <span aria-hidden="true"><Words text={title} /></span>
          </h1>
          <p className="mt-3 max-w-xl text-sm leading-relaxed text-[#add7c9]">{text}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {["සිංහල · தமிழ் · English", "3 trained models", "Offline inference"].map((pill, i) => (
            <span key={pill} className="fresh-hero-pill" style={{ "--i": i }}>{pill}</span>
          ))}
        </div>
      </div>
    </section>
  );
}

const SAMPLES = [
  ["Late delivery", "mage order eka late, refund ekak denna"],
  [
    "Lost item",
    "I left my bag in the car after my ride. Please help me get it back.",
  ],
  ["Safety concern", "The driver is not stopping the car and I am scared."],
  ["Tamil message", "என் ஆர்டர்ல ஒரு ஐட்டம் வரல, பணம் திருப்பி தாங்க"],
];
const sampleBatch = {
  tickets: SAMPLES.map(([name, text], i) => ({
    ticket_id: `DEMO-${i + 1}`,
    channel: "chat",
    text,
  })),
};

export default function App() {
  const [page, setPage] = useState("home"),
    [health, setHealth] = useState(null),
    [access, setAccess] = useState(false),
    [models, setModels] = useState(null);
  const [records, setRecords] = useState([]),
    [selectedId, setSelectedId] = useState(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [filter, setFilter] = useState("all");
  const [form, setForm] = useState({
    channel: "chat",
    ticket_id: "",
    subject: "",
    text: "",
  });
  const [batch, setBatch] = useState(JSON.stringify(sampleBatch, null, 2)),
    [job, setJob] = useState(null),
    [batchResults, setBatchResults] = useState(null),
    [notice, setNotice] = useState("");
  const activeJob = useRef(null),
    mounted = useRef(true);
  const [role, setRole] = useState("customer"), [password, setPassword] = useState("");
  async function refreshTickets() {
    try {
      const result = await api("/tickets");
      if (mounted.current) {setRecords(result.records);setRole(result.role);}
    } catch (error) {if (mounted.current) setError(error.message);}
  }
  useEffect(() => {
    mounted.current = true;
    const load = async () => {
      try {
        const [h, a, m] = await Promise.all([
          fetch(serviceUrl("/health")).then((r) => r.json()),
          fetch(serviceUrl("/dashboard/status")).then((r) => r.json()),
          fetch(serviceUrl("/dashboard/models")).then((r) => r.json()),
        ]);
        if (mounted.current) {
          setHealth(h);
          setAccess(a.configured);
          setModels(m.models ? m : null);
        }
      } catch {
        if (mounted.current) {
          setHealth(null);
          setAccess(false);
        }
      }
    };
    load();
    refreshTickets();
    const timer = setInterval(load, 15000);
    const ticketsTimer = setInterval(refreshTickets, 10000);
    return () => {
      mounted.current = false;
      clearInterval(timer);
      clearInterval(ticketsTimer);
    };
  }, []);
  const selected = records.find((r) => r.id === selectedId) || records[0];
  const stats = {
    total: records.length,
    urgent: records.filter((r) => r.prediction.is_urgent).length,
    review: records.filter((r) => r.state === "review").length,
    resolved: records.filter((r) => r.state === "accepted").length,
  };
  const rows = useMemo(
    () =>
      records
        .filter((r) => page !== "support" || r.state === "review")
        .filter(
          (r) =>
            filter === "all" ||
            (filter === "urgent"
              ? r.prediction.is_urgent
              : filter === "review"
                ? r.state === "review"
                : r.state === "accepted"),
        ),
    [records, page, filter],
  );
  const update = (key, value) => setForm((f) => ({ ...f, [key]: value }));
  async function classify(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const ticket = {
        channel: form.channel,
        text: form.text,
        ...(form.ticket_id ? { ticket_id: form.ticket_id } : {}),
        ...(form.channel === "email" ? { subject: form.subject } : {}),
      };
      const result = await api("/tickets", ticket);
      await refreshTickets();
      setSelectedId(result.records[0].id);
      const state = result.records[0].state;
      setNotice(state === "review" ? "Ticket submitted. Support approval is required." : state === "accepted" ? "High confidence: ticket auto-approved and routed." : "Ticket classified and routed.");
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  async function runBatch() {
    setBusy(true);
    setError("");
    setBatchResults(null);
    setNotice("");
    setJob(null);
    try {
      const payload = JSON.parse(batch);
      if (
        !Array.isArray(payload.tickets) ||
        !payload.tickets.length ||
        payload.tickets.length > 5000
      )
        throw new Error("Provide 1–5,000 tickets in a tickets array.");
      let result;
      if (payload.tickets.length <= 100) {
        result = await api("/predict/batch", payload);
      } else {
        const submitted = await api("/batch/jobs", payload);
        activeJob.current = submitted.job_id;
        setJob(submitted);
        while (mounted.current && activeJob.current === submitted.job_id) {
          await new Promise((r) => setTimeout(r, 500));
          const status = await api(`/batch/jobs/${submitted.job_id}`);
          setJob(status);
          if (status.status === "succeeded") {
            result = await api(`/batch/jobs/${submitted.job_id}/results`);
            break;
          }
          if (!["queued", "running"].includes(status.status))
            throw new Error(`Job ${status.status}.`);
        }
        if (activeJob.current !== submitted.job_id) return;
        activeJob.current = null;
      }
      if (result) {
        setBatchResults(result);
        const saved = await api("/tickets/import", payload);
        await refreshTickets();
        setSelectedId(saved.records[0]?.id);
        setNotice(
          `${result.predictions.length} tickets classified. Results are available below.`,
        );
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  async function cancelJob() {
    const id = activeJob.current;
    if (!id) return;
    try {
      await api(`/batch/jobs/${id}`, null, "DELETE");
      activeJob.current = null;
      setJob((j) => ({ ...j, status: "cancelled" }));
      setNotice("Job cancelled.");
    } catch (e) {
      setError(e.message);
    }
  }
  async function review(id, team, notes) {
    try {
      const record = await api(`/tickets/${id}/accept`, {team, notes});
      setRecords(old=>old.map(r=>r.id===id?record:r));
      setNotice("Ticket accepted by support. The decision has been saved.");
    } catch (error) {setError(error.message);}
  }
  async function signIn(event) {
    event.preventDefault();setBusy(true);setError("");
    try {await sessionRequest("/dashboard/support/login", {password});setPassword("");await refreshTickets();}
    catch(error) {setError(error.message);}
    finally {setBusy(false);}
  }
  async function signOut() {
    await sessionRequest("/dashboard/support/logout", {});await refreshTickets();navigate("intake");
  }
  function navigate(next) {
    setPage(next);
    setFilter("all");
    setError("");
    setNotice("");
    window.scrollTo({ top: 0, behavior: "instant" });
  }
  return (
    <FreshSurface className="app-surface min-h-screen">
      <header className="sticky top-0 z-40 border-b border-slate-200/70 bg-white/90 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-4 px-4 py-3 sm:px-6">
          <a
            href="#"
            onClick={(e) => {
              e.preventDefault();
              navigate("home");
            }}
            className="flex items-center gap-2"
          >
            <span className="fresh-logo">
              f<span>✳</span>
            </span>
            <span className="font-black tracking-tight">
              Fresh Desk
              <span className="block text-[10px] font-semibold uppercase tracking-widest text-teal-700">
                Support intelligence
              </span>
            </span>
          </a>
          <nav
            className="order-3 flex w-full gap-1 overflow-x-auto lg:order-none lg:w-auto lg:flex-1"
            aria-label="Workspace navigation"
          >
            {NAV.map(([id, icon, name]) => (
              <button
                key={id}
                onClick={() => navigate(id)}
                className={`shrink-0 rounded-xl px-3 py-2 text-sm font-semibold transition ${page === id ? "bg-[#133d36] text-white shadow-[0_10px_24px_-14px_#133d36]" : "text-slate-500 hover:bg-[#e8f3ee] hover:text-[#133d36]"}`}
              >
                <span className="mr-2">{icon}</span>
                {name}
              </button>
            ))}
          </nav>
          <span className="status-pill">{role === "support" ? "Support role" : "Customer role"}</span>
          {role === "support" && <button className="text-xs font-semibold" onClick={signOut}>Sign out</button>}
          <span
            role="status"
            className={`ml-auto rounded-full px-3 py-1 text-xs font-bold ${access && health?.model_loaded ? "bg-teal-50 text-teal-800" : "bg-amber-50 text-amber-800"}`}
          >
            {access && health?.model_loaded
              ? "● Service ready"
              : "○ Service unavailable"}
          </span>
          <a
            href="/docs"
            target="_blank"
            rel="noreferrer"
            className="text-xs font-bold text-slate-500"
          >
            API docs ↗
          </a>
        </div>
      </header>
      <main className="page-shell space-y-6 animate-fade-up">
        {page === "home" ? <Landing onStart={()=>navigate("intake")} onModels={()=>navigate("models")} onSupport={()=>navigate("support")}/> : <div key={page} className="fresh-page space-y-6">
        <PageHero page={page} />
        <section
          className="grid grid-cols-2 gap-3 lg:grid-cols-4"
          aria-label="Session activity"
        >
          {[
            ["Classified", stats.total, "saved tickets"],
            ["Urgent", stats.urgent, "priority attention"],
            ["Needs review", stats.review, "waiting for a decision"],
            ["Approved", stats.resolved, "auto or by support"],
          ].map(([name, value, caption]) => (
            <article key={name} className="metric-card">
              <p className="text-xs font-semibold text-slate-500">{name}</p>
              <p className="my-2 text-3xl font-bold"><Count value={value} /></p>
              <p className="text-xs text-slate-400">{caption}</p>
            </article>
          ))}
        </section>
        {error && (
          <p
            role="alert"
            className="rounded-2xl bg-rose-50 p-4 text-sm text-rose-800"
          >
            {error}
          </p>
        )}
        {notice && (
          <p
            role="status"
            className="rounded-2xl bg-teal-50 p-4 text-sm text-teal-800"
          >
            {notice}
          </p>
        )}
        {page === "support" && role !== "support" && (
        <section className="panel mx-auto max-w-lg p-6">
          <p className="kicker">Support role</p><h2 className="mt-2 text-xl font-bold">Sign in to review tickets</h2>
          <p className="mt-3 text-sm text-slate-500">Support staff can inspect the shared review queue and accept or adjust a ticket's routing.</p>
          <form onSubmit={signIn} className="mt-5 space-y-4">
            <label className="block text-xs font-semibold">Support password<input className="field" type="password" autoComplete="current-password" required value={password} onChange={event=>setPassword(event.target.value)}/></label>
            <button className="btn" disabled={busy}>{busy ? "Signing in…" : "Sign in as support"}</button>
          </form>
        </section>
      )}
      {page === "intake" && (
          <div className="grid gap-5 lg:grid-cols-2">
            <section className="panel p-5 sm:p-6">
              <p className="kicker">Customer message</p>
              <h2 className="mt-2 text-xl font-bold">
                Create a support ticket
              </h2>
              <form onSubmit={classify} className="mt-5 space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <label className="text-xs font-bold">
                    Channel
                    <select
                      className="field"
                      value={form.channel}
                      onChange={(e) => update("channel", e.target.value)}
                    >
                      <option value="chat">Live chat</option>
                      <option value="email">Email</option>
                      <option value="call_transcript">Call transcript</option>
                    </select>
                  </label>
                  <label className="text-xs font-bold">
                    Ticket ID · optional
                    <input
                      className="field"
                      maxLength={64}
                      placeholder="TF-1048"
                      value={form.ticket_id}
                      onChange={(e) => update("ticket_id", e.target.value)}
                    />
                  </label>
                </div>
                {form.channel === "email" && (
                  <label className="block text-xs font-bold">
                    Subject
                    <input
                      className="field"
                      maxLength={500}
                      value={form.subject}
                      onChange={(e) => update("subject", e.target.value)}
                    />
                  </label>
                )}
                <label className="block text-xs font-bold">
                  Message
                  <textarea
                    className="field min-h-44"
                    required
                    maxLength={10000}
                    placeholder="For example: My food order is late and I need a refund…"
                    value={form.text}
                    onChange={(e) => update("text", e.target.value)}
                  />
                </label>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-400">
                    {form.text.length.toLocaleString()} / 10,000
                  </span>
                  <button
                    className="btn"
                    disabled={busy || !access || !form.text.trim()}
                  >
                    {busy ? "Classifying…" : "Classify & route ↗"}
                  </button>
                </div>
              </form>
              <div className="mt-6 border-t pt-4">
                <p className="mb-2 text-xs font-semibold text-slate-500">
                  Try a customer scenario
                </p>
                <div className="flex flex-wrap gap-2">
                  {SAMPLES.map(([name, text]) => (
                    <button
                      key={name}
                      className="btn-secondary !px-3 !py-2 !text-xs"
                      onClick={() => {
                        update("text", text);
                        setNotice("");
                      }}
                    >
                      {name} ↗
                    </button>
                  ))}
                </div>
              </div>
            </section>
            <section className="panel p-5 sm:p-6">
              {selected ? (
                <TicketPanel
                  key={selected.id}
                  record={selected}
                  routes={models?.routes || {}}
                  models={models}
                  role={role}
                  onOpenSupport={()=>navigate("support")}
                  onReview={review}
                />
              ) : (
                <div className="grid min-h-96 place-items-center text-center">
                  <div>
                    <div className="fresh-empty-icon mx-auto mb-6">
                      ◇
                    </div>
                    <p className="kicker">Prediction preview</p>
                    <h2 className="mt-3 text-xl font-bold">
                      Ready for your first ticket
                    </h2>
                    <p className="mt-2 max-w-xs text-sm text-slate-500">
                      See the category, recommended team, urgency, and whether
                      human review is needed.
                    </p>
                  </div>
                </div>
              )}
            </section>
          </div>
        )}
        {(page === "ops" || (page === "support" && role === "support")) && (
          <>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap gap-2">
                {[
                  "all",
                  "urgent",
                  ...(page === "ops" ? ["review", "resolved"] : []),
                ].map((f) => (
                  <button
                    key={f}
                    onClick={() => setFilter(f)}
                    className={filter === f ? "btn" : "btn-secondary"}
                  >
                    {label(f)}
                  </button>
                ))}
              </div>
              <button
                className="btn-secondary"
                onClick={() => download(records, "session-tickets.json")}
                disabled={!records.length}
              >
                Export session ↓
              </button>
            </div>
            <div className="grid gap-5 lg:grid-cols-12">
              <aside className="space-y-2 lg:col-span-4">
                {rows.slice(0, 100).map((r) => (
                  <button
                    key={r.id}
                    onClick={() => setSelectedId(r.id)}
                    className={`fresh-ticket-row ${selected?.id === r.id ? "is-selected" : ""}`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <strong className="break-all text-sm">
                        {r.ticket.ticket_id || "Ticket"}
                        <span className="mt-1 block text-xs font-normal text-slate-400">
                          {label(r.ticket.channel)}
                        </span>
                      </strong>
                      <span
                        className={`rounded-full px-2 py-1 text-[11px] font-bold ${r.prediction.is_urgent ? "bg-rose-100 text-rose-800" : "bg-teal-50 text-teal-800"}`}
                      >
                        {r.prediction.is_urgent
                          ? "Urgent"
                          : `${Math.round(r.prediction.confidence * 100)}%`}
                      </span>
                    </div>
                    <p className="mt-3 line-clamp-2 text-sm text-slate-600">
                      {r.ticket.text}
                    </p>
                    <div className="mt-3 flex justify-between gap-2 text-xs">
                      <span>{r.finalTeam}</span>
                      <span className="text-slate-400">{label(r.state)}</span>
                    </div>
                  </button>
                ))}
                {!rows.length && (
                  <div className="panel p-8 text-sm text-slate-500">
                    {page === "support"
                      ? "No tickets waiting for review. Classify a ticket to begin."
                      : "Your session is empty. Add a ticket or run a batch."}
                    <button
                      className="btn mt-4 block"
                      onClick={() => navigate("intake")}
                    >
                      Open ticket intake ↗
                    </button>
                  </div>
                )}
                {rows.length > 100 && (
                  <p className="text-xs text-slate-500">
                    Showing the first 100 tickets. Export includes the full
                    session.
                  </p>
                )}
              </aside>
              <section className="panel p-5 lg:col-span-8">
                {selected && rows.some((r) => r.id === selected.id) ? (
                  <TicketPanel
                    key={selected.id}
                    record={selected}
                    routes={models?.routes || {}}
                  models={models}
                  role={role}
                  onOpenSupport={()=>navigate("support")}
                    onReview={review}
                  />
                ) : rows[0] ? (
                  <TicketPanel
                    key={rows[0].id}
                    record={rows[0]}
                    routes={models?.routes || {}}
                  models={models}
                  role={role}
                  onOpenSupport={()=>navigate("support")}
                    onReview={review}
                  />
                ) : (
                  <div className="grid min-h-80 place-items-center text-sm text-slate-400">
                    Select a ticket to inspect its routing.
                  </div>
                )}
              </section>
            </div>
          </>
        )}
        {page === "batch" && (
          <>
            <section className="panel p-5 sm:p-6">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="kicker">Evaluation workbench</p>
                  <h2 className="mt-2 text-xl font-bold">Batch inference</h2>
                </div>
                <label className="btn-secondary cursor-pointer">
                  Load JSON ↑
                  <input
                    type="file"
                    accept="application/json,.json"
                    className="hidden"
                    disabled={busy}
                    onChange={async (e) => {
                      try {
                        if (e.target.files[0])
                          setBatch(await e.target.files[0].text());
                      } catch {
                        setError("Could not read this file.");
                      }
                      e.target.value = "";
                    }}
                  />
                </label>
              </div>
              <p className="my-4 text-sm text-slate-500">
                1–100 tickets run synchronously. 101–5,000 run as a background
                job. Every ticket requires a unique ticket_id.
              </p>
              <textarea
                aria-label="Batch request JSON"
                className="field min-h-64 font-mono"
                spellCheck={false}
                value={batch}
                onChange={(e) => setBatch(e.target.value)}
                disabled={busy}
              />
              <div className="mt-4 flex flex-wrap justify-between gap-3">
                <button
                  className="btn-secondary"
                  disabled={busy}
                  onClick={() => setBatch(JSON.stringify(sampleBatch, null, 2))}
                >
                  Load sample
                </button>
                <button
                  className="btn"
                  disabled={busy || !access}
                  onClick={runBatch}
                >
                  {busy ? "Processing…" : "Run batch ↗"}
                </button>
              </div>
              {job && (
                <div
                  className="mt-5 rounded-2xl bg-slate-50 p-4"
                  aria-live="polite"
                >
                  <div className="flex justify-between text-sm">
                    <strong>Job {label(job.status)}</strong>
                    <span>
                      {job.processed} / {job.total}
                    </span>
                  </div>
                  <progress
                    className="mt-3 w-full accent-teal-600"
                    max={job.total || 1}
                    value={job.processed || 0}
                  />
                  {activeJob.current && (
                    <button className="btn-secondary mt-3" onClick={cancelJob}>
                      Cancel job
                    </button>
                  )}
                </div>
              )}
            </section>
            {batchResults && (
              <section className="panel overflow-hidden">
                <div className="flex items-center justify-between gap-3 p-5">
                  <h2 className="font-bold">
                    {batchResults.predictions.length} predictions
                  </h2>
                  <button
                    className="btn"
                    onClick={() => download(batchResults)}
                  >
                    Download JSON ↓
                  </button>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr>
                        {[
                          "Ticket",
                          "Category / team",
                          "Confidence",
                          "Urgency",
                        ].map((h) => (
                          <th className="p-4" key={h}>
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {batchResults.predictions.slice(0, 100).map((p, i) => (
                        <tr key={i}>
                          <td className="p-4">{p.ticket_id}</td>
                          <td className="p-4 font-semibold">
                            {label(p.category)}
                            <span className="block text-xs font-normal text-slate-500">
                              {p.team}
                            </span>
                          </td>
                          <td className="p-4">
                            {(p.confidence * 100).toFixed(1)}%
                          </td>
                          <td className="p-4">
                            {p.is_urgent ? "Urgent" : "Standard"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="p-5 text-xs text-slate-400">
                  Preview limited to 100 rows. Download includes all results.
                </p>
              </section>
            )}
          </>
        )}
        {page === "models" && (
          <>
            <div className="grid gap-4 md:grid-cols-3">
              {(models?.models || []).map((m, i) => (
                <section className="panel p-5" key={m.id}>
                  <div className="flex justify-between">
                    <span className="kicker">Model 0{i + 1}</span>
                    <span className="status-pill">● Loaded</span>
                  </div>
                  <h2 className="mt-4 text-xl font-bold">{label(m.id)}</h2>
                  <p className="mt-2 text-sm text-slate-500">{m.algorithm}</p>
                  <p className="mt-6 text-3xl font-bold">
                    {(m.validation.accuracy * 100).toFixed(1)}%
                    <span className="ml-2 text-xs font-normal text-slate-400">
                      accuracy
                    </span>
                  </p>
                  <div className="fresh-bar mt-3">
                    <div
                      style={{ width: `${m.validation.accuracy * 100}%` }}
                    />
                  </div>
                  <p className="mt-3 text-xs text-slate-500">
                    Macro-F1 {(m.validation.macro_f1 * 100).toFixed(1)}% ·{" "}
                    {m.classes.length} classes
                  </p>
                </section>
              ))}
            </div>
            <section className="panel p-6">
              <p className="kicker">Training & validation</p>
              <h2 className="mt-2 text-xl font-bold">
                Our own classifiers, loaded from disk
              </h2>
              <p className="mt-3 text-sm leading-relaxed text-slate-500">
                Trained on{" "}
                {models?.training_examples?.toLocaleString() || "4,000"}{" "}
                synthetic RideEat tickets with word and character TF-IDF
                features. The {models?.validation_examples || 800}-ticket
                validation split is used for reporting. Configurations and
                thresholds were compared on training and validation data.
                These are development scores; the judges' unseen data is the
                independent test.
                Predictions use all three classifiers, then enforce category
                precedence and the fixed category-to-team map. Primary
                confidence below 50% or very little message context recommends
                human review.
              </p>
              <p className="mt-3 text-xs text-slate-400">
                Artifact: {models?.model_version || "Loading"} · No model
                downloads or external AI calls at runtime.
              </p>
            </section>
            <section className="panel p-6">
              <p className="kicker">Routing directory</p>
              <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {Object.entries(models?.routes || {}).map(([c, t]) => (
                  <div className="fresh-route-tile" key={c}>
                    <p className="text-sm font-bold">{t}</p>
                    <p className="mt-1 text-xs text-slate-500">{label(c)}</p>
                  </div>
                ))}
              </div>
            </section>
          </>
        )}
        </div>}
        <footer className="flex flex-wrap justify-between gap-3 border-t py-4 text-xs text-slate-400">
          <span>Fresh Desk · TensorForge Phase 2</span>
          <span>
            Tickets and support decisions are saved. Async jobs
            retained for 24 hours.
          </span>
        </footer>
      </main>
    </FreshSurface>
  );
}
