"""Recuperador híbrido con componentes de LangChain.

- BM25Retriever (langchain-community): palabras clave, se arma en memoria desde la tabla `chunks`.
- SQLiteVec (langchain-community): similitud semántica, solo si la ingesta generó embeddings y hay clave.
- EnsembleRetriever (langchain-classic): fusiona ambos con Reciprocal Rank Fusion.

SQLiteVec y BM25Retriever no filtran por metadatos: el filtro por cultivo lo hace `SourceSearch` (BM25 sobre el
subconjunto del cultivo + vectorial con k ampliado y filtrado). El blog de baja fiabilidad no se indexa.
"""

import json
import re
import sqlite3
import unicodedata
from dataclasses import dataclass

from langchain_classic.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_community.vectorstores import SQLiteVec
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_openai import OpenAIEmbeddings

from app.config import Settings
from app.engine.models import KnowledgeBase
from app.engine.validation import resolve_crop
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


def _vector_store(conn: sqlite3.Connection, settings: Settings) -> SQLiteVec:
    embeddings = OpenAIEmbeddings(model=settings.embedding_model, dimensions=settings.embedding_dimensions,
                                  api_key=settings.openai_api_key)
    return SQLiteVec(table=VECTOR_TABLE, connection=conn, embedding=embeddings)


def _uses_vectors(conn: sqlite3.Connection, settings: Settings) -> bool:
    return settings.llm_enabled and has_vectors(conn)


def build_retriever(conn: sqlite3.Connection, settings: Settings) -> tuple[BaseRetriever, str]:
    """Devuelve (retriever, modo). Modo: 'hybrid' (BM25 + vectores) o 'bm25'."""
    docs = load_chunk_documents(conn)
    bm25 = BM25Retriever.from_documents(docs, preprocess_func=spanish_tokens, k=settings.rag_top_k)
    if not _uses_vectors(conn, settings):
        return bm25, "bm25"
    vector = _vector_store(conn, settings)
    ensemble = EnsembleRetriever(retrievers=[bm25, vector.as_retriever(search_kwargs={"k": settings.rag_top_k})],
                                 weights=[0.5, 0.5])
    return ensemble, "hybrid"


class _CropFiltered(BaseRetriever):
    """Pide más resultados al recuperador interno y se queda con los `k` primeros que mencionan el cultivo."""

    inner: BaseRetriever
    crop: str
    k: int

    def _get_relevant_documents(self, query: str, *, run_manager: CallbackManagerForRetrieverRun) -> list[Document]:
        return [d for d in self.inner.invoke(query) if self.crop in d.metadata.get("crops", [])][: self.k]


@dataclass(frozen=True)
class SearchResult:
    docs: list[Document]
    crop: str | None      # id del cultivo resuelto, o None
    filtered: bool        # False si no se pidió cultivo o si se buscó sin filtro
    suggestions: tuple[str, ...] = ()   # cultivos del pool parecidos, si el nombre no se reconoció


class SourceSearch:
    """Búsqueda en las fuentes, opcionalmente solo en los fragmentos que mencionan un cultivo.

    Sin cultivo usa el recuperador de siempre. Con cultivo arma (y guarda en caché) un recuperador sobre ese
    subconjunto. Si el cultivo no se reconoce, no tiene fragmentos o la búsqueda filtrada no trae nada, busca sin filtro.
    """

    def __init__(self, conn: sqlite3.Connection, settings: Settings, kb: KnowledgeBase) -> None:
        self._conn, self._settings, self._kb = conn, settings, kb
        self._docs = load_chunk_documents(conn)
        self._base, self.mode = build_retriever(conn, settings)
        self._cache: dict[str, BaseRetriever | None] = {}

    def _for_crop(self, crop_id: str) -> BaseRetriever | None:
        if crop_id not in self._cache:
            subset = [d for d in self._docs if crop_id in d.metadata.get("crops", [])]
            retriever: BaseRetriever | None = None
            if subset:
                k = self._settings.rag_top_k
                retriever = BM25Retriever.from_documents(subset, preprocess_func=spanish_tokens, k=k)
                if self.mode == "hybrid":
                    vector = _vector_store(self._conn, self._settings).as_retriever(search_kwargs={"k": k * 10})
                    retriever = EnsembleRetriever(retrievers=[retriever, _CropFiltered(inner=vector, crop=crop_id, k=k)],
                                                  weights=[0.5, 0.5])
            self._cache[crop_id] = retriever
        return self._cache[crop_id]

    def search(self, query: str, crop: str | None = None) -> SearchResult:
        crop_id, close = resolve_crop(crop, self._kb) if crop else (None, [])
        if crop_id is not None:
            retriever = self._for_crop(crop_id)
            docs = retriever.invoke(query) if retriever is not None else []
            if docs:
                return SearchResult(docs, crop_id, True)
        suggestions = tuple(s for s in close if s in self._kb.crops)
        return SearchResult(self._base.invoke(query), crop_id, False, suggestions)


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
