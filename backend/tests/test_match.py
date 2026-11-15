import json

import pytest
from fastapi.testclient import TestClient

from src import match_nasa_sentinel as m
from src.main import app

client = TestClient(app)
URL = "/parcelas/1/match"


def test_simulado_por_defecto_devuelve_el_json_tal_cual():
    esperado = json.loads((m.DATA_DIR / "resultado_match.json").read_text(encoding="utf-8"))
    r = client.get(URL)
    assert r.status_code == 200
    assert r.json() == esperado
    assert client.get(URL, params={"simulated": "true"}).json() == esperado


def test_en_vivo_corre_integrar():
    r = client.get(URL, params={"simulated": "false"})
    assert r.status_code == 200
    body = r.json()
    assert {"input", "output"} <= body.keys()
    assert body["output"]["historial_cruces"]
    assert body["output"]["cruce_ultima_captura"]["fecha_captura"]


def test_en_vivo_sin_datos_da_error_claro(monkeypatch, tmp_path):
    monkeypatch.setattr(m, "NASA_DIR", tmp_path)
    r = client.get(URL, params={"simulated": "false"})
    assert r.status_code == 503
    assert r.json()["detail"]["error"] == "datos_faltantes"
    assert r.json()["detail"]["faltan"]


def test_parcela_desconocida_404():
    assert client.get("/parcelas/999/match").status_code == 404
    assert client.get("/parcelas/999/match", params={"simulated": "false"}).status_code == 404
