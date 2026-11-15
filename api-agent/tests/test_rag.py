"""Ingesta y recuperación (solo BM25: sin embeddings ni clave de OpenAI)."""

import json

import pytest

from app.rag.db import connect, has_vectors
from app.rag.retriever import SourceSearch, build_retriever, spanish_tokens
from ingestion.documents import detect_crops


def test_ingestion_loads_structured_data_and_chunks(settings):
    conn = connect(settings.resolve(settings.db_path))
    assert conn.execute("SELECT count(*) FROM crops").fetchone()[0] == 18
    assert conn.execute("SELECT count(*) FROM transitions").fetchone()[0] == 47
    docs = {json.loads(r[0])["doc_id"] for r in conn.execute("SELECT metadata_json FROM chunks")}
    assert "fao-guia-de-campo-cultivos-andinos.pdf" in docs
    assert not any("redalyc" in d for d in docs), "la base se limita a la papa: el estudio de Tumbaco (fréjol-maíz) se retiró"
    assert not any("radeco" in d for d in docs), "el blog de Radeco no se indexa"
    assert not has_vectors(conn)


def test_bm25_finds_andean_weevil_in_field_guide(settings):
    retriever, mode = build_retriever(connect(settings.resolve(settings.db_path)), settings)
    assert mode == "bm25"
    docs = retriever.invoke("gorgojo de los Andes en papa")
    assert any(d.metadata["source_id"] == 2 and "Premnotrypes" in d.page_content for d in docs)


def test_chunks_have_citation_metadata(settings):
    retriever, _ = build_retriever(connect(settings.resolve(settings.db_path)), settings)
    doc = retriever.invoke("costos de producción del haba jornales")[0]
    for key in ("title", "reliability_level", "doc_kind", "crops"):
        assert key in doc.metadata
    assert doc.metadata["page"] is not None


def test_spanish_tokens_and_crop_detection():
    assert spanish_tokens("¿Cuántos jornales necesita el haba?") == ["jornal", "haba"]
    assert detect_crops("Rotar tarwi después de la papa") == ["papa", "chocho"]


def test_remote_sensing_indicators_one_chunk_per_section(settings):
    conn = connect(settings.resolve(settings.db_path))
    rows = [json.loads(r[0]) for r in conn.execute("SELECT metadata_json FROM chunks")]
    sections = [m["section"] for m in rows if m["doc_id"] == "07-indicadores-remote-sensing.md"]
    assert len(sections) >= 28 and len(sections) == len(set(sections)), "cada sección ## debe ser un fragmento único"
    assert any("humedad_raiz_pct" in s for s in sections)


# --- Búsqueda filtrada por cultivo (SourceSearch) --------------------------------------------------------

@pytest.fixture
def sources(settings, kb):
    return SourceSearch(connect(settings.resolve(settings.db_path)), settings, kb)


def test_search_without_crop_matches_old_behavior(sources):
    r = sources.search("gorgojo de los Andes en papa")
    assert not r.filtered and r.crop is None
    assert any(d.metadata["source_id"] == 2 for d in r.docs)


def test_search_filters_by_crop(sources):
    r = sources.search("plagas y enfermedades", crop="quinua")
    assert r.filtered and r.crop == "quinua" and r.docs
    assert all("quinua" in d.metadata["crops"] for d in r.docs)


def test_search_filters_by_alias(sources):
    r = sources.search("rotación", crop="tarwi")
    assert r.crop == "chocho" and all("chocho" in d.metadata["crops"] for d in r.docs)


def test_search_unknown_crop_falls_back(sources):
    r = sources.search("rotación de cultivos", crop="tomate")
    assert not r.filtered and r.crop is None and r.docs


def test_search_crop_without_chunks_falls_back(sources, monkeypatch):
    monkeypatch.setattr(sources, "_docs", [d for d in sources._docs if "haba" not in d.metadata["crops"]])
    sources._cache.clear()
    r = sources.search("rotación", crop="haba")
    assert not r.filtered and r.docs


def test_search_unresolved_crop_keeps_pool_suggestions(sources):
    r = sources.search("plagas", crop="quinoa")
    assert r.crop is None and not r.filtered and r.docs
    assert "quinua" in r.suggestions and all(s in sources._kb.crops for s in r.suggestions)


@pytest.fixture
def hybrid_sources(settings, kb, tmp_path, monkeypatch):
    """Base con vectores falsos y deterministas: ejercita la rama hybrid sin llamar a OpenAI."""
    import shutil

    from langchain_community.vectorstores import SQLiteVec
    from langchain_core.embeddings import DeterministicFakeEmbedding

    import app.rag.retriever as retriever_mod
    from app.rag.db import VECTOR_TABLE
    from app.rag.retriever import load_chunk_documents

    db = tmp_path / "hybrid.db"
    shutil.copy(settings.resolve(settings.db_path), db)
    fake = DeterministicFakeEmbedding(size=settings.embedding_dimensions)
    monkeypatch.setattr(retriever_mod, "OpenAIEmbeddings", lambda **_: fake)
    conn = connect(db)
    SQLiteVec(table=VECTOR_TABLE, connection=conn, embedding=fake).add_documents(load_chunk_documents(conn))
    s = settings.model_copy(update={"openai_api_key": "sk-test", "db_path": db})
    return SourceSearch(conn, s, kb)


def test_hybrid_search_filters_by_crop(hybrid_sources):
    assert hybrid_sources.mode == "hybrid"
    r = hybrid_sources.search("plagas y enfermedades", crop="quinua")
    assert r.filtered and r.crop == "quinua" and r.docs
    assert all("quinua" in d.metadata["crops"] for d in r.docs)
