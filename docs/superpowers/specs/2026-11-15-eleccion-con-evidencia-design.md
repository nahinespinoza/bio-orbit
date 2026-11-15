# Recomendación de una sola llamada con evidencia (remote-sensing + fichas)

## Por qué

El frontend (capturas en `reference/`) necesita un endpoint de **una sola llamada** que devuelva **solo JSON**: el cultivo recomendado con su afinidad de 0 a 100, su rotación, el porqué y las otras opciones.

La investigación de cada cultivo (`indicadores*` en `cultivos.json`) se hizo para compararla con los indicadores del remote-sensing de la parcela. Hoy ninguna de las dos cosas pesa en la recomendación:
- La investigación no está en el RAG ni se puede consultar.
- Del `output` del remote-sensing, el motor usa menos de 1 KB: las alertas de la última semana.

**Objetivo:** el servidor recibe las respuestas de la pantalla de opciones. El motor filtra y entrega los 5 mejores candidatos agronómicos. El modelo de lenguaje califica cada uno por **riesgo** (comparando la parcela con la investigación) y por **prioridad del agricultor** (con los datos de la ficha). El código combina las notas y devuelve el JSON del contrato.

## Metas, no-metas y anti-metas

**Metas**
- `POST /v1/recommendations`: petición con las respuestas de la pantalla → respuesta JSON con la recomendación, la rotación, el porqué y las 5 opciones.
- La investigación de las fichas entra al RAG, como fragmentos por cultivo y tema.
- El modelo califica y el código combina; el número es estable y explicable.

**No-metas**
- **No se toca la conversación** (`/v1/sessions`) **ni el motor directo** (`/v1/recommend`). Siguen igual, prioridades incluidas.
- No se reescriben los documentos 03 ni 07.
- No se cubren varias parcelas: es la parcela 1, con su JSON fijo.
- No hay datos de suelo opcionales: se asume que no vienen.
- No se evalúa la calidad de las notas con el modelo real (va aparte).

**Anti-metas.** Sería un fracaso si:
- Gana un cultivo con riesgo alto frente a uno sin riesgo.
- El modelo inventa datos o umbrales, o presenta un dato de otra región como si fuera de Ecuador.
- La respuesta trae texto conversacional en vez del JSON del contrato.
- El modelo propone un cultivo fuera de los candidatos del motor.

## Restricciones

- Los textos del JSON, en español sencillo, como los de las capturas.
- Las pruebas no llaman a OpenAI: el modelo de chat es falso y devuelve JSON guionado.
- Hay que volver a ingerir para que la investigación entre al RAG.
- Una sola llamada al modelo por petición.

## Enfoques considerados

| | Enfoque | Decisión |
|---|---|---|
| A | El modelo pone el número de 0 a 100 directamente | Descartado: el número varía entre corridas |
| **B** | **El modelo califica por criterio y el código combina con pesos fijos** | **Elegido (usuario).** Estable, explicable, y alimenta la pestaña «Por qué» |
| C | El código calcula todo y el modelo solo explica | Descartado: el modelo dejaría de decidir por prioridad y riesgo |

Para llevar la evidencia al modelo se eligió el **híbrido**: la investigación entra al RAG y el código adjunta a cada candidato sus fragmentos, buscados por cultivo y tema.

## Diseño

### 1. Petición

`POST /v1/recommendations`:

```json
{
  "previous_crop": "cebada",
  "priority": "low_labor",
  "irrigation": "rain_only",
  "waterlogging": "long",
  "remote_sensing": null
}
```

- `previous_crop`: id o nombre de un cultivo del pool (se resuelve con `resolve_crop`), o `"new_land"`. Es uno solo, como en la pantalla.
- `priority`: una de `market_value` | `speed` | `fewer_pests` | `low_labor`. Una sola, porque la pantalla usa botones de opción única.
- `irrigation`: `rain_only` | `pump` | `canal` | `sprinkler_drip` | `manual`. `rain_only` se traduce a riego `no`; el resto, a `yes`.
- `waterlogging`: `no` | `briefly` | `long`, que se traduce a drenaje `good` | `fair` | `poor`.
- `remote_sensing`: se acepta, pero **en el MVP se ignora y no se valida**: siempre se usa la copia del servidor (decidido por el usuario).
- La altitud sale de `output.altitud_parcela_msnm`.
- **Decisiones del autor:** los nombres de los campos (en inglés, como el resto de la API), los valores de riego y empozamiento y su traducción.

### 2. Candidatos (motor)

- Se reutilizan la validación, los filtros duros y la rotación del motor, sin prioridades: el orden es **solo por aptitud agronómica**, con `aptitude()` de `scoring.py`.
- Se entregan los **5 primeros**. Cada uno trae:
  - `aptitud` (0-100), la transición con su fuente, la rotación (`build_rotation`), las advertencias (`advisories_for`), los `facts`, la confianza de la ficha y las fuentes.
  - `datos_prioridades`, con lo que dice la ficha de cada prioridad, sin puntaje:
    - `mercado`: precio, unidad, fecha, volatilidad y confianza.
    - `rapidez`: ciclo en meses.
    - `mano_obra`: nivel, jornales por hectárea y si se puede mecanizar.
    - `plagas`: plagas y enfermedades, y si comparte plagas con el cultivo anterior.
    - Lo que falta va como `"sin dato"`.
  - `evidencia` (punto 4).
