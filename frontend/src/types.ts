export type Risk = "Critical" | "High" | "Medium" | "Low";

export interface Stats {
  documents: number;
  chunks: number;
  interpreted: number;
  scanned_needs_ocr: number;
  requirements: number;
  obligations: number;
  authorities: number;
  total_pages: number;
}

export interface Facets {
  authorities: string[];
  regions: string[];
  categories: string[];
  risk_levels: string[];
  regulatory_areas: string[];
}

export interface DocListItem {
  id: number;
  title: string;
  authority: string;
  region: string;
  category: string;
  rel_path: string;
  page_count: number;
  is_scanned: number;
  risk_level: Risk | null;
  urgency: string | null;
  summary: string | null;
  regulatory_areas: string[];
  interpreted: boolean;
}

export interface DocList {
  total: number;
  count: number;
  offset: number;
  items: DocListItem[];
}

export interface Requirement {
  text: string;
  area: string;
  citation: string;
}
export interface Obligation {
  text: string;
  actor: string;
  area: string;
  risk: Risk;
}
export interface Interpretation {
  summary: string;
  regulatory_areas: string[];
  device_types: string[];
  key_dates: { date?: string; label: string }[];
  risk_level: Risk;
  urgency: string;
  business_impact: string;
  model: string;
  created_at: string;
}
export interface DocumentDetail extends DocListItem {
  interpretation: Interpretation | null;
  requirements: Requirement[];
  obligations: Obligation[];
  char_count: number;
  size_bytes: number;
  content_hash: string;
}

export interface Grouped {
  label: string;
  count: number;
}
export interface Dashboard {
  by_authority: Grouped[];
  by_region: Grouped[];
  by_risk: Grouped[];
  by_area: Grouped[];
  by_actor: Grouped[];
  top_risk_documents: {
    id: number;
    title: string;
    authority: string;
    region: string;
    risk_level: Risk;
    urgency: string;
    business_impact: string;
  }[];
  critical_obligations: {
    text: string;
    actor: string;
    area: string;
    risk: Risk;
    title: string;
    authority: string;
    document_id: number;
  }[];
}

export interface SearchResult {
  document_id: number;
  title: string;
  authority: string;
  region: string;
  category: string;
  rel_path: string;
  score: number;
  snippet: string;
}

export interface AskSource {
  n: number;
  document_id: number;
  title: string;
  authority: string;
  region: string;
  rel_path: string;
  score: number;
  snippet: string;
}
export interface AskResponse {
  answer: string;
  sources: AskSource[];
  grounded: boolean;
}

export interface Health {
  status: string;
  claude_enabled: boolean;
  model: string;
}

/* ---------- Phase 2 ---------- */
export interface Profile {
  org_name: string;
  markets: string[];
  regulatory_areas: string[];
  device_classes: string[];
  keywords: string[];
  processes: string[];
}
export interface Product {
  id: number;
  name: string;
  device_class: string;
  markets: string[];
  regulatory_areas: string[];
  description: string;
}
export interface Source {
  id: number;
  key: string;
  name: string;
  authority: string;
  region: string;
  type: string;
  url: string;
  areas: string[];
  enabled: number;
  last_checked: string | null;
  last_status: string | null;
}
export interface Alert {
  id: number;
  update_id: number;
  relevance: number;
  risk: Risk;
  urgency: string;
  business_impact: string;
  areas: string[];
  matched_products: string[];
  rationale: string;
  scored_by: string;
  status: "new" | "read" | "dismissed";
  title: string;
  url: string;
  authority: string;
  region: string;
  published: string;
  summary_raw: string;
}
export interface AlertStats {
  total: number;
  new: number;
  high_or_critical: number;
  by_status: Record<string, number>;
  by_risk: Record<string, number>;
}
export interface ImpactRow {
  id: number;
  update_id: number;
  product_id: number;
  product_name: string;
  device_class: string;
  impact_level: "None" | "Low" | "Medium" | "High";
  affected_areas: string[];
  required_actions: { action: string; owner: string; priority: string }[];
  rationale: string;
  assessed_by: string;
}
export interface MonitorRunResult {
  sources_ok: number;
  sources_error: number;
  new_updates: number;
  alerts_created: number;
}
export interface Trends {
  corpus_area_frequency: Grouped[];
  monitoring_by_month: Grouped[];
  monitoring_area_momentum: Grouped[];
  monitoring_by_authority: Grouped[];
  alert_risk_mix: Grouped[];
  total_updates: number;
}
export interface Briefing {
  grounded: boolean;
  summary: string;
  predicted_shifts: { trend: string; horizon: string; confidence: string; rationale?: string }[];
  emerging_risks: string[];
  areas_of_increasing_scrutiny: string[];
  recommended_preparations?: string[];
  trends?: Trends;
}

export interface Task {
  id: number;
  title: string;
  description: string;
  source_type: string;
  source_ref: string;
  document_id: number | null;
  product: string;
  area: string;
  owner: string;
  priority: Risk;
  status: "todo" | "in_progress" | "review" | "done";
  due_date: string;
  created_at: string;
  updated_at: string;
}
export interface TaskBoard {
  columns: string[];
  board: Record<string, Task[]>;
  stats: {
    total: number;
    open: number;
    done: number;
    high_or_critical: number;
    by_status: Record<string, number>;
  };
}

export interface Jurisdiction {
  key: string;
  region: string;
  country: string;
  regulator: string;
  abbrev: string;
  url: string;
  safety_url: string;
  lat: number;
  lon: number;
}

export interface SafetyCountry {
  key: string;
  country: string;
  region: string;
  regulator: string;
  abbrev: string;
  safety_url: string;
  count: number;
  alerts: { title: string; url: string; date: string; authority: string }[];
}
export interface SafetyScan {
  scanned_at: string;
  timeframe_days: number;
  jurisdictions: string[];
  total_alerts: number;
  countries: SafetyCountry[];
}
export interface JurisdictionRegion {
  region: string;
  jurisdictions: Jurisdiction[];
}
export interface CountryCard {
  key: string;
  country: string;
  region: string;
  regulator: string;
  abbrev: string;
  source_url: string;
  summary: string;
  ai: boolean;
  sources: { title: string; url: string }[];
  updates: { title: string; url: string; published: string; authority: string }[];
  documents: { id: number; title: string; authority: string; rel_path: string }[];
}
export interface CountryScan {
  scanned_at: string;
  timeframe_days: number;
  filters: { product_code: string; indication: string };
  jurisdictions: string[];
  ai_enabled: boolean;
  countries: CountryCard[];
}

export interface HorizonItem {
  id: number;
  title: string;
  authority: string;
  region: string;
  published: string;
  url: string;
  category: string;
  priority: "Actionable" | "Indicative" | "Informative";
  snippet: string;
}
export interface HorizonDeadline {
  date: string;
  label: string;
  document_id: number;
  document_title: string;
  authority: string;
}
export interface HorizonScan {
  scanned_at: string | null;
  polled: { new_updates?: number; sources_ok?: number; error?: string } | null;
  summary: string;
  counts: Record<string, number>;
  items: HorizonItem[];
  upcoming_deadlines: HorizonDeadline[];
  by_authority: Grouped[];
}

export interface UpdateRow {
  id: number;
  title: string;
  url: string;
  published: string;
  authority: string;
  region: string;
  summary_raw: string;
  relevance: number | null;
  risk: Risk | null;
  urgency: string | null;
  status: string | null;
}
