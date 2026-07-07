import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import type { SearchResult } from "../types";
import { Spinner } from "../components";

export default function Search() {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [loading, setLoading] = useState(false);
  const nav = useNavigate();

  const run = async () => {
    if (!q.trim()) return;
    setLoading(true); setResults(null);
    try { setResults((await api.search(q)).results); }
    finally { setLoading(false); }
  };

  return (
    <>
      <div className="page-head">
        <h2>Semantic Search</h2>
        <p>Meaning-based retrieval across the corpus — finds relevant content even when the words differ.</p>
      </div>

      <div className="search-bar">
        <input type="text" placeholder="e.g. cybersecurity documentation for network-connected devices"
          value={q} onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run()} autoFocus />
        <button className="btn" onClick={run} disabled={loading}>Search</button>
      </div>

      {loading && <Spinner label="Searching…" />}
      {results && results.length === 0 && <div className="center-empty">No matches.</div>}
      {results?.map((r) => (
        <div key={r.document_id} className="doc-row" onClick={() => nav(`/documents/${r.document_id}`)}>
          <div className="row-top">
            <span className="title">{r.title}</span>
            <span className="tag brand">{(r.score * 100).toFixed(0)}% match</span>
          </div>
          <div className="meta">{r.authority} · {r.region} · {r.category}</div>
          <div className="summary">…{r.snippet}…</div>
        </div>
      ))}
    </>
  );
}
