"""Jurisdiction & regulator registry — the markets the platform can cover.

Sourced from the user's curated list of national medical-device / drug regulators
and their official websites. Each entry powers the jurisdiction picker on the
Global Monitoring page and provides the primary source link (traceability) on
each country-level scan result.

`match_authorities` / `match_regions` map a jurisdiction to how our own ingested
data (corpus documents + monitored updates) is tagged, so a scan can attach any
relevant items we already hold to the right country.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

REGION_ORDER = ["Americas", "Europe", "Asia", "Oceania", "Middle East", "Africa", "International"]

# key, region, country, regulator, abbrev, url, match_authorities, match_regions
_J: List[Dict[str, Any]] = [
    # Americas
    ("us", "Americas", "United States", "Food and Drug Administration", "FDA", "https://www.fda.gov", ["FDA"], ["US"]),
    ("canada", "Americas", "Canada", "Health Canada", "Health Canada", "https://www.canada.ca/en/health-canada.html", [], []),
    ("brazil", "Americas", "Brazil", "Agência Nacional de Vigilância Sanitária", "ANVISA", "https://www.gov.br/anvisa", [], []),
    ("mexico", "Americas", "Mexico", "Comisión Federal para la Protección contra Riesgos Sanitarios", "COFEPRIS", "https://www.gob.mx/cofepris", [], []),
    ("argentina", "Americas", "Argentina", "Administración Nacional de Medicamentos, Alimentos y Tecnología Médica", "ANMAT", "https://www.argentina.gob.ar/anmat", [], []),
    ("colombia", "Americas", "Colombia", "Instituto Nacional de Vigilancia de Medicamentos y Alimentos", "INVIMA", "https://www.invima.gov.co", [], []),
    # Europe
    ("eu", "Europe", "European Union", "European Medicines Agency", "EMA", "https://www.ema.europa.eu", ["EU", "Clinical Evaluation"], ["EU"]),
    ("uk", "Europe", "United Kingdom", "Medicines and Healthcare products Regulatory Agency", "MHRA", "https://www.gov.uk/mhra", ["MHRA"], ["UK"]),
    ("germany", "Europe", "Germany", "Bundesinstitut für Arzneimittel und Medizinprodukte", "BfArM", "https://www.bfarm.de", [], []),
    ("france", "Europe", "France", "Agence nationale de sécurité du médicament", "ANSM", "https://ansm.sante.fr", [], []),
    ("switzerland", "Europe", "Switzerland", "Swiss Agency for Therapeutic Products", "Swissmedic", "https://www.swissmedic.ch", [], []),
    ("netherlands", "Europe", "Netherlands", "Inspectie Gezondheidszorg en Jeugd", "IGJ", "https://www.igj.nl", [], []),
    ("italy", "Europe", "Italy", "Agenzia Italiana del Farmaco", "AIFA", "https://www.aifa.gov.it", [], []),
    ("spain", "Europe", "Spain", "Agencia Española de Medicamentos y Productos Sanitarios", "AEMPS", "https://www.aemps.gob.es", [], []),
    # Asia
    ("china", "Asia", "China", "National Medical Products Administration", "NMPA", "https://www.nmpa.gov.cn", [], []),
    ("hongkong", "Asia", "Hong Kong", "Medical Device Control Office", "MDCO", "https://www.mdd.gov.hk", [], []),
    ("taiwan", "Asia", "Taiwan", "Taiwan Food and Drug Administration", "TFDA", "https://www.fda.gov.tw", [], []),
    ("japan", "Asia", "Japan", "Pharmaceuticals and Medical Devices Agency", "PMDA", "https://www.pmda.go.jp", ["PMDA/MHLW"], ["Japan"]),
    ("korea", "Asia", "South Korea", "Ministry of Food and Drug Safety", "MFDS", "https://www.mfds.go.kr", [], []),
    ("singapore", "Asia", "Singapore", "Health Sciences Authority", "HSA", "https://www.hsa.gov.sg", [], []),
    ("malaysia", "Asia", "Malaysia", "Medical Device Authority", "MDA", "https://www.mda.gov.my", [], []),
    ("thailand", "Asia", "Thailand", "Thai Food and Drug Administration", "Thai FDA", "https://www.fda.moph.go.th", [], []),
    ("indonesia", "Asia", "Indonesia", "Ministry of Health (Medical Devices)", "MoH", "https://www.kemkes.go.id", [], []),
    ("philippines", "Asia", "Philippines", "Food and Drug Administration Philippines", "FDA PH", "https://www.fda.gov.ph", [], []),
    ("vietnam", "Asia", "Vietnam", "Department of Medical Equipment and Construction", "DMEC", "https://dmec.moh.gov.vn", [], []),
    ("india", "Asia", "India", "Central Drugs Standard Control Organisation", "CDSCO", "https://cdsco.gov.in", [], []),
    # Oceania
    ("australia", "Oceania", "Australia", "Therapeutic Goods Administration", "TGA", "https://www.tga.gov.au", ["TGA"], ["Australia"]),
    ("newzealand", "Oceania", "New Zealand", "Medicines and Medical Devices Safety Authority", "Medsafe", "https://www.medsafe.govt.nz", [], []),
    # Middle East
    ("saudi", "Middle East", "Saudi Arabia", "Saudi Food and Drug Authority", "SFDA", "https://www.sfda.gov.sa", [], []),
    ("uae", "Middle East", "United Arab Emirates", "Ministry of Health and Prevention", "MOHAP", "https://www.mohap.gov.ae", [], []),
    ("israel", "Middle East", "Israel", "Israel Ministry of Health", "IMOH", "https://www.health.gov.il", [], []),
    ("turkey", "Middle East", "Turkey", "Turkish Medicines and Medical Devices Agency", "TITCK", "https://www.titck.gov.tr", [], []),
    # Africa
    ("southafrica", "Africa", "South Africa", "South African Health Products Regulatory Authority", "SAHPRA", "https://www.sahpra.org.za", [], []),
    ("egypt", "Africa", "Egypt", "Egyptian Drug Authority", "EDA", "https://edaegypt.gov.eg", [], []),
    ("au", "Africa", "African Union", "African Medicines Agency", "AMA", "https://www.ama-africa.org", [], []),
    # International bodies
    ("imdrf", "International", "International", "International Medical Device Regulators Forum", "IMDRF", "https://www.imdrf.org/news-events", ["IMDRF"], []),
    ("mdcg", "International", "EU / International", "Medical Device Coordination Group", "MDCG", "https://health.ec.europa.eu/medical-devices-sector/new-regulations/guidance-mdcg-endorsed-documents-and-other-guidance_en", ["MDCG"], []),
    ("teamnb", "International", "EU / International", "Team-NB — European Notified Bodies", "Team-NB", "https://www.team-nb.org/", ["Team-NB"], []),
    ("ghwp", "International", "International", "Global Harmonization Working Party", "GHWP", "https://www.ghwp.org", [], []),
    ("who", "International", "International", "World Health Organization", "WHO", "https://www.who.int", [], []),
    ("ich", "International", "International", "Int'l Council for Harmonisation", "ICH", "https://www.ich.org", [], []),
]

# approximate lat/lon for the coverage world map
_COORDS: Dict[str, tuple] = {
    "us": (38, -97), "canada": (56, -106), "brazil": (-10, -52), "mexico": (23, -102),
    "argentina": (-34, -64), "colombia": (4, -73), "eu": (50, 9), "uk": (54, -2),
    "germany": (51, 10), "france": (46, 2), "switzerland": (47, 8), "netherlands": (52, 5),
    "italy": (42, 12), "spain": (40, -4), "china": (35, 105), "hongkong": (22, 114),
    "taiwan": (24, 121), "japan": (36, 138), "korea": (37, 128), "singapore": (1, 104),
    "malaysia": (4, 102), "thailand": (15, 101), "indonesia": (-2, 118), "philippines": (13, 122),
    "vietnam": (16, 108), "india": (22, 79), "australia": (-25, 133), "newzealand": (-42, 172),
    "saudi": (24, 45), "uae": (24, 54), "israel": (31, 35), "turkey": (39, 35),
    "southafrica": (-29, 24), "egypt": (27, 30), "au": (9, 39),
    "imdrf": (46, 6), "ghwp": (48, 8), "who": (46, 6), "ich": (47, 7),
    "mdcg": (50.8, 4.4), "teamnb": (50.5, 4.5),
}

# direct safety-information / recalls pages where known (else falls back to url)
_SAFETY_URL: Dict[str, str] = {
    "us": "https://www.fda.gov/medical-devices/medical-device-safety/medical-device-recalls-and-early-alerts",
    "uk": "https://www.gov.uk/drug-device-alerts",
    "eu": "https://ec.europa.eu/tools/eudamed",
    "australia": "https://apps.tga.gov.au/prod/DEVICES/daen-entry.aspx",
    "japan": "https://www.pmda.go.jp/safety/info-services/medi-navi/0007.html",
    "canada": "https://recalls-rappels.canada.ca/en",
    "imdrf": "https://www.imdrf.org/safety-information",
    "who": "https://www.who.int/teams/regulation-prequalification/incidents-and-SF",
}

JURISDICTIONS: List[Dict[str, Any]] = [
    {"key": k, "region": reg, "country": c, "regulator": r, "abbrev": ab, "url": u,
     "safety_url": _SAFETY_URL.get(k, u),
     "match_authorities": ma, "match_regions": mr,
     "lat": _COORDS.get(k, (0, 0))[0], "lon": _COORDS.get(k, (0, 0))[1]}
    for (k, reg, c, r, ab, u, ma, mr) in _J
]

_BY_KEY = {j["key"]: j for j in JURISDICTIONS}


def get(key: str) -> Optional[Dict[str, Any]]:
    return _BY_KEY.get(key)


def grouped() -> List[Dict[str, Any]]:
    out = []
    for region in REGION_ORDER:
        members = [j for j in JURISDICTIONS if j["region"] == region]
        if members:
            out.append({"region": region, "jurisdictions": members})
    return out
