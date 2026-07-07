import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import type { DocumentDetail as Doc } from "../types";
import { RiskBadge, Spinner, Tags } from "../components";

export default function DocumentDetail() {
  const { id } = useParams();
  const [doc, setDoc] = useState<Doc | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [interpreting, setInterpreting] = useState(false);
  const [claudeOn, setClaudeOn] = useState(false);
  const nav = useNavigate();

  const load = () => api.document(Number(id)).then(setDoc).catch((e) => setErr(String(e)));
  useEffect(() => { load(); api.health().then((h) => setClaudeOn(h.claude_enabled)); }, [id]);

  const runInterpret = async () => {
    setInterpreting(true);
    try { await api.interpret(Number(id)); await load(); }
    catch (e) { setErr(String(e)); }
    finally { setInterpreting(false); }
  };

  if (err) return <div className="banner">{err}</div>;
  if (!doc) return <Spinner />;
  const it = doc.interpretation;

  return (
    <>
      <span className="back" onClick={() => nav(-1)}>← Back</span>
      <div className="detail-head">
        <div className="kv" style={{ marginBottom: 6 }}>
          <span className="tag brand">{doc.authority}</span>
          <span className="tag">{doc.region}</span>
          <span className="tag">{doc.category}</span>
          <RiskBadge level={it?.risk_level} />
        </div>
        <h2>{doc.title}</h2>
        <div className="kv">
          <span>{doc.page_count} pages</span>
          <span>{doc.char_count.toLocaleString()} characters</span>
          <span className="muted">{doc.rel_path}</span>
        </div>
      </div>

      {!it && (
        <div className="banner" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span>
            {doc.is_scanned
              ? "This document has no extractable text (scanned or non-PDF). It needs OCR before interpretation."
              : "This document has not been AI-interpreted yet."}
          </span>
          {!doc.is_scanned && claudeOn && (
            <button className="btn" disabled={interpreting} onClick={runInterpret}>
              {interpreting ? <><span className="spinner" /> Interpreting…</> : "Interpret with Claude"}
            </button>
          )}
        </div>
      )}

      {it && (
        <>
          <div className="card" style={{ marginBottom: 16 }}>
            <h3>AI Summary</h3>
            <p style={{ margin: 0, fontSize: 15, lineHeight: 1.6 }}>{it.summary}</p>
            <div style={{ marginTop: 14 }}>
              <Tags items={it.regulatory_areas} brand />
              {it.device_types.length > 0 && <Tags items={it.device_types} />}
            </div>
            <div className="kv" style={{ marginTop: 14 }}>
              <span><strong>Risk:</strong> <RiskBadge level={it.risk_level} /></span>
              <span><strong>Urgency:</strong> {it.urgency}</span>
            </div>
            <p className="muted" style={{ marginTop: 12, marginBottom: 0 }}>
              <strong style={{ color: "var(--ink)" }}>Business impact:</strong> {it.business_impact}
            </p>
          </div>

          {it.key_dates.length > 0 && (
            <div className="card" style={{ marginBottom: 16 }}>
              <h3>Key dates & deadlines</h3>
              {it.key_dates.map((d, i) => (
                <div key={i} style={{ marginBottom: 6 }}>
                  <span className="tag brand">{d.date ?? "—"}</span> {d.label}
                </div>
              ))}
            </div>
          )}

          <div className="grid cols-2">
            <div>
              <div className="section-title">Key requirements ({doc.requirements.length})</div>
              {doc.requirements.map((r, i) => (
                <div key={i} className="req-item">
                  <div>{r.text}</div>
                  <div className="cite">
                    {r.area}{r.citation ? ` · ${r.citation}` : ""}
                  </div>
                </div>
              ))}
            </div>
            <div>
              <div className="section-title">Obligations ({doc.obligations.length})</div>
              {doc.obligations.map((o, i) => (
                <div key={i} className={`obl-item risk-b-${o.risk}`}>
                  <div><span className="actor">{o.actor}</span> — {o.text}</div>
                  <div className="cite" style={{ marginTop: 4 }}>
                    {o.area} <RiskBadge level={o.risk} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </>
  );
}
