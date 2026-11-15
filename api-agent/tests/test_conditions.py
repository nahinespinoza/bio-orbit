"""Condiciones de la parcela (resumen del `output` del remote-sensing) y temas activos."""

import json

from app.engine.conditions import ALERT_TOPICS, plot_conditions
from app.repository.crops import STRUCTURED_DIR

RS = json.loads((STRUCTURED_DIR / "remote_sensing.json").read_text(encoding="utf-8"))


def test_conditions_fields_and_size():
    c = plot_conditions(RS)
    assert c["parcela"]["altitud_msnm"] == 3588.0
    assert c["clima_semana"]["humedad_relativa_pct"] == 85.9
    assert c["proyeccion"]["mes"] == "Diciembre" and c["lote_satelite"]["ndvi_promedio"] == 0.4482
    text = json.dumps(c, ensure_ascii=False)
    assert ".png" not in text and len(text) <= 1500


def test_active_topics_from_current_json():
    assert set(plot_conditions(RS)["temas_activos"]) == {"sanidad", "fertilidad", "agua", "ciclo_siembra"}
    assert "ciclo_siembra" not in ALERT_TOPICS


def test_active_topics_follow_json_codes():
    rs = json.loads(json.dumps(RS))
    rs["output"]["clima_regional_nasa_power"]["semaforos"]["estado_helada"]["codigo"] = "AMARILLO"
    assert "helada" in plot_conditions(rs)["temas_activos"]


def test_kb_has_conditions(kb):
    assert kb.conditions["temas_activos"]
