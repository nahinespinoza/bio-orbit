# remote-sensing

| Carpeta / archivo | Qué es |
|---|---|
| `nasa-power/` | Clima regional (NASA POWER): heladas, riego, calor y proyección a 30 días. `process_2.py` → `resultado_prototipo.json` |
| `sentinel_2/` | Parcela a 10 m (Sentinel-2): vigor, clorofila y humedad del follaje. `preprocesar.py` → `resultado_prototipo_sentinel_2.json` (ver `sentinel_2/README.md`) |
| `match_nasa_sentinel.py` | **Match final** de los dos módulos. Solo lee sus datos, no los modifica |
| `resultado_match.json` | Resultado del match |
| `match_html.py` → `resultado_match.html` | Vista HTML del match: alerta confirmada, cruces, semáforos, indicadores, sectores, imágenes e historial. Se genera solo al correr el match, o aparte con `python match_html.py`. Ábrelo en el navegador desde esta carpeta |

```
conda activate ecofolia-frontend
cd remote-sensing
python sentinel_2/preprocesar.py     # 1. datos Sentinel-2 (sin internet)
python match_nasa_sentinel.py        # 2. match NASA POWER + Sentinel-2
python sentinel_2/preprocesar.py     # 3. (opcional) mete el match en api_sentinel_2.json
```

La idea del match: **NASA POWER dice si hay RIESGO** (clima de una celda de ~50 km) y **Sentinel-2 confirma si
ya hay DAÑO** visible en la parcela. Si los dos coinciden, la alerta es *confirmada*.

## Correcciones para que los dos datos sean comparables

1. **Misma fecha.** El modelo de NASA (`procesar_prototipo` de `process_2.py`, reutilizado sin copiarlo) se corre
   con la ventana de 7 días que termina **el día de cada foto** Sentinel-2. Así cada foto se compara con el
   clima de esa misma semana, no con el de la semana actual.
2. **Misma altura.** NASA ubica la parcela a **2 501 m** (altura media de su celda), pero la parcela está a
   **3 588 m**. Por eso las temperaturas de NASA salen ~7 °C más altas que en la parcela y nunca marcarían helada.
   Se corrigen con el sesgo medido contra Open-Meteo en 1 690 días comunes: T media −7,03 °C, T mín −6,47 °C,
   T máx −7,81 °C. Coincide con el gradiente teórico (6,5 °C/km × 1 087 m = −7,07 °C), que se usa si faltan datos.
   La corrección solo se aplica a **heladas y calor**. Lancha, riego, sequía y nutrientes usan el modelo original,
   porque sus umbrales se calibraron con los datos de NASA sin corregir.

## Cruces

| Código | NASA POWER | Sentinel-2 | ¿Confirmada? |
|---|---|---|---|
| `LANCHA_CONFIRMADA` | alerta `PLAGAS_LANCHA` | caída de NDVI ≥ 0,08 en el lote o en un sector | sí |
| `LANCHA_PREVENTIVA` | alerta `PLAGAS_LANCHA` | sin caída de vigor | no |
| `RIEGO_CONFIRMADO` | `ROJO_SECO` o alerta `SEQUIA` | humedad roja o NDMI cae ≥ 0,03 | sí |
| `RIEGO_PREVENTIVO` | `ROJO_SECO` o alerta `SEQUIA` | follaje sin estrés | no |
| `HUMEDAD_DISCREPANTE` | riego `VERDE_OPTIMO` o `AZUL_SATURADO` | humedad roja o amarilla | no (revisar en campo) |
| `EXCESO_AGUA_CONFIRMADO` | `AZUL_SATURADO` | humedad azul o caída de vigor | sí |
| `EXCESO_AGUA_PREVENTIVO` | `AZUL_SATURADO` | sin daño visible | no |
| `DANO_HELADA_CONFIRMADO` | helada `ROJO` (T mín corregida ≤ 3 °C) | caída de vigor | sí |
| `HELADA_SIN_DANO` | helada `ROJO` | sin caída de vigor | no |
| `ESTRES_CALOR_CONFIRMADO` | calor `ROJO` (corregido) | NDMI cae ≥ 0,03 | sí |
| `NUTRICION_PROBABLE` | sin helada roja, calor ni sequía, o alerta `NUTRIENTES` (lavado) | vigor amarillo (NDVI 0,35-0,59 o NDRE < 0,35) | sí |
| `VIGOR_BAJO_POR_CLIMA` | helada, calor o sequía | vigor amarillo | no |

Con suelo desnudo (vigor gris: siembra o cosecha) no se evalúan lancha, riego, heladas ni nutrientes.

## `resultado_match.json`

- `input.nasa_power` / `input.sentinel2`: los `input` de cada módulo.
- `input.alineacion`: altitudes, corrección aplicada, método, días comparados y desfase entre la última foto y el
  último dato de NASA.
- `output.cruce_ultima_captura`: clima NASA alineado a la última foto y los cruces, con la evidencia de cada fuente.
- `output.alerta_cruzada_confirmada` y `output.cruces_evaluados`: resumen para el frontend.
- `output.proyeccion_vigente_nasa`: proyección a 30 días de la semana más reciente.
- `output.historial_cruces`: los cruces de cada foto de los 6 meses.
