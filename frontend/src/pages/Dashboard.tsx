import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Bar, BarChart, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { api } from "../api";
import type { Dashboard as Dash, Stats } from "../types";
import { RiskBadge, Spinner, StatCard } from "../components";

const RISK_COLORS: Record<string, string> = {
  Critical: "#dc2626", High: "#ea580c", Medium: "#ca8a04", Low: "#16a34a",
};
const BAR = "#6366f1";

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [dash, setDash] = useState<Dash | null>(null);
  const nav = useNavigate();

  useEffect(() => {
    api.stats().then(setStats).catch(() => {});
    api.dashboard().then(setDash).catch(() => {});
  }, []);

  if (!stats || !dash) return <Spinner label="Loading intelligence…" />;

  const interpretedPct = stats.documents
    ? Math.round((stats.interpreted / stats.documents) * 100) : 0;

  return (
    <>
      <div className="page-head">
        <h2>Regulatory Intelligence Dashboard</h2>
        <p>AI-interpreted view across your global medical-device regulatory corpus.</p>
      </div>

      {stats.interpreted === 0 && (
        <div className="banner">
          <strong>NLP interpretation not yet run.</strong> Risk levels, requirements and
          obligations appear once you add an <code>ANTHROPIC_API_KEY</code> and run{" "}
          <code>python -m scripts.interpret_corpus</code>. Search and browse work now.
        </div>
      )}

      <div className="grid cols-4" style={{ marginBottom: 16 }}>
        <StatCard value={stats.documents} label="Documents indexed" icon="▦"
          sub={`${stats.total_pages.toLocaleString()} pages · ${stats.authorities} authorities`} />
        <StatCard value={`${interpretedPct}%`} label="AI-interpreted" icon="✦"
          sub={`${stats.interpreted} of ${stats.documents} documents`} />
        <StatCard value={stats.obligations} label="Obligations extracted" icon="§"
          sub={`${stats.requirements} key requirements`} />
        <StatCard value={stats.scanned_needs_ocr} label="Need OCR / refetch" icon="⚠"
          sub="scanned or non-text files" />
      </div>

      <div className="grid cols-2" style={{ marginBottom: 16 }}>
        <div className="card">
          <h3>Documents by authority</h3>
          <div className="chart-wrap">
            <ResponsiveContainer>
              <BarChart data={dash.by_authority} layout="vertical"
                margin={{ left: 20, right: 20 }}>
                <XAxis type="number" hide />
                <YAxis type="category" dataKey="label" width={130}
                  tick={{ fontSize: 12 }} />
                <Tooltip cursor={{ fill: "#f1f3f6" }} />
                <Bar dataKey="count" fill={BAR} radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card">
          <h3>Risk distribution</h3>
          {dash.by_risk.length === 0 ? (
            <div className="center-empty">No interpretations yet.</div>
          ) : (
            <div className="chart-wrap">
              <ResponsiveContainer>
                <PieChart>
                  <Pie data={dash.by_risk} dataKey="count" nameKey="label"
                    innerRadius={55} outerRadius={95} paddingAngle={2}>
                    {dash.by_risk.map((d) => (
                      <Cell key={d.label} fill={RISK_COLORS[d.label] ?? BAR} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
          <div style={{ display: "flex", gap: 14, flexWrap: "wrap", justifyContent: "center" }}>
            {dash.by_risk.map((d) => (
              <span key={d.label} className={`pill risk-${d.label}`}>
                <span className={`dot dot-${d.label}`} /> {d.label}: {d.count}
              </span>
            ))}
          </div>
        </div>
      </div>

      <div className="grid cols-2" style={{ marginBottom: 16 }}>
        <div className="card">
          <h3>Top regulatory areas</h3>
          {dash.by_area.length === 0 ? <div className="center-empty">—</div> : (
            <div className="chart-wrap">
              <ResponsiveContainer>
                <BarChart data={dash.by_area} margin={{ bottom: 60 }}>
                  <XAxis dataKey="label" angle={-35} textAnchor="end"
                    interval={0} tick={{ fontSize: 11 }} height={70} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                  <Tooltip cursor={{ fill: "#f1f3f6" }} />
                  <Bar dataKey="count" fill="#22d3ee" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
        <div className="card">
          <h3>Obligations by responsible actor</h3>
          {dash.by_actor.length === 0 ? <div className="center-empty">—</div> : (
            <div className="chart-wrap">
              <ResponsiveContainer>
                <BarChart data={dash.by_actor} layout="vertical" margin={{ left: 30, right: 20 }}>
                  <XAxis type="number" hide />
                  <YAxis type="category" dataKey="label" width={140} tick={{ fontSize: 11 }} />
                  <Tooltip cursor={{ fill: "#f1f3f6" }} />
                  <Bar dataKey="count" fill="#818cf8" radius={[0, 6, 6, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>

      <div className="grid cols-2">
        <div className="card">
          <h3>Highest-risk documents</h3>
          {dash.top_risk_documents.length === 0 ? (
            <div className="center-empty">Run interpretation to populate.</div>
          ) : dash.top_risk_documents.map((d) => (
            <div key={d.id} className="doc-row" onClick={() => nav(`/documents/${d.id}`)}>
              <div className="row-top">
                <span className="title">{d.title}</span>
                <RiskBadge level={d.risk_level} />
              </div>
              <div className="meta">{d.authority} · {d.region} · urgency {d.urgency}</div>
              {d.business_impact && <div className="summary">{d.business_impact}</div>}
            </div>
          ))}
        </div>
        <div className="card">
          <h3>Critical & high obligations</h3>
          {dash.critical_obligations.length === 0 ? (
            <div className="center-empty">Run interpretation to populate.</div>
          ) : dash.critical_obligations.map((o, i) => (
            <div key={i} className={`obl-item risk-b-${o.risk}`}
              onClick={() => nav(`/documents/${o.document_id}`)} style={{ cursor: "pointer" }}>
              <div><span className="actor">{o.actor}</span> — {o.text}</div>
              <div className="meta muted" style={{ marginTop: 4 }}>
                {o.title} · {o.authority} <RiskBadge level={o.risk} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
