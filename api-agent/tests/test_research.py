"""La investigación de las fichas entra al RAG y se lee como evidencia por cultivo y tema."""

import json

from app.rag.db import connect
from app.repository.crops import STRUCTURED_DIR
from app.repository.research import research_evidence
from ingestion.research import research_documents

DOC = json.loads((STRUCTURED_DIR / "cultivos.json").read_text(encoding="utf-8"))


def test_research_documents_one_per_block():
    docs = research_documents(DOC)
    blocks = sum(len(f.get("indicadores", {})) for f in DOC["cultivos"].values())
    gaps = sum(1 for f in DOC["cultivos"].values() if f.get("huecos_indicadores"))
    assert len(docs) == blocks + gaps
    d = next(d for d in docs if d.metadata["doc_id"] == "cultivos.json#papa/sanidad_lancha")
    assert d.metadata["crops"] == ["papa"] and d.metadata["tema"] == "sanidad" and d.metadata["doc_kind"] == "crop_research"
    assert not d.page_content.lstrip().startswith("{") and "http" in d.page_content


def test_unknown_research_key_goes_to_otros():
    fake = {"cultivos": {"papa": {"nombre": "Papa", "indicadores": {"clave_nueva": {"nota": "x"}}}}}
    assert research_documents(fake)[0].metadata["tema"] == "otros"


def test_other_region_warning_in_text():
    docs = [d for d in research_documents(DOC) if d.metadata.get("origen")]
    assert docs and all("otra región" in d.page_content.lower() for d in docs)


def test_research_in_index_and_evidence(settings):
    conn = connect(settings.resolve(settings.db_path))
    ev = research_evidence(conn, "papa", ["sanidad", "helada"])
    assert ev["sanidad"] and "http" not in " ".join(ev["sanidad"])
    assert all(len(t) <= 1200 for ts in ev.values() for t in ts)
    assert research_evidence(conn, "papa", ["sanidad"], compact=False)["sanidad"]
