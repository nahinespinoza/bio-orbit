# Búsqueda acotada del agente: plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** que `get_crop_profile` devuelva solo las secciones de la ficha que pide el agente, y que `search_sources` pueda buscar solo en los fragmentos de un cultivo.

**Architecture:** la ficha sale de SQLite por sección: una función nueva del repositorio arma la respuesta a partir de `get_crop_profile` (que se mantiene igual para el REST). El RAG suma la clase `SourceSearch`, que envuelve al recuperador actual y arma recuperadores por cultivo (BM25 sobre el subconjunto + vectorial con `k` ampliado y filtrado), guardados en caché. `AgentContext.retriever` pasa a ser `AgentContext.sources: SourceSearch`.

**Tech Stack:** Python 3.13, LangChain (`BM25Retriever`, `EnsembleRetriever`, `SQLiteVec`), FastAPI, pytest y uv.

**Spec:** `docs/superpowers/specs/2026-11-15-busqueda-acotada-design.md`

## Global Constraints

- Todo texto que vea el modelo o el usuario, en español.
- `GET /v1/crops/{crop}` no cambia: sigue devolviendo la ficha completa.
- No se modifica `cultivos.json` ni hace falta volver a ingerir.
- Se mantienen `rag_top_k` (5) y `PASSAGE_CHARS` (900).
- Las pruebas no llaman a OpenAI: se corren en modo `bm25`, con el modelo guionado de `tests/conftest.py`.
- Las pruebas se corren desde `api-agent/` con `uv run pytest`.

## Review Focus

- **Cultivo con alias o con tildes** (`"tarwi"`, `"Maíz"`) en `crop` de las dos tools: debe resolverse con `resolve_crop()`, igual que hoy. → Lo prueban `test_crop_sections_resolves_alias` (Task 2) y `test_search_filters_by_alias` (Task 3).
- **Cultivo sin bloque en `sensibilidades.json`** (abono, barbecho, lenteja, pasto, trigo): la sección `sensibilidades` devuelve `null` con una nota, sin lanzar un error. → `test_sections_sensitivities_missing` (Task 1).
- **Cultivo desconocido en `search_sources`** (`crop="tomate"`): busca sin filtro y lo avisa; no da error. → `test_search_unknown_crop_falls_back` (Task 3).
- **`sections` vacía o con un valor inválido** (`[]`, `["indicadores"]`): el modelo recibe un mensaje de error de la tool y el agente no se cae. → `test_get_crop_profile_rejects_invalid_sections` (Task 2).
- **Cultivo sin fragmentos en el índice** (p. ej. `barbecho` podría tener pocos o ninguno): `BM25Retriever.from_documents([])` falla. Si el subconjunto está vacío, se usa la búsqueda sin filtro. → `test_search_crop_without_chunks_falls_back` (Task 3).

---

### Task 0: Rama y commits de lo que ya está hecho

- [ ] **Step 1:** desde `D:\gitprojects\bio-orbit`, verificar `git config core.hooksPath` → `.githooks`.
- [ ] **Step 2:** crear la rama desde `origin/main`, llevando los cambios sin commit: `git switch -c feat/api-agent-busqueda-acotada origin/main`. Expected: sin conflictos (los cambios locales no tocan `frontend/`).
- [ ] **Step 3:** commit del borrado del backend:

```bash
git add -A backend compose.yml compose.override.yml api-agent/README.md api-agent/knowledge/docs/07-indicadores-remote-sensing.md
git commit -m "backend: eliminar el servicio; el clima del agente sale de remote-sensing/resultado_match.json"
```

- [ ] **Step 4:** commit del diseño y del plan: `git add docs/superpowers && git commit -m "docs: diseño y plan de la búsqueda acotada del agente"`.

---

### Task 1: Ficha por secciones en el repositorio

**Files:**
- Modify: `api-agent/app/repository/crops.py` (agregar después de `get_crop_profile`, línea ~89)
- Test: `api-agent/tests/test_crop_profile.py` (nuevo)

