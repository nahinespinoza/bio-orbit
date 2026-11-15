"""POST /v1/recommendations: candidatos agronómicos, payload con evidencia, reglas de combinación y contrato.
El modelo es falso (Scorer guionado): no se llama a OpenAI."""

import json

import pytest
from fastapi.testclient import TestClient

from app.advisor.combine import combine
from app.advisor.payload import MAX_BYTES, build_payload, size
from app.advisor.request import AdvisorRequest, to_plot_raw
from app.advisor.scoring import Criterion, CropScore, ScoringOutput
from app.engine.conditions import plot_conditions
from app.engine.ranking import rank_by_aptitude
from app.engine.validation import validate_plot
from app.main import create_app
from app.rag.db import connect
from app.repository.crops import STRUCTURED_DIR

RS = json.loads((STRUCTURED_DIR / "remote_sensing.json").read_text(encoding="utf-8"))
REQ = {"previous_crop": "papa", "priority": "low_labor", "irrigation": "rain_only", "waterlogging": "no"}


def _plot(kb, raw):
    v = validate_plot(raw, kb)
    assert v.ok, v.errors
    return v.plot


def _crit(score, refs=()):
    return Criterion(score=score, reason="motivo", references=list(refs))


class FakeScorer:
    """Califica a cada candidato del payload con notas fijas (o las de `by_crop`)."""

    def __init__(self, by_crop=None, extra=()):
        self.by_crop, self.extra, self.payloads = by_crop or {}, list(extra), []

    def __call__(self, payload):
        self.payloads.append(payload)
        scores = [CropScore(crop=c["crop"], priority=_crit(self.by_crop.get(c["crop"], (70, 80))[0], ["F1", "X99"]),
                            risk=_crit(self.by_crop.get(c["crop"], (70, 80))[1]), summary=f"Resumen de {c['nombre']}")
                  for c in payload["candidatos"]]
        return ScoringOutput(scores=scores + self.extra, how_to_compare="Compare la afinidad.")


def _cand(crop, aptitude=60.0, missing=False, advisories=(), confidence="high"):
    pdata = {"detail": "dato", "source": "F1", "confidence": "high", "missing": missing}
    return {"crop": crop, "name": crop.title(), "aptitude": aptitude, "transition": None, "confidence": confidence,
            "priority_data": {p: pdata for p in ("market_value", "speed", "fewer_pests", "low_labor")},
            "advisories": [{"level": lv, "message": "m"} for lv in advisories], "rotation": None}


# --- Motor: candidatos agronómicos ------------------------------------------------------------------------

def test_rank_by_aptitude_top5_no_priorities(kb):
    base = {"previous_crops": ["papa"], "climate": {"altitude_masl": 3588, "irrigation": "no"}}
    a = rank_by_aptitude(_plot(kb, {**base, "priorities": ["market_value"]}), kb)
    b = rank_by_aptitude(_plot(kb, {**base, "priorities": ["low_labor"]}), kb)
    assert a["status"] == "ok" and 1 <= len(a["candidates"]) <= 5
    assert [c["crop"] for c in a["candidates"]] == [c["crop"] for c in b["candidates"]]   # la prioridad no ordena
    apt = [c["aptitude"] for c in a["candidates"]]
    assert apt == sorted(apt, reverse=True)
    assert all(c["rotation"] is not None and "low_labor" in c["priority_data"] for c in a["candidates"])


def test_rank_new_land(kb):
    r = rank_by_aptitude(_plot(kb, {"new_land": True, "priorities": ["speed"], "climate": {"altitude_masl": 3588}}), kb)
    assert r["status"] == "ok" and all(kb.crops[c["crop"]].has_tag("starter") for c in r["candidates"])


# --- Petición y payload -----------------------------------------------------------------------------------

