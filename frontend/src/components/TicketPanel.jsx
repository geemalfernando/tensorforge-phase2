// Adapted from ResolveX's CasePanel: decision header, evidence blocks and support review.
import { useState } from "react";
import { label, download } from "../lib/api";
export default function TicketPanel({ record, routes, onReview }) {
  const { ticket, prediction: p } = record;
  const [team, setTeam] = useState(record.finalTeam),
    [notes, setNotes] = useState(record.notes);
  return (
    <section className="space-y-5" data-testid="ticket-panel">
      <div className="overflow-hidden rounded-2xl bg-slate-900 p-5 text-white">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-[11px] uppercase tracking-widest text-teal-200">
              Recommended route
            </p>
            <h2 className="mt-2 text-2xl font-bold">{record.finalTeam}</h2>
            <p className="mt-1 text-sm text-slate-300">{label(p.category)}</p>
          </div>
          <span
            className={`rounded-full px-3 py-1 text-xs font-bold ${p.is_urgent ? "bg-rose-100 text-rose-800" : "bg-teal-100 text-teal-800"}`}
          >
            {p.is_urgent ? "Urgent attention" : "Standard priority"}
          </span>
        </div>
        <p className="mt-4 text-sm text-slate-300">
          Primary category confidence {(p.confidence * 100).toFixed(1)}%
        </p>
        <div className="mt-2 h-1.5 rounded-full bg-white/10">
          <div
            className="h-full rounded-full bg-teal-300"
            style={{ width: `${p.confidence * 100}%` }}
          />
        </div>
      </div>
      <div className="flex items-center justify-between gap-3 text-xs">
        <strong className="break-all">
          {ticket.ticket_id || "Ticket without external ID"}
        </strong>
        <span className="status-pill">{label(record.state)}</span>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-2xl bg-slate-50 p-4">
          <p className="kicker">Customer message</p>
          {ticket.subject && (
            <p className="mt-2 text-sm font-bold">{ticket.subject}</p>
          )}
          <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-relaxed text-slate-600">
            {ticket.text}
          </p>
          <p className="mt-3 text-xs text-slate-400">{label(ticket.channel)}</p>
        </div>
        <div className="rounded-2xl bg-slate-50 p-4">
          <p className="kicker">Three model signals</p>
          <dl className="mt-3 space-y-3 text-sm">
            <div>
              <dt className="text-xs text-slate-400">Primary issue</dt>
              <dd className="font-semibold">{label(p.category)}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-400">Secondary issue</dt>
              <dd>{label(p.secondary_category)}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-400">Urgency</dt>
              <dd>{p.is_urgent ? "Urgent" : "Standard"}</dd>
            </div>
          </dl>
        </div>
      </div>
      {p.needs_human_review && (
        <p className="rounded-2xl bg-amber-50 p-4 text-sm text-amber-900">
          {ticket.text.trim().split(/\s+/).length <= 3
            ? "Human review recommended: this message has very little context. Add what happened and whether it concerns a ride, food order, account, or payment."
            : "Human review recommended: the primary confidence is below 50%."}
        </p>
      )}
      <form
        className="rounded-2xl border border-slate-200 p-4"
        onSubmit={(e) => {
          e.preventDefault();
          onReview(record.id, team, notes.trim());
        }}
      >
        <h3 className="font-semibold">Support decision</h3>
        <p className="mt-1 text-xs text-slate-500">
          Confirm or change the support team for this session.
        </p>
        <label className="mt-3 block text-xs font-semibold">
          Final team
          <select
            className="field"
            value={team}
            onChange={(e) => setTeam(e.target.value)}
          >
            {[...new Set([p.team, ...Object.values(routes)])].map((t) => (
              <option key={t}>{t}</option>
            ))}
          </select>
        </label>
        <label className="mt-3 block text-xs font-semibold">
          Review notes
          <textarea
            className="field"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            required={team !== p.team}
            maxLength={2000}
            placeholder={
              team !== p.team
                ? "Explain the routing override"
                : "Optional review note"
            }
          />
        </label>
        <button className="btn mt-3" type="submit">
          {record.state === "resolved" ? "Update review" : "Confirm routing"}
        </button>
      </form>
      <details className="rounded-2xl border p-4">
        <summary className="cursor-pointer text-sm font-semibold">
          Prediction JSON
        </summary>
        <pre className="mt-3 overflow-auto text-xs">
          {JSON.stringify(p, null, 2)}
        </pre>
        <button
          className="btn-secondary mt-3"
          onClick={() => download(p, "ticket-prediction.json")}
        >
          Download JSON ↓
        </button>
      </details>
      <p className="text-[11px] text-slate-400">
        Model {p.model_version} · {new Date(record.at).toLocaleTimeString()}
      </p>
    </section>
  );
}
