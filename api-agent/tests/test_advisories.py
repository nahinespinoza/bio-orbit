"""Advertencias del MVP: alerta del remote-sensing × sensibilidad de la ficha.

Se prueba con el snapshot real (knowledge/structured/remote_sensing.json: hoy solo PLAGAS_LANCHA en la ventana más
reciente) y con señales sintéticas para las que hoy no están activas (helada, nutrientes, sequía, suelo saturado)."""

import copy
import json
from dataclasses import replace

from app.engine.advisories import CLOSE, MAX_ADVISORIES, RULES, advisories_for, read_signals
from app.engine.explanation import explain
from app.engine.recommender import recommend
from app.repository.crops import STRUCTURED_DIR, load_advisory_data

ALERT = {"nivel": "ALTO", "mensaje": "prueba", "confirmed": False}


def rules(crop: str, kb, **kw) -> list[str]:
    return [a["rule"] for a in advisories_for(crop, kb, **kw)]


def snapshot() -> dict:
    return json.loads((STRUCTURED_DIR / "remote_sensing.json").read_text(encoding="utf-8"))


def test_lancha_alert_x_potato_host(kb):
    lancha = next(a for a in advisories_for("papa", kb) if a["rule"] == "lancha")
    assert lancha["level"] == "ALTO" and lancha["signal"]["code"] == "PLAGAS_LANCHA"
    assert lancha["crop_field"]["origin"] == "ecuador" and lancha["crop_field"]["sources"]   # con cita
    assert "riesgo" in lancha["message"] and "experto" in lancha["message"]
    assert not lancha["signal"]["confirmed_by_satellite"]                                      # LANCHA_PREVENTIVA


def test_satellite_confirmation_is_said_faithfully(kb):
    sig = {"NUTRIENTES": {**ALERT, "nivel": "MEDIO", "confirmed": True}}
    nutr = advisories_for("papa", kb, signals=sig)[0]
    assert nutr["signal"]["confirmed_by_satellite"]
    # el satélite ve poco verdor (NDRE bajo), no el lavado de nitrógeno: «puede ser», no «ya muestra»
    assert "satélite también ve hojas con poco verdor, que puede ser falta de nitrógeno" in nutr["message"]
    assert "ya muestra" not in nutr["message"]
    lancha = next(a for a in advisories_for("papa", kb) if a["rule"] == "lancha")
    assert "satélite" not in lancha["message"]                          # LANCHA_PREVENTIVA no está confirmada


def test_frost_alert_x_sensitive_phase(kb):
    a = advisories_for("chocho", kb, signals={"HELADAS": {**ALERT, "nivel": "MEDIO"}})[0]
    assert a["rule"] == "helada" and "plántula" in a["message"] and "riesgo medio de helada" in a["message"]


def test_no_data_means_no_advisory(kb):
    frost = {"HELADAS": ALERT, "PLAGAS_LANCHA": ALERT}
    assert rules("lenteja", kb, signals=frost) == []                    # sin sensibilidades con cita de Ecuador/Andes
    assert "helada" not in rules("haba", kb, signals=frost)             # su dato de helada es de Australia: no se usa
    assert "helada" not in rules("papa", kb, signals=frost)             # fase sensible de la papa: fiabilidad baja


def test_signal_absent_means_no_advisory(kb):
    assert advisories_for("papa", kb, signals={}) == []
    assert advisories_for("chocho", kb, signals={"PLAGAS_LANCHA": ALERT}) == []   # chocho no es hospedero de lancha


def test_dry_and_saturated_soil_alerts(kb):
    sig = {"SEQUIA": ALERT, "EXCESO_AGUA": ALERT}
    assert rules("cebada", kb, signals=sig) == ["sequia"]               # sensible a la sequía en formación de polen y espigado
    assert rules("haba", kb, signals=sig) == ["exceso_agua"]            # no soporta el agua estancada
    assert "falta de agua" in advisories_for("cebada", kb, signals=sig)[0]["message"]