**Interfaces:**
- Produces:
  - `PROFILE_SECTIONS: tuple[str, ...] = ("suelo", "clima", "ciclo_meses", "plagas", "enfermedades", "efecto_rotacion", "mano_obra", "facilidad_cultivo", "mercado", "huecos", "fuentes", "siguientes", "sensibilidades")`
  - `get_crop_sections(conn: sqlite3.Connection, crop_id: str, sections: Sequence[str], sensitivities: dict) -> dict | None`. Devuelve `None` si el cultivo no existe y lanza `ValueError` si alguna sección no está en `PROFILE_SECTIONS`. Si no, devuelve `{"crop_id", "name", "family", "crop_type", "tags", "confidence", "alcance_geografico", "sections": {<sección pedida>: valor}}`.
  - Valor de cada sección:
    - Secciones de la ficha → `profile_json[sección]` (o `None` si falta).
    - `siguientes` → `next_crops` de `get_crop_profile`.
    - `fuentes` → `{"citas": profile_json["fuentes"], "detalle": sources}`.
    - `sensibilidades` → `sensitivities.get(crop_id)`, o `{"valor": None, "nota": "Sin datos de sensibilidad con cita de Ecuador o los Andes."}` si no existe.

- [ ] **Step 1: escribir las pruebas que fallan**

```python
# tests/test_crop_profile.py
"""Ficha por secciones: solo lo pedido, nunca los indicadores de investigación."""
import json
import pytest
from app.rag.db import connect
from app.repository.crops import PROFILE_SECTIONS, get_crop_sections

HEADER = {"crop_id", "name", "family", "crop_type", "tags", "confidence", "alcance_geografico", "sections"}

@pytest.fixture
def conn(settings):
    return connect(settings.resolve(settings.db_path))

def test_sections_returns_only_requested(conn, kb):
    r = get_crop_sections(conn, "papa", ["plagas", "mano_obra"], kb.sensitivities)
    assert set(r) == HEADER
    assert set(r["sections"]) == {"plagas", "mano_obra"}
    assert r["sections"]["plagas"]                                   # dato real de la ficha
    assert "indicadores" not in json.dumps(r, ensure_ascii=False)

def test_sections_is_much_smaller_than_full_profile(conn, kb):
    r = get_crop_sections(conn, "papa", ["plagas"], kb.sensitivities)
    assert len(json.dumps(r, ensure_ascii=False)) < 2000

def test_sections_siguientes_and_fuentes(conn, kb):
    r = get_crop_sections(conn, "papa", ["siguientes", "fuentes"], kb.sensitivities)["sections"]
    assert r["siguientes"] and {"to_crop", "kind", "source_note"} <= set(r["siguientes"][0])
    assert set(r["fuentes"]) == {"citas", "detalle"} and r["fuentes"]["detalle"]

def test_sections_sensitivities_present(conn, kb):
    r = get_crop_sections(conn, "papa", ["sensibilidades"], kb.sensitivities)["sections"]
    assert r["sensibilidades"]["hospedero_lancha"]["valor"] is True

def test_sections_sensitivities_missing(conn, kb):
    r = get_crop_sections(conn, "barbecho", ["sensibilidades"], kb.sensitivities)["sections"]
    assert r["sensibilidades"]["valor"] is None and "Sin datos" in r["sensibilidades"]["nota"]

def test_sections_rejects_research_fields(conn, kb):
    assert "indicadores" not in PROFILE_SECTIONS
    with pytest.raises(ValueError):
        get_crop_sections(conn, "papa", ["indicadores"], kb.sensitivities)

def test_sections_unknown_crop(conn, kb):
    assert get_crop_sections(conn, "xyz", ["plagas"], kb.sensitivities) is None
```

