"""POST /v1/recommendations: recomendación de una sola llamada con evidencia (remote-sensing + fichas). Solo JSON."""

import openai
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from loguru import logger

from app.advisor.request import AdvisorRequest
from app.advisor.scoring import AdvisorModelError
from app.advisor.service import AdvisorInputError, advise
from app.api.deps import Services, get_services

router = APIRouter(prefix="/v1", tags=["recommendations"])


@router.post("/recommendations", summary="Recomendación con evidencia (una sola llamada)", response_model=None)
def post_recommendations(body: AdvisorRequest, services: Services = Depends(get_services)) -> dict | JSONResponse:
    """Afinidad 0-100 (100 = el mejor) = 0,30 · prioridad + 0,40 · riesgo de la parcela + 0,30 · aptitud agronómica."""
    if services.scorer is None:
        raise HTTPException(503, {"code": "LLM_NOT_CONFIGURED",
                                  "message": "Falta OPENAI_API_KEY en .env. /v1/recommend funciona sin ella."})
    try:
        return advise(body, services.kb, services.conn, services.scorer)
    except AdvisorInputError as exc:
        return JSONResponse(status_code=422, content={"errors": exc.errors})
    except (openai.OpenAIError, AdvisorModelError) as exc:
        logger.exception("Error del modelo en /v1/recommendations")
        raise HTTPException(502, {"code": "LLM_ERROR", "message": f"El modelo no respondió: {type(exc).__name__}"}) from exc
