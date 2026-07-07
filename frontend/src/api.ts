import type {
  Alert, AlertStats, AskResponse, Briefing, CountryScan, Dashboard, DocList, DocumentDetail,
  Facets, Health, HorizonScan, ImpactRow, JurisdictionRegion, MonitorRunResult, Product,
  Profile, SafetyScan, SearchResult, Source, Stats, Task, TaskBoard, Trends, UpdateRow,
} from "./types";

async function get<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}
async function post<T>(url: string, body: unknown): Promise<T> {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}
async function put<T>(url: string, body: unknown): Promise<T> {
  const r = await fetch(url, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}
async function patch<T>(url: string, body: unknown): Promise<T> {
  const r = await fetch(url, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}
async function del<T>(url: string): Promise<T> {
  const r = await fetch(url, { method: "DELETE" });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

export const api = {
  health: () => get<Health>("/api/health"),
  stats: () => get<Stats>("/api/stats"),
  facets: () => get<Facets>("/api/facets"),
  dashboard: () => get<Dashboard>("/api/dashboard"),
  documents: (params: Record<string, string | number | undefined>) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== "") qs.set(k, String(v));
    });
    return get<DocList>(`/api/documents?${qs.toString()}`);
  },
  document: (id: number) => get<DocumentDetail>(`/api/documents/${id}`),
  interpret: (id: number) =>
    post<{ document_id: number; interpretation: unknown }>(
      `/api/documents/${id}/interpret`, {}),
  search: (query: string, authority?: string, region?: string) =>
    post<{ query: string; results: SearchResult[] }>("/api/search", {
      query, top_k: 12, authority, region,
    }),
  ask: (question: string, authority?: string, region?: string) =>
    post<AskResponse>("/api/ask", { question, top_k: 8, authority, region }),

  // ---- Phase 2 ----
  profile: () => get<Profile>("/api/profile"),
  saveProfile: (p: Partial<Profile>) => put<Profile>("/api/profile", p),
  products: () => get<Product[]>("/api/products"),
  addProduct: (p: Partial<Product>) => post<Product>("/api/products", p),
  deleteProduct: (id: number) => del(`/api/products/${id}`),

  sources: () => get<Source[]>("/api/sources"),
  toggleSource: (id: number, enabled: boolean) =>
    post(`/api/sources/${id}/toggle?enabled=${enabled}`, {}),
  runMonitor: () => post<MonitorRunResult>("/api/monitor/run", {}),
  horizonScan: () => post<HorizonScan>("/api/monitor/horizon-scan?poll=true", {}),
  horizonLast: () => get<HorizonScan>("/api/monitor/horizon"),
  jurisdictions: () => get<{ regions: JurisdictionRegion[] }>("/api/jurisdictions"),
  countryScan: (body: { jurisdictions: string[]; days: number; product_code: string; indication: string }) =>
    post<CountryScan>("/api/monitor/country-scan", body),

  alerts: (params: Record<string, string | number | undefined>) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== "") qs.set(k, String(v)); });
    return get<Alert[]>(`/api/alerts?${qs.toString()}`);
  },
  alertStats: () => get<AlertStats>("/api/alerts/stats"),
  safetyScan: (jurisdictions: string[], days: number) =>
    post<SafetyScan>("/api/alerts/safety-scan", { jurisdictions, days }),
  setAlertStatus: (id: number, status: string) =>
    post(`/api/alerts/${id}/status`, { status }),
  rescore: () => post<{ rescored: number }>("/api/alerts/rescore", {}),

  impact: (updateId: number) => get<ImpactRow[]>(`/api/updates/${updateId}/impact`),
  assess: (updateId: number) => post<ImpactRow[]>(`/api/updates/${updateId}/assess`, {}),

  trends: () => get<Trends>("/api/insights/trends"),
  briefing: () => get<Briefing>("/api/insights/briefing"),

  updates: (limit = 100) => get<UpdateRow[]>(`/api/updates?limit=${limit}`),

  ingestStatus: () => get<{ ran_at: string | null; busy: boolean; autoingest_minutes: number; ingest: { ingested: number; skipped: number } | null }>("/api/ingest/status"),
  ingestRun: (interpret = false) =>
    post<{ ingest: { scanned: number; ingested: number; skipped: number; errors: number } }>(`/api/ingest/run?interpret=${interpret}`, {}),

  // ---- workflow (pillar 7) ----
  taskBoard: () => get<TaskBoard>("/api/tasks/board"),
  createTask: (t: Partial<Task>) => post<Task>("/api/tasks", t),
  updateTask: (id: number, t: Partial<Task>) => patch<Task>(`/api/tasks/${id}`, t),
  deleteTask: (id: number) => del(`/api/tasks/${id}`),
  seedTasks: () => post<{ created: number }>("/api/tasks/seed", {}),
};
