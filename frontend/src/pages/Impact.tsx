import { useEffect, useState } from "react";
import { api } from "../api";
import type { ImpactRow, UpdateRow } from "../types";
import { RiskBadge, Spinner, Tags } from "../components";

const LVL: Record<string, string> = { High: "risk-High", Medium: "risk-Medium", Low: "risk-Low", None: "risk-b-None" };

function Row({ u }: { u: UpdateRow }) {
  const [open, setOpen] = useState(false);
  const [impact, setImpact] = useState<ImpactRow[] | null>(null);
  const [busy, setBusy] = useState(false);

  const toggle = async () => {
    setOpen(!open);
    if (!open && impact === null) setImpact(await api.impact(u.id));
  };
  const assess = async () => {
    setBusy(true);
    try { setImpact(await api.assess(u.id)); } finally { setBusy(false); }
  };

  return (
    <div className="doc-row" style={{ cursor: "default" }}>
      <div className="row-top">
        <span className="title">{u.title}</span>
        <RiskBadge level={u.risk} />
      </div>
      <div className="meta">{u.authority} · {u.region} · {u.published?.slice(0, 10) || "—"}</div>
      <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
        <button className="btn ghost" onClick={toggle}>{open ? "Hide impact" : "Product impact"}</button>
        {open && <button className="btn" disabled={busy} onClick={assess}>{busy ? <><span className="spinner" /> Assessing…</> : "Run / re-assess"}</button>}
      </div>
      {open && (
        <div style={{ marginTop: 12 }}>
          {impact === null ? <Spinner /> : impact.length === 0 ? (
            <div className="muted">No assessment yet — click Run / re-assess.</div>
          ) : impact.map((i) => (
            <div key={i.id} className={`obl-item risk-b-${i.impact_level}`} style={{ marginTop: 8 }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span className="actor">{i.product_name}</span>
                <span className={`pill ${LVL[i.impact_level] ?? ""}`}>{i.impact_level} impact</span>
              </div>
              {i.affected_areas.length > 0 && <div style={{ marginTop: 6 }}><Tags items={i.affected_areas} /></div>}
              {i.required_actions.map((a, k) => (
                <div key={k} className="cite" style={{ marginTop: 4 }}>☐ {a.action} — <strong>{a.owner}</strong> ({a.priority})</div>
              ))}
              <div className="cite muted" style={{ marginTop: 4 }}>{i.rationale}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Impact() {
  const [updates, setUpdates] = useState<UpdateRow[] | null>(null);
  useEffect(() => { api.updates(60).then(setUpdates).catch(() => {}); }, []);

  return (
    <>
      <div className="page-head">
        <h2>Automated Impact Assessment</h2>
        <p>Map monitored regulatory changes onto your product portfolio, with required actions and owners.</p>
      </div>
      {!updates ? <Spinner /> : updates.length === 0 ? (
        <div className="center-empty">No monitored updates yet. Run monitoring first.</div>
      ) : (
        <>
          <div className="muted" style={{ marginBottom: 10 }}>{updates.length} monitored updates</div>
          {updates.map((u) => <Row key={u.id} u={u} />)}
        </>
      )}
    </>
  );
}
