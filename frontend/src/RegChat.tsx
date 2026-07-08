import { useRef, useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "./api";
import type { AskSource } from "./types";

interface Msg {
  role: "user" | "assistant";
  text: string;
  sources?: AskSource[];
  grounded?: boolean;
}

const SUGGESTIONS = [
  "What are the clinical evaluation requirements under EU MDR?",
  "Summarize FDA cybersecurity expectations for premarket submissions.",
  "Who is responsible for post-market surveillance and what must they do?",
];

export function RegChat() {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const nav = useNavigate();
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs, busy]);

  const send = async (question?: string) => {
    const text = (question ?? q).trim();
    if (!text || busy) return;
    setMsgs((m) => [...m, { role: "user", text }]);
    setQ(""); setBusy(true);
    try {
      const r = await api.ask(text);
      setMsgs((m) => [...m, { role: "assistant", text: r.answer, sources: r.sources, grounded: r.grounded }]);
    } catch {
      setMsgs((m) => [...m, { role: "assistant", text: "Sorry — the analysis service is unavailable. Is the backend running?" }]);
    } finally { setBusy(false); }
  };

  return (
    <div className="card" style={{ borderColor: "rgba(242,120,60,.35)", marginBottom: 20, display: "flex", flexDirection: "column" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
        <span style={{ fontSize: 18 }}>✦</span>
        <strong style={{ fontSize: 15 }}>AI Analysis & Interpretation</strong>
        <span className="muted" style={{ fontSize: 12 }}>— ask anything about the regulations; answers cite the source documents</span>
      </div>

      <div style={{ maxHeight: 420, overflowY: "auto", padding: "10px 2px", display: "flex", flexDirection: "column", gap: 12 }}>
        {msgs.length === 0 && (
          <div style={{ padding: "8px 0" }}>
            <div className="muted" style={{ fontSize: 13, marginBottom: 8 }}>Try asking:</div>
            {SUGGESTIONS.map((s) => (
              <div key={s} className="source-chip" style={{ width: "100%", cursor: "pointer" }} onClick={() => send(s)}>{s}</div>
            ))}
          </div>
        )}
        {msgs.map((m, i) => (
          <div key={i} style={{ display: "flex", justifyContent: m.role === "user" ? "flex-end" : "flex-start" }}>
            <div style={{
              maxWidth: "82%", padding: "10px 14px", borderRadius: 12, fontSize: 13.5, lineHeight: 1.6,
              whiteSpace: "pre-wrap",
              background: m.role === "user" ? "var(--brand-soft)" : "var(--surface-2)",
              border: "1px solid var(--border)",
              color: m.role === "user" ? "var(--ink)" : "var(--ink)",
            }}>
              {m.text}
              {m.sources && m.sources.length > 0 && (
                <div style={{ marginTop: 10, display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {m.sources.map((s) => (
                    <span key={s.n} className="source-chip" style={{ marginBottom: 0, cursor: "pointer", fontSize: 11.5 }}
                      onClick={() => nav(`/documents/${s.document_id}`)}>
                      <span className="n">[{s.n}]</span> {s.title.slice(0, 40)}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {busy && <div className="muted" style={{ fontSize: 13 }}><span className="spinner" /> Analyzing the regulations…</div>}
        <div ref={endRef} />
      </div>

      <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
        <input type="text" placeholder="Ask about a regulation, requirement, obligation…" value={q}
          onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && send()}
          style={{ flex: 1, padding: "11px 14px" }} disabled={busy} />
        <button className="btn" onClick={() => send()} disabled={busy || !q.trim()}>Send</button>
      </div>
    </div>
  );
}
