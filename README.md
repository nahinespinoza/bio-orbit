# Crop Advisor API

API REST (FastAPI) de un agente que guía a agricultores con poca experiencia en la elección de cultivo y rotación (sierra andina del Ecuador).

- **Agente:** LangChain `create_agent` + OpenAI (`gpt-5.4-mini`, razonamiento `low`, vía Responses API). Conversa, pregunta lo que falta y explica. **No calcula**: usa herramientas.
- **Embeddings:** `text-embedding-3-small`.
- **Logs:** loguru (herramientas usadas por turno, errores de OpenAI con traza).
- **Motor de reglas:** `app/engine/`, versión en Python de `local/agente-rotacion/scripts/recomendar.mjs` (mismos resultados, verificado). Determinista, sin LLM.
- **RAG sobre SQLite:** `BM25Retriever` + `SQLiteVec` (langchain-community) unidos con `EnsembleRetriever` (langchain-classic).
- **Memoria:** solo de corto plazo, por sesión (`InMemorySaver`, TTL de 120 min). Nada entre sesiones.

## Puesta en marcha

```bash
uv sync
cp .env.example .env               # y poner OPENAI_API_KEY
uv run python -m ingestion.build_db                # crea data/knowledge.db (con embeddings si hay clave)
uv run uvicorn app.main:app --reload               # 1 worker: la memoria de sesión vive en el proceso
```
Documentación interactiva: http://127.0.0.1:8000/docs

Sin `OPENAI_API_KEY` funcionan `/v1/recommend`, `/v1/crops` y la búsqueda BM25; `/v1/sessions` responde 503.

## Endpoints

| Método | Ruta | Para qué |
|---|---|---|
| POST | `/v1/sessions/{session_id}/messages` | Conversar con el agente. El frontend genera `session_id` (UUID v4); el primer mensaje crea la sesión |
| GET | `/v1/sessions/{session_id}` | Estado: datos del lote, datos faltantes, última recomendación, vencimiento |
| DELETE | `/v1/sessions/{session_id}` | Olvidar la sesión de inmediato |
| POST | `/v1/recommend` | Motor directo, sin LLM y sin estado (`?include_explanation=true` agrega texto en español) |
| GET | `/v1/crops`, `/v1/crops/{crop}` | Cultivos y fichas (acepta nombres comunes: tarwi, ataco, fréjol) |
| GET | `/health` | Estado del servicio |

## Estructura

```
app/
├── main.py                 # create_app(), lifespan, purga de sesiones vencidas
├── config.py               # Settings (.env)
├── api/deps.py             # servicios compartidos (DB, KB, retriever, agente, registro de sesiones)
├── api/routes/             # sessions.py, recommend.py, crops.py
├── agent/
│   ├── system_prompt.md    # prompt del asesor (español)
│   ├── tools.py            # update_plot, recommend_crop, search_sources, get_crop_profile, list_crops
│   └── factory.py          # create_agent + @dynamic_prompt (datos del lote) + recorte de historial
├── engine/                 # motor de reglas: validation, filters, scoring, rotation, recommender, explanation
├── memory/                 # state.py (estado del agente), sessions.py (TTL y bloqueo por sesión)
├── rag/                    # db.py (sqlite-vec), retriever.py (BM25 + SQLiteVec + Ensemble)
├── repository/crops.py     # lectura de fichas y grafo
└── schemas/                # Pydantic
ingestion/
├── build_db.py             # comando de ingesta
├── schema.sql              # tablas sources, crops, transitions, chunks, meta
├── load_structured.py      # cultivos.json / transiciones.json → tablas (claves en inglés)
└── documents.py            # PyPDFLoader, BSHTMLLoader, TextLoader + text splitters
tests/                      # 47 pruebas; ninguna llama a OpenAI
```

## Pruebas

```bash
uv run pytest
```
El agente se prueba con un modelo de chat guionado: `create_agent`, las herramientas, el checkpointer y el TTL son reales.

## Modelos
Configurables en `.env` (`CHAT_MODEL`, `CHAT_REASONING_EFFORT`, `EMBEDDING_MODEL`). Los modelos `gpt-5.4-*` no aceptan
herramientas junto con `reasoning_effort` en `/v1/chat/completions`; por eso `ChatOpenAI` usa `use_responses_api=True`.
Si cambias `EMBEDDING_MODEL` o `EMBEDDING_DIMENSIONS`, vuelve a correr la ingesta.

## Límites del MVP
- `langchain-community` está archivado (sin mantenimiento desde junio de 2026). `SQLiteVec` y `BM25Retriever` no filtran por metadatos.
- Sin embeddings, la búsqueda es solo por palabras clave y falla con preguntas parafraseadas.
- `InMemorySaver` exige 1 worker y pierde las sesiones al reiniciar.
- Sin autenticación: quien conozca un `session_id` puede leer esa sesión.
