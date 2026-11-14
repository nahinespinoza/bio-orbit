"""POST /v1/recommend: motor de reglas directo. Sin LLM, sin estado, determinista."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.api.deps import Services, get_services
from app.engine.explanation import explain
from app.engine.recommender import recommend
from app.schemas.recommendation import RecommendationInput

router = APIRouter(prefix="/v1", tags=["recommend"])


@router.post("/recommend", summary="Recomendación directa del motor (sin LLM)")
def post_recommend(body: RecommendationInput, include_explanation: bool = Query(False, description="Agrega la explicación en español"),
                   services: Services = Depends(get_services)) -> JSONResponse:
    result = recommend(body.model_dump(), services.kb)
    if include_explanation:
        result["explanation"] = explain(result)
    status_code = 422 if result["status"] == "invalid_input" else 200
    return JSONResponse(result, status_code=status_code)
