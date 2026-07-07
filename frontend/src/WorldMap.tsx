/** Coverage world map for the Global Monitoring dashboard.
 *  Real geography (Natural Earth, public-domain via world-atlas) rendered with
 *  react-simple-maps, plus glowing markers for jurisdictions in scope.
 */
import { ComposableMap, Geographies, Geography, Marker } from "react-simple-maps";
// public-domain Natural Earth topojson (110m resolution)
import geoData from "world-atlas/countries-110m.json";

export interface MapMarker {
  key: string; country: string; lat: number; lon: number;
  region: string; covered: boolean; count: number;
}

export function WorldMap({ markers }: { markers: MapMarker[]; activeRegions?: Set<string> }) {
  return (
    <ComposableMap
      projection="geoEqualEarth"
      projectionConfig={{ scale: 165 }}
      width={980}
      height={440}
      style={{ width: "100%", height: "auto", display: "block" }}
    >
      <defs>
        <radialGradient id="mk" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#f7b34a" />
          <stop offset="100%" stopColor="#e5484d" />
        </radialGradient>
        <filter id="mkglow" x="-120%" y="-120%" width="340%" height="340%">
          <feGaussianBlur stdDeviation="5" />
        </filter>
      </defs>

      <Geographies geography={geoData as any}>
        {({ geographies }: { geographies: any[] }) =>
          geographies.map((geo) => (
            <Geography
              key={geo.rsmKey}
              geography={geo}
              style={{
                default: { fill: "#182138", stroke: "#26334f", strokeWidth: 0.4, outline: "none" },
                hover: { fill: "#1e2a45", stroke: "#26334f", strokeWidth: 0.4, outline: "none" },
                pressed: { fill: "#1e2a45", outline: "none" },
              }}
            />
          ))
        }
      </Geographies>

      {markers.map((m) => (
        <Marker key={m.key} coordinates={[m.lon, m.lat]}>
          <title>{m.country}{m.count ? ` — ${m.count} update${m.count !== 1 ? "s" : ""}` : ""}</title>
          {m.covered ? (
            <>
              <circle r={11} fill="url(#mk)" opacity={0.35} filter="url(#mkglow)" />
              <circle r={5} fill="url(#mk)" stroke="#fff" strokeWidth={1.1} />
            </>
          ) : (
            <circle r={4} fill="rgba(10,15,30,.6)" stroke="rgba(242,120,60,.9)" strokeWidth={1.5} />
          )}
        </Marker>
      ))}
    </ComposableMap>
  );
}
