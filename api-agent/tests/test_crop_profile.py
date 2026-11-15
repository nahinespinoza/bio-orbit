"""Ficha por secciones: solo lo pedido, nunca los indicadores de investigación."""

import json

import pytest

from app.rag.db import connect
from app.repository.crops import PROFILE_SECTIONS, get_crop_sections

HEADER = {"crop_id", "name", "family", "crop_type", "tags", "confidence", "alcance_geografico", "sections"}


@pytest.fixture
def conn(settings):
    return connect(settings.resolve(settings.db_path))


def test_sections_returns_only_requested(conn, kb):
    r = get_crop_sections(conn, "papa", ["plagas", "mano_obra"], kb.sensitivities)
    assert set(r) == HEADER
    assert set(r["sections"]) == {"plagas", "mano_obra"}
    assert r["sections"]["plagas"]                                   # dato real de la ficha
    assert "indicadores" not in json.dumps(r, ensure_ascii=False)


def test_sections_is_much_smaller_than_full_profile(conn, kb):
    r = get_crop_sections(conn, "papa", ["plagas"], kb.sensitivities)
    assert len(json.dumps(r, ensure_ascii=False)) < 2000


def test_sections_siguientes_and_fuentes(conn, kb):
    r = get_crop_sections(conn, "papa", ["siguientes", "fuentes"], kb.sensitivities)["sections"]
    assert r["siguientes"] and {"to_crop", "kind", "source_note"} <= set(r["siguientes"][0])
    assert set(r["fuentes"]) == {"citas", "detalle"} and r["fuentes"]["detalle"]


def test_sections_sensitivities_present(conn, kb):
    r = get_crop_sections(conn, "papa", ["sensibilidades"], kb.sensitivities)["sections"]
    assert r["sensibilidades"]["hospedero_lancha"]["valor"] is True


def test_sections_sensitivities_missing(conn, kb):
    r = get_crop_sections(conn, "barbecho", ["sensibilidades"], kb.sensitivities)["sections"]
    assert r["sensibilidades"]["valor"] is None and "Sin datos" in r["sensibilidades"]["nota"]


def test_sections_rejects_research_fields(conn, kb):
    assert "indicadores" not in PROFILE_SECTIONS
    with pytest.raises(ValueError):
        get_crop_sections(conn, "papa", ["indicadores"], kb.sensitivities)


def test_sections_unknown_crop(conn, kb):
    assert get_crop_sections(conn, "xyz", ["plagas"], kb.sensitivities) is None
