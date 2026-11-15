# backend

API FastAPI (uv, Python 3.13) que expone el match NASA POWER + Sentinel-2 de una parcela.

## Instalar y correr

```bash
cd backend
uv sync
uv run uvicorn src.main:app --reload      # http://localhost:8000  (docs: /docs)
uv run pytest                             # tests
```

## Endpoint

`GET /parcelas/{parcela_id}/match?simulated=true`

- La parcela es el recurso y el match es su resultado procesado, por eso `/parcelas/{id}/match`.
  Por ahora solo existe la parcela `1` (Toacaso / Sigchos); otro id devuelve **404**.
- `simulated` (bool, default `true`):
  - `true`: devuelve `src/data/resultado_match.json` tal cual.
  - `false`: corre `integrar()` sobre los datos de `src/data/` (~1 s). Si falta algún archivo responde
    **503** con `{"detail": {"error": "datos_faltantes", "faltan": [...]}}`.

```bash
curl localhost:8000/parcelas/1/match
curl "localhost:8000/parcelas/1/match?simulated=false"
```

## Datos

`src/match_nasa_sentinel.py` y `src/data/` son **copias** de `remote-sensing/` (solo cambian las rutas y se
quitó todo lo que genera HTML). Si se regeneran los datos allá, hay que volver a copiarlos.
