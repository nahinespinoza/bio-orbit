"""Contrato del motor: las mismas 23 pruebas de local/agente-rotacion/tests/pruebas.mjs, ahora en Python."""

import pytest

from app.engine.models import KnowledgeBase
from app.engine.recommender import recommend
from app.engine.validation import validate_plot

BASE = {"climate": {"altitude_masl": 2800, "irrigation": "yes"}, "soil": {"fertility": "medium"}}
RECOVERY = {"pasto", "barbecho", "abono"}


def run(kb: KnowledgeBase, **plot) -> dict:
    return recommend({**BASE, **plot}, kb)


def names(r: dict) -> list[str]:
    return [r["recommendation"]["crop"], *(a["crop"] for a in r["alternatives"])]


def sequence(r: dict) -> list[str]:
    return [s["crop"] for s in r["rotation"]["sequence"]] if r.get("rotation") else []


def codes(kb: KnowledgeBase, plot: dict, **kw) -> list[str]:
    return [e["code"] for e in validate_plot(plot, kb, **kw).errors]


# 1. Tierra nueva
def test_new_land_starts_from_starters_without_f1_f3(kb):
    r = run(kb, new_land=True, priorities=["market_value"])
    assert r["status"] == "ok"
    assert all(kb.crops[c].has_tag("starter") for c in names(r))
    assert any(w["code"] == "NEW_LAND" for w in r["warnings"])
    assert not any(d["filter"] in ("F1", "F2", "F3") for d in r["discarded"])


# 2. Solo papa como previo
def test_only_potato_follows_graph_and_applies_f1(kb):
    r = run(kb, previous_crops=["papa"], priorities=["fewer_pests"])
    assert r["status"] == "ok"
    assert "papa" not in names(r)
    successors = {e.to_crop for e in kb.edges["papa"]}
    assert set(names(r)) <= successors
    assert any(d["crop"] == "papa" and d["filter"] == "F1" for d in r["discarded"])


# 3. Papa y cebada
def test_potato_and_barley_last_crop_rules_and_rotation_respects_f1_f2(kb):
    r = run(kb, previous_crops=["cebada", "papa"], priorities=["fewer_pests", "speed"])
    assert r["status"] == "ok"
    assert "cebada" not in names(r) and "trigo" not in names(r), "cereal tras cereal (F2)"
    seq = sequence(r)
    for a, b in zip(seq, seq[1:]):
        assert a != b
        assert kb.crops[a].family != kb.crops[b].family, f"F2 roto en {a}→{b}"
    assert len(set(seq)) == len(seq)


# 4. Suelo pobre frente a fértil
def test_poor_vs_fertile_soil_changes_recommendation(kb):
    plot = {"previous_crops": ["papa"], "priorities": ["low_labor"], "climate": {"altitude_masl": 2800, "irrigation": "yes"}}
    poor = recommend({**plot, "soil": {"fertility": "low"}}, kb)
    rich = recommend({**plot, "soil": {"fertility": "high"}}, kb)
    assert poor["recommendation"]["crop"] != rich["recommendation"]["crop"]
    assert poor["recommendation"]["crop"] in RECOVERY
    assert rich["recommendation"]["crop"] not in RECOVERY


def test_poor_soil_lowers_aptitude_of_demanding_crop(kb):
    plot = {"previous_crops": ["quinua"], "priorities": ["market_value"], "climate": {"altitude_masl": 2800, "irrigation": "yes"}}
    poor = recommend({**plot, "soil": {"fertility": "low"}}, kb)
    rich = recommend({**plot, "soil": {"fertility": "high"}}, kb)
    assert poor["recommendation"]["aptitude_score"] != rich["recommendation"]["aptitude_score"]


# 5. Mismas condiciones, prioridades distintas
def test_different_priorities_give_different_results(kb):
    results = {p: run(kb, previous_crops=["papa"], priorities=[p]) for p in ("market_value", "speed", "fewer_pests", "low_labor")}
    assert len({r["recommendation"]["crop"] for r in results.values()}) >= 2
    assert len({tuple(sequence(r)) for r in results.values()}) >= 2


# 6. Una, dos y tres prioridades
@pytest.mark.parametrize(("n", "weights"), [(1, [1.0]), (2, [0.6, 0.4]), (3, [0.5, 0.3, 0.2])])
def test_weights_by_number_of_priorities(kb, n, weights):
    r = run(kb, previous_crops=["papa", "cebada"], priorities=["market_value", "speed", "fewer_pests"][:n])
    assert [p["weight"] for p in r["priority_weights"]] == weights
    assert len(r["recommendation"]["breakdown"]["priorities"]) == n
    assert abs(sum(weights) - 1) < 1e-9
    assert 1 <= len(r["alternatives"]) <= 2


def test_priority_order_matters(kb):
    a = run(kb, previous_crops=["papa"], priorities=["market_value", "low_labor"])
    b = run(kb, previous_crops=["papa"], priorities=["low_labor", "market_value"])
    assert [p["priority"] for p in a["recommendation"]["breakdown"]["priorities"]] == ["market_value", "low_labor"]
    assert [p["priority"] for p in b["recommendation"]["breakdown"]["priorities"]] == ["low_labor", "market_value"]
    assert a["recommendation"]["score"] != b["recommendation"]["score"] or a["recommendation"]["crop"] != b["recommendation"]["crop"]


# 7. Filtros duros y datos faltantes
def test_f2_no_tomato_after_potato_even_with_source5(kb):
    r = run(kb, previous_crops=["papa"], priorities=["market_value"], use_source5=True)
    assert "tomate" not in names(r)


