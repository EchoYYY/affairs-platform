import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import type { HowToBlock, Market, RegFacets } from "../types";
import { Spinner } from "../components";
import { RegMap } from "../RegMap";

export default function KnowledgeHub() {
  const [markets, setMarkets] = useState<Market[] | null>(null);
  const [facets, setFacets] = useState<RegFacets | null>(null);
  const [time, setTime] = useState("");   // time bucket key
  const [cost, setCost] = useState("");   // cost bucket key
  const [selected, setSelected] = useState<string>(
    () => new URLSearchParams(window.location.search).get("country") ?? "",
  );

  useEffect(() => {
    api.registration().then((d) => { setMarkets(d.markets); setFacets(d.facets); }).catch(() => {});
  }, []);

  const maxMonths = useMemo(
    () => facets?.time_buckets.find((b) => b.key === time)?.max_months ?? null,
    [facets, time],
  );
  const maxUsd = useMemo(
    () => facets?.cost_buckets.find((b) => b.key === cost)?.max_usd ?? null,
    [facets, cost],
  );

  // set of countries passing the active filters (null when no filter is set)
  const qualifies = useMemo(() => {
    if (!markets || (maxMonths == null && maxUsd == null)) return null;
    const s = new Set<string>();
    for (const m of markets) {
      if (maxMonths != null && (!m.fastest || m.fastest.low_m > maxMonths + 1e-6)) continue;
      if (maxUsd != null && (!m.cheapest || m.cheapest.usd_num > maxUsd + 1e-6)) continue;
      s.add(m.country);
    }
    return s;
  }, [markets, maxMonths, maxUsd]);

  const countryList = useMemo(() => {
    if (!markets) return [];
    return [...markets]
      .filter((m) => qualifies === null || qualifies.has(m.country))
      .sort((a, b) => a.country.localeCompare(b.country));
  }, [markets, qualifies]);

  const detail = selected ? markets?.find((m) => m.country === selected) ?? null : null;
  const nMatch = qualifies ? qualifies.size : markets?.length ?? 0;

  return (
    <>
      <div className="page-head">
        <h2>Regulatory Knowledge Hub</h2>
        <p>Pick a market — from the list or the map — to see its registration timelines and government fees across {markets?.length ?? "…"} countries.</p>
      </div>

      {/* selectors: country + the two optional highlight filters */}
      <div className="filters" style={{ alignItems: "flex-end" }}>
        <label className="fld">
          <span className="fld-lbl">🌐 Country</span>
          <select value={selected} onChange={(e) => setSelected(e.target.value)} style={{ minWidth: 220 }}>
            <option value="">Select a country…</option>
            {countryList.map((m) => <option key={m.country} value={m.country}>{m.country}</option>)}
          </select>
        </label>
        <label className="fld">
          <span className="fld-lbl">⏱ Time to approval</span>
          <select value={time} onChange={(e) => setTime(e.target.value)}>
            <option value="">Any timeline</option>
            {facets?.time_buckets.map((b) => <option key={b.key} value={b.key}>{b.label}</option>)}
          </select>
        </label>
        <label className="fld">
          <span className="fld-lbl">💰 Government fee</span>
          <select value={cost} onChange={(e) => setCost(e.target.value)}>
            <option value="">Any cost</option>
            {facets?.cost_buckets.map((b) => <option key={b.key} value={b.key}>{b.label}</option>)}
          </select>
        </label>
        {(time || cost) && (
          <button className="btn ghost" onClick={() => { setTime(""); setCost(""); }}>Clear filters</button>
        )}
      </div>

      {!markets ? <Spinner /> : detail ? (
        <CountryDetail m={detail} onBack={() => setSelected("")} />
      ) : (
        <div className="card">
          <div className="muted" style={{ fontSize: 12.5, marginBottom: 8 }}>
            {time || cost
              ? <><strong style={{ color: "var(--brand)" }}>{nMatch}</strong> of {markets.length} markets match your filters — highlighted below. Click one to open it.</>
              : <>Click any highlighted country to see its timelines and fees.</>}
          </div>
          <RegMap markets={markets} selected={selected} qualifies={qualifies} onSelect={setSelected} />
        </div>
      )}
    </>
  );
}

