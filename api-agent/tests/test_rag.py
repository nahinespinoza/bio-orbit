"""Ingesta y recuperación (solo BM25: sin embeddings ni clave de OpenAI)."""

import json

from app.rag.db import connect, has_vectors
from app.rag.retriever import build_retriever, spanish_tokens
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
