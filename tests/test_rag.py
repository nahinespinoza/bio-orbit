"""Ingesta y recuperación (solo BM25: sin embeddings ni clave de OpenAI)."""

import json

from app.rag.db import connect, has_vectors
from app.rag.retriever import build_retriever, spanish_tokens
from ingestion.documents import detect_crops


def test_ingestion_loads_structured_data_and_chunks(settings):
    conn = connect(settings.resolve(settings.db_path))
    assert conn.execute("SELECT count(*) FROM crops").fetchone()[0] == 27
    assert conn.execute("SELECT count(*) FROM transitions").fetchone()[0] == 162
    docs = {json.loads(r[0])["doc_id"] for r in conn.execute("SELECT metadata_json FROM chunks")}
    assert "fao-guia-de-campo-cultivos-andinos.pdf" in docs
    assert "redalyc-rentabilidad-cultivos-rotacion-tumbaco-2023.html" in docs
    assert not any("radeco" in d for d in docs), "el blog de Radeco no se indexa"
    assert not has_vectors(conn)


def test_bm25_finds_andean_weevil_in_field_guide(settings):
    retriever, mode = build_retriever(connect(settings.resolve(settings.db_path)), settings)
    assert mode == "bm25"
    docs = retriever.invoke("gorgojo de los Andes en papa")
    assert any(d.metadata["source_id"] == 2 and "Premnotrypes" in d.page_content for d in docs)


def test_bm25_finds_tumbaco_study(settings):
    retriever, _ = build_retriever(connect(settings.resolve(settings.db_path)), settings)
    docs = retriever.invoke("rendimiento del fréjol en Tumbaco")
    assert docs[0].metadata["source_id"] == 4


def test_chunks_have_citation_metadata(settings):
    retriever, _ = build_retriever(connect(settings.resolve(settings.db_path)), settings)
    doc = retriever.invoke("costos de producción del haba jornales")[0]
    for key in ("title", "reliability_level", "doc_kind", "crops"):
        assert key in doc.metadata
    assert doc.metadata["page"] is not None


def test_spanish_tokens_and_crop_detection():
    assert spanish_tokens("¿Cuántos jornales necesita el haba?") == ["jornal", "haba"]
    assert detect_crops("Rotar tarwi después de la papa") == ["papa", "chocho"]
