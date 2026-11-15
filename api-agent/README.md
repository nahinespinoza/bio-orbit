# Crop Advisor API (`api-agent`)

API REST de un agente que guía a pequeños agricultores de la sierra andina del Ecuador en la elección del próximo cultivo y en la rotación del lote para los ciclos siguientes.

La API combina tres piezas:

- **Agente conversacional** (LangChain `create_agent` + OpenAI). Conversa en español sencillo, pregunta los datos que faltan y explica el resultado. **No calcula nada**: delega en herramientas.
- **Motor de reglas** (`app/engine/`). Es determinista y no usa LLM. Aplica filtros duros, calcula puntajes y arma la rotación sobre un grafo de transiciones entre cultivos.
- **RAG sobre SQLite**. Busca pasajes en fuentes FAO, MAGAP y documentos del proyecto con BM25 y, si hay embeddings, también con vectores (`sqlite-vec`).

## Requisitos

- Python 3.13
- [uv](https://docs.astral.sh/uv/)
- `OPENAI_API_KEY`: opcional. Sin ella funcionan `/v1/recommend`, `/v1/crops` y la búsqueda por palabras clave, pero `/v1/sessions` responde `503`.

## Puesta en marcha (local)

```bash
cd api-agent
uv sync
cp ../.env.example ../.env                 # el .env vive en la RAÍZ del repo; completa OPENAI_API_KEY
uv run python -m ingestion.build_db        # crea data/knowledge.db (con embeddings si hay clave)
uv run uvicorn app.main:app --reload       # siempre 1 worker (ver «Memoria de sesión»)
```

- Documentación interactiva: http://127.0.0.1:8000/docs
- Estado del servicio: http://127.0.0.1:8000/health

Si `data/knowledge.db` no existe, la API no arranca y te indica el comando de ingesta que debes correr.

### Ingesta

```bash
uv run python -m ingestion.build_db                  # embeddings si hay OPENAI_API_KEY
uv run python -m ingestion.build_db --no-embeddings  # sin costo: solo datos estructurados + fragmentos (búsqueda BM25)
uv run python -m ingestion.build_db --embeddings     # exige embeddings (falla si no hay clave)
uv run python -m ingestion.build_db --db otra.db     # ruta de salida alternativa
```

La base se construye en un archivo temporal y reemplaza a la anterior solo al final, así que si la ingesta falla la base vieja sigue siendo válida. Vuelve a correr la ingesta cada vez que cambies `knowledge/` o `EMBEDDING_MODEL`/`EMBEDDING_DIMENSIONS`.

## Advertencias del clima (prueba de concepto)

Además de recomendar, el motor puede avisar de un riesgo del clima. La idea cabe en una frase: **si el remote-sensing avisa de algo y la ficha del cultivo dice, con cita de Ecuador o los Andes, que le afecta, el motor genera la advertencia.**

| Alerta del remote-sensing | Campo de la ficha que la cruza |
|---|---|
| `HELADAS` | `tolerancia_helada` = baja, o `fase_sensible_helada` |
| `PLAGAS_LANCHA` | `hospedero_lancha` |
| `NUTRIENTES` (lluvia que lava el nitrógeno) | `perdida_nitrogeno_por_lluvia` |
| `SEQUIA` (riego `ROJO_SECO`) | `fase_sensible_sequia` |
| Suelo saturado (riego `AZUL_SATURADO`) | `tolerancia_exceso_agua` = baja |

- **Las alertas** salen de `knowledge/structured/remote_sensing.json`, una copia de `remote-sensing/resultado_match.json` (lo genera `remote-sensing/match_nasa_sentinel.py`: reporte de ventanas de 7 días). Para actualizarlo, reemplace el archivo. Aquí no se recalcula ningún clima.
- **Solo la ventana más reciente:** las alertas y el semáforo de riego se toman solo de la semana más reciente (`proyeccion_vigente_nasa` / `clima_regional_nasa_power`; hoy 05-11/11/2026, que solo trae `PLAGAS_LANCHA`). La ventana de la última foto Sentinel-2 (21-27/10) ya no está vigente: sus `HELADAS` y `NUTRIENTES` no generan advertencias. Un cruce confirmado de esa foto solo se menciona («el satélite también ve…») si su alerta sigue en la ventana reciente. La fecha de los datos va en `signal.data_date` de cada advertencia y en `remote_sensing_date` / `remote_sensing_scope.data_date` del resultado.
- **Altitud del lote:** las alertas son de la parcela monitoreada (Toacaso / Sigchos; altitud de `output.altitud_parcela_msnm`, o 3 588 msnm si falta) y la helada usa temperatura corregida a esa altura. Solo se aplican si el lote está a ±200 m de ella (3 388-3 788 m hoy). Fuera de ese rango no hay advertencias del remote-sensing; si la altitud es desconocida se aplican y consta `plot_altitude: "unknown"` (en `signal` y en `remote_sensing_scope`). Lo que cuenta el agricultor (`observations`: helada, lancha, suelo seco o encharcado) vale a cualquier altitud.
- **Las sensibilidades** salen de `knowledge/structured/sensibilidades.json`. Sin dato, sin cita o de otra región (Australia, EcoCrop…) no hay advertencia. El detalle de qué cultivos tienen o no dato está en `propuesta_campos_tipados.json`.
- **El texto** sale de una plantilla fija en español sencillo y sin palabras internas como «alerta» (`app/engine/advisories.py`): «Ahora el clima de su zona trae riesgo alto de lancha. Si siembra pronto, el cultivo de papa puede enfermarse de lancha. Consulte con un experto para una revisión más a detalle.» Si el cruce con el satélite salió confirmado, dice solo lo que el satélite ve (p. ej. «hojas con poco verdor, que puede ser falta de nitrógeno»): es un indicio en el cultivo en pie, no un diagnóstico. El agente solo la repite.
- **Planificación frente a monitoreo:** las alertas semanales describen el clima de ahora y el cultivo en pie, no el ciclo del cultivo que se va a sembrar (matriz de reglas, R-NV9 y D11). Por eso las plantillas dicen «ahora» y «si siembra pronto», y no cambian la recomendación. Un conjunto propio de reglas de monitoreo del cultivo en curso queda pendiente.
- **Límites:** máximo 2 por cultivo (primero las de nivel ALTO); ninguna baja el puntaje; ninguna está calibrada en campo (`agronomic_validation_pending`). No pasan por la base SQLite: se leen de los JSON al arrancar.
- **Fuera del MVP:** vigor (NDVI/NDRE/NDMI) y calor. El calor porque el semáforo del código (22 °C) está por debajo de todos los topes de la ficha (28-35 °C); el vigor porque ninguna ficha tiene valores por fase.
- **Dónde aparece:** `recommendation.advisories` y `alternatives[].advisories` de `POST /v1/recommend`, y `advisories` en el resumen que recibe el agente.

### Contexto libre del agricultor y datos de la ficha

- **Notas (`notes`):** lo que el agricultor cuenta y no cabe en ningún campo (tipo de riego, tamaño de la parcela, comprador, ayuda en casa). El motor no las usa para calcular; las lee el agente.
- **`facts`:** el cultivo recomendado trae en el resumen que recibe el agente unos datos de su ficha (`app/engine/crop_facts.py`): mano de obra (jornales por hectárea), riego, ciclo y fertilidad. Lo que la ficha no trae va en `no_hay_dato` (el agente dice «no tengo dato de…») y lo que las fuentes contradicen va en `en_conflicto`.
- **Cómo lo usa el agente:** conecta el tema de la nota con el dato que le corresponde (trabajo → mano de obra, riego → riego, dinero para abono → fertilidad, tamaño o tiempo → ciclo). Está en `app/agent/system_prompt.md`, con ejemplos. Las pruebas que respaldan este diseño están en `pruebas_matiz.md`.

### Datos de las fichas por revisar

- **Amaranto, fertilidad:** la ficha dice «baja» y un ensayo de Ecuador dice que extrae altas cantidades de nitrógeno. Hoy no se entrega como dato (`en_conflicto`).
- **Quinua, altitud:** la ficha dice 2 200–3 000 m y el manual CIP/INIAP la da por viable hasta ~3 700 m con riesgo de helada; el filtro del motor usa la primera y la descarta a 3 588 m.
- **Lizas y olluco:** son la misma ficha duplicada.
- **Mano de obra y riego:** casi todas las fichas no traen mano de obra (solo la papa) ni si necesitan riego.

## Configuración

Las variables se leen del entorno o del `.env` de la raíz del monorepo (`../.env`; plantilla en `../.env.example`). Las rutas relativas se resuelven contra `api-agent/`, no contra el directorio de trabajo.

| Variable | Por defecto | Uso |
|---|---|---|
| `OPENAI_API_KEY` | — | Agente y embeddings. Vacía o con el placeholder `PON_AQUI…` = LLM desactivado |
| `CHAT_MODEL` | `gpt-5.4` | Modelo del agente (se llama por la Responses API) |
| `CHAT_REASONING_EFFORT` | `low` | `minimal` · `low` · `medium` · `high` |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Embeddings de la ingesta y de las consultas |
| `EMBEDDING_DIMENSIONS` | `1536` | Dimensión de los vectores |
| `DB_PATH` | `data/knowledge.db` | Base SQLite generada por la ingesta |
| `STRUCTURED_DATA_DIR` | `knowledge/structured` | `cultivos.json` y `transiciones.json` |
| `PDF_DIR` | `knowledge/pdfs` | PDFs de las fuentes |
| `WEB_DIR` | `knowledge/web` | Páginas HTML (hoy no se indexa ninguna) |
| `PROJECT_DOCS_DIR` | `knowledge/docs` | Documentos `.md` del proyecto |
| `SESSION_TTL_MINUTES` | `120` | Inactividad tras la que vence una sesión |
| `SESSION_CLEANUP_INTERVAL_SECONDS` | `300` | Frecuencia de la purga de sesiones vencidas |
| `MAX_CONVERSATION_TURNS` | `12` | Turnos de historial que ve el modelo |
| `RAG_TOP_K` | `5` | Pasajes por búsqueda |

Los modelos `gpt-5.4-*` no aceptan herramientas junto con `reasoning_effort` en `/v1/chat/completions`. Por eso `ChatOpenAI` se crea con `use_responses_api=True`.

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/v1/sessions/{session_id}/messages` | Envía un mensaje al agente. El cliente genera `session_id` (UUID v4) y el primer mensaje crea la sesión |
| `GET` | `/v1/sessions/{session_id}` | Estado de la sesión: datos del lote, datos faltantes, última recomendación, turnos y vencimiento |
| `DELETE` | `/v1/sessions/{session_id}` | Borra la sesión de inmediato (`204`) |
| `POST` | `/v1/recommendations` | Recomendación de una sola llamada con evidencia (remote-sensing + investigación de las fichas). Solo JSON |
| `POST` | `/v1/recommend` | Llama al motor directamente, sin LLM y sin estado. Con `?include_explanation=true` agrega una explicación en español |
| `GET` | `/v1/crops` | Lista de cultivos con familia, tipo, tags y confianza |
| `GET` | `/v1/crops/{crop}` | Ficha de un cultivo. Acepta nombres comunes (tarwi, ataco, ulluco…) |
| `GET` | `/health` | Estado: LLM activo, modo de búsqueda, número de cultivos, sesiones activas y fecha de la base |

### Recomendación con evidencia (una sola llamada)

`POST /v1/recommendations` recibe las respuestas de la pantalla de opciones y devuelve solo JSON (sin texto conversacional):

```bash
curl -X POST localhost:8000/v1/recommendations -H "Content-Type: application/json"   -d '{"previous_crop": "cebada", "priority": "low_labor", "irrigation": "rain_only", "waterlogging": "long"}'
```

- **Entrada:**
  - `previous_crop`: un cultivo del pool, o `new_land`.
  - `priority`: una de `market_value` | `speed` | `fewer_pests` | `low_labor`.
  - `irrigation`: `rain_only` | `pump` | `canal` | `sprinkler_drip` | `manual`. `rain_only` es sin riego.
  - `waterlogging`: `no` | `briefly` | `long`. Se traduce a drenaje bueno, regular o malo.
  - `remote_sensing`: se acepta, pero en el MVP **se ignora y no se valida**: siempre se usa la copia del servidor, `knowledge/structured/remote_sensing.json`. La altitud sale de esa copia.
- **Cómo decide:**
  1. El motor aplica los filtros duros y la rotación, y entrega los **5 mejores por aptitud agronómica**, sin prioridades. Aquí no se aplica la regla de no comerciales: barbecho, pasto y abono verde también son candidatos.
  2. El modelo (una llamada con salida estructurada) califica cada candidato de 0 a 100 en:
     - **prioridad**, con el dato de la ficha;
     - **riesgo de la parcela**: compara las condiciones del remote-sensing con la investigación del cultivo, que se lee del RAG por cultivo y tema.
  3. El código combina: **afinidad = 0,30 · prioridad + 0,40 · riesgo + 0,30 · aptitud**, y 100 es el mejor cultivo.
- **Reglas fijas del código:**
  - sin dato de la prioridad → 30;
  - advertencia ALTO del motor → riesgo ≤ 40; MEDIO → riesgo ≤ 70;
  - evidencia solo de otra región o sin verificar → riesgo ≥ 50;
  - sin investigación de los temas activos → riesgo 60;
  - riesgo < 40 → afinidad ≤ 40 (riesgo primero).
- **Salida:**
  - `recommendation` y `alternatives` (hasta 4), cada una con `affinity`, `confidence` (alta, media o baja), `summary`, `why` (prioridad, riesgo y rotación, con su nota, su motivo y sus referencias), `rotation` y `advisories`;
  - además: `how_to_compare`, `sources` (`F<n>` = fuente de la ficha, `I<n>` = fragmento de investigación), `missing_data`, `discarded`, `plot_conditions` y `flags`.
- **Errores:**
  - `422` con `{"errors": [...]}` (cultivo desconocido o entrada inválida);
  - `503` sin `OPENAI_API_KEY`;
  - `502` si el modelo falla.

### Conversación con el agente

```bash
SID=$(uuidgen)   # debe ser UUID v4
curl -X POST "http://127.0.0.1:8000/v1/sessions/$SID/messages" \
  -H "Content-Type: application/json" \
  -d '{"message": "Sembré papa y antes cebada, ¿qué siembro ahora? Quiero cosechar rápido."}'
```

La respuesta (`MessageOut`) trae:

- `reply`: el texto del agente.
- `plot`: los datos del lote ya validados.
- `missing_data`: los datos que faltan, ordenados por importancia.
- `recommendation`: el resultado del motor, solo si se recomendó en ese turno.
- `citations`: las fuentes consultadas en ese turno.
- `session_status` (`new` | `active`) y `expires_at`.

Los mensajes de una misma sesión se procesan de uno en uno (hay un bloqueo por sesión).

### Motor directo

```bash
curl -X POST "http://127.0.0.1:8000/v1/recommend?include_explanation=true" \
  -H "Content-Type: application/json" \
  -d '{
        "previous_crops": ["papa", "cebada"],
        "soil": {"fertility": "medium", "drainage": "good"},
        "climate": {"altitude_masl": 2800, "irrigation": "yes"},
        "priorities": ["speed", "fewer_pests"]
      }'
