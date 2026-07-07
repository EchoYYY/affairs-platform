import { useEffect, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { api } from "../api";
import type { Briefing } from "../types";
import { Spinner } from "../components";

const CONF: Record<string, string> = { High: "risk-Low", Medium: "risk-Medium", Low: "risk-High" };

export default function Insights() {
  const [b, setB] = useState<Briefing | null>(null);

  useEffect(() => { api.briefing().then(setB).catch(() => {}); }, []);
  if (!b) return <Spinner label="Analyzing regulatory horizon…" />;
  const t = b.trends;

  return (
    <>
      <div className="page-head">
        <h2>Predictive Insights</h2>
        <p>Trend analysis and a forward-looking regulatory horizon — anticipate shifts before they land.</p>
      </div>

      {!b.grounded && (
        <div className="banner">
          Heuristic outlook shown. Add <code>ANTHROPIC_API_KEY</code> for AI-generated predictions,
          and run monitoring regularly to build predictive history.
        </div>
      )}

      <div className="card" style={{ marginBottom: 16 }}>
        <h3>Regulatory horizon briefing</h3>
        <p style={{ fontSize: 15, lineHeight: 1.6, marginTop: 0 }}>{b.summary}</p>

        <div className="grid cols-2">
          <div>
            <div className="section-title" style={{ marginTop: 8 }}>Predicted shifts</div>
            {b.predicted_shifts.map((s, i) => (
              <div key={i} className="req-item">
                <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
                  <strong>{s.trend}</strong>
                  <span className={`pill ${CONF[s.confidence] ?? ""}`}>{s.confidence}</span>
                </div>
                <div className="cite">Horizon: {s.horizon}{s.rationale ? ` · ${s.rationale}` : ""}</div>
              </div>
            ))}
          </div>
          <div>
            <div className="section-title" style={{ marginTop: 8 }}>Emerging risks</div>
            {b.emerging_risks.map((r, i) => <div key={i} className="obl-item risk-b-High">{r}</div>)}
            <div className="section-title">Increasing scrutiny</div>
            <div>{b.areas_of_increasing_scrutiny.map((a, i) => <span key={i} className="tag brand">{a}</span>)}</div>
            {b.recommended_preparations && b.recommended_preparations.length > 0 && (
              <>
                <div className="section-title">Recommended preparations</div>
                {b.recommended_preparations.map((r, i) => <div key={i} className="req-item">☐ {r}</div>)}
              </>
            )}
          </div>
        </div>
      </div>

      <div className="grid cols-2">
        <div className="card">
          <h3>Monitoring volume over time</h3>
          {t && t.monitoring_by_month.length > 0 ? (
            <div className="chart-wrap">
              <ResponsiveContainer>
                <LineChart data={t.monitoring_by_month}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#eef0f3" />
                  <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Line type="monotone" dataKey="count" stroke="#4338ca" strokeWidth={2} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : <div className="center-empty">Run monitoring to build history.</div>}
        </div>
        <div className="card">
          <h3>Area momentum (from monitoring)</h3>
          {t && t.monitoring_area_momentum.length > 0 ? (
            <div className="chart-wrap">
              <ResponsiveContainer>
                <BarChart data={t.monitoring_area_momentum} layout="vertical" margin={{ left: 20 }}>
                  <XAxis type="number" hide />
                  <YAxis type="category" dataKey="label" width={120} tick={{ fontSize: 11 }} />
                  <Tooltip cursor={{ fill: "#f1f3f6" }} />
                  <Bar dataKey="count" fill="#22d3ee" radius={[0, 6, 6, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : <div className="center-empty">—</div>}
        </div>
      </div>
    </>
  );
}