- [ ] **Step 2:** `cd api-agent && uv run pytest tests/test_crop_profile.py -v` → FAIL (`ImportError: cannot import name 'PROFILE_SECTIONS'`).
- [ ] **Step 3:** implementar `PROFILE_SECTIONS` y `get_crop_sections` en `app/repository/crops.py`. Llamar a `get_crop_profile` y elegir las secciones. La cabecera toma `alcance_geografico` de `profile`.
- [ ] **Step 4:** `uv run pytest tests/test_crop_profile.py -v` → PASS.
- [ ] **Step 5:** `git add api-agent/app/repository/crops.py api-agent/tests/test_crop_profile.py && git commit -m "api-agent: ficha del cultivo por secciones en el repositorio"`

---

### Task 2: La tool `get_crop_profile` pide secciones

**Files:**
- Modify: `api-agent/app/agent/tools.py:184-190`
- Modify: `api-agent/app/agent/system_prompt.md:60`
- Modify: `api-agent/README.md:184`
- Test: `api-agent/tests/test_sessions.py` (agregar al final)

**Interfaces:**
- Consumes: `PROFILE_SECTIONS` y `get_crop_sections(...)` (Task 1).
- Produces: tool `get_crop_profile(runtime, crop: str, sections: Annotated[list[Section], Field(min_length=1)]) -> str`, con `Section = Literal[...]` y los mismos 13 valores de `PROFILE_SECTIONS`. Una prueba verifica que coinciden.

- [ ] **Step 1: escribir las pruebas que fallan** (en `tests/test_sessions.py`)

```python
def _tool_content(model, call_index=1):
    return next(m for m in model.seen[call_index] if isinstance(m, ToolMessage)).content

def test_get_crop_profile_returns_requested_sections(make_client, scripted):
    model = scripted(tool_call("get_crop_profile", {"crop": "papa", "sections": ["plagas"]}, "c1"), AIMessage(content="Ok."))
    send(make_client(model), SID, "¿Qué plagas tiene la papa?")
    body = json.loads(_tool_content(model))
    assert set(body["sections"]) == {"plagas"} and "indicadores" not in _tool_content(model)

def test_crop_sections_resolves_alias(make_client, scripted):
    model = scripted(tool_call("get_crop_profile", {"crop": "tarwi", "sections": ["mano_obra"]}, "c1"), AIMessage(content="Ok."))
    send(make_client(model), SID, "¿Cuánto trabajo da el tarwi?")
    assert json.loads(_tool_content(model))["crop_id"] == "chocho"

@pytest.mark.parametrize("sections", [[], ["indicadores"]])
def test_get_crop_profile_rejects_invalid_sections(make_client, scripted, sections):
    model = scripted(tool_call("get_crop_profile", {"crop": "papa", "sections": sections}, "c1"), AIMessage(content="Ok."))
    r = send(make_client(model), SID, "Ficha de la papa")
    assert r.status_code == 200 and "sections" in _tool_content(model)

def test_section_literal_matches_repository():
    from typing import get_args
    from app.agent.tools import Section
    from app.repository.crops import PROFILE_SECTIONS
    assert set(get_args(Section)) == set(PROFILE_SECTIONS)
```

(Agregar `import json` y `import pytest` arriba si faltan.)

- [ ] **Step 2:** `uv run pytest tests/test_sessions.py -k "crop_profile or crop_sections or section_literal" -v` → FAIL.
- [ ] **Step 3:** en `tools.py`, cambiar la firma de la tool a la de **Interfaces**. Para un cultivo desconocido, mantener el error actual con `suggestions`. El docstring tiene que listar cada sección con lo que trae, en una línea: suelo, clima, ciclo_meses, plagas, enfermedades, efecto_rotacion (qué aporta o quita al suelo), mano_obra, facilidad_cultivo, mercado, huecos (datos que faltan), fuentes, siguientes (qué cultivos pueden ir después) y sensibilidades (helada, lancha, sequía, nitrógeno, exceso de agua). Además debe decir: «Pide solo las secciones que necesitas para responder».
- [ ] **Step 4:** en `system_prompt.md:60`, cambiar la línea por: «Para datos de un cultivo, usa `get_crop_profile` con solo las secciones que necesitas (p. ej. `plagas` para «¿qué plagas tiene la quinua?»). Para el porqué o lo que dicen las fuentes, usa `search_sources`». La parte del filtro por cultivo se agrega en la Task 4. En `README.md:184`, cambiar la fila por: «Devuelve las secciones pedidas de la ficha de un cultivo (nunca los indicadores de investigación)».
- [ ] **Step 5:** `uv run pytest -q` → todo PASS.
- [ ] **Step 6:** `git add api-agent/app/agent api-agent/README.md api-agent/tests/test_sessions.py && git commit -m "api-agent: get_crop_profile devuelve solo las secciones pedidas"`

