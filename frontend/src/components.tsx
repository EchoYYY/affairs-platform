import type { Risk } from "./types";

export function RiskBadge({ level }: { level: Risk | null | undefined }) {
  if (!level) return <span className="pill" style={{ background: "#f1f3f6", color: "#94a3b8" }}>Not assessed</span>;
  return (
    <span className={`pill risk-${level}`}>
      <span className={`dot dot-${level}`} />
      {level}
    </span>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="center-empty">
      <span className="spinner" /> <span style={{ marginLeft: 8 }}>{label ?? "Loading…"}</span>
    </div>
  );
}

export function Tags({ items, brand }: { items: string[]; brand?: boolean }) {
  return (
    <div>
      {items.map((t, i) => (
        <span key={i} className={brand ? "tag brand" : "tag"}>{t}</span>
      ))}
    </div>
  );
}

export function StatCard({
  value, label, sub, icon,
}: { value: React.ReactNode; label: string; sub?: string; icon?: string }) {
  return (
    <div className="card stat">
      {icon && <span className="icon">{icon}</span>}
      <div className="value">{value}</div>
      <div className="label">{label}</div>
      {sub && <div className="sub">{sub}</div>}
    </div>
  );
}
