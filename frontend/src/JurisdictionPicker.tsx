/** Shared jurisdiction + timeframe selector used by Global Monitoring and the
 *  Intelligent Alerts safety scan. Presentational — parent owns the state and
 *  renders its own Scan button (and any extra filters). */
import type { JurisdictionRegion } from "./types";
import { Spinner } from "./components";

const KEY_MARKETS = ["us", "eu", "uk", "japan", "china", "australia"];

export function JurisdictionPicker({
  regions, sel, setSel, days, setDays, timeframes, stepOffset = 0,
}: {
  regions: JurisdictionRegion[] | null;
  sel: Set<string>;
  setSel: (s: Set<string>) => void;
  days: number;
  setDays: (d: number) => void;
  timeframes: { d: number; label: string }[];
  stepOffset?: number;
}) {
  const toggle = (k: string) => {
    const n = new Set(sel); n.has(k) ? n.delete(k) : n.add(k); setSel(n);
  };
  const toggleRegion = (r: JurisdictionRegion) => {
    const n = new Set(sel);
    const keys = r.jurisdictions.map((j) => j.key);
    const allOn = keys.every((k) => n.has(k));
    keys.forEach((k) => (allOn ? n.delete(k) : n.add(k)));
    setSel(n);
  };

  return (
    <>
      <h3 style={{ marginBottom: 10 }}>{1 + stepOffset} · Choose jurisdictions</h3>
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

      <h3 style={{ margin: "18px 0 10px" }}>{2 + stepOffset} · Timeframe</h3>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {timeframes.map((t) => (
          <button key={t.d} className={"btn " + (days === t.d ? "" : "ghost")} onClick={() => setDays(t.d)}>{t.label}</button>
        ))}
      </div>
    </>
  );
}