def test_max_two_advisories_high_level_first(kb):
    sig = {"HELADAS": {**ALERT, "nivel": "MEDIO"}, "SEQUIA": ALERT, "EXCESO_AGUA": ALERT}
    # el chocho es sensible a helada, sequía y exceso de agua: salen 2 y el nivel ALTO va primero
    out = advisories_for("chocho", kb, signals=sig)
    assert len(out) == MAX_ADVISORIES == 2
    assert out[0]["level"] == "ALTO" and out[1]["level"] == "ALTO"
    assert "helada" not in [a["rule"] for a in out]


def test_unreliable_or_foreign_data_is_ignored(kb):
    sens = copy.deepcopy(kb.sensitivities)
    sens["papa"]["hospedero_lancha"]["origen"] = "otra_region"
    assert "lancha" not in rules("papa", replace(kb, sensitivities=sens))
    sens["papa"]["hospedero_lancha"].update(origen="ecuador", fiabilidad="baja")
    assert "lancha" not in rules("papa", replace(kb, sensitivities=sens))


def test_riego_semaphore_becomes_alerts():
    rs = snapshot()
    assert "SEQUIA" not in read_signals(rs)                             # hoy: VERDE_OPTIMO
    rs["output"]["clima_regional_nasa_power"]["semaforos"]["estado_riego"]["codigo"] = "ROJO_SECO"
    assert read_signals(rs)["SEQUIA"]["nivel"] == "ALTO"
    rs["output"]["clima_regional_nasa_power"]["semaforos"]["estado_riego"]["codigo"] = "AZUL_SATURADO"
    assert "EXCESO_AGUA" in read_signals(rs)


# --- Solo la ventana más reciente -----------------------------------------------------------------------

def test_only_most_recent_window_gives_signals():
    rs = snapshot()
    old = {a["codigo"] for a in rs["output"]["cruce_ultima_captura"]["clima_nasa_alineado"]["alertas_preventivas"]}
    assert {"HELADAS", "NUTRIENTES"} <= old                             # la ventana de la última foto (21-27/10) las tenía
    sig = read_signals(rs)
    assert {c for c in sig if not c.startswith("_")} == {"PLAGAS_LANCHA"}   # la vigente (05-11/11) solo trae lancha
    assert sig["_fecha_datos"]["mensaje"] == "11/11/2026"


def test_old_window_alerts_do_not_reach_the_farmer(kb):
    assert rules("papa", kb) == ["lancha"]                              # ya no sale «lluvias fuertes» (NUTRIENTES vieja)
    assert rules("chocho", kb) == [] and rules("amaranto", kb) == []    # ya no sale la helada de la ventana vieja


def test_satellite_confirmation_only_if_signal_still_present():
    rs = snapshot()
    assert any(c["codigo"] == "NUTRICION_PROBABLE" and c["confirmada"] for c in rs["output"]["cruces_evaluados"])
    assert "NUTRIENTES" not in read_signals(rs)                         # confirmada en la foto, pero ya no vigente
    rs["output"]["proyeccion_vigente_nasa"]["alertas_preventivas"].append(
        {"codigo": "NUTRIENTES", "nivel": "MEDIO", "mensaje": "prueba"})
    sig = read_signals(rs)
    assert sig["NUTRIENTES"]["confirmed"] and not sig["PLAGAS_LANCHA"]["confirmed"]   # LANCHA_PREVENTIVA no confirma


def test_advisory_carries_data_date(kb):
    lancha = advisories_for("papa", kb, altitude_masl=3588)[0]
    assert lancha["signal"]["data_date"] == "11/11/2026" and lancha["signal"]["plot_altitude"] == "within"
    assert "11/11" not in lancha["message"]                             # la fecha va en un campo, no en el texto


# --- Altitud del lote frente a la parcela monitoreada ----------------------------------------------------

def test_altitude_within_range_uses_remote_sensing(kb):
    assert rules("papa", kb, altitude_masl=3588) == ["lancha"]
    assert rules("papa", kb, altitude_masl=3388) == ["lancha"]          # borde: −200 m
    assert rules("papa", kb, altitude_masl=3788) == ["lancha"]          # borde: +200 m


def test_altitude_outside_range_drops_remote_sensing(kb):
    assert rules("papa", kb, altitude_masl=3200) == []
    assert rules("papa", kb, altitude_masl=3387) == []
    assert rules("chocho", kb, signals={"HELADAS": ALERT}, altitude_masl=3200) == []   # helada calculada para 3588 m


