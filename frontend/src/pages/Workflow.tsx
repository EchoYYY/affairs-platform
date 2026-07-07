import { useEffect, useState } from "react";
import { api } from "../api";
import type { Task, TaskBoard } from "../types";
import { Spinner, StatCard } from "../components";

const COLTITLE: Record<string, string> = {
  todo: "To do", in_progress: "In progress", review: "Review / approval", done: "Done",
};
const NEXT: Record<string, string> = { todo: "in_progress", in_progress: "review", review: "done" };
const PREV: Record<string, string> = { done: "review", review: "in_progress", in_progress: "todo" };

export default function Workflow() {
  const [data, setData] = useState<TaskBoard | null>(null);
  const [adding, setAdding] = useState(false);
  const [nt, setNt] = useState<Partial<Task>>({ title: "", owner: "", priority: "Medium" });

  const load = () => { api.taskBoard().then(setData).catch(() => {}); };
  useEffect(load, []);

  const move = async (t: Task, status: string) => { await api.updateTask(t.id, { status: status as Task["status"] }); load(); };
  const setPriority = async (t: Task, priority: string) => { await api.updateTask(t.id, { priority: priority as Task["priority"] }); load(); };
  const remove = async (t: Task) => { await api.deleteTask(t.id); load(); };
  const seed = async () => { await api.seedTasks(); load(); };
  const add = async () => {
    if (!nt.title) return;
    await api.createTask(nt);
    setNt({ title: "", owner: "", priority: "Medium" }); setAdding(false); load();
  };

  if (!data) return <Spinner label="Loading workflow…" />;
  const s = data.stats;

  return (
    <>
      <div className="page-head">
        <h2>Compliance Workflow & Approvals</h2>
        <p>Track obligations and impact actions through to closure — owners, priorities and status.</p>
      </div>

      <div className="grid cols-4" style={{ marginBottom: 18 }}>
        <StatCard value={s.total} label="Total tasks" icon="✅" />
        <StatCard value={s.open} label="Open" icon="●" />
        <StatCard value={s.high_or_critical} label="High / critical open" icon="⚠" />
        <StatCard value={s.done} label="Completed" icon="✓" />
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <button className="btn" onClick={() => setAdding(!adding)}>{adding ? "Cancel" : "+ New task"}</button>
        {s.total === 0 && <button className="btn ghost" onClick={seed}>Seed from high-risk obligations</button>}
      </div>

      {adding && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <input type="text" placeholder="Task title" value={nt.title}
              onChange={(e) => setNt({ ...nt, title: e.target.value })} style={{ minWidth: 280 }} />
            <input type="text" placeholder="Owner (team/person)" value={nt.owner}
              onChange={(e) => setNt({ ...nt, owner: e.target.value })} />
            <select value={nt.priority} onChange={(e) => setNt({ ...nt, priority: e.target.value as Task["priority"] })}>
              {["Critical", "High", "Medium", "Low"].map((p) => <option key={p}>{p}</option>)}
            </select>
            <input type="date" value={nt.due_date ?? ""} onChange={(e) => setNt({ ...nt, due_date: e.target.value })} />
            <button className="btn" onClick={add}>Add</button>
          </div>
        </div>
      )}

      <div className="kanban">
        {data.columns.map((col) => (
          <div key={col} className="kcol">
            <h4>{COLTITLE[col] ?? col} <span className="count">{data.board[col]?.length ?? 0}</span></h4>
            {(data.board[col] ?? []).map((t) => (
              <div key={t.id} className={`kcard p-${t.priority}`}>
                <div className="kt">{t.title}</div>
                <div className="km">
                  {t.owner && <span>👤 {t.owner}</span>}
                  <span className={`pill risk-${t.priority}`} style={{ padding: "1px 7px" }}>{t.priority}</span>
                  {t.area && <span className="tag" style={{ margin: 0 }}>{t.area}</span>}
                  {t.due_date && <span>📅 {t.due_date}</span>}
                </div>
                <div className="kactions">
                  {PREV[t.status] && <button className="kbtn" onClick={() => move(t, PREV[t.status])}>←</button>}
                  {NEXT[t.status] && <button className="kbtn" onClick={() => move(t, NEXT[t.status])}>→ {COLTITLE[NEXT[t.status]]}</button>}
                  <select className="kbtn" value={t.priority}
                    onChange={(e) => setPriority(t, e.target.value)} style={{ padding: "2px 4px" }}>
                    {["Critical", "High", "Medium", "Low"].map((p) => <option key={p}>{p}</option>)}
                  </select>
                  <button className="kbtn" onClick={() => remove(t)}>✕</button>
                </div>
              </div>
            ))}
            {(data.board[col] ?? []).length === 0 && <div className="muted" style={{ fontSize: 12, padding: 8 }}>—</div>}
          </div>
        ))}
      </div>
    </>
  );
}
