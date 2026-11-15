"""API del backend de bio-orbit."""
from fastapi import FastAPI, HTTPException

from . import service

# Por ahora hay una sola parcela (Toacaso / Sigchos, papa).
PARCELAS = {"1"}

app = FastAPI(title="bio-orbit backend", version="0.1.0")


@app.get("/parcelas/{parcela_id}/match", summary="Match NASA POWER + Sentinel-2 de una parcela")
def match_parcela(parcela_id: str, simulated: bool = True) -> dict:
    """Resultado del cruce NASA POWER (riesgo climático) + Sentinel-2 (daño visible).

    - `simulated=true` (default): devuelve el JSON precalculado (`resultado_match.json`).
    - `simulated=false`: corre `integrar()` sobre los datos del backend.
    """
    if parcela_id not in PARCELAS:
        raise HTTPException(404, f"Parcela '{parcela_id}' no encontrada")
    try:
        return service.resultado_simulado() if simulated else service.resultado_en_vivo()
    except service.DatosFaltantes as e:
        raise HTTPException(503, {"error": "datos_faltantes", "mensaje": str(e), "faltan": e.faltan})
