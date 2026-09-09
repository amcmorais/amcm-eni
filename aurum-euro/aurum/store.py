from __future__ import annotations
import sqlite3
from pathlib import Path

SCHEMA = Path(__file__).resolve().parents[1] / "sql" / "schema.sql"
DEFAULT_DB = Path(__file__).resolve().parents[1] / "data" / "aurum.sqlite"


def connect(db: Path | None = None) -> sqlite3.Connection:
    path = Path(db or DEFAULT_DB)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con


def init_db(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA.read_text(encoding="utf-8"))
    con.commit()
