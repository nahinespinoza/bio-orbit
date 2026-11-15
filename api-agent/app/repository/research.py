"""Evidencia de la investigación de las fichas, leída por metadatos (cultivo + tema), no por parecido."""

import json
import re
import sqlite3
from collections.abc import Sequence

URL = re.compile(r"\s*\(?https?://\S+?\)?(?=\s|$)")
MAX_CHARS = 1200


def _compact(text: str) -> str:
    text = URL.sub("", text)
    return text if len(text) <= MAX_CHARS else text[: MAX_CHARS - 1].rstrip() + "…"


def research_evidence(conn: sqlite3.Connection, crop_id: str, topics: Sequence[str],
                      compact: bool = True) -> dict[str, list[str]]:
    """tema → textos de los fragmentos de investigación de ese cultivo. Un tema sin fragmentos no aparece.
    `compact`: sin URL (siguen en el RAG) y ≤ 1 200 caracteres por fragmento."""
    rows = conn.execute(
        "SELECT text, metadata_json FROM chunks WHERE json_extract(metadata_json, '$.doc_kind') = 'crop_research' "
        "AND json_extract(metadata_json, '$.doc_id') LIKE ? ORDER BY chunk_id",
        (f"cultivos.json#{crop_id}/%",),
    ).fetchall()
    out: dict[str, list[str]] = {}
    for r in rows:
        topic = json.loads(r["metadata_json"]).get("tema")
        if topic in topics:
            out.setdefault(topic, []).append(_compact(r["text"]) if compact else r["text"])
    return out
