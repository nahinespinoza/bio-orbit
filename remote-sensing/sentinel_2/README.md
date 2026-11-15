# sentinel_2: monitoreo de la parcela con Sentinel-2

Analiza la parcela de papa con imágenes Sentinel-2 L2A (10 m) de los últimos 6 meses. Calcula índices de
vegetación y humedad, los clasifica en semáforos y los cruza con el clima. Escribe un reporte por semana con
las alertas para el agricultor.

Ambiente: `conda activate ecofolia-frontend`. Los comandos se corren desde esta carpeta.

```
python preprocesar.py    # PROCESAMIENTO: regenera todo con los datos ya descargados (sin internet)
python monitoreo.py      # DESCARGA lo nuevo (Sentinel-2 + clima) y después procesa todo
```

---

## Scripts

| Script | Tipo | Qué hace |
|---|---|---|
| `monitoreo.py` | **Descarga** + procesamiento | Busca las escenas en el catálogo STAC de Earth Search (AWS) y lee solo el recorte de la parcela más 200 m alrededor. Guarda los TIF y PNG en `datos_sentinel/imagenes/` y baja el clima de Open-Meteo (ERA5). Después hace todo lo que hace `preprocesar.py`. Es incremental: solo baja las escenas nuevas. Opciones: `--inicio`, `--fin`, `--parcela` |
| `preprocesar.py` | **Procesamiento** | Regenera todos los datos que muestra el Streamlit sin descargar nada: (1) índices por pase desde los TIF, (2) análisis a 10 m (`precision_s2.py`), (3) climatología, (4) reportes semanales y gráfico de series, (5) `api_sentinel_2.json` |
| `precision_s2.py` | Módulo de análisis | Filtra las imágenes con < 20 % de nubes **sobre el polígono** y elige ~1 cada 15 días. Calcula NDVI, NDRE y NDMI píxel a píxel y aplica la regla A (vigor) y la regla B (humedad). Calcula el % de área por estado y los sectores N/S/E/O. Genera los PNG y TIF de `salida_s2/`, `resultado_prototipo_sentinel_2.json` y el cruce con NASA POWER. Lo llaman los dos scripts anteriores |
| `reglas.py` | Configuración | Reglas R1-R4 del reporte semanal (sequía, lancha, nutrientes, heladas) y sus umbrales en `UMBRALES`. Si se edita, basta con correr `preprocesar.py` |

### Reglas a 10 m (`precision_s2.py`)

**Regla A (vigor y plagas).** Si se cumplen varias, gana la de mayor prioridad: gris > rojo > amarillo > verde.

| Estado | Condición |
|---|---|
| Gris | NDVI < 0,25 (suelo desnudo) |
| Rojo | caída de NDVI ≥ 0,12 respecto a la imagen anterior, o NDVI < 0,35 |
| Amarillo | NDVI 0,35-0,59, o NDRE < 0,35 |
| Verde | NDVI ≥ 0,60 y caída < 0,08 |

**Regla B (humedad, NDMI):** rojo < 0 · amarillo 0-0,20 · verde 0,21-0,45 · azul > 0,45. Sobre suelo desnudo
sale "no aplica".

Los umbrales están al inicio del archivo, en `U_A`, `U_B` y `MAX_NUBE_POLIGONO`.

---

## JSON de resultados (raíz de la carpeta)

| Archivo | Qué contiene |
|---|---|
| `resultado_prototipo_sentinel_2.json` | Mismo formato `input` / `output` que `../nasa-power/resultado_prototipo.json`. **input:** fuente, ubicación y polígono, parámetros (bandas, nubosidad máxima, frecuencia) y capturas evaluadas. **output:** última captura, estado del lote (NDVI, NDRE, NDMI, variación a 15 días, % sano/alerta/crítico), semáforos de vigor y humedad, sectores, capas visuales y serie fenológica |
| `resultado_integrado.json` | Cruce del clima regional (NASA POWER) con la parcela (Sentinel-2): `LANCHA_CONFIRMADA`, `LANCHA_PREVENTIVA`, `RIEGO_CONFIRMADO` o `HUMEDAD_DISCREPANTE`. Solo se genera si existe `../nasa-power/resultado_prototipo.json` |
| `api_sentinel_2.json` | Todos los datos juntos para consumirlos como API |

### Recursos de `api_sentinel_2.json`