---

### Task 3: `SourceSearch`, RAG filtrado por cultivo

**Files:**
- Modify: `api-agent/app/rag/retriever.py`
- Test: `api-agent/tests/test_rag.py` (agregar)

**Interfaces:**
- Consumes: `build_retriever(conn, settings)` (existente, no cambia) y `resolve_crop(text, kb) -> tuple[str | None, list[str]]` de `app/engine/validation.py`.
- Produces:
  - `@dataclass(frozen=True) class SearchResult: docs: list[Document]; crop: str | None; filtered: bool` (`crop` = id resuelto o `None`; `filtered` = `False` si no se pidió cultivo o si se buscó sin filtro).
  - `class SourceSearch: __init__(self, conn: sqlite3.Connection, settings: Settings, kb: KnowledgeBase)`, con el atributo `mode: str` (el mismo valor que devuelve `build_retriever`) y el método `search(self, query: str, crop: str | None = None) -> SearchResult`.

Cómo funciona:
- El recuperador sin filtro sale de `build_retriever`.
- El recuperador de un cultivo se arma la primera vez que se pide y queda en caché (`dict[str, BaseRetriever]`):
  - BM25 sobre los documentos cuyo `metadata["crops"]` contiene el cultivo, con `k=rag_top_k`.
  - En modo `hybrid`, además un `BaseRetriever` interno que pide `rag_top_k * 10` al vectorial, filtra por cultivo y corta en `rag_top_k`. Los dos se fusionan con `EnsembleRetriever` y pesos `[0.5, 0.5]`.
- Hay que buscar sin filtro (con `filtered=False`) en tres casos: el cultivo no se resuelve, el subconjunto está vacío o la búsqueda filtrada no devuelve nada.

- [ ] **Step 1: escribir las pruebas que fallan**

```python
from app.rag.retriever import SourceSearch

@pytest.fixture
def sources(settings, kb):
    return SourceSearch(connect(settings.resolve(settings.db_path)), settings, kb)

def test_search_without_crop_matches_old_behavior(sources):
    r = sources.search("gorgojo de los Andes en papa")
    assert not r.filtered and r.crop is None
    assert any(d.metadata["source_id"] == 2 for d in r.docs)

def test_search_filters_by_crop(sources):
    r = sources.search("plagas y enfermedades", crop="quinua")
    assert r.filtered and r.crop == "quinua" and r.docs
    assert all("quinua" in d.metadata["crops"] for d in r.docs)

def test_search_filters_by_alias(sources):
    r = sources.search("rotación", crop="tarwi")
    assert r.crop == "chocho" and all("chocho" in d.metadata["crops"] for d in r.docs)

def test_search_unknown_crop_falls_back(sources):
    r = sources.search("rotación de cultivos", crop="tomate")
    assert not r.filtered and r.crop is None and r.docs

def test_search_crop_without_chunks_falls_back(sources, monkeypatch):
    monkeypatch.setattr(sources, "_docs", [d for d in sources._docs if "haba" not in d.metadata["crops"]])
    sources._cache.clear()
    r = sources.search("rotación", crop="haba")
    assert not r.filtered and r.docs
```

