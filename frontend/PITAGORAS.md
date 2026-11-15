# Recomendaciones de Pitágoras

Desde el análisis de una parcela, abrir **Próximos sembríos**.
El formulario usa `GET /v1/crops` y envía cultivo anterior, una prioridad,
tipo de riego y si se empoza el agua a `POST /v1/recommendations` (una sola llamada
con evidencia; el modelo de lenguaje tarda ~20 s, por eso el límite es de 60 s).
Altitud y clima salen de la copia de remote-sensing del servidor, no del formulario.

La pantalla muestra el resultado real del motor: primera opción, afinidad,
confianza, motivos con fuentes, alternativas y la rotación de cada alternativa. Una rotación
puede tener menos de cuatro ciclos; no se presenta como un calendario de años.
Los errores y la ausencia de candidatos se muestran sin inventar resultados.

## Desarrollo

Desde `api-agent/`:

```sh
uv sync --locked
# Solo si aún no existe data/knowledge.db:
uv run python -m ingestion.build_db --no-embeddings
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Desde `frontend/`, ejecutar `npm run dev` y abrir `/prueba`.
Vite reenvía `/api` al puerto 8000. El destino puede cambiarse mediante
`PITAGORAS_PROXY_TARGET` en el `.env` raíz. En Docker Compose, el servicio `proxy`
(nginx Alpine) reenvía la misma ruta a `api-agent:8000`, sin CORS ni claves del
modelo en el navegador.

Validación: `npm test`, `npm run build`, `npm run lint`.

## Alcance

- Consume el motor agronómico determinista existente. No llama al chat LLM de
  `/v1/sessions`; no requiere `OPENAI_API_KEY`.
- La altitud se envía solo cuando está disponible en la ubicación, sin pedirla
  en el formulario ni inferirla de las respuestas. Si falta, se envía como
  desconocida. El último cultivo se precarga como papa solo si el nombre de la
  parcela lo indica; se puede corregir antes de enviar.
- No envía datos climáticos simulados como observaciones del agricultor. La API
  aún tiene una captura fija de Toacaso: sus alertas solo se presentan en la
  parcela monitoreada y conservan la fecha que devuelve el servicio.
- Las respuestas viven en la pantalla. No se guardan planes ni se establece un
  calendario de siembra. Cambiar de parcela crea una consulta independiente.

## Referencias visuales

Consultadas como inspiración; no se copiaron imágenes ni componentes:

- [FarmRise, Lollypop Design](https://www.behance.net/gallery/90952627/Farmrise):
  jerarquía móvil y orientación por etapas del cultivo.
- [Cropwise Protector](https://www.cropwise.com/protector): decisiones y consejos
  relacionados con una parcela.
- [xarvio FIELD MANAGER](https://www.xarvio.com/us/en/products/field-manager.html):
  separación entre monitoreo, recomendaciones y detalle.

Paleta: verde `#21664a`, tinta `#223d32`, hoja `#edf5ef`, violeta `#7352a3`,
blanco `#ffffff`. Se conserva la tipografía del proyecto y el marco móvil. La
tarjeta del cultivo concentra el énfasis visual; las pestañas revelan el detalle.