def test_unknown_altitude_uses_remote_sensing_and_says_so(kb):
    a = advisories_for("papa", kb, altitude_masl=None)[0]
    assert a["rule"] == "lancha" and a["signal"]["plot_altitude"] == "unknown"


def test_monitored_altitude_comes_from_the_json(kb):
    rs = snapshot()
    rs["output"]["altitud_parcela_msnm"] = 3200
    sig = read_signals(rs)
    assert rules("papa", kb, signals=sig, altitude_masl=3200) == ["lancha"]
    assert rules("papa", kb, signals=sig, altitude_masl=3588) == []
    del rs["output"]["altitud_parcela_msnm"]
    assert read_signals(rs)["_parcela"]["altitud_msnm"] == 3588        # sin dato: constante documentada


def test_farmer_observations_count_at_any_altitude(kb):
    out = advisories_for("papa", kb, observations=["blight"], altitude_masl=3200)
    assert [a["rule"] for a in out] == ["lancha"] and out[0]["signal"]["sources"] == ["farmer"]
    assert out[0]["message"].startswith("Usted nos contó que vio lancha")
    assert rules("chocho", kb, signals={}, observations=["frost"], altitude_masl=2800) == ["helada"]


def test_engine_passes_plot_altitude(kb):
    far = recommend({"new_land": True, "priorities": ["market_value"], "climate": {"altitude_masl": 3200}}, kb)
    assert all(t["advisories"] == [] for t in [far["recommendation"], *far["alternatives"]])
    assert far["remote_sensing_scope"]["applies"] is False and far["remote_sensing_scope"]["plot_altitude"] == "outside"
    unknown = recommend({"new_land": True, "priorities": ["market_value"], "climate": {"altitude_masl": None}}, kb)
    assert unknown["status"] == "ok" and unknown["remote_sensing_scope"]["plot_altitude"] == "unknown"


# --- Textos que ve el agricultor -------------------------------------------------------------------------

def test_templates_speak_of_current_weather_without_internal_words(kb):
    crops = {"helada": "chocho", "lancha": "papa", "nutrientes": "papa", "sequia": "cebada", "exceso_agua": "haba"}
    obs = {"helada": ["frost"], "lancha": ["blight"], "nutrientes": [], "sequia": ["dry_soil"], "exceso_agua": ["waterlogging"]}
    for rule in RULES:
        for level in ("ALTO", "MEDIO"):
            for confirmed in (False, True):
                sig = {rule["signal"]: {"nivel": level, "mensaje": "prueba", "confirmed": confirmed}}
                for observations in ([], obs[rule["id"]]):
                    a = next(x for x in advisories_for(crops[rule["id"]], kb, signals=sig, observations=observations)
                             if x["rule"] == rule["id"])
                    msg = a["message"]
                    assert "alerta" not in msg.lower(), msg
                    assert msg.startswith("Ahora ") and "Si siembra pronto" in msg and msg.endswith(CLOSE), msg
                    assert f"riesgo {'alto' if level == 'ALTO' else 'medio'}" in msg, msg
                    assert ("satélite" in msg) == confirmed and "ya muestra" not in msg, msg
        if rule["lote"]:
            a = advisories_for(crops[rule["id"]], kb, signals={}, observations=obs[rule["id"]])[0]
            assert a["message"].startswith("Usted nos contó") and "alerta" not in a["message"].lower()
            assert "Si siembra pronto" in a["message"] and a["message"].endswith(CLOSE)


def test_every_typed_value_has_ecuador_or_andes_source():
    data = json.loads((STRUCTURED_DIR / "sensibilidades.json").read_text(encoding="utf-8"))["cultivos"]
    for crop, fields in data.items():
        for name, f in fields.items():
            assert f["valor"] is not None, (crop, name)
            assert f["origen"] in ("ecuador", "andes") and f["fiabilidad"] in ("alta", "media", "baja"), (crop, name)
            assert f["fuente"] and all(s["cita"] for s in f["fuente"]), (crop, name)


def test_missing_files_mean_no_advisories(tmp_path):
    assert load_advisory_data(tmp_path) == ({}, {})