def test_f4_climate_discards_by_altitude(kb):
    r = recommend({"previous_crops": ["papa"], "priorities": ["speed"], "climate": {"altitude_masl": 3600, "irrigation": "yes"}}, kb)
    discarded = {d["crop"] for d in r["discarded"] if d["filter"] == "F4-climate"}
    assert discarded & {"maiz", "quinua", "amaranto"}


def test_f4_soil_discards_by_ph(kb):
    r = run(kb, previous_crops=["papa"], priorities=["speed"], soil={"fertility": "medium", "ph": 4.0})
    assert any(d["filter"] == "F4-soil" for d in r["discarded"])


def test_f3_broad_bean_hosts_andean_weevil(kb):
    without = run(kb, previous_crops=["papa"], priorities=["speed"])
    assert not any(d["filter"] == "F3" for d in without["discarded"])
    r = run(kb, previous_crops=["papa"], priorities=["speed"], last_pest=["gorgojo de los andes"])
    assert any(d["filter"] == "F3" and d["crop"] == "haba" for d in r["discarded"])
    assert "haba" not in names(r)


def test_unknown_soil_warns_and_does_not_discard(kb):
    r = recommend({"previous_crops": ["papa"], "priorities": ["speed"]}, kb)
    assert r["status"] == "ok"
    codes_ = {w["code"] for w in r["warnings"]}
    assert {"UNKNOWN_SOIL", "UNKNOWN_ALTITUDE"} <= codes_


def test_missing_market_data_scores_neutral(kb):
    r = run(kb, previous_crops=["cebada"], priorities=["market_value"])
    for t in [r["recommendation"], *r["alternatives"]]:
        for p in t["breakdown"]["priorities"]:
            if p["missing"]:
                assert p["value"] == 50


# 8. Entradas inválidas
def test_too_many_priorities_is_not_truncated(kb):
    r = run(kb, previous_crops=["papa"], priorities=["market_value", "speed", "fewer_pests", "low_labor"])
    assert r["status"] == "invalid_input"
    assert "TOO_MANY_PRIORITIES" in [e["code"] for e in r["errors"]]


def test_duplicate_priorities(kb):
    assert "DUPLICATE_PRIORITIES" in codes(kb, {"previous_crops": ["papa"], "priorities": ["speed", "speed"]})


def test_missing_or_invalid_priority(kb):
    assert "NO_PRIORITIES" in codes(kb, {"previous_crops": ["papa"], "priorities": []})
    assert "INVALID_PRIORITY" in codes(kb, {"previous_crops": ["papa"], "priorities": ["barato"]})


def test_unknown_crop_with_suggestion(kb):
    errors = validate_plot({"previous_crops": ["papaa", "cebada"], "priorities": ["speed"]}, kb).errors
    e = next(x for x in errors if x["code"] == "UNKNOWN_CROP")
    assert "papa" in e["suggestions"]
    assert "UNKNOWN_CROP" in codes(kb, {"previous_crops": ["dragonfruit"], "priorities": ["speed"]})


def test_unknown_crop_accepted_only_when_allowed(kb):
    v = validate_plot({"previous_crops": ["dragonfruit", "papa"], "priorities": ["speed"]}, kb, allow_unknown_crops=True)
    assert v.ok and any(w["code"] == "UNKNOWN_PREVIOUS_CROP" for w in v.warnings)


def test_other_invalid_inputs(kb):
    assert "MISSING_PREVIOUS_CROPS" in codes(kb, {"priorities": ["speed"]})
    assert "NEW_LAND_WITH_CROPS" in codes(kb, {"new_land": True, "previous_crops": ["papa"], "priorities": ["speed"]})
    assert "INVALID_VALUE" in codes(kb, {"previous_crops": ["papa"], "priorities": ["speed"], "soil": {"ph": 15}})
    assert "INVALID_VALUE" in codes(kb, {"previous_crops": ["papa"], "priorities": ["speed"], "soil": {"fertility": "riquisima"}})
    assert "INVALID_VALUE" in codes(kb, {"previous_crops": ["papa"], "priorities": ["speed"], "rotation_cycles": 0})


def test_aliases(kb):
    v = validate_plot({"previous_crops": ["Tarwi", "ataco", "Fríjol"], "priorities": ["speed"]}, kb)
    assert v.plot.previous_crops == ["chocho", "amaranto", "frejol"]


# 9. Rotación
@pytest.mark.parametrize("cycles", [3, 5])
def test_rotation_length_is_configurable(kb, cycles):
    r = run(kb, previous_crops=["papa"], priorities=["market_value", "fewer_pests"], rotation_cycles=cycles)
    rot = r["rotation"]
    assert rot["cycles"] <= cycles
    if rot["cycles"] == cycles:
        assert rot["ends_with_ender"] or rot["warnings"]


def test_every_crop_has_profile_with_sources_and_confidence(kb):
    for crop in kb.crops.values():
        assert crop.confidence in ("high", "medium", "low")
        assert isinstance(crop.sources, tuple)


# Valores de referencia verificados contra el motor JS (16/16 casos idénticos al pasarlo a Python).
def test_reference_values_match_js_engine(kb):
    r = run(kb, previous_crops=["cebada", "papa"], priorities=["fewer_pests", "speed"])
    assert names(r) == ["mashua", "arveja", "amaranto"]
    assert sequence(r) == ["mashua", "cebada", "amaranto", "abono"]
    r = run(kb, previous_crops=["papa", "cebada"], priorities=["speed", "fewer_pests"])
    assert (r["recommendation"]["crop"], r["recommendation"]["score"]) == ("amaranto", 61.0)
