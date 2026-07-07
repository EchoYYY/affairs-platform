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