def test_request_translation():
    req = AdvisorRequest(previous_crop="cebada", priority="speed", irrigation="pump", waterlogging="long")
    raw = to_plot_raw(req, "cebada", 3588.0)
    assert raw == {"priorities": ["speed"], "climate": {"altitude_masl": 3588.0, "irrigation": "yes"},
                   "soil": {"drainage": "poor"}, "previous_crops": ["cebada"]}
    assert to_plot_raw(req.model_copy(update={"irrigation": "rain_only"}), None, None)["climate"]["irrigation"] == "no"
    assert to_plot_raw(req, None, None)["new_land"] is True


def test_payload_evidence_active_topics_and_cap(settings, kb):
    conn = connect(settings.resolve(settings.db_path))
    req = AdvisorRequest(**REQ)
    ranked = rank_by_aptitude(_plot(kb, to_plot_raw(req, "papa", 3588.0)), kb)["candidates"]
    cond = plot_conditions(RS)
    payload, refs, trimmed = build_payload(req, "Papa", cond, ranked, conn, scope_applies=True)
    assert size(payload) <= MAX_BYTES
    active = set(cond["temas_activos"])
    for c in payload["candidatos"]:
        if isinstance(c["evidencia"], dict):
            assert set(c["evidencia"]) <= active
            for items in c["evidencia"].values():
                for i in items if isinstance(items, list) else []:
                    assert i["ref"] in refs and "http" not in i["texto"]
    assert set(payload["referencias_disponibles"]) == set(refs)
    assert payload["candidatos"][0]["dato_prioridad"].keys() == {"detalle", "fuente", "sin_dato"}


# --- Combinación ------------------------------------------------------------------------------------------

def _score(*items):
    return ScoringOutput(scores=[CropScore(crop=c, priority=_crit(p), risk=_crit(r), summary="s") for c, p, r in items],
                         how_to_compare="x")


def _ev(crop, items):
    return {"crop": crop, "evidencia": {"sanidad": items, "ciclo_siembra": []}}


def test_combine_weights():
    out = combine([_cand("haba", aptitude=50)], [_ev("haba", [{"ref": "I1", "texto": "dato andino"}])],
                  _score(("haba", 80, 90)), "low_labor", {}, ["sanidad"])
    assert out[0]["affinity"] == round(0.30 * 80 + 0.40 * 90 + 0.30 * 50, 1) and out[0]["rules_applied"] == []


def test_combine_rules_1_to_5():
    good = [{"ref": "I1", "texto": "dato andino"}]
    weak = [{"ref": "I2", "texto": "Dato de otra región: Australia."}]
    cands = [_cand("a", missing=True), _cand("b", advisories=["ALTO"]), _cand("c", advisories=["MEDIO"]),
             _cand("d"), _cand("e"), _cand("f")]
    ev = [_ev("a", good), _ev("b", good), _ev("c", good), _ev("d", weak), _ev("e", []), _ev("f", good)]
    out = {c["crop"]: c for c in combine(cands, ev, _score(("a", 90, 90), ("b", 90, 95), ("c", 90, 95), ("d", 90, 10),
                                                           ("e", 90, 95), ("f", 100, 20)), "low_labor", {}, ["sanidad"])}
    assert out["a"]["why"][0]["score"] == 30 and "prioridad_sin_dato" in out["a"]["rules_applied"]       # regla 1
    assert out["b"]["why"][1]["score"] == 40 and out["c"]["why"][1]["score"] == 70                     # regla 2
    assert out["d"]["why"][1]["score"] == 50 and "evidencia_debil" in out["d"]["rules_applied"]         # regla 3
    assert out["e"]["why"][1]["score"] == 60 and "sin_evidencia" in out["e"]["rules_applied"]           # regla 4
    assert out["f"]["affinity"] <= 40                                                                  # regla 5
    assert out["a"]["confidence"] == "media" and out["e"]["confidence"] == "media"


