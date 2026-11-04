"""SQLite data layer for the Bug Tracker.

All SQL lives here so the Flask routes stay small and easy to test.
"""
import sqlite3
from datetime import datetime, timezone

SEVERITIES = ("Low", "Medium", "High")
STATUSES = ("Open", "In Progress", "Fixed")

SCHEMA = """
CREATE TABLE IF NOT EXISTS bugs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL,
    description TEXT    NOT NULL DEFAULT '',
    severity    TEXT    NOT NULL CHECK (severity IN ('Low', 'Medium', 'High')),
    status      TEXT    NOT NULL CHECK (status IN ('Open', 'In Progress', 'Fixed')),
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL
);
"""


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def get_connection(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path):
    with get_connection(db_path) as conn:
        conn.executescript(SCHEMA)


def list_bugs(db_path, severity=None, status=None, search=None):
    """Return bugs, newest first, with optional filters (all combined with AND)."""
    query = "SELECT * FROM bugs WHERE 1=1"
    params = []
    if severity:
        query += " AND severity = ?"
        params.append(severity)
    if status:
        query += " AND status = ?"
        params.append(status)
    if search:
        query += " AND (title LIKE ? OR description LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like])
    query += " ORDER BY id DESC"
    with get_connection(db_path) as conn:
        return [dict(r) for r in conn.execute(query, params).fetchall()]


def get_bug(db_path, bug_id):
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM bugs WHERE id = ?", (bug_id,)).fetchone()
    return dict(row) if row else None


def create_bug(db_path, title, description, severity, status):
    now = _now()
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO bugs (title, description, severity, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (title, description, severity, status, now, now),
        )
        return cur.lastrowid


def update_bug(db_path, bug_id, fields):
    """Update only the given fields. Returns True if a row was changed."""
    allowed = {"title", "description", "severity", "status"}
    fields = {k: v for k, v in fields.items() if k in allowed}
    if not fields:
        return get_bug(db_path, bug_id) is not None
    assignments = ", ".join(f"{k} = ?" for k in fields)
    params = list(fields.values()) + [_now(), bug_id]
    with get_connection(db_path) as conn:
        cur = conn.execute(
            f"UPDATE bugs SET {assignments}, updated_at = ? WHERE id = ?", params
        )
        return cur.rowcount > 0


def delete_bug(db_path, bug_id):
    with get_connection(db_path) as conn:
        cur = conn.execute("DELETE FROM bugs WHERE id = ?", (bug_id,))
        return cur.rowcount > 0


def get_stats(db_path):
    """Counts per status and per severity, using GROUP BY."""
    with get_connection(db_path) as conn:
        by_status = conn.execute(
            "SELECT status, COUNT(*) AS n FROM bugs GROUP BY status"
        ).fetchall()
        by_severity = conn.execute(
            "SELECT severity, COUNT(*) AS n FROM bugs GROUP BY severity"
        ).fetchall()
    stats = {
        "total": 0,
        "status": {s: 0 for s in STATUSES},
        "severity": {s: 0 for s in SEVERITIES},
    }
    for row in by_status:
        stats["status"][row["status"]] = row["n"]
        stats["total"] += row["n"]
    for row in by_severity:
        stats["severity"][row["severity"]] = row["n"]
    return stats