```

Datos de entrada:

- **Obligatorios:** `previous_crops`, del más reciente al más antiguo (o `new_land: true` si el lote nunca se cultivó), y `priorities`. Las prioridades van de 1 a 3, en orden: `market_value`, `speed`, `fewer_pests`, `low_labor`.
- **Opcionales:** `soil` (fertilidad, textura, profundidad, pH, drenaje, compactación), `climate` (`altitude_masl`, `irrigation`), `last_pest`, `rotation_cycles` (por defecto `4`) y `use_source5`. Cualquier dato puede valer `"unknown"`.

El campo `status` del resultado puede ser:

- `ok`: incluye el cultivo recomendado, 2 alternativas, la rotación, los descartes con su motivo, las advertencias y los datos faltantes.
- `no_candidates`: ningún cultivo pasó los filtros.
- `invalid_input`: la entrada tiene errores. Responde HTTP `422`, con los errores y sugerencias para cada uno.

### Errores

Los errores de las rutas devuelven `detail: {code, message}`:

| Código | HTTP | Causa |
|---|---|---|
| `INVALID_SESSION_ID` | 422 | `session_id` no es un UUID v4 |
| `LLM_NOT_CONFIGURED` | 503 | Falta `OPENAI_API_KEY` |
| `LLM_ERROR` | 502 | OpenAI falló durante el turno |
| `SESSION_NOT_FOUND` | 404 | La sesión no existe o ya venció |
| `UNKNOWN_CROP` | 404 | El cultivo no está en el pool (incluye `suggestions`) |

## Cómo funciona

### Agente (`app/agent/`)

- `system_prompt.md` define el tono y las reglas: español sencillo, trato de «usted», mensajes cortos, una sola pregunta por mensaje, nada de dosis de agroquímicos ni promesas de rendimiento.
- `factory.py` crea el agente con `create_agent` y dos middlewares:
  - `@dynamic_prompt`: añade al prompt los datos del lote ya registrados y los que faltan.
  - `@before_model`: recorta el historial a `MAX_CONVERSATION_TURNS` turnos. Siempre corta en un mensaje del usuario para no separar una llamada a herramienta de su resultado.
- `tools.py` define las herramientas:

| Herramienta | Qué hace |
|---|---|
| `update_plot` | Valida y guarda en el estado los datos del lote que dio el agricultor |
| `recommend_crop` | Ejecuta el motor con el lote registrado (exige los datos obligatorios) |
| `search_sources` | Busca pasajes en las fuentes (opcionalmente solo los de un cultivo) y acumula las citas |
| `get_crop_profile` | Devuelve las secciones pedidas de la ficha de un cultivo (nunca los indicadores de investigación) |
| `list_crops` | Devuelve los cultivos conocidos |

### Motor de reglas (`app/engine/`)

El motor es una versión en Python de `local/agente-rotacion/scripts/recomendar.mjs` y la especificación está en `local/agente-rotacion/docs/ESPECIFICACION.md`. Funciona en cuatro pasos:

1. **Candidatos.** Son los sucesores del cultivo anterior en el grafo de transiciones. Si el lote es tierra nueva, son los cultivos con tag `starter`.
2. **Filtros duros** (`filters.py`). Un cultivo que falla uno queda descartado:
   - **F1:** no repetir el mismo cultivo. Quinua y maíz admiten hasta 2 temporadas seguidas.
   - **F2:** no repetir la familia botánica del ciclo anterior. Entre dos solanáceas deben pasar 3 ciclos.
   - **F3:** descartar los cultivos hospederos de la plaga o enfermedad del último ciclo.
   - **F4:** comprobar clima y suelo: altitud (con margen de 200 m), riego, pH (con margen de 0,5), drenaje y profundidad.
3. **Puntaje** (`scoring.py`). Se calcula como `0,75 · prioridades + 0,25 · aptitud agronómica`. Los pesos de las prioridades son `1,0`, `0,6/0,4` o `0,5/0,3/0,2`. Un dato faltante vale 50 (neutral) y baja la confianza.
4. **Rotación** (`rotation.py`). Busca exhaustivamente en el grafo la secuencia de `rotation_cycles` ciclos. Prefiere las secuencias completas que terminan en un cultivo `ender` y, entre ellas, la de mayor puntaje medio.

`explanation.py` genera el texto en español que devuelve `?include_explanation=true`.

### RAG (`app/rag/`)

- `BM25Retriever` se arma en memoria al iniciar la API, a partir de la tabla `chunks`, con un preprocesado para español: sin tildes, sin palabras vacías y con una raíz mínima de plurales.
- Si la base tiene vectores y hay clave, se combina con `SQLiteVec` mediante `EnsembleRetriever` (Reciprocal Rank Fusion, pesos 0,5/0,5). En `/health`, `retrieval_mode` indica `hybrid` o `bm25`.

### Base de conocimiento (`knowledge/` → `data/knowledge.db`)

| Origen | Contenido | Tratamiento en la ingesta |
|---|---|---|
| `structured/cultivos.json` | Fichas de cultivos y fuentes (claves en español) | Tablas `crops` y `sources` (columnas en inglés) |
| `structured/transiciones.json` | Grafo: nodos con tags `starter`/`follower`/`ender` y aristas `fuente`/`general`/`inferida`/`fuente5` | Tabla `transitions` |
| `pdfs/*.pdf` | FAO (producción orgánica y guía de campo de cultivos andinos) y MAGAP (política agropecuaria 2015-2025) | `PyPDFLoader` por página, fragmentos de 1200 caracteres |
| `docs/*.md` | Reglas, tabla de puntaje, calendario, pool de cultivos, indicadores de remote sensing | `MarkdownHeaderTextSplitter`, fragmentos de 1600 caracteres |

Cada fragmento guarda como metadatos la fuente, la página o sección, la fiabilidad y los cultivos mencionados. El blog de Radeco (fuente 5) **no se indexa** porque no se considera evidencia. Las transiciones respaldadas solo por esa fuente se descartan, salvo que se envíe `use_source5: true`.

El esquema completo está en `ingestion/schema.sql`.

### Memoria de sesión (`app/memory/`)

- La memoria es solo de corto plazo: `InMemorySaver` guarda una conversación por `session_id`. No se conserva nada entre sesiones.
- `SessionRegistry` aplica el TTL por inactividad. Una tarea en segundo plano purga las sesiones vencidas cada `SESSION_CLEANUP_INTERVAL_SECONDS`.
- Como todo vive en la memoria del proceso, **uvicorn debe correr con 1 worker**, y las sesiones se pierden al reiniciar.

## Estructura

```
api-agent/
├── app/
│   ├── main.py              # create_app(), lifespan, /health, purga de sesiones
│   ├── config.py            # Settings (pydantic-settings, lee ../.env)
│   ├── api/
│   │   ├── deps.py          # servicios compartidos (DB, KB, retriever, agente, sesiones)
│   │   └── routes/          # sessions.py, recommend.py, crops.py
│   ├── agent/               # system_prompt.md, tools.py, factory.py
│   ├── engine/              # validation, filters, scoring, rotation, recommender, explanation
│   ├── memory/              # state.py (estado del agente), sessions.py (TTL y bloqueos)
│   ├── rag/                 # db.py (sqlite-vec), retriever.py (BM25 + SQLiteVec)
│   ├── repository/crops.py  # lectura de fichas y del grafo
│   └── schemas/             # modelos Pydantic de entrada/salida
├── ingestion/
│   ├── build_db.py          # comando de ingesta
│   ├── schema.sql           # tablas sources, crops, transitions, chunks, meta
│   ├── load_structured.py   # JSON estructurado → tablas
│   └── documents.py         # carga y fragmentación de PDFs y Markdown
├── knowledge/               # datos de origen (structured/, pdfs/, docs/)
├── tests/                   # pytest; ninguna prueba llama a OpenAI
├── Dockerfile
└── pyproject.toml
```

## Pruebas

```bash
cd api-agent
uv run pytest
```

El agente se prueba con un modelo de chat guionado. `create_agent`, las herramientas, el checkpointer y el TTL de las sesiones son reales; solo el LLM está simulado.

## Docker

### Con Docker Compose (desde la raíz del repo)

```bash
docker compose --profile ingest run --rm ingest   # genera knowledge.db en el volumen api-data
docker compose up -d api-agent                    # en local, compose.override.yml publica el puerto 8000
```

En producción (Dokploy), `compose.yml` no publica puertos: Traefik enruta por dominio. Repite la ingesta cada vez que cambie la base de conocimiento.

### Solo la imagen

```bash
docker build -t crop-advisor api-agent
docker run --rm --env-file .env -v ./api-agent/data:/app/data crop-advisor python -m ingestion.build_db
docker run --env-file .env -v ./api-agent/data:/app/data -p 8000:8000 crop-advisor
```

La imagen corre como un usuario sin privilegios, incluye un `HEALTHCHECK` contra `/health` y lanza uvicorn con 1 worker. `data/` es un volumen y no se copia a la imagen.

## Límites conocidos

- `InMemorySaver` exige 1 worker y pierde las sesiones al reiniciar.
- No hay autenticación: cualquiera que conozca un `session_id` puede leer esa sesión.
- `langchain-community` está archivado. `SQLiteVec` y `BM25Retriever` no filtran por metadatos.
- Sin embeddings, la búsqueda es solo por palabras clave y falla con preguntas parafraseadas.
- Los datos y las reglas son de la sierra andina; el sistema tiene poco respaldo para la costa o la Amazonía.
