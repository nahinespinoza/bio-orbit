# Búsqueda acotada del agente (ficha por secciones + RAG filtrado por cultivo)

## Por qué

El agente sabe razonar qué necesita. Hoy no puede pedir solo eso:

- `get_crop_profile` devuelve la ficha completa. La de papa pesa 18,7 KB, y 9,5 KB son `indicadores` (notas de investigación). Lo que entra queda en el historial y se reenvía en cada turno siguiente, hasta 12 turnos.
- `search_sources` busca en todo el índice. Aunque la ingesta ya guarda en cada fragmento qué cultivos menciona (`metadata.crops`), la búsqueda no lo usa. El PDF del MAGAP ocupa el 56 % del índice, y la mayoría de sus fragmentos no menciona ningún cultivo.

**Objetivo:** que cada llamada devuelva solo lo que el agente pidió.

## Enfoques considerados

| | Enfoque | Por qué sí o por qué no |
|---|---|---|
| A | Ficha por secciones | Dato exacto y barato. Por sí sola no mejora el RAG |
| B | Las fichas dentro del RAG | La búsqueda por parecido puede traer otro cultivo o perder un número exacto. Obliga a volver a ingerir con embeddings |
| **C** | **A + RAG filtrado por cultivo** | **Elegido.** Datos con estructura → consulta exacta; texto libre (PDF y documentos) → RAG con filtro |

## Diseño

### 1. `get_crop_profile(crop, sections)`

- `sections` es una lista **obligatoria** (mínimo 1). Sus valores son los nombres de las secciones de la ficha: `suelo`, `clima`, `ciclo_meses`, `plagas`, `enfermedades`, `efecto_rotacion`, `mano_obra`, `facilidad_cultivo`, `mercado`, `huecos`, `fuentes`, `siguientes`, `sensibilidades`.
- Siempre devuelve una cabecera corta: `crop_id`, `name`, `family`, `crop_type`, `tags`, `confidence` y `alcance_geografico`.
- `siguientes` = las transiciones de salida del cultivo (hoy `next_crops`).
- `fuentes` = las citas de la ficha, más título y fiabilidad de cada fuente (hoy `sources`).
- `sensibilidades` = el bloque del cultivo en `sensibilidades.json` (hoy no llega a la tool).
- **No se pueden pedir** `indicadores`, `indicadores_nota` ni `huecos_indicadores`. *(Decisión mía: lo que sirve de ahí ya está depurado en `sensibilidades`.)*
- El docstring de la tool lista las secciones y qué trae cada una, para que el agente elija.

### 2. `search_sources(query, crop=None)`

- Si recibe `crop`, solo busca entre los fragmentos cuyo `metadata.crops` incluye ese cultivo. El nombre se resuelve con `resolve_crop()`, igual que en la ficha.
- Si el filtro no deja ningún resultado, busca sin filtro y lo avisa en la respuesta («no hay pasajes que mencionen X; resultados generales»). *(Decisión mía.)*
- Sin `crop`, funciona igual que hoy.
- Se mantienen el `k` y el recorte de 900 caracteres que se usan hoy.

### 3. Prompt

En la línea 60 de `system_prompt.md`: para datos de un cultivo, usar `get_crop_profile` con solo las secciones necesarias; para el porqué o para lo que dicen las fuentes, usar `search_sources` con `crop` cuando la pregunta es de un cultivo.

## Fuera de alcance

- El endpoint REST `GET /v1/crops/{crop}` sigue devolviendo la ficha completa. Ese consumidor es la API, no el modelo.
- No se cambia el contenido de `cultivos.json`. No se borran los `indicadores` ni se vuelve a ingerir.
- El ruido del MAGAP se decide aparte.

## Lo que queda para quien lo construya

- Cómo filtrar en el recuperador híbrido. BM25 y SQLiteVec no filtran por metadatos: se puede armar BM25 sobre el subconjunto del cultivo (son ~2 400 fragmentos en memoria) y en la parte vectorial pedir un `k` mayor y filtrar después.
- Pruebas: secciones pedidas frente a secciones devueltas; sección inválida; `indicadores` imposible de pedir; filtro por cultivo; caso sin resultados que busca sin filtro.
- Actualizar la sección de tools del README.
