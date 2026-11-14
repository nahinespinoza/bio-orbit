"""Recuperador híbrido con componentes de LangChain.

- BM25Retriever (langchain-community): palabras clave, se arma en memoria desde la tabla `chunks`.
- SQLiteVec (langchain-community): similitud semántica, solo si la ingesta generó embeddings y hay clave.
- EnsembleRetriever (langchain-classic): fusiona ambos con Reciprocal Rank Fusion.

MVP: SQLiteVec y BM25Retriever no filtran por metadatos; el blog de baja fiabilidad no se indexa.
"""

import json
import re
import sqlite3
import unicodedata

from langchain_classic.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_community.vectorstores import SQLiteVec
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_openai import OpenAIEmbeddings

from app.config import Settings
from app.rag.db import VECTOR_TABLE, has_vectors

_STOPWORDS = set(
    "el la los las un una unos unas de del al a en y o u que con por para se su sus es son como mas pero lo le les "
    "me mi mis yo tu si no ya ni hay esta este esto ese esa cual cuales donde cuando puedo debo tengo quiero sembrar "
    "siembro mejor cuanto cuantos cuanta cuantas necesita necesito sirve hacer hago tiene tienen sobre entre segun".split()
)


def _stem(term: str) -> str:
    for suffix in ("ones", "es", "s"):
        if term.endswith(suffix) and len(term) - len(suffix) >= 4:
            return term[: -len(suffix)] + ("on" if suffix == "ones" else "")
    return term


def spanish_tokens(text: str) -> list[str]:
    """Preprocesado para BM25: sin tildes, minúsculas, sin palabras vacías y con raíz mínima de plurales."""
    plain = unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode().lower()
    return [_stem(t) for t in re.findall(r"[a-z0-9]{2,}", plain) if t not in _STOPWORDS]


def load_chunk_documents(conn: sqlite3.Connection) -> list[Document]:
    rows = conn.execute("SELECT chunk_id, text, metadata_json FROM chunks ORDER BY chunk_id").fetchall()
    return [Document(page_content=r["text"], metadata={**json.loads(r["metadata_json"]), "chunk_id": r["chunk_id"]},
                     id=str(r["chunk_id"])) for r in rows]


def build_retriever(conn: sqlite3.Connection, settings: Settings) -> tuple[BaseRetriever, str]:
    """Devuelve (retriever, modo). Modo: 'hybrid' (BM25 + vectores) o 'bm25'."""
    docs = load_chunk_documents(conn)
    bm25 = BM25Retriever.from_documents(docs, preprocess_func=spanish_tokens, k=settings.rag_top_k)
    if not (settings.llm_enabled and has_vectors(conn)):
        return bm25, "bm25"

    embeddings = OpenAIEmbeddings(model=settings.embedding_model, dimensions=settings.embedding_dimensions,
                                  api_key=settings.openai_api_key)
    vector = SQLiteVec(table=VECTOR_TABLE, connection=conn, embedding=embeddings)
    ensemble = EnsembleRetriever(retrievers=[bm25, vector.as_retriever(search_kwargs={"k": settings.rag_top_k})],
                                 weights=[0.5, 0.5])
    return ensemble, "hybrid"


def format_citation(doc: Document) -> dict:
    m = doc.metadata
    return {
        "source_id": m.get("source_id"),
        "title": m.get("title"),
        "doc_kind": m.get("doc_kind"),
        "reliability": m.get("reliability_level"),
        "page": m.get("page"),
        "page_label": m.get("page_label"),
        "section": m.get("section"),
    }
