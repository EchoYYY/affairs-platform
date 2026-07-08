/** Interactive market-picker map for the Knowledge Hub.
 *  Covered countries are filled and clickable; a glowing marker anchors each
 *  market (and is the click target for tiny/EU entries with no polygon).
 *  Countries passing the active Time/Cost filters are highlighted brightest.
 */
import { ComposableMap, Geographies, Geography, Marker } from "react-simple-maps";
import geoData from "world-atlas/countries-110m.json";
import type { Market } from "./types";

// our name -> topojson (Natural Earth 110m) name
const ALIAS: Record<string, string> = { "United States": "United States of America" };
const topoName = (c: string) => ALIAS[c] ?? c;

// approximate centroids [lon, lat]
const COORDS: Record<string, [number, number]> = {
  Argentina: [-64, -34], Australia: [134, -25], Bangladesh: [90.4, 23.7], Brazil: [-52, -12],
  Canada: [-106, 58], China: [104, 35], Colombia: [-74, 4.6], "Costa Rica": [-84, 9.9],
  Ecuador: [-78, -1.5], Egypt: [30, 27], "European Union": [9, 50], "Hong Kong": [114.2, 22.3],
  India: [79, 22], Indonesia: [118, -2.5], Israel: [35, 31.5], Japan: [138, 37],
  Malaysia: [102, 4], Mexico: [-102, 23.6], Pakistan: [69, 30], Peru: [-75, -9.2],
  Philippines: [122, 12.9], "Saudi Arabia": [45, 24], Singapore: [103.8, 1.35],
  "South Korea": [128, 36.5], Switzerland: [8.2, 46.8], Taiwan: [121, 23.7],
  Thailand: [101, 15.9], "United Arab Emirates": [54, 24], "United Kingdom": [-2, 54],
  "United States": [-98, 39.8], Vietnam: [108, 14.1],
};

interface Props {
  markets: Market[];
  selected: string;
  qualifies: Set<string> | null; // null = no filter, everything qualifies
  onSelect: (country: string) => void;
}

export function RegMap({ markets, selected, qualifies, onSelect }: Props) {
  const byTopo = new Map(markets.map((m) => [topoName(m.country), m.country]));
  const passes = (c: string) => qualifies === null || qualifies.has(c);

  const fillFor = (country: string | undefined) => {
    if (!country) return "#182138";                 // not a market
    if (country === selected) return "#f7b34a";      // selected
    if (passes(country)) return "rgba(242,120,60,.72)"; // matches filters
    return "rgba(242,120,60,.20)";                   // covered but filtered out
  };

  return (
    <ComposableMap
      projection="geoEqualEarth"
      projectionConfig={{ scale: 168 }}
      width={980}
      height={450}
      style={{ width: "100%", height: "auto", display: "block" }}
    >
      <defs>
        <radialGradient id="rmk" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#f7b34a" />
          <stop offset="100%" stopColor="#e5484d" />
        </radialGradient>
        <filter id="rmkglow" x="-120%" y="-120%" width="340%" height="340%">
          <feGaussianBlur stdDeviation="4" />
        </filter>
      </defs>

      <Geographies geography={geoData as any}>
        {({ geographies }: { geographies: any[] }) =>
          geographies.map((geo) => {
            const country = byTopo.get(geo.properties.name);
            const isMarket = !!country;
            return (
              <Geography
                key={geo.rsmKey}
                geography={geo}
                onClick={() => country && onSelect(country)}
                style={{
                  default: { fill: fillFor(country), stroke: "#26334f", strokeWidth: 0.4, outline: "none",
                    cursor: isMarket ? "pointer" : "default" },
                  hover: { fill: isMarket ? "#f7b34a" : "#1e2a45", stroke: "#26334f", strokeWidth: 0.4, outline: "none",
                    cursor: isMarket ? "pointer" : "default" },
                  pressed: { fill: "#f7b34a", outline: "none" },
                }}
              />
            );
          })
        }
      </Geographies>

      {markets.map((m) => {
        const c = COORDS[m.country];
        if (!c) return null;
        const on = passes(m.country);
        const sel = m.country === selected;
        return (
          <Marker key={m.country} coordinates={c} onClick={() => onSelect(m.country)} style={{ default: { cursor: "pointer" } }}>
            <title>{m.country}{m.fastest ? ` — fastest ${m.fastest.display}` : ""}{m.cheapest ? `, from ${m.cheapest.usd_str}` : ""}</title>
            {sel && <circle r={13} fill="url(#rmk)" opacity={0.4} filter="url(#rmkglow)" />}
            <circle
              r={sel ? 6 : 4}
              fill={on ? "url(#rmk)" : "rgba(242,120,60,.35)"}
              stroke="#fff"
              strokeWidth={sel ? 1.6 : on ? 1 : 0.5}
            />
          </Marker>
        );
      })}
    </ComposableMap>
  );
}
