// Adapted from ResolveX's CasePanel: decision header, evidence blocks and support review.
import { useState } from "react";
import { label, download } from "../lib/api";
export default function TicketPanel({ record, routes, onReview, role, models, onOpenSupport }) {
  const { ticket, prediction: p } = record;
  const [team, setTeam] = useState(record.finalTeam),
    [notes, setNotes] = useState(record.notes);
  const [accepting,setAccepting] = useState(false);
  const analysis = record.analysis;
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
      {analysis && <section className="rounded-2xl border border-slate-200 p-4" data-testid="model-details">
        <p className="kicker">How the models scored this ticket</p>
        <div className="mt-4 grid gap-4 sm:grid-cols-3">
          {(models?.models || []).map(model=><div key={model.id}><h3 className="text-sm font-bold">{label(model.id)}</h3><p className="mt-1 text-xs text-slate-500">{model.algorithm}</p><p className="mt-2 text-xs text-slate-500">Validation accuracy {(model.validation.accuracy*100).toFixed(1)}% · macro-F1 {(model.validation.macro_f1*100).toFixed(1)}%</p></div>)}
        </div>
        <div className="mt-5 grid gap-5 sm:grid-cols-2">
          <div><h3 className="text-sm font-semibold">Primary category candidates</h3>{analysis.primary_candidates.slice(0,3).map(candidate=><div className="mt-3" key={candidate.label}><div className="flex justify-between gap-2 text-xs"><span>{label(candidate.label)}</span><strong>{(candidate.probability*100).toFixed(1)}%</strong></div><div className="mt-1 h-1.5 rounded bg-slate-100"><div className="h-full rounded bg-teal-500" style={{width:`${candidate.probability*100}%`}}/></div></div>)}</div>
          <div><h3 className="text-sm font-semibold">Secondary and urgency signals</h3><p className="mt-3 text-xs text-slate-500">Secondary cutoff: {(analysis.secondary_threshold*100).toFixed(0)}%</p>{analysis.secondary_candidates.slice(0,3).map(candidate=><p className="mt-2 flex justify-between gap-2 text-xs" key={candidate.label}><span>{candidate.label==='__none__'?'No secondary issue':label(candidate.label)}</span><strong>{(candidate.probability*100).toFixed(1)}%</strong></p>)}<p className="mt-4 text-xs">Urgency probability <strong>{(analysis.urgent_probability*100).toFixed(1)}%</strong> · cutoff {(analysis.urgent_threshold*100).toFixed(0)}%</p></div>
        </div>
        <p className="mt-4 text-xs text-slate-500">{analysis.rule_adjusted?`Routing rules adjusted the raw prediction (${label(analysis.raw_category)}).`:'No category precedence adjustment was applied.'} Model probabilities describe predictions; they do not guarantee correctness.</p>
        {!!analysis.review_reasons.length&&<p className="mt-3 text-xs text-amber-800">Review reasons: {analysis.review_reasons.join(' · ')}</p>}
      </section>}
      {role === 'support' && record.state !== 'accepted' ? <form
        className="rounded-2xl border border-slate-200 p-4"
        onSubmit={async (e) => {
          e.preventDefault();
          setAccepting(true);
          try {await onReview(record.id, team, notes.trim());} finally {setAccepting(false);}
        }}
      >
        <h3 className="font-semibold">Support decision</h3>
        <p className="mt-1 text-xs text-slate-500">
          Review the model signals, then accept the ticket or explain a routing change.
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
        <button className="btn mt-3" type="submit" disabled={accepting}>
          {accepting ? "Accepting…" : "Accept ticket"}
        </button>
      </form> : record.state === 'accepted' ? <section className="rounded-2xl bg-teal-50 p-4 text-sm text-teal-900"><strong>Accepted by support</strong><p className="mt-2">{record.finalTeam} · {new Date(record.reviewedAt).toLocaleString()}</p>{record.notes&&<p className="mt-2">{record.notes}</p>}</section> : record.state === 'review' ? <section className="rounded-2xl border border-amber-200 bg-amber-50 p-4"><h3 className="text-sm font-bold">Waiting for support approval</h3><p className="mt-2 text-xs text-amber-900">A support team member must review and accept this ticket.</p><button className="btn-secondary mt-3" onClick={onOpenSupport}>Open support sign-in</button></section> : <p className="text-xs text-slate-500">Routed automatically. Support can review this ticket if needed.</p>}
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