(La última prueba asume que `SourceSearch` guarda los documentos en `self._docs` y la caché en `self._cache`; son nombres fijados por este plan. Agregar `import pytest` arriba si falta.)

- [ ] **Step 2:** `uv run pytest tests/test_rag.py -v` → FAIL (`ImportError: SourceSearch`).
- [ ] **Step 3:** implementar `SearchResult` y `SourceSearch` en `retriever.py`. Actualizar el docstring del módulo: la línea «MVP: … no filtran por metadatos» pasa a decir que el filtro por cultivo lo hace `SourceSearch`.
- [ ] **Step 4:** `uv run pytest tests/test_rag.py -v` → PASS.
- [ ] **Step 5:** `git add api-agent/app/rag/retriever.py api-agent/tests/test_rag.py && git commit -m "api-agent: búsqueda en las fuentes filtrada por cultivo (SourceSearch)"`

---

### Task 4: `search_sources(query, crop)` conectado al agente

**Files:**
- Modify: `api-agent/app/memory/state.py:24-29` (`retriever: BaseRetriever` → `sources: SourceSearch`)
- Modify: `api-agent/app/api/deps.py:23-47` (`Services.retriever` → `Services.sources: SourceSearch`; `retrieval_mode` toma el valor de `sources.mode`)
- Modify: `api-agent/app/agent/tools.py:166-181`
- Modify: `api-agent/app/agent/system_prompt.md:60` y `api-agent/README.md:183`
- Test: `api-agent/tests/test_sessions.py`

**Interfaces:**
- Consumes: `SourceSearch` y `SearchResult` (Task 3).
- Produces: tool `search_sources(runtime, query: str, crop: str | None = None) -> Command`.

- [ ] **Step 1: escribir las pruebas que fallan**

```python
def test_search_sources_with_crop_filters(make_client, scripted):
    model = scripted(tool_call("search_sources", {"query": "plagas", "crop": "quinua"}, "c1"), AIMessage(content="Ok."))
    b = send(make_client(model), SID, "¿Qué plagas tiene la quinua?").json()
    assert b["citations"]
    assert "resultados generales" not in _tool_content(model)

def test_search_sources_unknown_crop_says_so(make_client, scripted):
    model = scripted(tool_call("search_sources", {"query": "rotación", "crop": "tomate"}, "c1"), AIMessage(content="Ok."))
    send(make_client(model), SID, "¿Y el tomate?")
    assert _tool_content(model).startswith("No hay pasajes que mencionen «tomate»; resultados generales.")
```

- [ ] **Step 2:** `uv run pytest tests/test_sessions.py -k search_sources -v` → FAIL.
- [ ] **Step 3:** conectar `SourceSearch`. En `deps.py`, `build_services` crea `SourceSearch(conn, settings, kb)` en lugar de `build_retriever`. En la tool:
  - Si se pidió `crop` y `filtered` es `False`, anteponer al contenido la línea fija «No hay pasajes que mencionen «{crop}»; resultados generales.» (`{crop}` es el texto que recibió la tool) y una línea en blanco.
  - Agregar al docstring: «Si la pregunta es sobre un cultivo, pasa `crop` para buscar solo en pasajes que lo mencionan».
  - Arreglar también el pendiente de `PENDIENTES.md`: la descripción de fuentes pasa a «FAO (cultivos andinos), MAGAP y documentos del proyecto».
- [ ] **Step 4:** completar la línea 60 del prompt: «…usa `search_sources`, y si la pregunta es sobre un cultivo pásale `crop`». En `README.md:183`, cambiar la fila por: «Busca pasajes en las fuentes (opcionalmente solo los de un cultivo) y acumula las citas».
- [ ] **Step 5:** `uv run pytest -q` → todo PASS (incluido `test_api.py`, que comprueba `retrieval_mode == "bm25"`).
- [ ] **Step 6:** `git add api-agent && git commit -m "api-agent: search_sources acepta crop y filtra los pasajes por cultivo"`
