"""Calificación del modelo (una sola llamada, salida estructurada). El `Scorer` se inyecta: en pruebas es falso."""

import json
from collections.abc import Callable

import openai
from pathlib import Path

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

PROMPT = Path(__file__).with_name("prompt.md").read_text(encoding="utf-8")


class Criterion(BaseModel):
    score: int = Field(description="0-100; 100 es lo mejor")
    reason: str = Field(description="Una o dos frases con el dato concreto")
    references: list[str] = Field(description="Ids de referencias_disponibles (F<n> o I<n>)")


class CropScore(BaseModel):
    crop: str = Field(description="El `crop` exacto del candidato")
    priority: Criterion
    risk: Criterion
    summary: str = Field(description="Una frase: por qué conviene o no en su lote")


class ScoringOutput(BaseModel):
    scores: list[CropScore]
    how_to_compare: str


Scorer = Callable[[dict], ScoringOutput]


class AdvisorModelError(Exception):
    """El modelo no dio una calificación usable (negativa, salida incompleta o inválida). La ruta responde 502."""


def guarded(scorer: Scorer) -> Scorer:
    """Errores del modelo que no son de la API de OpenAI (esos los atrapa la ruta) → AdvisorModelError."""

    def score(payload: dict) -> ScoringOutput:
        try:
            return scorer(payload)
        except openai.OpenAIError:
            raise
        except Exception as exc:   # negativa del modelo, salida sin `parsed`, ValidationError…
            raise AdvisorModelError(f"{type(exc).__name__}: {exc}") from exc

    return score


def llm_scorer(model: BaseChatModel) -> Scorer:
    structured = model.with_structured_output(ScoringOutput)
    return guarded(lambda payload: structured.invoke(
        [SystemMessage(PROMPT), HumanMessage(json.dumps(payload, ensure_ascii=False))]))