/* ---------------- single-country detail ---------------- */
function CountryDetail({ m, onBack }: { m: Market; onBack: () => void }) {
  const p = m.profile;
  return (
    <>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
        <div>
          <button className="btn ghost" onClick={onBack} style={{ marginBottom: 8 }}>← All markets</button>
          <h3 style={{ margin: 0 }}>{p?.title ?? m.country} <span className="tag" style={{ marginLeft: 6 }}>{m.region}</span></h3>
        </div>
      </div>

      {/* profile: description + key market numbers */}
      {p && (
        <>
          {p.description.map((para, i) => (
            <p key={i} className="muted" style={{ fontSize: 14, lineHeight: 1.6, margin: "0 0 10px", maxWidth: 900 }}>{para}</p>
          ))}
          {p.key_numbers.length > 0 && (
            <div className="stat-grid" style={{ margin: "16px 0 22px" }}>
              {p.key_numbers.map((k, i) => (
                <div key={i} className="stat-card">
                  <div className="stat-val">{k.value}</div>
                  <div className="stat-lbl">{k.metric}</div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* metrics */}
      <div className="grid cols-2" style={{ marginBottom: 18 }}>
        <div className="card" style={{ background: "var(--surface-2)" }}>
          <div className="muted" style={{ fontSize: 11.5 }}>⏱ FASTEST PATHWAY</div>
          <div style={{ fontSize: 18, fontWeight: 700, color: "#fff", marginTop: 2 }}>{m.fastest?.display ?? "—"}</div>
          <div className="muted" style={{ fontSize: 12.5 }}>{m.fastest?.class_pathway ?? ""}</div>
        </div>
        <div className="card" style={{ background: "var(--surface-2)" }}>
          <div className="muted" style={{ fontSize: 11.5 }}>💰 LOWEST GOV. FEE</div>
          <div style={{ fontSize: 18, fontWeight: 700, color: m.cheapest?.usd_num === 0 ? "var(--ok,#34d399)" : "#fff", marginTop: 2 }}>{m.cheapest?.usd_str ?? "—"}</div>
          <div className="muted" style={{ fontSize: 12.5 }}>{m.cheapest?.item ?? ""}</div>
        </div>
      </div>

      {/* timelines */}
      <div className="card" style={{ overflowX: "auto", marginBottom: 18 }}>
        <div className="section-title" style={{ marginBottom: 8 }}>Registration timelines</div>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ textAlign: "left", color: "var(--ink-2)", fontSize: 11.5, textTransform: "uppercase", letterSpacing: ".04em" }}>
              {["Device class (pathway)", "Official", "Realistic", "Accelerated", "Unlocks accelerated route"].map((h) => (
                <th key={h} style={{ padding: "8px 10px", borderBottom: "1px solid var(--border)" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {m.timelines.map((t, i) => (
              <tr key={i} style={{ borderBottom: "1px solid var(--border-soft)" }}>
                <td style={{ padding: "9px 10px", color: "#fff" }}>{t.class_pathway}</td>
                <td style={{ padding: "9px 10px", whiteSpace: "nowrap" }}>{t.official}</td>
                <td style={{ padding: "9px 10px", whiteSpace: "nowrap", color: "#fff" }}>{t.realistic}</td>
                <td style={{ padding: "9px 10px", whiteSpace: "nowrap" }}>{t.accelerated}</td>
                <td style={{ padding: "9px 10px" }} className="muted">{t.prior_approval ?? "—"}</td>
              </tr>
            ))}
            {m.timelines.length === 0 && (
              <tr><td colSpan={5} className="muted" style={{ padding: "14px 10px" }}>No timeline data for this market.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* fees */}
      <div className="card" style={{ overflowX: "auto" }}>
        <div className="section-title" style={{ marginBottom: 8 }}>Government fees</div>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ textAlign: "left", color: "var(--ink-2)", fontSize: 11.5, textTransform: "uppercase", letterSpacing: ".04em" }}>
              {["Fee item", "Local", "USD ≈", "Notes"].map((h) => (
                <th key={h} style={{ padding: "8px 10px", borderBottom: "1px solid var(--border)" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {m.fees.map((f, i) => (
              <tr key={i} style={{ borderBottom: "1px solid var(--border-soft)" }}>
                <td style={{ padding: "9px 10px", color: "#fff" }}>
                  {f.item}
                  {!f.upfront && <span className="tag" style={{ marginLeft: 6, fontSize: 10 }}>recurring</span>}
                </td>
                <td style={{ padding: "9px 10px", whiteSpace: "nowrap" }}>{f.local}</td>
                <td style={{ padding: "9px 10px", whiteSpace: "nowrap", color: f.usd_num === 0 ? "var(--ok,#34d399)" : "#fff", fontWeight: 600 }}>{f.usd_str}</td>
                <td style={{ padding: "9px 10px" }} className="muted">{f.notes}</td>
              </tr>
            ))}
            {m.fees.length === 0 && (
              <tr><td colSpan={4} className="muted" style={{ padding: "14px 10px" }}>No fee data for this market.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* how to register (long-form profile) */}
      {p && p.how_to.length > 0 && (
        <div className="card" style={{ marginTop: 18 }}>
          <div className="section-title" style={{ marginBottom: 6 }}>{p.how_to_title}</div>
          <div className="howto">{renderHowTo(p.how_to)}</div>
          {p.source && (
            <div className="muted" style={{ fontSize: 12, marginTop: 18, borderTop: "1px solid var(--border-soft)", paddingTop: 12 }}>
              Source: <a href={p.source} target="_blank" rel="noreferrer" style={{ color: "var(--brand)" }}>{p.source}</a>
              {p.captured ? ` · captured ${p.captured}` : ""}
            </div>
          )}
        </div>
      )}
    </>
  );
}

/* linkify bare URLs inside profile text */
function linkify(text: string) {
  const parts = text.split(/(https?:\/\/[^\s]+)/g);
  return parts.map((s, i) =>
    /^https?:\/\//.test(s)
      ? <a key={i} href={s} target="_blank" rel="noreferrer" style={{ color: "var(--brand)", wordBreak: "break-all" }}>{s}</a>
      : <span key={i}>{s}</span>,
  );
}

/* render the classified How-to-Register blocks, grouping consecutive bullets */
function renderHowTo(blocks: HowToBlock[]) {
  const out: JSX.Element[] = [];
  let bullets: string[] = [];
  const flush = () => {
    if (bullets.length) {
      out.push(
        <ul key={"ul" + out.length} className="howto-ul">
          {bullets.map((b, i) => <li key={i}>{linkify(b)}</li>)}
        </ul>,
      );
      bullets = [];
    }
  };
  blocks.forEach((b, i) => {
    if (b.k === "li") { bullets.push(b.t); return; }
    flush();
    if (b.k === "h") out.push(<h5 key={i} className="howto-h">{b.t}</h5>);
    else if (b.k === "q") out.push(<h5 key={i} className="howto-q">{b.t}</h5>);
    else out.push(<p key={i} className="howto-p">{linkify(b.t)}</p>);
  });
  flush();
  return out;
}
