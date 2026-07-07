import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import type { CountryScan, JurisdictionRegion } from "../types";
import { Spinner, StatCard } from "../components";
import { WorldMap, type MapMarker } from "../WorldMap";

const TIMEFRAMES = [
  { d: 1, label: "Last 24 hours" },
  { d: 7, label: "Last 7 days" },
  { d: 30, label: "Last 30 days" },
  { d: 90, label: "Last 90 days" },
];
const KEY_MARKETS = ["us", "eu", "uk", "japan", "china", "australia"];

export default function Monitoring() {
  const [regions, setRegions] = useState<JurisdictionRegion[] | null>(null);
  const [sel, setSel] = useState<Set<string>>(new Set(["us", "eu", "uk"]));
  const [days, setDays] = useState(90);
  const [productCode, setProductCode] = useState("");
  const [indication, setIndication] = useState("");
  const [advanced, setAdvanced] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [result, setResult] = useState<CountryScan | null>(null);

  useEffect(() => { api.jurisdictions().then((r) => setRegions(r.regions)).catch(() => {}); }, []);

  const toggle = (k: string) => setSel((p) => {
    const n = new Set(p); n.has(k) ? n.delete(k) : n.add(k); return n;
  });
  const toggleRegion = (r: JurisdictionRegion) => setSel((p) => {
    const n = new Set(p);
    const keys = r.jurisdictions.map((j) => j.key);
    const allOn = keys.every((k) => n.has(k));
    keys.forEach((k) => (allOn ? n.delete(k) : n.add(k)));
    return n;
  });

  const allJur = useMemo(() => (regions ?? []).flatMap((r) => r.jurisdictions), [regions]);

  const dash = useMemo(() => {
    if (!result) return null;
    const covered = new Map(result.countries.map((c) => [c.key, c.updates.length]));
    const markers: MapMarker[] = result.jurisdictions.map((k) => {
      const j = allJur.find((x) => x.key === k);
      const count = covered.get(k) ?? 0;
      return { key: k, country: j?.country ?? k, lat: j?.lat ?? 0, lon: j?.lon ?? 0,
        region: j?.region ?? "", covered: count > 0, count };
    }).filter((m) => m.lat || m.lon);
    const activeRegions = new Set(result.countries.map((c) => c.region));
    const totalUpdates = result.countries.reduce((a, c) => a + c.updates.length, 0);
    const withData = result.countries.filter((c) => c.updates.length > 0).length;
    return { markers, activeRegions, totalUpdates, withData };
  }, [result, allJur]);

  const scan = async () => {
    if (sel.size === 0) return;
    setScanning(true); setResult(null);
    try {
      setResult(await api.countryScan({
        jurisdictions: [...sel], days, product_code: productCode, indication,
      }));
    } finally { setScanning(false); }
  };

  return (
    <>
      <div className="page-head">
        <h2>Global Monitoring</h2>
        <p>Cover the jurisdictions that matter to your business. Pick markets and a timeframe, then Scan for country-level regulatory summaries with source links.</p>
      </div>

      {/* ---- Scan builder ---- */}
      <div className="card" style={{ marginBottom: 18, borderColor: "rgba(242,120,60,.35)" }}>
        <h3 style={{ marginBottom: 10 }}>1 · Choose jurisdictions</h3>
        <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
          <button className="btn ghost" onClick={() => setSel(new Set(KEY_MARKETS))}>Key markets</button>
          <button className="btn ghost" onClick={() => setSel(new Set(regions?.flatMap((r) => r.jurisdictions.map((j) => j.key)) ?? []))}>Select all</button>
          <button className="btn ghost" onClick={() => setSel(new Set())}>Clear</button>
          <span className="muted" style={{ alignSelf: "center", fontSize: 12.5 }}>{sel.size} selected</span>
        </div>

        {!regions ? <Spinner /> : (
          <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))" }}>
            {regions.map((r) => {
              const keys = r.jurisdictions.map((j) => j.key);
              const allOn = keys.every((k) => sel.has(k));
              return (
                <div key={r.region} style={{ border: "1px solid var(--border)", borderRadius: 10, padding: 12 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                    <strong style={{ fontSize: 12.5, textTransform: "uppercase", letterSpacing: ".05em", color: "var(--ink-2)" }}>{r.region}</strong>
                    <span className="kbtn" onClick={() => toggleRegion(r)} style={{ cursor: "pointer" }}>{allOn ? "none" : "all"}</span>
                  </div>
                  {r.jurisdictions.map((j) => (
                    <label key={j.key} style={{ display: "flex", gap: 8, alignItems: "center", padding: "3px 0", cursor: "pointer", fontSize: 13 }}>
                      <input type="checkbox" checked={sel.has(j.key)} onChange={() => toggle(j.key)} />
                      <span>{j.country} <span className="muted">· {j.abbrev}</span></span>
                    </label>
                  ))}
                </div>
              );
            })}
          </div>
        )}

        <h3 style={{ margin: "18px 0 10px" }}>2 · Timeframe</h3>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {TIMEFRAMES.map((t) => (
            <button key={t.d} className={"btn " + (days === t.d ? "" : "ghost")} onClick={() => setDays(t.d)}>{t.label}</button>
          ))}
        </div>

        <div style={{ marginTop: 16 }}>
          <span className="back" onClick={() => setAdvanced(!advanced)}>{advanced ? "▾" : "▸"} Advanced filter — device product code / indication</span>
          {advanced && (
            <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
              <input type="text" placeholder="FDA product code (e.g. DXY)" value={productCode}
                onChange={(e) => setProductCode(e.target.value)} style={{ minWidth: 200 }} />
              <input type="text" placeholder="Indication for use (e.g. coronary stent)" value={indication}
                onChange={(e) => setIndication(e.target.value)} style={{ minWidth: 280 }} />
              <span className="muted" style={{ alignSelf: "center", fontSize: 12 }}>Re-scan filters to only relevant updates</span>
            </div>
          )}
        </div>

        <div style={{ marginTop: 18 }}>
          <button className="btn" onClick={scan} disabled={scanning || sel.size === 0} style={{ fontSize: 14, padding: "10px 22px" }}>
            {scanning ? <><span className="spinner" /> Scanning {sel.size} jurisdiction{sel.size !== 1 ? "s" : ""}…</> : `⌖ Scan ${sel.size || ""} jurisdiction${sel.size !== 1 ? "s" : ""}`}
          </button>
        </div>
      </div>

      {/* ---- Dashboard results ---- */}
      {result && dash && (
        <div style={{ marginBottom: 18 }}>
          <div className="muted" style={{ marginBottom: 12, fontSize: 12.5 }}>
            Scanned {result.countries.length} jurisdiction{result.countries.length !== 1 ? "s" : ""} · last {result.timeframe_days} days
            {result.filters.product_code && ` · code "${result.filters.product_code}"`}
            {result.filters.indication && ` · "${result.filters.indication}"`}
            {!result.ai_enabled && " · rule-based (add API key for live AI web-scan)"}
          </div>

          <div className="grid cols-3" style={{ marginBottom: 16 }}>
            <StatCard value={result.countries.length} label="Jurisdictions scanned" icon="🌐" />
            <StatCard value={dash.withData} label="With activity" icon="◉" sub={`of ${result.countries.length} in scope`} />
            <StatCard value={dash.totalUpdates} label="Regulatory updates" icon="📡" />
          </div>

          {/* Coverage world map */}
          <div className="card" style={{ marginBottom: 16 }}>
            <h3 style={{ marginBottom: 6 }}>Coverage map</h3>
            <WorldMap markers={dash.markers} activeRegions={dash.activeRegions} />
            <div style={{ display: "flex", gap: 18, marginTop: 8, fontSize: 12, color: "var(--ink-3)" }}>
              <span><span style={{ display: "inline-block", width: 9, height: 9, borderRadius: 9, background: "linear-gradient(135deg,#f7b34a,#e5484d)", marginRight: 6 }} /> Active (has updates)</span>
              <span><span style={{ display: "inline-block", width: 9, height: 9, borderRadius: 9, border: "1.5px solid rgba(242,120,60,.85)", marginRight: 6 }} /> In scope</span>
            </div>
          </div>

          <div className="section-title">Country-level summaries</div>
          <div className="grid cols-2">
          {result.countries.map((c) => (
            <div key={c.key} className="card" style={{ marginBottom: 0 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
                <div>
                  <strong style={{ fontSize: 15.5 }}>{c.country}</strong>
                  <span className="tag" style={{ marginLeft: 8 }}>{c.region}</span>
                  {c.ai && <span className="tag brand">AI web-scan</span>}
                  <div className="muted" style={{ fontSize: 12.5, marginTop: 2 }}>{c.regulator} ({c.abbrev})</div>
                </div>
                <a className="btn ghost" href={c.source_url} target="_blank" rel="noreferrer">Official source ↗</a>
              </div>

              <p style={{ fontSize: 13.5, marginTop: 12, marginBottom: 6, whiteSpace: "pre-wrap" }}>{c.summary}</p>

              {c.sources.length > 0 && (
                <div style={{ marginTop: 6 }}>
                  <div className="muted" style={{ fontSize: 11.5, fontWeight: 700, textTransform: "uppercase", letterSpacing: ".05em" }}>Cited sources</div>
                  {c.sources.map((s, i) => (
                    <a key={i} className="source-chip" href={s.url} target="_blank" rel="noreferrer" style={{ marginRight: 8, marginTop: 6 }}>
                      <span className="n">↗</span> <span style={{ fontSize: 12.5 }}>{s.title}</span>
                    </a>
                  ))}
                </div>
              )}

              {c.updates.length > 0 && (
                <div style={{ marginTop: 10 }}>
                  <div className="muted" style={{ fontSize: 11.5, fontWeight: 700, textTransform: "uppercase", letterSpacing: ".05em", marginBottom: 4 }}>Monitored updates ({c.updates.length})</div>
                  {c.updates.map((u, i) => (
                    <div key={i} style={{ fontSize: 12.5, marginBottom: 3 }}>
                      • {u.url ? <a href={u.url} target="_blank" rel="noreferrer" style={{ color: "var(--brand)" }}>{u.title}</a> : u.title}
                      <span className="muted"> — {u.published?.slice(0, 10)}</span>
                    </div>
                  ))}
                </div>
              )}

            </div>
          ))}
          </div>
        </div>
      )}
    </>
  );
}
