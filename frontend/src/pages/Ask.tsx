import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import type { AskResponse } from "../types";
import { Spinner } from "../components";

const SAMPLES = [
  "What are the clinical evaluation requirements for legacy devices under the EU MDR?",
  "What cybersecurity documentation does the FDA expect in a premarket submission?",
  "Who is responsible for post-market surveillance and what must they do?",
];

export default function Ask() {
  const [q, setQ] = useState("");
  const [res, setRes] = useState<AskResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const nav = useNavigate();

  const run = async (question?: string) => {
    const query = question ?? q;
    if (!query.trim()) return;
    setQ(query); setLoading(true); setRes(null);
    try { setRes(await api.ask(query)); }
    finally { setLoading(false); }
  };

  return (
    <>
      <div className="page-head">
        <h2>Ask the Corpus</h2>
        <p>Retrieval-augmented answers grounded in your regulatory documents, with citations.</p>
      </div>

      <div className="search-bar">
        <input type="text" placeholder="Ask a regulatory question…" value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run()} autoFocus />
        <button className="btn" onClick={() => run()} disabled={loading}>Ask</button>
      </div>

      {!res && !loading && (
        <div className="card">
          <h3>Try asking</h3>
          {SAMPLES.map((s) => (
            <div key={s} className="source-chip" style={{ display: "flex", width: "100%" }}
              onClick={() => run(s)}>{s}</div>
          ))}
        </div>
      )}

      {loading && <Spinner label="Reading the corpus…" />}

      {res && (
        <>
          {!res.grounded && <div className="banner">{res.answer.startsWith("(") ? res.answer : "Answer not fully grounded — verify against sources."}</div>}
          {res.grounded && <div className="answer">{res.answer}</div>}
          {res.sources.length > 0 && (
            <>
              <div className="section-title">Sources</div>
              {res.sources.map((s) => (
                <div key={s.n} className="source-chip" style={{ width: "100%" }}
                  onClick={() => nav(`/documents/${s.document_id}`)}>
                  <span className="n">[{s.n}]</span>
                  <span>
                    <strong>{s.title}</strong> — {s.authority} · {s.region}
                    <div className="muted" style={{ fontSize: 12, marginTop: 3 }}>…{s.snippet}…</div>
                  </span>
                </div>
              ))}
            </>
          )}
        </>
      )}
    </>
  );
}
