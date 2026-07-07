import { useEffect, useState } from "react";
import { api } from "../api";
import type { Product, Profile as P } from "../types";
import { Spinner, Tags } from "../components";

function ChipEditor({ label, items, onChange }: {
  label: string; items: string[]; onChange: (v: string[]) => void;
}) {
  const [val, setVal] = useState("");
  return (
    <div style={{ marginBottom: 14 }}>
      <div className="muted" style={{ fontSize: 12, fontWeight: 700, marginBottom: 6 }}>{label}</div>
      <div>
        {items.map((it, i) => (
          <span key={i} className="tag brand" style={{ cursor: "pointer" }}
            onClick={() => onChange(items.filter((_, k) => k !== i))}>{it} ✕</span>
        ))}
      </div>
      <input type="text" placeholder={`Add ${label.toLowerCase()}… (Enter)`} value={val}
        onChange={(e) => setVal(e.target.value)} style={{ marginTop: 6, width: 280 }}
        onKeyDown={(e) => {
          if (e.key === "Enter" && val.trim()) { onChange([...items, val.trim()]); setVal(""); }
        }} />
    </div>
  );
}

export default function Profile() {
  const [p, setP] = useState<P | null>(null);
  const [products, setProducts] = useState<Product[] | null>(null);
  const [saved, setSaved] = useState(false);
  const [np, setNp] = useState<Partial<Product>>({ name: "", device_class: "", markets: [], regulatory_areas: [], description: "" });

  useEffect(() => {
    api.profile().then(setP).catch(() => {});
    api.products().then(setProducts).catch(() => {});
  }, []);

  const save = async () => {
    if (!p) return;
    await api.saveProfile(p);
    setSaved(true); setTimeout(() => setSaved(false), 1800);
  };
  const addProduct = async () => {
    if (!np.name) return;
    await api.addProduct(np);
    setNp({ name: "", device_class: "", markets: [], regulatory_areas: [], description: "" });
    setProducts(await api.products());
  };
  const removeProduct = async (id: number) => {
    await api.deleteProduct(id);
    setProducts(await api.products());
  };

  if (!p || !products) return <Spinner />;

  return (
    <>
      <div className="page-head">
        <h2>Watch Profile & Portfolio</h2>
        <p>Defines what's relevant — drives alert scoring and impact assessment across the platform.</p>
      </div>

      <div className="card" style={{ marginBottom: 18 }}>
        <h3>Organization profile</h3>
        <div style={{ marginBottom: 14 }}>
          <div className="muted" style={{ fontSize: 12, fontWeight: 700, marginBottom: 6 }}>Organization name</div>
          <input type="text" value={p.org_name} style={{ width: 320 }}
            onChange={(e) => setP({ ...p, org_name: e.target.value })} />
        </div>
        <ChipEditor label="Markets" items={p.markets} onChange={(v) => setP({ ...p, markets: v })} />
        <ChipEditor label="Regulatory areas" items={p.regulatory_areas} onChange={(v) => setP({ ...p, regulatory_areas: v })} />
        <ChipEditor label="Device classes" items={p.device_classes} onChange={(v) => setP({ ...p, device_classes: v })} />
        <ChipEditor label="Keywords" items={p.keywords} onChange={(v) => setP({ ...p, keywords: v })} />
        <ChipEditor label="Internal processes" items={p.processes} onChange={(v) => setP({ ...p, processes: v })} />
        <button className="btn" onClick={save}>{saved ? "✓ Saved" : "Save profile"}</button>
      </div>

      <div className="card">
        <h3>Product portfolio ({products.length})</h3>
        {products.map((pr) => (
          <div key={pr.id} className="req-item" style={{ display: "flex", justifyContent: "space-between" }}>
            <div>
              <strong>{pr.name}</strong> <span className="tag">{pr.device_class}</span>
              <div style={{ marginTop: 6 }}><Tags items={pr.markets} /><Tags items={pr.regulatory_areas} brand /></div>
              {pr.description && <div className="muted" style={{ fontSize: 12.5, marginTop: 4 }}>{pr.description}</div>}
            </div>
            <button className="btn ghost" onClick={() => removeProduct(pr.id)}>Remove</button>
          </div>
        ))}

        <div style={{ marginTop: 16, borderTop: "1px solid var(--border)", paddingTop: 14 }}>
          <div className="muted" style={{ fontSize: 12, fontWeight: 700, marginBottom: 8 }}>Add product</div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
            <input type="text" placeholder="Product name" value={np.name}
              onChange={(e) => setNp({ ...np, name: e.target.value })} />
            <input type="text" placeholder="Device class (e.g. Class IIb)" value={np.device_class}
              onChange={(e) => setNp({ ...np, device_class: e.target.value })} />
            <input type="text" placeholder="Markets (comma-sep)"
              onChange={(e) => setNp({ ...np, markets: e.target.value.split(",").map((x) => x.trim()).filter(Boolean) })} />
            <input type="text" placeholder="Areas (comma-sep)"
              onChange={(e) => setNp({ ...np, regulatory_areas: e.target.value.split(",").map((x) => x.trim()).filter(Boolean) })} />
          </div>
          <button className="btn" onClick={addProduct}>Add product</button>
        </div>
      </div>
    </>
  );
}
