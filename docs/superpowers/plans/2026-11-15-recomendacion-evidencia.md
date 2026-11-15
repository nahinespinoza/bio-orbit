# Recomendación de una sola llamada con evidencia: plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** `POST /v1/recommendations`: las respuestas de la pantalla de opciones entran y sale el JSON del contrato. Afinidad = 0,30 · prioridad + 0,40 · riesgo + 0,30 · aptitud.

**Architecture:** paquete nuevo `app/advisor/`. Usa el motor (filtros, aptitud, rotación, advertencias) sin tocar `recommend()`, las condiciones de la parcela (`engine/conditions.py`) y la investigación indexada (`repository/research.py`). Una sola llamada al modelo con salida estructurada, detrás de un `Scorer` que se puede inyectar; el código aplica las reglas y combina.

**Tech Stack:** FastAPI, Pydantic, LangChain (`with_structured_output`) y pytest.

**Spec:** `docs/superpowers/specs/2026-11-15-eleccion-con-evidencia-design.md`

## Global Constraints

- La conversación (`/v1/sessions`) y `/v1/recommend` no cambian.
- 100 es lo mejor en todas las notas y en la afinidad.
- Pesos: prioridad 0,30, riesgo 0,40, aptitud 0,30.
- Reglas fijas:
  - sin dato de la prioridad → 30;
  - advertencia ALTO → riesgo ≤ 40; MEDIO → riesgo ≤ 70;
  - evidencia solo de otra región o sin verificar → riesgo ≥ 50;
  - sin evidencia de los temas activos → riesgo 60;
  - riesgo < 40 → afinidad ≤ 49.
- 5 candidatos; lo que recibe el modelo pesa ≤ 12 KB.
- Las pruebas no llaman a OpenAI. Por pedido del usuario se corren **al final**, en una sola corrida.

## Review Focus

- **El modelo devuelve un cultivo que no es candidato, o se salta uno:** se ignora el que sobra, y al que falta se le aplica la nota neutral (60) y se marca. → `test_combine_ignores_unknown_and_fills_missing`
- **El modelo cita una referencia que no existe:** se descarta. → `test_combine_drops_unknown_references`
- **`previous_crop` desconocido:** `422` con la lista de cultivos parecidos. → `test_endpoint_unknown_crop_422`
- **El lote está fuera de la altitud monitoreada:** el JSON de la petición lleva otra altitud y no se adjunta evidencia. → `test_payload_no_evidence_outside_scope`
- **Tierra nueva:** los candidatos salen de los cultivos `starter`. → `test_rank_new_land`

---

### Task 0: Base y piezas reusadas (hecho)

Rama `feat/api-agent-recomendacion-evidencia` desde `origin/main`, con los commits del borrado del backend y de la búsqueda acotada. De la rama de la otra sesión se reusan `engine/conditions.py`, `ingestion/research.py`, `repository/research.py` y sus pruebas. Están conectados a la ingesta y al `kb.conditions`.

- [ ] Commit: «api-agent: condiciones de la parcela e investigación de las fichas en el RAG».

### Task 1: Candidatos agronómicos — `app/engine/ranking.py`

- `rank_by_aptitude(plot: PlotInput, kb: KnowledgeBase, n: int = 5) -> dict`. Devuelve:
  - `{"status": "ok", "candidates": [...], "discarded": [...], "outside_graph": [...], "warnings": [...]}`, o `{"status": "no_candidates", "discarded", "outside_graph"}`.
- Reusa `_candidates_now`, `_non_commercial_allowed`, `aptitude`, `build_rotation`, `advisories_for` y `crop_facts`.
- Cada candidato:
  - `crop`, `name`, `aptitude` (redondeada), `aptitude_parts`, `transition`, `confidence` (la de `score_crop`: ficha + arista), `rotation`, `advisories`, `facts`.
  - `priority_data`: `{p: SUBSCORES[p](...) sin "value"}` para las 4 prioridades.
  - `sources`: los ids de fuente de la ficha.
- Orden: aptitud de mayor a menor y luego `crop`.
- `waterlogging` → `exceso_agua` activo: `plot_conditions(rs, extra_topics=...)` acepta temas extra (cambio menor en `conditions.py`).

### Task 2: Petición y payload — `app/advisor/request.py` y `app/advisor/payload.py`

- `AdvisorRequest` (Pydantic): `previous_crop: str`, `priority: Literal[4]`, `irrigation: Literal["rain_only","pump","canal","sprinkler_drip","manual"]`, `waterlogging: Literal["no","briefly","long"]` y `remote_sensing: dict | None`.
- `to_plot_raw(req, altitude) -> dict`, con la traducción del diseño: `new_land`, riego yes/no y drenaje good/fair/poor.
- `build_payload(req, conditions, ranked, conn, scope_applies) -> tuple[dict, dict[str, dict], bool]`. Devuelve (payload para el modelo, catálogo de referencias por id, `evidence_trimmed`).
  - Referencias: `F<n>` para las fuentes de las fichas e `I<n>` para cada fragmento de investigación adjunto (título y primera URL del texto completo).
  - Tope de 12 KB con el recorte del diseño.

### Task 3: Modelo y combinación — `app/advisor/scoring.py`, `app/advisor/combine.py`, `app/advisor/prompt.md`

- `Criterion(score: int 0-100, reason: str, references: list[str])`, `CropScore(crop, priority, risk, summary)` y `ScoringOutput(scores: list[CropScore], how_to_compare: str)`.
- `Scorer = Callable[[dict], ScoringOutput]`; `llm_scorer(model: BaseChatModel) -> Scorer` usa `model.with_structured_output(ScoringOutput)` con `prompt.md` como mensaje de sistema y el payload en JSON como mensaje de usuario.
- `combine(ranked_candidates, scoring, priority, refs, scope_applies) -> list[dict]`, con las reglas 1-5, la afinidad redondeada a una decimal, la confianza y el orden por afinidad.

### Task 4: Servicio, endpoint y README

- `advise(req, kb, conn, scorer) -> dict` en `app/advisor/service.py`: arma la respuesta del contrato del diseño (punto 7).
- `POST /v1/recommendations` en `app/api/routes/recommendations.py`:
  - `422` si el cultivo es desconocido;
  - `503` si no hay modelo;
  - `502` ante un `openai.OpenAIError`.
- `Services.scorer` se arma con el modelo de chat. `create_app(..., scorer=None)` permite inyectar uno falso en las pruebas.
- README: el endpoint, los pesos y las reglas.

### Pruebas (al final, una sola corrida)

`tests/test_advisor.py`: `test_rank_by_aptitude_top5_no_priorities`, `test_rank_new_land`, `test_request_translation`, `test_payload_evidence_active_topics_and_cap`, `test_payload_no_evidence_outside_scope`, `test_combine_weights`, `test_combine_rules_1_to_5`, `test_combine_ignores_unknown_and_fills_missing`, `test_combine_drops_unknown_references`, `test_endpoint_contract`, `test_endpoint_unknown_crop_422`, `test_endpoint_without_model_503`. Más las reusadas: `test_conditions.py` y `test_research.py`.