def test_combine_ignores_unknown_and_fills_missing():
    out = combine([_cand("haba"), _cand("oca")], [_ev("haba", []), _ev("oca", [])],
                  _score(("haba", 80, 80), ("tomate", 100, 100)), "speed", {}, [])
    crops = {c["crop"]: c for c in out}
    assert set(crops) == {"haba", "oca"}
    assert crops["oca"]["why"][0]["score"] == 60 and "sin_calificacion_del_modelo" in crops["oca"]["rules_applied"]


def test_combine_drops_unknown_references():
    s = ScoringOutput(scores=[CropScore(crop="haba", priority=_crit(80, ["F1", "X9"]), risk=_crit(80, ["I1"]), summary="s")],
                      how_to_compare="x")
    out = combine([_cand("haba")], [_ev("haba", [])], s, "speed", {"F1": {}, "I1": {}}, [])
    assert out[0]["why"][0]["references"] == ["F1"] and out[0]["why"][1]["references"] == ["I1"]


# --- Endpoint ---------------------------------------------------------------------------------------------

@pytest.fixture
def client_with(settings):
    clients = []

    def factory(scorer):
        c = TestClient(create_app(settings, scorer=scorer))
        c.__enter__()
        clients.append(c)
        return c

    yield factory
    for c in clients:
        c.__exit__(None, None, None)


def test_endpoint_contract(client_with):
    scorer = FakeScorer(by_crop={})
    r = client_with(scorer).post("/v1/recommendations", json=REQ)
    assert r.status_code == 200
    b = r.json()
    assert b["status"] == "ok" and 0 <= b["recommendation"]["affinity"] <= 100
    opts = [b["recommendation"], *b["alternatives"]]
    assert 1 <= len(opts) <= 5 and [o["affinity"] for o in opts] == sorted((o["affinity"] for o in opts), reverse=True)
    assert [w["criterion"] for w in b["recommendation"]["why"]] == ["priority", "risk", "aptitude"]
    assert b["recommendation"]["why"][0]["title"] == "Menos trabajo"
    assert b["recommendation"]["rotation"] and b["recommendation"]["confidence"] in ("alta", "media", "baja")
    assert all(s["id"][0] in "FI" for s in b["sources"]) and "X99" not in json.dumps(b)
    assert b["weights"] == {"priority": 0.30, "risk": 0.40, "aptitude": 0.30}
    assert len(scorer.payloads) == 1   # una sola llamada al modelo


def test_endpoint_ignores_request_remote_sensing(client_with):
    # MVP: el JSON de la petición se ignora; manda la copia del servidor
    rs = json.loads(json.dumps(RS))
    rs["output"]["clima_regional_nasa_power"]["semaforos"]["estado_helada"]["codigo"] = "AMARILLO"
    b = client_with(FakeScorer()).post("/v1/recommendations", json={**REQ, "remote_sensing": rs}).json()
    assert "helada" not in b["plot_conditions"]["temas_activos"]


def test_endpoint_waterlogging_activates_excess_water(client_with):
    b = client_with(FakeScorer()).post("/v1/recommendations", json={**REQ, "waterlogging": "long"}).json()
    assert "exceso_agua" in b["plot_conditions"]["temas_activos"]


def test_endpoint_unknown_crop_422(client_with):
    r = client_with(FakeScorer()).post("/v1/recommendations", json={**REQ, "previous_crop": "tomatillo"})
    assert r.status_code == 422 and r.json()["errors"][0]["code"] == "UNKNOWN_CROP"


def test_endpoint_without_model_503(client_with):
    r = client_with(None).post("/v1/recommendations", json=REQ)
    assert r.status_code == 503


# --- Hallazgos de la revisión final ------------------------------------------------------------------------

@pytest.mark.parametrize("rs", [
    {"output": {}},
    {"output": {"clima_regional_nasa_power": {"fecha_fin": "11/11/2026"}}},
    {"output": {"clima_regional_nasa_power": {"fecha_fin": "x", "semaforos": {"estado_riego": "VERDE"}}}},
])
def test_endpoint_partial_remote_sensing_is_ignored(client_with, rs):
    r = client_with(FakeScorer()).post("/v1/recommendations", json={**REQ, "remote_sensing": rs})
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_combine_alto_with_weak_evidence_keeps_cap():
    weak = [{"ref": "I2", "texto": "Dato de otra región: Australia."}]
    out = combine([_cand("b", advisories=["ALTO"])], [_ev("b", weak)], _score(("b", 90, 10)), "low_labor", {}, ["sanidad"])
    assert out[0]["why"][1]["score"] == 40 and "advertencia_alto" in out[0]["rules_applied"]