- El motor existente no cambia: se agrega una función nueva `rank_by_aptitude(...)` que usa sus piezas.
- **No se aplica la regla de no comerciales** (decidido por el usuario): barbecho, pasto y abono verde entran como candidatos para que haya más opciones. Con un solo cultivo previo, F1 deja repetir quinua o maíz una vez.

### 3. Condiciones de la parcela

`plot_conditions(rs) -> dict` resume el `output`:
- `clima_semana`: fechas, lluvia, balance hídrico, humedad de raíz y superficial, humedad relativa, temperatura mínima y máxima, y los códigos de los semáforos.
- `proyeccion`: mes, lluvia esperada, temperatura mínima esperada y las alertas.
- `lote_satelite`: fecha de la última foto, días desde la foto, NDVI, NDRE, NDMI, variación de NDVI, distribución, sector más afectado y los códigos de los semáforos.
- `alerta_cruzada` y `parcela` (zona y altitud).
- `temas_activos`.

No incluye rutas de imágenes, series ni historial. Objetivo: ≤ 1,5 KB.

**Temas activos**, decididos solo con los códigos del propio remote-sensing:

| Tema | Se activa si |
|---|---|
| `helada` | El semáforo de helada no es `VERDE`, o hay una alerta `HELADAS` |
| `agua` | Riego `ROJO_SECO`, humedad del lote `ROJO_ESTRES_HIDRICO` o una alerta `SEQUIA` |
| `exceso_agua` | Riego `AZUL_SATURADO`, una alerta `EXCESO_AGUA` o `waterlogging = long` |
| `sanidad` | Una alerta `PLAGAS_LANCHA` o un cruce `LANCHA_CONFIRMADA` |
| `fertilidad` | Vigor `AMARILLO_NUTRICION`, alerta `NUTRIENTES` o un cruce `NUTRICION_PROBABLE` confirmado |
| `ciclo_siembra` | Siempre |

Con el JSON actual: `sanidad`, `fertilidad`, `agua` y `ciclo_siembra`.

### 4. Investigación de las fichas en el RAG (ingesta)

- **Un fragmento por bloque de origen** (132 bloques más uno de vacíos por cultivo), con:
  - `doc_id = "cultivos.json#<crop>/<clave original>"`, `doc_kind = "crop_research"`, `crops = [<crop>]`, `tema` normalizado, `title = "Investigación del cultivo: <Nombre> — <tema>"` y `reliability_level = "medium"`.
  - Texto en español legible: valores, notas, citas con URL y los avisos de calidad (origen y citas sin verificar).
- **Temas normalizados:**

| Tema | Claves de origen |
|---|---|
| `helada` | `helada` |
| `agua` | `agua`, `humedad_suelo` |
| `exceso_agua` | `exceso_agua` |
| `sanidad` | `sanidad`, `sanidad_lancha`, `hospedero_plagas_papa`, `efecto_plagas` |
| `fertilidad` | `fertilidad`, `N_aportado`, `biomasa_N` |
| `ciclo_siembra` | `ciclo_siembra`, `duracion_andina` |
| `altitud_temperatura` | `altitud_temperatura`, `altitud_adaptacion` |
| `rotacion` | `rotacion`, `tiempo_antes_papa`, `riesgo_antes_papa`, `abono_verde_papa`, `momento_incorporacion`, `especies_y_biomasa` |
| `fenologia` | `fenologia_indices` |
| `vacios` | `huecos_indicadores` |
| `otros` | Cualquier clave nueva (y se registra en el log) |

- **Evidencia de cada candidato:** sus fragmentos de los `temas_activos`, leídos de `chunks` por `crops` y `tema`, en versión compacta: sin URL, con autor y año, y con los avisos de calidad. Si un tema no tiene fragmento, va `"sin investigación"`.
- **Tope:** lo que recibe el modelo pesa ≤ 12 KB. Si se pasa:
  1. Del quinto candidato hacia el segundo, a cada uno le queda solo la evidencia de los temas con alerta (sin `ciclo_siembra`), hasta bajar del tope.
  2. Si aún se pasa, del quinto hacia el segundo se quita la evidencia (`"recortada"`).
  3. Se marca `evidencia_recortada`.

### 5. Llamada al modelo (salida estructurada)

- Una llamada con salida estructurada (esquema Pydantic). Entrada: la petición traducida, `condiciones_parcela` y los 5 candidatos.
- Salida: por cada candidato,
  - `prioridad`: `{nota 0-100, motivo, referencias}`.
  - `riesgo`: `{nota 0-100, motivo, referencias}`.
  - Un `resumen` de una frase.
