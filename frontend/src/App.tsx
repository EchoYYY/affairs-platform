import { useEffect, useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import { api } from "./api";
import type { Health } from "./types";
import { Brand } from "./Logo";
import Overview from "./pages/Overview";
import Dashboard from "./pages/Dashboard";
import Corpus from "./pages/Corpus";
import DocumentDetail from "./pages/DocumentDetail";
import KnowledgeHub from "./pages/KnowledgeHub";
import Ask from "./pages/Ask";
import Alerts from "./pages/Alerts";
import Monitoring from "./pages/Monitoring";
import Impact from "./pages/Impact";
import Profile from "./pages/Profile";
import Insights from "./pages/Insights";
import Workflow from "./pages/Workflow";

const NAV = [
  { section: "Platform" },
  { to: "/", label: "Overview", ico: "◆", end: true },
  { to: "/dashboard", label: "Dashboard", ico: "▤" },
  { section: "The 8 Pillars" },
  { to: "/monitoring", label: "Global Monitoring", ico: "📡" },
  { to: "/corpus", label: "Regulatory Library", ico: "📚" },
  { to: "/alerts", label: "Intelligent Alerts", ico: "◉" },
  { to: "/impact", label: "Impact Assessment", ico: "🎯" },
  { to: "/insights", label: "Predictive Insights", ico: "📈" },
  { to: "/search", label: "Knowledge Hub", ico: "🔎" },
  { to: "/workflow", label: "Compliance Workflow", ico: "✅" },
  { to: "/profile", label: "Portfolio & Profile", ico: "⚙️" },
  { section: "Tools" },
  { to: "/ask", label: "Ask the Corpus", ico: "✦" },
];

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  useEffect(() => { api.health().then(setHealth).catch(() => {}); }, []);

  return (
    <div className="app">
      <aside className="sidebar">
        <Brand />
        {NAV.map((n, i) =>
          "section" in n ? (
            <div key={i} className="nav-section">{n.section}</div>
          ) : (
            <NavLink key={n.to} to={n.to!} end={n.end}
              className={({ isActive }) => "navlink" + (isActive ? " active" : "")}>
              <span className="ico">{n.ico}</span> {n.label}
            </NavLink>
          )
        )}
        <div className="sidebar-footer">
          <div className="badge-ai">
            <span className={"dot " + (health?.claude_enabled ? "on" : "off")} />
            {health?.claude_enabled ? "Claude NLP active" : "NLP offline (no API key)"}
          </div>
          <div style={{ marginTop: 6 }}>{health?.model}</div>
        </div>
      </aside>

      <main className="main">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/monitoring" element={<Monitoring />} />
          <Route path="/corpus" element={<Corpus />} />
          <Route path="/documents/:id" element={<DocumentDetail />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/impact" element={<Impact />} />
          <Route path="/insights" element={<Insights />} />
          <Route path="/search" element={<KnowledgeHub />} />
          <Route path="/workflow" element={<Workflow />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/ask" element={<Ask />} />
        </Routes>
      </main>
    </div>
  );
}