def test_combine_trimmed_counts_as_no_evidence():
    out = combine([_cand("oca")], [{"crop": "oca", "evidencia": "recortada por tamaño"}], _score(("oca", 90, 95)),
                  "low_labor", {}, ["sanidad"])
    assert out[0]["why"][1]["score"] == 60 and "evidencia_recortada" in out[0]["rules_applied"]


def test_combine_matches_crop_by_case_and_name():
    cands = [_cand("haba"), {**_cand("chocho"), "name": "Chocho (tarwi)"}]
    out = {c["crop"]: c for c in combine(cands, [_ev("haba", []), _ev("chocho", [])],
                                         _score(("Haba", 80, 80), ("Chocho (tarwi)", 70, 70)), "speed", {}, [])}
    assert out["haba"]["why"][0]["score"] == 80 and out["chocho"]["why"][0]["score"] == 70


def test_endpoint_model_scores_nothing_502(client_with):
    r = client_with(lambda payload: _score(("tomate", 90, 90))).post("/v1/recommendations", json=REQ)
    assert r.status_code == 502 and r.json()["detail"]["code"] == "LLM_ERROR"


def test_endpoint_model_failure_502(client_with):
    def broken(payload):
        raise ValueError("salida incompleta")
    from app.advisor.scoring import guarded
    r = client_with(guarded(broken)).post("/v1/recommendations", json=REQ)
    assert r.status_code == 502


@pytest.mark.parametrize("value", ["new_land", "New Land", "tierra nueva"])
def test_endpoint_new_land_variants(client_with, value):
    assert client_with(FakeScorer()).post("/v1/recommendations", json={**REQ, "previous_crop": value}).status_code == 200


def test_rotation_why_plain_text_and_reference():
    from app.advisor.combine import rotation_why
    text, refs = rotation_why({"kind": "source", "source_note": "1 · rotación de haba (año 4: haba, chocho o trigo)"},
                              "Chocho", "Cebada")
    assert refs == ["F1"] and text.startswith("Una fuente agrícola recomienda sembrar chocho después de cebada")
    assert "1 ·" not in text
    text, refs = rotation_why(None, "Papa", None)
    assert refs == [] and "terreno es nuevo" in text
    assert rotation_why({"kind": "general", "source_note": "1 · «cereales» antes del tubérculo"}, "Oca", "Cebada")[0] \
        .startswith("Es una práctica general")


def test_rank_includes_non_commercial(kb):
    # después de cebada a 3 588 m: chocho y oca por la rotación, y el barbecho ya no se descarta por no comercial
    r = rank_by_aptitude(_plot(kb, {"previous_crops": ["cebada"], "priorities": ["low_labor"],
                                    "climate": {"altitude_masl": 3588, "irrigation": "no"}}), kb)
    crops = {c["crop"] for c in r["candidates"]}
    assert "barbecho" in crops and not any(d["filter"] == "NON_COMMERCIAL_RULE" for d in r["discarded"])



def test_rotation_why_fallow_is_not_sown():
    from app.advisor.combine import rotation_why
    text, refs = rotation_why({"kind": "source", "source_note": "2 · muyuy de Cusco (cebada, descanso)"},
                              "Barbecho / descanso", "Cebada", "barbecho")
    assert text.startswith("Una fuente agrícola recomienda dejar el terreno en descanso después de cebada")
    assert "sembrar barbecho" not in text and refs == ["F2"]
    assert "descanso" in rotation_why(None, "Barbecho / descanso", None, "barbecho")[0]
