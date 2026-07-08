import { useNavigate } from "react-router-dom";
import { ChipMark, MicroPortLogo } from "../Logo";

export interface Pillar {
  n: string;
  icon: string;
  title: string;
  desc: string;
  to: string;
  built?: boolean;
}

export const PILLARS: Pillar[] = [
  { n: "01", icon: "📡", title: "Global Regulatory Monitoring",
    desc: "AI continuously scans health-authority feeds, safety alerts and guidance for new and revised regulations — captured instantly, not weeks later.",
    to: "/monitoring", built: true },
  { n: "02", icon: "📚", title: "Regulatory Library",
    desc: "Medical Device Regulations Database with AI analysis — interprets regulations into summaries, requirements and obligations, and links to each actual regulation.",
    to: "/corpus", built: true },
  { n: "03", icon: "◉", title: "Intelligent Alerts & Triage",
    desc: "Filters the noise and surfaces only relevant updates, scored by geography, product, area, urgency and business impact.",
    to: "/alerts", built: true },
  { n: "04", icon: "🎯", title: "Automated Impact Assessment",
    desc: "Maps each regulatory change onto your products, markets and processes, with concrete required actions and owners.",
    to: "/impact" },
  { n: "05", icon: "📈", title: "Predictive Insights",
    desc: "Analyzes trends to anticipate future regulatory shifts, emerging risks and areas of increasing scrutiny — prepare, don't react.",
    to: "/insights" },
  { n: "06", icon: "🔎", title: "Regulatory Knowledge Hub",
    desc: "Registration timeline & government-fee lookup by country and device classification — compare markets at a glance with official-source links.",
    to: "/search", built: true },
  { n: "07", icon: "✅", title: "Compliance Workflow & Approvals",
    desc: "Turns obligations and impact actions into a trackable board of tasks with owners, priorities and status — through to closure.",
    to: "/workflow" },
  { n: "08", icon: "⚙️", title: "Portfolio & Watch Profile",
    desc: "Defines the markets, device classes and products that make everything relevant — the backbone driving scoring and impact.",
    to: "/profile" },
];

export default function Overview() {
  const nav = useNavigate();

  return (
    <>
      <div className="hero">
        <div style={{ marginBottom: 16 }}>
          <MicroPortLogo height={34} />
        </div>
        <div style={{ display: "flex", gap: 18, alignItems: "center", marginBottom: 6 }}>
          <ChipMark size={54} />
          <div className="eyebrow">AFFAIRS</div>
        </div>
        <h1>Global Regulatory <span className="grad-text">Intelligence Platform</span></h1>
      </div>

      <div className="pillars">
        {PILLARS.map((p) => (
          <div key={p.n} className={"pillar" + (p.built ? " built" : "")} onClick={() => nav(p.to)}>
            <div className="picon">{p.icon}</div>
            <h4>{p.title}</h4>
            <p>{p.desc}</p>
            <div className="go">Open →</div>
          </div>
        ))}
      </div>
    </>
  );
}
