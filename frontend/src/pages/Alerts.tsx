import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import type { Alert, AlertStats, ImpactRow, JurisdictionRegion, SafetyScan } from "../types";
import { RiskBadge, Spinner, StatCard, Tags } from "../components";
import { JurisdictionPicker } from "../JurisdictionPicker";
import { WorldMap, type MapMarker } from "../WorldMap";

const SAFETY_TIMEFRAMES = [
  { d: 1, label: "Last 24 hours" },
  { d: 7, label: "Last 7 days" },
  { d: 30, label: "Last 30 days" },
  { d: 90, label: "Last 90 days" },
];

const IMPACT_CLASS: Record<string, string> = {
  High: "risk-High", Medium: "risk-Medium", Low: "risk-Low", None: "risk-b-Low",
};

function AlertCard({ a, onStatus }: { a: Alert; onStatus: (s: string) => void }) {
  const [open, setOpen] = useState(false);
  const [impact, setImpact] = useState<ImpactRow[] | null>(null);
  const [assessing, setAssessing] = useState(false);

  const loadImpact = async () => {
    setOpen(!open);
    if (!open && impact === null) setImpact(await api.impact(a.update_id));
  };
  const runAssess = async () => {
    setAssessing(true);
    try { setImpact(await api.assess(a.update_id)); }
    finally { setAssessing(false); }
  };

  return (
    <div className="doc-row" style={{ opacity: a.status === "dismissed" ? 0.55 : 1 }}>
      <div className="row-top">
        <span className="title">{a.title}</span>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <span className="tag brand">{Math.round(a.relevance * 100)}% rel</span>
          <RiskBadge level={a.risk} />
        </div>
      </div>
      <div className="meta">
        {a.authority} · {a.region} · {a.published?.slice(0, 10) || "—"} ·
        urgency {a.urgency} · scored by {a.scored_by}
        {a.status !== "new" && <span className="tag" style={{ marginLeft: 8 }}>{a.status}</span>}
      </div>
      {a.business_impact && <div className="summary">{a.business_impact}</div>}
      {a.areas.length > 0 && <div style={{ marginTop: 6 }}><Tags items={a.areas} brand /></div>}
      {a.matched_products.length > 0 && (
        <div style={{ marginTop: 4 }}><span className="muted" style={{ fontSize: 12 }}>Affects: </span><Tags items={a.matched_products} /></div>
      )}

      <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
        <button className="btn ghost" onClick={loadImpact}>{open ? "Hide" : "Impact assessment"}</button>
        {a.url && <a className="btn ghost" href={a.url} target="_blank" rel="noreferrer">Open source ↗</a>}
        {a.status !== "read" && <button className="btn ghost" onClick={() => onStatus("read")}>Mark read</button>}
        {a.status !== "dismissed" && <button className="btn ghost" onClick={() => onStatus("dismissed")}>Dismiss</button>}
      </div>

      {open && (
        <div style={{ marginTop: 12, borderTop: "1px solid var(--border)", paddingTop: 12 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <strong>Product impact</strong>
            <button className="btn" disabled={assessing} onClick={runAssess}>
              {assessing ? <><span className="spinner" /> Assessing…</> : "Re-assess"}
            </button>
          </div>
          {impact === null ? <Spinner /> : impact.length === 0 ? (
            <div className="muted" style={{ marginTop: 8 }}>No assessment yet — click Re-assess.</div>
          ) : impact.map((i) => (
            <div key={i.id} className={`obl-item risk-b-${i.impact_level}`} style={{ marginTop: 8 }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span className="actor">{i.product_name}</span>
                <span className={`pill ${IMPACT_CLASS[i.impact_level] ?? ""}`}>{i.impact_level} impact</span>
              </div>
              {i.affected_areas.length > 0 && <div style={{ marginTop: 6 }}><Tags items={i.affected_areas} /></div>}
              {i.required_actions.map((act, k) => (
                <div key={k} className="cite" style={{ marginTop: 4 }}>
                  ☐ {act.action} — <strong>{act.owner}</strong> ({act.priority})
                </div>
              ))}
              <div className="cite muted" style={{ marginTop: 4 }}>{i.rationale}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Alerts() {
  const [stats, setStats] = useState<AlertStats | null>(null);
  const [alerts, setAlerts] = useState<Alert[] | null>(null);
  const [f, setF] = useState<Record<string, string>>({ status: "new" });

  // safety-information scan
  const [regions, setRegions] = useState<JurisdictionRegion[] | null>(null);
  const [sel, setSel] = useState<Set<string>>(new Set(["us", "uk", "eu", "imdrf"]));
  const [days, setDays] = useState(30);
  const [scanning, setScanning] = useState(false);
  const [safety, setSafety] = useState<SafetyScan | null>(null);

  const load = () => {
    api.alertStats().then(setStats).catch(() => {});
    setAlerts(null);
    api.alerts({ ...f, limit: 200 }).then(setAlerts).catch(() => {});
  };
  useEffect(load, [f]);
  useEffect(() => { api.jurisdictions().then((r) => setRegions(r.regions)).catch(() => {}); }, []);

  const setStatus = async (a: Alert, status: string) => {
    await api.setAlertStatus(a.id, status);
    load();
  };
  const set = (k: string, v: string) => setF((p) => ({ ...p, [k]: v }));

  const allJur = useMemo(() => (regions ?? []).flatMap((r) => r.jurisdictions), [regions]);
  const markers: MapMarker[] = useMemo(() => {
    if (!safety) return [];
    return safety.countries.map((c) => {
      const j = allJur.find((x) => x.key === c.key);
      return { key: c.key, country: c.country, lat: j?.lat ?? 0, lon: j?.lon ?? 0,
        region: c.region, covered: c.count > 0, count: c.count };
    }).filter((m) => m.lat || m.lon);
  }, [safety, allJur]);

  const runSafety = async () => {
    if (sel.size === 0) return;
    setScanning(true); setSafety(null);
    try { setSafety(await api.safetyScan([...sel], days)); }
    finally { setScanning(false); }
  };

  return (
    <>
      <div className="page-head">
        <h2>Intelligent Alerts</h2>
        <p>Scan medical-device safety information across jurisdictions, and triage monitored changes against your profile.</p>
      </div>

      {/* ---- Safety Information Scan ---- */}
      <div className="card" style={{ marginBottom: 18, borderColor: "rgba(242,120,60,.35)" }}>
        <h3 style={{ margin: "0 0 4px" }}>🛡 Safety Information Scan</h3>
        <p className="muted" style={{ fontSize: 12.5, marginTop: 0 }}>
          Recalls, field-safety notices and early alerts from FDA, MHRA and IMDRF's cross-jurisdiction
          gateway. Pick jurisdictions and a timeframe, then Scan — results link straight to the source.
        </p>
        <JurisdictionPicker regions={regions} sel={sel} setSel={setSel} days={days} setDays={setDays} timeframes={SAFETY_TIMEFRAMES} />
        <div style={{ marginTop: 16 }}>
          <button className="btn" onClick={runSafety} disabled={scanning || sel.size === 0} style={{ fontSize: 14, padding: "10px 22px" }}>
            {scanning ? <><span className="spinner" /> Scanning…</> : `⌖ Scan safety information (${sel.size})`}
          </button>
        </div>
      </div>

      {safety && (
        <div style={{ marginBottom: 22 }}>
          <div className="grid cols-3" style={{ marginBottom: 16 }}>
            <StatCard value={safety.countries.length} label="Jurisdictions scanned" icon="🌐" />
            <StatCard value={safety.countries.filter((c) => c.count > 0).length} label="With safety signals" icon="🛡" />
            <StatCard value={safety.total_alerts} label="Safety alerts" icon="⚠" sub={`last ${safety.timeframe_days} days`} />
          </div>
          <div className="card" style={{ marginBottom: 16 }}>
            <h3 style={{ marginBottom: 6 }}>Coverage map</h3>
            <WorldMap markers={markers} />
            <div style={{ display: "flex", gap: 18, marginTop: 8, fontSize: 12, color: "var(--ink-3)" }}>
              <span><span style={{ display: "inline-block", width: 9, height: 9, borderRadius: 9, background: "linear-gradient(135deg,#f7b34a,#e5484d)", marginRight: 6 }} /> Safety signals</span>
              <span><span style={{ display: "inline-block", width: 9, height: 9, borderRadius: 9, border: "1.5px solid rgba(242,120,60,.85)", marginRight: 6 }} /> In scope</span>
            </div>
          </div>

          <div className="section-title">Safety summary by jurisdiction</div>
          <div className="grid cols-2">
            {safety.countries.map((c) => (
              <div key={c.key} className="card" style={{ marginBottom: 0 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 10 }}>
                  <div>
                    <strong style={{ fontSize: 15 }}>{c.country}</strong>
                    <span className="tag" style={{ marginLeft: 8 }}>{c.region}</span>
                    <div className="muted" style={{ fontSize: 12, marginTop: 2 }}>{c.regulator} ({c.abbrev})</div>
                  </div>
                  <a className="btn ghost" href={c.safety_url} target="_blank" rel="noreferrer">Safety page ↗</a>
                </div>
                <div style={{ fontSize: 13, marginTop: 10 }}>
                  {c.count > 0
                    ? <><strong>{c.count}</strong> safety alert{c.count !== 1 ? "s" : ""} in the last {safety.timeframe_days} days</>
                    : <span className="muted">No safety alerts captured in this window — see the official safety page.</span>}
                </div>
                {c.alerts.length > 0 && (
                  <div style={{ marginTop: 8 }}>
                    {c.alerts.slice(0, 12).map((a, i) => (
                      <div key={i} style={{ fontSize: 12.5, marginBottom: 3 }}>
                        • <a href={a.url} target="_blank" rel="noreferrer" style={{ color: "var(--brand)" }}>{a.title}</a>
                        {a.date && <span className="muted"> — {a.date}</span>}
                      </div>
                    ))}
                    {c.count > 12 && <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>+ {c.count - 12} more on the official page</div>}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="section-title">Alert triage</div>
      {stats && (
        <div className="grid cols-4" style={{ marginBottom: 18 }}>
          <StatCard value={stats.total} label="Total alerts" icon="✦" />
          <StatCard value={stats.new} label="New / unread" icon="●" />
          <StatCard value={stats.high_or_critical} label="High or critical risk" icon="⚠" />
          <StatCard value={Object.keys(stats.by_risk).length} label="Risk levels present"
            sub={Object.entries(stats.by_risk).map(([k, v]) => `${k}: ${v}`).join("  ")} />
        </div>
      )}

      <div className="filters">
        <select value={f.status ?? ""} onChange={(e) => set("status", e.target.value)}>
          <option value="">All statuses</option>
          <option value="new">New</option>
          <option value="read">Read</option>
          <option value="dismissed">Dismissed</option>
        </select>
        <select value={f.risk ?? ""} onChange={(e) => set("risk", e.target.value)}>
          <option value="">Any risk</option>
          {["Critical", "High", "Medium", "Low"].map((r) => <option key={r}>{r}</option>)}
        </select>
        <select value={f.min_relevance ?? ""} onChange={(e) => set("min_relevance", e.target.value)}>
          <option value="">Any relevance</option>
          <option value="0.3">≥ 30%</option>
          <option value="0.5">≥ 50%</option>
          <option value="0.7">≥ 70%</option>
        </select>
      </div>

      {!alerts ? <Spinner /> : alerts.length === 0 ? (
        <div className="center-empty">No alerts match. Run monitoring from the Monitoring page.</div>
      ) : (
        <>
          <div className="muted" style={{ marginBottom: 10 }}>{alerts.length} alerts</div>
          {alerts.map((a) => <AlertCard key={a.id} a={a} onStatus={(s) => setStatus(a, s)} />)}
        </>
      )}
    </>
  );
}
