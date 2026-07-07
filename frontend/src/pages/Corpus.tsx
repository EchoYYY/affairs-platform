import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import type { DocList, Facets } from "../types";
import { RiskBadge, Spinner, Tags } from "../components";

export default function Corpus() {
  const [facets, setFacets] = useState<Facets | null>(null);
  const [data, setData] = useState<DocList | null>(null);
  const [f, setF] = useState<Record<string, string>>({});
  const [q, setQ] = useState("");
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState<string | null>(null);
  const [autoMin, setAutoMin] = useState<number | null>(null);
  const nav = useNavigate();

  const reload = () => {
    setData(null);
    api.documents({ ...f, q, limit: 200 }).then(setData).catch(() => {});
  };

  useEffect(() => { api.facets().then(setFacets).catch(() => {}); }, []);
  useEffect(reload, [f, q]);
  useEffect(() => { api.ingestStatus().then((s) => setAutoMin(s.autoingest_minutes)).catch(() => {}); }, []);

  const set = (k: string, v: string) => setF((p) => ({ ...p, [k]: v }));

  const sync = async () => {
    setSyncing(true); setSyncMsg(null);
    try {
      const r = await api.ingestRun();
      const g = r.ingest;
      setSyncMsg(g.ingested > 0
        ? `Added ${g.ingested} new document${g.ingested !== 1 ? "s" : ""} (${g.skipped} already indexed).`
        : `Up to date — no new documents (${g.skipped} already indexed).`);
      api.facets().then(setFacets).catch(() => {});
      reload();
    } catch {
      setSyncMsg("Sync failed — is the backend running?");
    } finally { setSyncing(false); }
  };

  return (
    <>
      <div className="page-head" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16 }}>
        <div>
          <h2>Regulatory Corpus</h2>
          <p>Centralized access to every ingested regulation, guidance and standard.</p>
        </div>
        <div style={{ textAlign: "right" }}>
          <button className="btn" onClick={sync} disabled={syncing}>
            {syncing ? <><span className="spinner" /> Syncing…</> : "⟳ Sync corpus"}
          </button>
          <div className="muted" style={{ fontSize: 11.5, marginTop: 6 }}>
            {autoMin ? `Auto-syncs every ${autoMin} min` : "Auto-sync off"}
          </div>
        </div>
      </div>
      {syncMsg && <div className="banner">{syncMsg}</div>}

      <div className="filters">
        <input type="search" placeholder="Filter by title…" value={q}
          onChange={(e) => setQ(e.target.value)} style={{ minWidth: 220 }} />
        <select value={f.authority ?? ""} onChange={(e) => set("authority", e.target.value)}>
          <option value="">All authorities</option>
          {facets?.authorities.map((a) => <option key={a}>{a}</option>)}
        </select>
        <select value={f.region ?? ""} onChange={(e) => set("region", e.target.value)}>
          <option value="">All regions</option>
          {facets?.regions.map((a) => <option key={a}>{a}</option>)}
        </select>
        <select value={f.risk_level ?? ""} onChange={(e) => set("risk_level", e.target.value)}>
          <option value="">Any risk</option>
          {facets?.risk_levels.map((a) => <option key={a}>{a}</option>)}
        </select>
        <select value={f.area ?? ""} onChange={(e) => set("area", e.target.value)}>
          <option value="">Any area</option>
          {facets?.regulatory_areas.map((a) => <option key={a}>{a}</option>)}
        </select>
        {(Object.values(f).some(Boolean) || q) && (
          <button className="btn ghost" onClick={() => { setF({}); setQ(""); }}>Clear</button>
        )}
      </div>

      {!data ? <Spinner /> : (
        <>
          <div className="muted" style={{ marginBottom: 12 }}>
            {data.total} document{data.total !== 1 ? "s" : ""}
          </div>
          {data.items.map((d) => (
            <div key={d.id} className="doc-row" onClick={() => nav(`/documents/${d.id}`)}>
              <div className="row-top">
                <span className="title">{d.title}</span>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  {d.is_scanned ? <span className="pill" style={{ background: "#fff7ed", color: "#ea580c" }}>Needs OCR</span> : null}
                  <RiskBadge level={d.risk_level} />
                </div>
              </div>
              <div className="meta">
                {d.authority} · {d.region} · {d.category} · {d.page_count} pp
              </div>
              {d.summary && <div className="summary">{d.summary}</div>}
              {d.regulatory_areas.length > 0 && (
                <div style={{ marginTop: 8 }}><Tags items={d.regulatory_areas} brand /></div>
              )}
            </div>
          ))}
        </>
      )}
    </>
  );
}