- Además, un texto corto `como_comparar`.
- Las referencias son ids de fuente (`F1`, `F2`, …) que existen en los datos entregados.
- **Tramos que debe seguir el modelo:**
  - *Prioridad:* 85-100 si es el mejor dato entre los candidatos y tiene fuente; 60-84 si es bueno; 35-59 si es regular; menos de 35 si es malo.
  - *Riesgo* (100 = sin riesgo): 90-100 si no hay condición adversa; 60-89 si la condición está y el cultivo la tolera; 30-59 si es sensible; 0-29 si es muy sensible, con evidencia de Ecuador o los Andes.
- Prompt de sistema nuevo, propio de este flujo (`app/advisor/prompt.md`).
- Los candidatos que el modelo no califique, o un cultivo que no esté entre ellos, se ignoran. Si falta la nota de un candidato, se usa el valor neutral (60) y se marca.

### 6. Combinación (código)

**Afinidad = 0,30 · prioridad + 0,40 · riesgo + 0,30 · aptitud** (pesos decididos por el usuario). **En todas las notas y en la afinidad, 100 es lo mejor** (decidido por el usuario). El riesgo también va en esa dirección: 100 = sin riesgo para ese cultivo en esta parcela. Reglas fijas que el código aplica sobre las notas del modelo antes de combinar:

1. Si la ficha no tiene el dato de la prioridad elegida → prioridad = 30 (decidido por el usuario).
2. Si el motor generó una advertencia ALTO para ese cultivo → riesgo ≤ 40; si fue MEDIO → riesgo ≤ 70.
3. Si toda la evidencia de los temas activos es de otra región o está sin verificar → riesgo ≥ 50.
4. Si no hay investigación de ningún tema activo → riesgo = 60 y la marca «sin evidencia».
5. **Tope «riesgo primero»:** si el riesgo queda bajo 40, la afinidad no pasa de 40 (el usuario bajó el tope de 49 a 40) (decisión del autor; el usuario puede quitarlo).

- Se ordena por afinidad, con una decimal. El primero es la recomendación.
- **Confianza** (`alta` | `media` | `baja`): parte de la confianza de la ficha y baja un nivel por cada uno de estos: falta el dato de la prioridad, no hay evidencia, o la evidencia es de otra región.

### 7. Respuesta (contrato con el frontend)

```json
{
  "status": "ok",
  "data_date": "11/11/2026",
  "recommendation": {
    "crop": "chocho",
    "name": "Chocho (tarwi)",
    "affinity": 54.2,
    "confidence": "media",
    "summary": "…",
    "why": [
      {"criterion": "priority", "title": "Menos trabajo", "score": 70, "detail": "…", "references": ["F1", "F2"]},
      {"criterion": "risk", "title": "Condiciones de tu parcela", "score": 90, "detail": "…", "references": ["F2"]},
      {"criterion": "aptitude", "title": "Un cambio en tu rotación", "score": 58, "detail": "…", "references": ["F1"]}
    ],
    "rotation": [{"cycle": 1, "crop": "chocho", "name": "Chocho (tarwi)", "confidence": "media"}],
    "advisories": [{"level": "ALTO", "message": "…"}]
  },
  "alternatives": [{"crop": "oca", "name": "Oca", "affinity": 34.2, "confidence": "baja", "summary": "…", "why": []}],
  "how_to_compare": "…",
  "sources": [{"id": "F1", "title": "…", "url": "…"}],
  "missing_data": ["Oca: mano_obra"],
  "flags": {"evidence_trimmed": false, "remote_sensing_applies": true}
}
```

- `alternatives` son los otros 4 candidatos, ordenados por afinidad. `why.title` usa la etiqueta de la pantalla para la prioridad («Valor de venta», «Cosechar antes», «Menos plagas», «Menos trabajo»).
- **Errores:**
  - `422`: entrada inválida.
  - `200` con `status = "no_candidates"`: ningún cultivo pasa los filtros duros, con los descartados y su motivo.
  - `503`: no hay modelo configurado. Mismo patrón que `/v1/sessions`.
  - `502`: el modelo falla.

## Lo que queda para quien lo construya

- La estructura de módulos (sugerencia: `app/advisor/` con la petición, las condiciones, la evidencia, la llamada al modelo y la combinación, y `app/api/routes/recommendations.py`).
- El formato del texto de los fragmentos de investigación y de la evidencia compacta.
- La medición del tope de 12 KB.
- Pruebas, como mínimo:
  - Traducción de la petición.
  - `rank_by_aptitude` da 5 candidatos o menos y no usa prioridades.
  - Fragmentos de investigación en la ingesta, con sus metadatos, y `otros` para una clave desconocida.
  - `plot_conditions` con el JSON actual: sin rutas `.png`, ≤ 1,5 KB y `temas_activos == {sanidad, fertilidad, agua, ciclo_siembra}`.
  - La evidencia trae solo temas activos y respeta el tope.
  - Cada regla de combinación (1-5) y el cálculo con los pesos.
  - El endpoint con un modelo falso: forma del contrato, `no_candidates`, `422` y `503`.
- Actualizar el README.
