"""Conexión SQLite (modo WAL) y migraciones SQL numeradas (`migrations/NNN_*.sql`)."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from wick.config import db_path

_MIGRATIONS = Path(__file__).resolve().parent / "migrations"
_lock = threading.Lock()
_migrated: set[str] = set()


def connect() -> sqlite3.Connection:
    path = db_path()
    conn = sqlite3.connect(path, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    key = str(path)
    if key not in _migrated:
        with _lock:
            if key not in _migrated:
                migrate(conn)
                _migrated.add(key)
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY)")
    done = {r[0] for r in conn.execute("SELECT name FROM schema_migrations")}
    for f in sorted(_MIGRATIONS.glob("*.sql")):
        if f.name in done:
            continue
        conn.executescript(f.read_text(encoding="utf-8"))
        conn.execute("INSERT INTO schema_migrations(name) VALUES (?)", (f.name,))
        conn.commit()
