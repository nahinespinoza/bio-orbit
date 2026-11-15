"""Construye la base de conocimiento SQLite desde cero.

Uso:
    uv run python -m ingestion.build_db                 # embeddings si hay OPENAI_API_KEY
    uv run python -m ingestion.build_db --no-embeddings # solo datos estructurados + fragmentos (sin costo)

Se escribe en un archivo temporal y se reemplaza al final: la base vieja sigue válida si algo falla.
"""

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from langchain_community.vectorstores import SQLiteVec
from langchain_openai import OpenAIEmbeddings

from app.config import Settings, get_settings
from app.rag.db import VECTOR_TABLE, connect
from ingestion.documents import default_sources, load_all
from ingestion.load_structured import load_structured

SCHEMA = Path(__file__).with_name("schema.sql")


def build(settings: Settings, db_path: Path, with_embeddings: bool) -> dict:
    sources = default_sources(settings.resolve(settings.pdf_dir), settings.resolve(settings.web_dir),
                              settings.resolve(settings.project_docs_dir))
    chunks = load_all(sources)

    tmp = db_path.with_suffix(".building.db")
    tmp.unlink(missing_ok=True)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(tmp)
    try:
        conn.executescript(SCHEMA.read_text(encoding="utf-8"))
        stats = load_structured(conn, settings.resolve(settings.structured_data_dir))
        conn.executemany("INSERT INTO chunks (text, metadata_json) VALUES (?, ?)",
                         [(c.page_content, json.dumps(c.metadata, ensure_ascii=False)) for c in chunks])
        stats["chunks"] = len(chunks)
        stats["embeddings"] = 0

        if with_embeddings:
            embeddings = OpenAIEmbeddings(model=settings.embedding_model, dimensions=settings.embedding_dimensions,
                                          api_key=settings.openai_api_key)
            store = SQLiteVec(table=VECTOR_TABLE, connection=conn, embedding=embeddings)
            for i in range(0, len(chunks), 200):
                store.add_documents(chunks[i:i + 200])
            stats["embeddings"] = len(chunks)
            conn.execute("INSERT INTO meta VALUES ('embedding_model', ?)", (settings.embedding_model,))
            conn.execute("INSERT INTO meta VALUES ('embedding_dimensions', ?)", (str(settings.embedding_dimensions),))

        conn.execute("INSERT INTO meta VALUES ('built_at', ?)", (datetime.now(UTC).isoformat(timespec="seconds"),))
        conn.execute("INSERT INTO meta VALUES ('stats', ?)", (json.dumps(stats),))
        conn.commit()
    finally:
        conn.close()
    os.replace(tmp, db_path)
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Construye data/knowledge.db")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--embeddings", action="store_true", help="exigir embeddings (falla sin OPENAI_API_KEY)")
    group.add_argument("--no-embeddings", action="store_true", help="omitir embeddings")
    parser.add_argument("--db", type=Path, help="ruta de salida (por defecto DB_PATH)")
    args = parser.parse_args()

    settings = get_settings()
    if args.embeddings and not settings.llm_enabled:
        parser.error("--embeddings requiere OPENAI_API_KEY en .env")
    with_embeddings = settings.llm_enabled and not args.no_embeddings
    db_path = settings.resolve(args.db or settings.db_path)
    stats = build(settings, db_path, with_embeddings)
    print(f"Base creada en {db_path}")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    if not with_embeddings:
        print("Sin embeddings: la búsqueda usará solo BM25 (palabras clave).")


if __name__ == "__main__":
    main()