| Clave | Contenido |
|---|---|
| `api` | Módulo, versión, fecha de generación, fuente y descripción de cada recurso |
| `parcela` | Nombre, centro, área, periodo analizado y GeoJSON del polígono |
| `criterios` | Colección, nubosidad máxima, ventana, fórmulas y umbrales |
| `ultima_captura` | Diagnóstico de la última imagen limpia: semáforos, mensajes, % de área, sectores, imágenes y `bounds_latlon` |
| `capturas` | Serie de imágenes limpias (~1 cada 15 días) con índices, caída, estados, % de área, sectores e imágenes |
| `pases_satelite` | Todos los pases del periodo: % de nubes, estado y 8 índices (NDVI, NDMI, NDRE, EVI, SAVI, BSI, NDWI, MSI) |
| `semanas` | Resumen semanal: índices, clima, alertas y ruta del reporte `.md` |
| `clima_diario` | T mín/máx/media, HR, lluvia, radiación y nubes de madrugada por día |
| `climatologia_mensual` | Promedios 2011-2025 por mes y clases seco/lluvioso, radiación y noches |
| `alerta_cruzada` | Alerta confirmada y cruces evaluados con NASA POWER |
| `archivos` | Rutas de los entregables |

Las rutas de imágenes en estos JSON son relativas a esta carpeta (`datos_sentinel/...`). Los `bounds_latlon`
van en el formato `[[sur, oeste], [norte, este]]` (EPSG:4326), listos para `L.imageOverlay` o
`folium.ImageOverlay`.

---

## Datos (`datos_sentinel/`)

| Ruta | Qué contiene | Lo genera |
|---|---|---|
| `papas_parcela.geojson` | Polígono de la parcela (1,17 ha) | entrada |
| `datos/parcela.json` | Nombre, centro, área y periodo procesado | `monitoreo.py` |
| `datos/indices_por_fecha.csv` | Una fila por pase del satélite: % de nubes, % válido, estado y todos los índices | `monitoreo.py` / `preprocesar.py` |
| `datos/clima_diario.csv` | Clima diario del periodo (Open-Meteo, ERA5 + pronóstico reciente) | `monitoreo.py` |
| `datos/clima_historico_diario.csv` | Clima diario 2011-2025 (base de la climatología) | `monitoreo.py` (una sola vez) |
| `datos/climatologia_mensual.csv` | Promedios por mes y clases seco/lluvioso, radiación y noches | `preprocesar.py` |
| `datos/historico_semanal.csv` | Una fila por semana: índices, cambios, clima y alertas | `preprocesar.py` |
| `imagenes/tif/S2_AAAAMMDD_TILE.tif` | Recorte con 10 bandas en reflectancia + SCL (máscara de nubes). Se abre en QGIS | `monitoreo.py` |
| `imagenes/png/S2_AAAAMMDD_TILE.png` | Vista rápida: color real, NDVI y NDMI | `monitoreo.py` |
| `imagenes/series_tiempo.png` | Series de índices y clima de todo el periodo | `preprocesar.py` |
| `reportes/INDICE.md` | Resumen de todas las semanas con enlaces | `preprocesar.py` |
| `reportes/semana_AAAA-Snn.md` | Reporte semanal: alertas, índices, clima, tendencia del mes siguiente y reglas | `preprocesar.py` |
| `salida_s2/sentinel2_parcela.json` | Datos completos por fecha (lo lee el Streamlit) | `precision_s2.py` |
| `salida_s2/sentinel2_parcela.csv` | Lo mismo en tabla | `precision_s2.py` |
| `salida_s2/entregable_sentinel2.json` | Formato del equipo: A (capas visuales), B (serie fenológica), C (diagnóstico) | `precision_s2.py` |
| `salida_s2/entregable_sentinel2.xlsx` | Entregable en Excel | anterior |
| `salida_s2/png/` | `vigor_`, `humedad_`, `recorte_ndvi_`, `ndre_`, `recorte_ndmi_` y `rgb_` por fecha (transparentes fuera del polígono) | `precision_s2.py` |
| `salida_s2/tif/s2_AAAAMMDD_indices.tif` | GeoTIFF con NDVI, NDRE, NDMI, estado de vigor y estado de humedad | `precision_s2.py` |

---

## Limitaciones

- **Nubes:** en la Sierra muchas fechas salen nubladas. Por eso los reportes siempre dicen la fecha del último dato
  válido y cuántos días tiene.
- **Tamaño:** 1,17 ha son ~117 píxeles de 10 m. Los bordes mezclan píxeles de las parcelas vecinas.
- **Clima de modelo:** ERA5 tiene celdas de ~9-25 km. En la montaña puede diferir 1-3 °C de la parcela.
- **Umbrales:** en estos 6 meses el NDVI promedio no pasó de 0,48 y el NDMI fue siempre negativo, así que la
  parcela casi nunca sale "verde". Conviene calibrar los umbrales con lo que se observa en campo.
