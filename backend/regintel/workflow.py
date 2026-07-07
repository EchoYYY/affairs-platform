"""Pillar 7 — compliance workflow.

Turns the platform's findings (obligations, impact actions) into trackable tasks
with an owner, priority, due date, and a status that moves through a simple
todo → in_progress → review → done board.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .db import connect

STATUSES = ["todo", "in_progress", "review", "done"]
PRIORITIES = ["Low", "Medium", "High", "Critical"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_tasks(status: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = connect()
    try:
        q = "SELECT * FROM tasks"
        params: List[Any] = []
        if status:
            q += " WHERE status = ?"
            params.append(status)
        q += (" ORDER BY CASE priority WHEN 'Critical' THEN 0 WHEN 'High' THEN 1 "
              "WHEN 'Medium' THEN 2 ELSE 3 END, id DESC")
        return [dict(r) for r in conn.execute(q, params)]
    finally:
        conn.close()


def board() -> Dict[str, List[Dict[str, Any]]]:
    """Tasks grouped by status column, for the kanban view."""
    grouped: Dict[str, List[Dict[str, Any]]] = {s: [] for s in STATUSES}
    for t in list_tasks():
        grouped.setdefault(t["status"], []).append(t)
    return grouped


def stats() -> Dict[str, Any]:
    conn = connect()
    try:
        by_status = {r[0]: r[1] for r in conn.execute(
            "SELECT status, COUNT(*) FROM tasks GROUP BY status")}
        return {
            "total": conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0],
            "open": sum(v for k, v in by_status.items() if k != "done"),
            "done": by_status.get("done", 0),
            "high_or_critical": conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE priority IN ('High','Critical') "
                "AND status != 'done'").fetchone()[0],
            "by_status": by_status,
        }
    finally:
        conn.close()


def create_task(data: Dict[str, Any]) -> Dict[str, Any]:
    conn = connect()
    try:
        now = _now()
        cur = conn.execute(
            """INSERT INTO tasks
               (title, description, source_type, source_ref, document_id, product,
                area, owner, priority, status, due_date, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                data.get("title", "Untitled task"), data.get("description", ""),
                data.get("source_type", "manual"), data.get("source_ref", ""),
                data.get("document_id"), data.get("product", ""), data.get("area", ""),
                data.get("owner", ""), data.get("priority", "Medium"),
                data.get("status", "todo"), data.get("due_date", ""), now, now,
            ),
        )
        conn.commit()
        tid = cur.lastrowid
        return dict(conn.execute("SELECT * FROM tasks WHERE id = ?", (tid,)).fetchone())
    finally:
        conn.close()


def update_task(task_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    conn = connect()
    try:
        fields, params = [], []
        for f in ("title", "description", "owner", "priority", "status", "due_date",
                  "product", "area"):
            if f in data and data[f] is not None:
                fields.append(f"{f} = ?"); params.append(data[f])
        if not fields:
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            return dict(row) if row else None
        fields.append("updated_at = ?"); params.append(_now())
        params.append(task_id)
        conn.execute(f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?", params)
        conn.commit()
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def delete_task(task_id: int) -> None:
    conn = connect()
    try:
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
    finally:
        conn.close()


def seed_from_obligations(limit: int = 25) -> int:
    """Bootstrap the board from the highest-risk extracted obligations.

    Skips obligations that already have a task (matched by source_ref), so it's
    safe to re-run. Returns the number of tasks created.
    """
    conn = connect()
    try:
        existing = {r[0] for r in conn.execute(
            "SELECT source_ref FROM tasks WHERE source_type = 'obligation'")}
        rows = conn.execute(
            """SELECT o.id, o.text, o.actor, o.area, o.risk, d.title, d.id AS document_id
               FROM obligations o JOIN documents d ON d.id = o.document_id
               WHERE o.risk IN ('Critical','High')
               ORDER BY CASE o.risk WHEN 'Critical' THEN 0 ELSE 1 END LIMIT ?""",
            (limit,),
        ).fetchall()
        created = 0
        now = _now()
        for r in rows:
            ref = f"obligation:{r['id']}"
            if ref in existing:
                continue
            conn.execute(
                """INSERT INTO tasks
                   (title, description, source_type, source_ref, document_id, area,
                    owner, priority, status, created_at, updated_at)
                   VALUES (?,?, 'obligation', ?,?,?,?,?, 'todo', ?, ?)""",
                (
                    (r["text"] or "")[:120], r["text"], ref, r["document_id"], r["area"],
                    r["actor"], r["risk"], now, now,
                ),
            )
            created += 1
        conn.commit()
        return created
    finally:
        conn.close()
