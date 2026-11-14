"""Rutas que no usan el LLM."""

SID = "6f1c0a3e-8c1a-4c5e-9b1a-2f3e4d5c6b7a"
UUID_V1 = "c232ab00-9414-11ec-b3c8-9e6bdeced846"
VALID = {"previous_crops": ["papa", "cebada"], "priorities": ["speed", "fewer_pests"],
         "soil": {"fertility": "medium"}, "climate": {"altitude_masl": 2800, "irrigation": "yes"}}


def test_health(make_client):
    body = make_client().get("/health").json()
    assert body["status"] == "ok" and body["crops"] == 27
    assert body["llm_enabled"] is False and body["retrieval_mode"] == "bm25"


def test_recommend_ok_with_explanation(make_client):
    r = make_client().post("/v1/recommend?include_explanation=true", json=VALID)
    assert r.status_code == 200
    body = r.json()
    assert body["recommendation"]["crop"] == "amaranto"
    assert body["explanation"].startswith("## Recomendación para el lote")


def test_recommend_invalid_returns_codes(make_client):
    r = make_client().post("/v1/recommend", json={"previous_crops": ["papaa"], "priorities": ["speed", "speed"]})
    assert r.status_code == 422
    assert {e["code"] for e in r.json()["errors"]} == {"UNKNOWN_CROP", "DUPLICATE_PRIORITIES"}


def test_recommend_rejects_bad_enum_at_schema_level(make_client):
    r = make_client().post("/v1/recommend", json={**VALID, "soil": {"fertility": "riquisima"}})
    assert r.status_code == 422


def test_crops_list_alias_and_404(make_client):
    c = make_client()
    assert len(c.get("/v1/crops").json()) == 27
    assert c.get("/v1/crops/tarwi").json()["crop_id"] == "chocho"
    r = c.get("/v1/crops/xyz")
    assert r.status_code == 404


def test_sessions_require_llm_and_uuid_v4(make_client):
    c = make_client()
    assert c.post(f"/v1/sessions/{SID}/messages", json={"message": "hola"}).status_code == 503
    assert c.post(f"/v1/sessions/{UUID_V1}/messages", json={"message": "hola"}).status_code == 422
    assert c.post("/v1/sessions/no-es-uuid/messages", json={"message": "hola"}).status_code == 422