def test_engine_attaches_advisories_to_proposed_crops(kb):
    r = recommend({"new_land": True, "priorities": ["market_value"], "climate": {"altitude_masl": 3588}}, kb)
    assert r["status"] == "ok" and r["remote_sensing_date"] == "11/11/2026"
    proposed = [r["recommendation"], *r["alternatives"]]
    assert all("advisories" in t and len(t["advisories"]) <= 2 for t in proposed)
    assert any(t["advisories"] for t in proposed)
    assert "Alerta del clima" in explain(r)
    assert all(a["agronomic_validation_pending"] for t in proposed for a in t["advisories"])


def test_engine_without_remote_sensing_has_no_advisories(kb):
    r = recommend({"new_land": True, "priorities": ["market_value"]}, replace(kb, signals={}))
    assert all(t["advisories"] == [] for t in [r["recommendation"], *r["alternatives"]])


# --- Observaciones del agricultor ----------------------------------------------------------------------

def test_farmer_frost_alone_triggers_advisory_for_sensitive_crop(kb):
    out = advisories_for("chocho", kb, signals={}, observations=["frost"])          # sin alerta del clima
    assert [a["rule"] for a in out] == ["helada"] and out[0]["level"] == "ALTO"
    assert out[0]["signal"]["sources"] == ["farmer"]
    assert out[0]["message"].startswith("Usted nos contó que hay heladas en su lote")
    assert "clima de su zona" not in out[0]["message"]


def test_farmer_and_remote_sensing_are_combined(kb):
    sig = {"HELADAS": {**ALERT, "nivel": "MEDIO"}}
    a = advisories_for("chocho", kb, signals=sig, observations=["frost"])[0]        # alerta HELADAS (MEDIO) + lo que ve él
    assert a["level"] == "ALTO" and a["signal"]["sources"] == ["remote_sensing", "farmer"]
    assert "clima de su zona" in a["message"] and "también nos contó" in a["message"]


def test_observation_needs_crop_sensitivity(kb):
    assert advisories_for("lenteja", kb, signals={}, observations=["frost", "blight"]) == []   # sin sensibilidad con cita
    assert advisories_for("haba", kb, signals={}, observations=["frost"]) == []                # su dato de helada es de Australia
    assert advisories_for("chocho", kb, signals={}, observations=["blight"]) == []             # chocho no es hospedero de lancha


def test_farmer_observation_does_not_cancel_remote_alert(kb):
    assert "lancha" in rules("papa", kb, observations=["frost"])                    # lo que no menciona no quita la alerta


def test_observations_validated(kb):
    ok = recommend({"new_land": True, "priorities": ["speed"], "observations": ["frost", "blight"]}, kb)
    assert ok["status"] == "ok" and ok["input"]["observations"] == ["frost", "blight"]
    bad = recommend({"new_land": True, "priorities": ["speed"], "observations": ["granizo"]}, kb)
    assert bad["status"] == "invalid_input" and bad["errors"][0]["field"] == "observations"


def test_engine_uses_farmer_observations(kb):
    kb0 = replace(kb, signals={})
    r = recommend({"new_land": True, "priorities": ["market_value"], "climate": {"altitude_masl": 3588}, "observations": ["blight"]}, kb0)
    proposed = {t["crop"]: t for t in [r["recommendation"], *r["alternatives"]]}
    assert "papa" in proposed and [a["rule"] for a in proposed["papa"]["advisories"]] == ["lancha"]


# --- Datos de la ficha para el matiz (crop_facts) -------------------------------------------------------

def test_crop_facts_gives_quotable_data_and_declares_gaps(kb):
    from app.engine.crop_facts import crop_facts
    papa = crop_facts(kb.crops["papa"])
    assert "90 jornales" in papa["mano_de_obra"] and "6 a 7 meses" in papa["ciclo"] and papa["no_hay_dato"] == ["riego"]
    chocho = crop_facts(kb.crops["chocho"])
    assert "29 jornales" in chocho["mano_de_obra"] and chocho["no_hay_dato"] == ["riego", "ciclo"]


def test_conflicting_data_is_not_given_as_fact(kb):
    from app.engine.crop_facts import crop_facts
    amaranto = crop_facts(kb.crops["amaranto"])
    assert "fertilidad" not in amaranto and "fertilidad" in amaranto["en_conflicto"]
