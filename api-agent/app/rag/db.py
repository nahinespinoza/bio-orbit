"""Conexión SQLite con la extensión sqlite-vec cargada (la necesita SQLiteVec de langchain-community)."""

import sqlite3
from pathlib import Path

import sqlite_vec

VECTOR_TABLE = "chunk_vectors"  # SQLiteVec crea chunk_vectors y chunk_vectors_vec


def connect(path: Path, read_only: bool = False) -> sqlite3.Connection:
    uri = f"file:{path.as_posix()}{'?mode=ro' if read_only else ''}"
    conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # SQLiteVec lee las filas por nombre de columna
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    return conn


def has_vectors(conn: sqlite3.Connection) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE name = ?", (VECTOR_TABLE,)).fetchone() is not None


def meta(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None
