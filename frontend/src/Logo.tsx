/** AFFAIRS chip mark: a warm-gradient microchip with "AI" in the die and
 *  pin ticks on each edge. Two sizes: sidebar (compact) and hero (large). */

export function ChipMark({ size = 40 }: { size?: number }) {
  const s = size;
  return (
    <div className="chip" style={{ width: s, height: s, borderRadius: s * 0.28 }}>
      <span className="pin t" style={{ left: "34%" }} />
      <span className="pin t" style={{ left: "50%" }} />
      <span className="pin t" style={{ left: "66%" }} />
      <span className="pin b" style={{ left: "34%" }} />
      <span className="pin b" style={{ left: "50%" }} />
      <span className="pin b" style={{ left: "66%" }} />
      <span className="pin l" style={{ top: "40%" }} />
      <span className="pin l" style={{ top: "60%" }} />
      <span className="pin r" style={{ top: "40%" }} />
      <span className="pin r" style={{ top: "60%" }} />
      <b style={{ fontSize: s * 0.38 }}>AI</b>
    </div>
  );
}

/** MicroPort corporate logo — target mark + baby-blue wordmark. */
export function MicroPortLogo({ height = 34 }: { height?: number }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: height * 0.34 }}>
      <svg width={height} height={height} viewBox="0 0 100 100" aria-label="MicroPort" role="img">
        <rect x="5" y="5" width="90" height="90" rx="18" fill="#fff" stroke="#17246b" strokeWidth="7" />
        {/* target ring */}
        <circle cx="50" cy="50" r="25" fill="none" stroke="#8ecdf5" strokeWidth="11" />
        {/* white cross breaks the ring into four arcs */}
        <rect x="43" y="12" width="14" height="76" fill="#fff" />
        <rect x="12" y="43" width="76" height="14" fill="#fff" />
        {/* baby-blue center */}
        <circle cx="50" cy="50" r="8" fill="#8ecdf5" />
      </svg>
      <span style={{
        fontSize: height * 0.72, fontWeight: 800, letterSpacing: "-0.01em",
        color: "#8ecdf5", lineHeight: 1, fontFamily: "inherit",
      }}>MicroPort</span>
    </div>
  );
}

export function Brand() {
  return (
    <div className="brand">
      <ChipMark size={40} />
      <div>
        <h1>AFF<span style={{ color: "#f7a83e" }}>AI</span>RS</h1>
        <small>Regulatory Intelligence</small>
      </div>
    </div>
  );
}
