# Indicadores de remote-sensing (parcela de papa, Toacaso / Sigchos, Ecuador)

Documento temporal para RAG. Cada sección `##` es un fragmento autocontenido: repite el contexto para que se pueda recuperar sola.

- **Cultivo:** papa. **Zona:** Toacaso / Sigchos. **Parcela:** 1,17 ha, 3 588 msnm, centro -0,749029 / -78,773999.
- **Fuente de los valores:** `backend/src/data/resultado_match.json`, generado por `backend/src/match_nasa_sentinel.py` (copia del script de `remote-sensing/`: solo cambian las rutas, la lógica es la misma). El JSON es un reporte de ventanas de 7 días (la semana de cada foto Sentinel-2 y la semana más reciente), no un agregado mensual. `remote-sensing/resultado_match.json` es idéntico. Datos hasta 2026-11-11 (NASA) y 2026-10-27 (Sentinel-2).
- **Dos ventanas de NASA POWER:** la **semana de la última foto limpia** (21-27/10/2026) y la **semana más reciente** (05-11/11/2026). Cada valor dice cuál es.
- **Categorías:** SUELO, VEGETACIÓN (follaje), CLIMA, DERIVADO (alerta o cruce).
- **Límites generales:** NASA POWER es una celda de ~50 km ubicada a 2 501 m (la parcela está a 3 588 m). La humedad de suelo no se corrige por altura. Sentinel-2 tiene un valor por foto limpia (~1 cada 15 días) y la última tiene 19 días de antigüedad al 2026-11-15.

---

## Resumen: qué es suelo y qué no

- **SUELO (todo viene de NASA POWER):** `humedad_raiz_pct`, `humedad_superficial_pct`, `balance_hidrico_7d`, `estado_riego`, alerta `NUTRIENTES`, alerta `SEQUIA`.
- **SUELO (cobertura, Sentinel-2):** `suelo_desnudo` (% de píxeles con NDVI < 0,25).
- **NO es suelo, aunque diga "humedad":** `ndmi_promedio` y `estado_humedad_parcela` miden humedad del follaje, no del suelo.
- **No existen en el JSON:** temperatura del suelo, humedad volumétrica (m³/m³), BSI, NDWI, MSI, EVI, SAVI y mediciones de campo.

---

## SUELO · humedad_raiz_pct

- **Nombre:** humedad de la zona de raíces (`humedad_raiz_pct`, de la variable NASA `GWETROOT`).
- **Categoría:** SUELO. **Fuente:** NASA POWER (MERRA-2).
- **Qué es:** promedio de 7 días de la saturación relativa del suelo en la zona de raíces, en % (0-100). No es humedad volumétrica.
- **Valores:** **75,4 %** en la semana 21-27/10/2026 y **75,4 %** en la semana 05-11/11/2026.
- **Rutas JSON:** `output.cruce_ultima_captura.clima_nasa_alineado.estado_actual_7d.humedad_raiz_pct` y `output.clima_regional_nasa_power.estado_actual_7d.humedad_raiz_pct`.
- **Lectura del valor:** 75,4 % cae en el rango 60-85 % del código = óptimo: suelo húmedo sin llegar a saturación, sin déficit ni exceso. Es una lectura regional (celda de ~50 km), no una medición en la parcela.
- **Significado para la papa:** agua disponible para raíces y estolones. Baja es déficit y necesidad de riego. Muy alta es riesgo de pudrición de tubérculo.
- **Umbrales (`nasa-power/process_2.py`):** < 45 % con lluvia 7 d < 10 mm es `ROJO_SECO` (línea 118). > 85 % con lluvia 7 d > 45 mm es `AZUL_SATURADO` (125). ≤ 60 % es `AMARILLO_VIGILAR` (132). ≤ 85 % es `VERDE_OPTIMO` (139). > 85 % sin lluvia extrema es `AMARILLO_VIGILAR` (146).
- **Limitación:** celda de ~50 km, sin corrección por altura.

## SUELO · humedad_superficial_pct

- **Nombre:** humedad superficial (`humedad_superficial_pct`, de `GWETTOP`).
- **Categoría:** SUELO. **Fuente:** NASA POWER.
- **Qué es:** promedio de 7 días de la saturación relativa de la capa superior del suelo, en %.
- **Valores:** **77,3 %** (21-27/10/2026) y **75,3 %** (05-11/11/2026).
- **Rutas JSON:** `…cruce_ultima_captura.clima_nasa_alineado.estado_actual_7d.humedad_superficial_pct` y `…clima_regional_nasa_power.estado_actual_7d.humedad_superficial_pct`.
- **Lectura del valor:** 77,3 % y 75,3 % superan apenas el 75 % del umbral. Por sí solo eso no alerta: en 21-27/10 la alerta `NUTRIENTES` se activó porque además la lluvia esperada superaba 120 mm. En 05-11/11 no se activó porque la esperada fue 117,1 mm.
- **Significado para la papa:** con lluvia fuerte indica riesgo de lavado de nitrógeno y potasio.
- **Umbral:** `GWETTOP` > 75 % junto con lluvia esperada del mes > 120 mm dispara la alerta `NUTRIENTES` (`process_2.py:227`).

## SUELO · balance_hidrico_7d

- **Nombre:** balance hídrico de 7 días (`balance_hidrico_7d`).
- **Categoría:** SUELO (derivado). **Fuente:** NASA POWER.
- **Qué es:** lluvia acumulada menos `EVPTRNS` acumulada (`process_2.py:81-83`).
- **Valores:** **+119,0 mm** (21-27/10/2026) y **+44,9 mm** (05-11/11/2026).
- **Lectura del valor:** +119,0 mm es una semana muy lluviosa (139,6 mm de lluvia). +44,9 mm es una semana moderada (69,5 mm de lluvia). El signo positivo dice que entró más agua de la que se perdió; el valor exacto no es fiable por las unidades.
- **Significado para la papa:** positivo, entró más agua de la que se perdió.
- **Advertencia de unidades:** `EVPTRNS` viene en MJ/m²/día en el JSON crudo de NASA, pero el código la resta de la lluvia como si fueran mm. Úsalo solo como referencia relativa.
- **Sin umbral propio.**

## SUELO · estado_riego (semáforo)

- **Nombre:** semáforo de riego y humedad del suelo (`semaforos.estado_riego.codigo`).
- **Categoría:** SUELO (derivado de `GWETROOT` y lluvia). **Fuente:** NASA POWER.
- **Valor:** `VERDE_OPTIMO` ("ÓPTIMO - Humedad Ideal") en las 9 fotos del historial (25/05 a 27/10/2026) y en la semana 05-11/11/2026.
- **Valores posibles:** `ROJO_SECO`, `AZUL_SATURADO`, `AMARILLO_VIGILAR`, `VERDE_OPTIMO`. Ver umbrales en `humedad_raiz_pct`.
- **Lectura del valor:** `VERDE_OPTIMO` = humedad de raíces entre 60 y 85 %, no hace falta riego. Que salga igual en las 9 fotos indica que el semáforo casi no cambia con la humedad regional; no prueba que el suelo de la parcela esté bien.
- **Rutas JSON:** `…clima_nasa_alineado.semaforos.estado_riego`, `…clima_regional_nasa_power.semaforos.estado_riego` e `historial_cruces[].nasa.estado_riego`.

## SUELO · serie diaria de humedad (05-11/11/2026)

- **Categoría:** SUELO. **Fuente:** NASA POWER. **Ruta JSON:** `input.nasa_power.ventana_7_dias_evaluada[]`. Es el único dato diario de suelo del archivo.
- **GWETROOT_pct (raíz):** 05/11 76 · 06/11 76 · 07/11 77 · 08/11 76 · 09/11 75 · 10/11 74 · 11/11 74.
- **GWETTOP_pct (superficie):** 05/11 78 · 06/11 78 · 07/11 78 · 08/11 76 · 09/11 73 · 10/11 72 · 11/11 72.
- **PRECTOTCORR_mm (lluvia):** 16,54 · 22,73 · 17,43 · 1,43 · 3,00 · 3,82 · 4,58.
- **EVPTRNS:** 3,19 · 2,41 · 2,49 · 4,28 · 3,95 · 4,11 · 4,15 (unidad real MJ/m²/día).
- **Tendencia:** la superficie baja de 78 a 72 % y la raíz de 76 a 74 %, tras tres días de lluvia fuerte (05-07/11).
- **Falta:** los días 12, 13 y 14/11 vienen con valor de relleno (-999) y se descartan. No hay serie diaria de suelo para las otras semanas.

## SUELO · suelo_desnudo (% del lote)

- **Nombre:** `distribucion_parcela_pct.suelo_desnudo`.
- **Categoría:** SUELO (cobertura). **Fuente:** Sentinel-2 a 10 m.
- **Qué es:** % de píxeles del polígono con NDVI < 0,25 (`precision_s2.py:66`). Indica cuánto suelo queda a la vista.
- **Valor:** **0,0 %** en la foto del 27/10/2026. El 17/09/2026 el lote entero salió `GRIS_SUELO` (NDVI 0,202).
- **Ruta JSON:** `output.parcela_sentinel2.estado_actual_lote.distribucion_parcela_pct.suelo_desnudo`.
- **Lectura del valor:** 0,0 % significa que todo el lote tiene cobertura vegetal (NDVI ≥ 0,25). No dice nada sobre la humedad del suelo bajo esas plantas.
- **Efecto:** con vigor gris se suspenden los cruces de lancha, riego, heladas y nutrientes (`match_nasa_sentinel.py:156`).

## ALERTA (suelo) · NUTRIENTES

- **Nombre:** alerta preventiva de lavado de nutrientes.
- **Categoría:** DERIVADO de suelo y lluvia. **Fuente:** NASA POWER.
- **Valor:** **MEDIO**, activa en la ventana 21-27/10/2026. No aparece en la semana 05-11/11/2026.
- **Condición:** lluvia esperada del mes > 120 mm **y** `GWETTOP` > 75 % (`process_2.py:227`).
- **Mensaje:** lluvias fuertes pueden lavar nitrógeno y potasio. Considerar fraccionar la fertilización.
- **Lectura del valor:** MEDIO = hay condiciones para que se pierdan nutrientes, no una pérdida medida. No hay análisis de suelo en el repo.

## ALERTA (suelo) · SEQUIA

- **Nombre:** alerta preventiva de sequía prolongada.
- **Categoría:** DERIVADO. **Fuente:** NASA POWER.
- **Valor:** **no aparece** en ninguna ventana.
- **Condición:** `GWETROOT` < 55 % **y** lluvia esperada < evaporación esperada (`process_2.py:209`). Nivel ALTO si `GWETROOT` < 45 %, si no MEDIO.
- **Lectura del valor:** que no aparezca significa que no se proyecta déficit de agua para el mes siguiente. Con humedad de raíces de ~75 % ni siquiera se cumple la primera condición (< 55 %).
- **Limitación:** la comparación mezcla mm de lluvia con MJ/m²/día de evapotranspiración.

---

## VEGETACIÓN · ndvi_promedio

- **Nombre:** NDVI promedio del lote.
- **Categoría:** VEGETACIÓN. **Fuente:** Sentinel-2 (B08 y B04).
- **Valor:** **0,4482** el 27/10/2026. Serie: 25/05 0,412 · 29/06 0,301 · 14/07 0,297 · 29/07 0,304 · 10/08 0,269 · 23/08 0,256 · 17/09 0,202 · 09/10 0,304 · 27/10 0,448.
- **Qué es:** vigor y biomasa verde de la planta. No es suelo.
- **Ruta JSON:** `output.parcela_sentinel2.estado_actual_lote.ndvi_promedio` y `serie_fenologica[].ndvi`.
- **Umbrales regla A (`precision_s2.py:66`):** < 0,25 gris (suelo desnudo); < 0,35 rojo; 0,35-0,59 amarillo; ≥ 0,60 verde.
- **Lectura del valor:** 0,4482 cae en amarillo: cobertura y vigor moderados, todavía lejos del verde (≥ 0,60). Viene de 0,304 el 09/10, así que el cultivo se está recuperando. El README de sentinel_2 advierte que en 6 meses el NDVI promedio nunca superó 0,48.

## VEGETACIÓN · ndre_promedio

- **Nombre:** NDRE promedio. **Fuente:** Sentinel-2 (B08 y B05).
- **Valor:** **0,2495** el 27/10/2026.
- **Qué es:** clorofila y nitrógeno de la planta (borde rojo). No es suelo.
- **Umbral:** NDRE < 0,35 coloca el vigor en amarillo.
- **Lectura del valor:** 0,2495 está por debajo de 0,35: poca clorofila, lo que el código interpreta como posible falta de nitrógeno. Sube desde 0,1626 el 09/10.
- **Ruta JSON:** `…estado_actual_lote.ndre_promedio` y `serie_fenologica[].ndre`.

## VEGETACIÓN · ndmi_promedio (humedad del follaje)

- **Nombre:** NDMI promedio. **Fuente:** Sentinel-2 (B08 y B11).
- **Valor:** **-0,1811** el 27/10/2026 (sube desde -0,3193 el 09/10).
- **Qué es:** contenido de agua de las **hojas**. **No mide humedad del suelo.** Con suelo expuesto sale negativo casi siempre.
- **Umbrales regla B (`precision_s2.py:77`):** < 0 rojo; 0-0,20 amarillo; 0,21-0,45 verde; > 0,45 azul. Con NDVI < 0,25 la regla no aplica.
- **Lectura del valor:** -0,18 es negativo, así que cae en rojo: el follaje tiene poca agua. Pero el propio README dice que en estos 6 meses el NDMI fue siempre negativo, por lo que el rojo no distingue una semana seca de una húmeda. Hay que contrastarlo en campo.
- **Ruta JSON:** `…estado_actual_lote.ndmi_promedio` y `serie_fenologica[].ndmi`.

## VEGETACIÓN · variacion_ndvi_15d y caída de NDVI

- **Nombre:** variación del NDVI frente a la foto anterior (`variacion_ndvi_15d`).
- **Valor:** **+0,1444** (27/10 frente al 09/10, 18 días antes). Positivo significa que el NDVI **subió**.
- **Lectura del valor:** +0,14 es una mejora de vigor en 18 días, no una pérdida.
- **Atención al signo:** en los cruces el campo `caida_ndvi_lote` usa la convención contraria (positivo = bajó). Allí vale **-0,1444**, es decir, el NDVI subió.
- **Umbrales:** caída ≥ 0,12 es rojo en la regla A. Caída ≥ 0,08 cuenta como "pierde vigor" en el cruce (`match_nasa_sentinel.py:44`).
- **Caída por sector (27/10):** norte -0,1538 · sur -0,1416 · este -0,1422 · oeste -0,1237.

## VEGETACIÓN · estado_vigor (semáforo)

- **Valor:** `AMARILLO_NUTRICION` ("ALERTA - Nutrición") el 27/10/2026.
- **Mensaje:** baja concentración de clorofila. Posible falta de nitrógeno o crecimiento lento.
- **Lectura del valor:** amarillo = NDVI entre 0,35 y 0,59 **o** NDRE < 0,35. Aquí se cumplen las dos. Es un indicio, no un diagnóstico de falta de nitrógeno.
- **Valores posibles:** `GRIS_SUELO`, `ROJO_ESTRES_SEVERO`, `AMARILLO_NUTRICION`, `VERDE_VIGOROSO`.
- **Historial 25/05→27/10:** amarillo, rojo, rojo, rojo, rojo, rojo, gris, rojo, amarillo. Nunca verde.
- **Ruta JSON:** `output.parcela_sentinel2.semaforos.estado_vigor`.

## VEGETACIÓN · estado_humedad_parcela (semáforo de follaje)

- **Valor:** `ROJO_ESTRES_HIDRICO` ("CRÍTICO - Estrés hídrico") el 27/10/2026.
- **Lectura del valor:** rojo = NDMI < 0. Se repite casi siempre, así que informa poco sobre un cambio reciente.
- **Qué es:** clasificación del NDMI del follaje (regla B). **No es humedad del suelo**, aunque el mensaje diga "activa riego".
- **Historial:** rojo en 8 de 9 fotos. El 17/09 fue `GRIS_NO_APLICA` (suelo desnudo).
- **Ruta JSON:** `output.parcela_sentinel2.semaforos.estado_humedad_parcela`.

## VEGETACIÓN · distribucion_parcela_pct (salud del lote)

- **Valores (27/10/2026):** sano **16,7 %** · alerta **55,8 %** · crítico **27,5 %** · suelo_desnudo 0,0 % · sin_dato 0,0 %.
- **Qué es:** % de píxeles de 10 m del lote por estado de vigor. **sano** = verde (NDVI ≥ 0,60), **alerta** = amarillo, **crítico** = rojo.
- **Lectura del valor:** solo 16,7 % del lote está sano; 83,3 % está en alerta o crítico.
- **Ruta JSON:** `…estado_actual_lote.distribucion_parcela_pct`.

## VEGETACIÓN · sectores (norte, sur, este, oeste)

- **Ruta JSON:** `output.parcela_sentinel2.sectores.{norte,sur,este,oeste}`. Foto del 27/10/2026.
- **Cómo leerlos:** `pct_rojo` = % de píxeles del sector en rojo (estrés severo). `pct_estres` = amarillo + rojo. El sector pequeño (oeste, 12 píxeles) pesa poco en el promedio del lote.
- **Norte:** 44 píxeles, NDVI 0,4094, 11,4 % rojo, 100 % en estrés.
- **Sur:** 48 píxeles, NDVI 0,5088, 39,6 % rojo, 62,5 % en estrés.
- **Este:** 16 píxeles, NDVI 0,4486, 6,2 % rojo, 87,5 % en estrés.
- **Oeste:** 12 píxeles, NDVI 0,3477, 66,7 % rojo, 100 % en estrés. **Es el sector más afectado.**

## VEGETACIÓN · cambio_ndmi

- **Valor:** **+0,1382** entre el 09/10 y el 27/10/2026 (el follaje ganó agua).
- **Lectura del valor:** positivo = el follaje ganó agua; el umbral de pérdida (-0,03) no se cumple, por eso no hay `ESTRES_CALOR_CONFIRMADO` ni `RIEGO_CONFIRMADO`.
- **Uso:** una caída de NDMI ≥ 0,03 se toma como pérdida de agua del follaje (`match_nasa_sentinel.py:45`).
- **Ruta JSON:** `cruces_evaluados[].evidencia.sentinel2.cambio_ndmi`.

---

## CLIMA · lluvia_7d

- **Nombre:** lluvia acumulada de 7 días. **Fuente:** NASA POWER (`PRECTOTCORR`).
- **Valores:** **139,6 mm** (21-27/10/2026) y **69,5 mm** (05-11/11/2026).
- **Lectura del valor:** 139,6 mm es una semana muy lluviosa y 69,5 mm es moderada-alta. Ambas superan los 45 mm de `AZUL_SATURADO`, pero ese estado exige además `GWETROOT` > 85 %, que no se cumple (75,4 %).
- **Uso:** entra en los umbrales de `ROJO_SECO` (< 10 mm) y `AZUL_SATURADO` (> 45 mm).
- **Ruta JSON:** `…estado_actual_7d.lluvia_7d`.

## CLIMA · humedad_relativa_pct

- **Nombre:** humedad relativa del aire (`RH2M`). **No es humedad de suelo.**
- **Valores:** **87,7 %** (21-27/10/2026) y **85,9 %** (05-11/11/2026).
- **Lectura del valor:** 87,7 % y 85,9 % superan el 82 % del umbral: aire muy húmedo, favorable a hongos como la lancha.
- **Uso:** condición de la alerta `PLAGAS_LANCHA` (humedad semanal > 82 %, `process_2.py:196`).

## CLIMA · temperaturas (con corrección por altura)

- **Fuente:** NASA POWER (`T2M_MIN`, `T2M_MAX`) corregida con el sesgo medido contra Open-Meteo en 1 690 días (T media -7,03 °C, T mín -6,47 °C, T máx -7,81 °C).
- **Semana 21-27/10/2026:** T mín NASA 10,3 °C → **parcela 3,9 °C**; T máx NASA 21,4 °C → **parcela 13,6 °C**.
- **Semana 05-11/11/2026 (sin corregir):** T mín 8,6 °C; T máx 20,8 °C.
- **Serie diaria 05-11/11 (sin corregir):** tmin 10,9 · 12,1 · 11,2 · 9,1 · 8,8 · 8,6 · 10,1; tmax 19,8 · 19,2 · 19,5 · 20,7 · 20,4 · 20,6 · 20,8. Ruta: `output.clima_regional_nasa_power.serie_7d[]`.
- **Lectura del valor:** T mín de 3,9 °C en la parcela está entre 3 y 6 °C: madrugadas frías cerca de helada, pero sin helada (≤ 3 °C). T máx de 13,6 °C es fresca y no hay estrés por calor (umbral 22 °C).
- **Es temperatura del aire.** No hay temperatura del suelo.

## CLIMA · estado_helada (semáforo)

- **Valor:** `AMARILLO` ("PRECAUCIÓN - Madrugadas Frías") en 21-27/10/2026 con la temperatura corregida (3,9 °C). Sin corregir daría `VERDE`. En 05-11/11/2026 es `VERDE`.
- **Umbrales (`process_2.py:95,102`):** T mín ≤ 3 °C es `ROJO`; ≤ 6 °C es `AMARILLO`; si no, `VERDE`.
- **Historial:** `ROJO` el 29/07 y el 10/08; `AMARILLO` en el resto de las 9 fotos.

## CLIMA · estado_estres_calor (semáforo)

- **Valor:** `VERDE` ("NORMAL - Temperatura Diurna Ideal") en todas las ventanas.
- **Umbral:** `ROJO` si hay 3 o más días seguidos con T máx > 22 °C (`process_2.py:157-160`).

## CLIMA · proyección a 30 días

- **Mes proyectado:** diciembre (semana 05-11/11/2026).
- **Valores:** lluvia esperada **117,1 mm**; evaporación esperada **17,0** (unidad no comparable con mm); T mín esperada **10,5 °C** (sin corregir por altura).
- **Base:** promedios diarios de diciembre de 2021 a 2025.
- **Lectura del valor:** 117,1 mm es un mes lluvioso, justo debajo del umbral de 120 mm de la alerta `NUTRIENTES`. La T mín de 10,5 °C es de la celda NASA; en la parcela sería unos 6,5 °C más baja.
- **Ruta JSON:** `output.proyeccion_vigente_nasa` y `output.clima_regional_nasa_power.proyeccion_30d`.

---

## DERIVADO · PLAGAS_LANCHA

- **Nombre:** alerta preventiva de tizón tardío (lancha).
- **Valor:** **ALTO** en 21-27/10/2026 y en 05-11/11/2026.
- **Condición (`process_2.py:196-200`):** humedad relativa semanal > 82 % y (lluvia esperada > 90 mm o humedad histórica > 80 %) y T media histórica entre 10 y 18 °C.
- **Lectura del valor:** ALTO = el clima del mes siguiente favorece la lancha; es un riesgo, no una infección observada. Sentinel-2 no vio caída de vigor, por eso el cruce quedó `LANCHA_PREVENTIVA`.
- **Es clima, no suelo.**

## DERIVADO · HELADAS (alerta futura)

- **Valor:** **MEDIO** en la ventana 21-27/10/2026. No aparece en 05-11/11/2026.
- **Condición (`process_2.py:218`):** T mín semanal < 5,5 °C y T mín esperada < 4,5 °C. ALTO si la T mín semanal ≤ 3 °C. Se evalúa con temperatura corregida.

## DERIVADO · cruces NASA + Sentinel-2 (última foto, 27/10/2026)

- **`NUTRICION_PROBABLE`:** nivel MEDIO, **confirmada**. Por la alerta `NUTRIENTES` (suelo) más vigor amarillo (follaje). Mensaje: evaluar fertilización foliar fraccionada.
- **`LANCHA_PREVENTIVA`:** nivel ALTO, no confirmada. Clima favorable a la lancha, pero el satélite no ve caída de vigor. Revisar el sector oeste.
- **`HUMEDAD_DISCREPANTE`:** nivel MEDIO, no confirmada. NASA da `VERDE_OPTIMO` (suelo húmedo, `humedad_raiz_pct` 75,4 %, lluvia 139,6 mm) pero el NDMI del follaje está en rojo. Pide revisar en campo (estrés local, drenaje o poca cobertura).
- **Ruta JSON:** `output.cruces_evaluados[]`. La alerta confirmada está en `output.alerta_cruzada_confirmada`.
- **Historial:** `HUMEDAD_DISCREPANTE` aparece en 8 de las 9 fotos (todas menos la del 17/09), porque el riego siempre es `VERDE_OPTIMO` y el NDMI siempre rojo. Otros cruces del historial: `HELADA_SIN_DANO` (29/07, 10/08) y `LANCHA_PREVENTIVA` (09/10).

---

## SERIE · las 9 fotos limpias de Sentinel-2 (vigor y humedad del follaje)

- **Zona:** parcela de papa, Toacaso / Sigchos, 3 588 msnm. **Fuente:** Sentinel-2 L2A, `output.parcela_sentinel2.serie_fenologica[]`. Cada foto cubre 120 píxeles de 10 m, con 0 % de nubosidad en el polígono.
- **Columnas:** fecha · NDVI · NDRE · NDMI · estado de vigor · estado de humedad del follaje (el NDMI es del follaje, no del suelo).

| Fecha | NDVI | NDRE | NDMI | Vigor | Humedad del follaje |
|---|---|---|---|---|---|
| 25/05 | 0,4121 | 0,2370 | -0,0926 | AMARILLO_NUTRICION | ROJO_ESTRES_HIDRICO |
| 29/06 | 0,3011 | 0,1911 | -0,2211 | ROJO_ESTRES_SEVERO | ROJO_ESTRES_HIDRICO |
| 14/07 | 0,2969 | 0,1924 | -0,2540 | ROJO_ESTRES_SEVERO | ROJO_ESTRES_HIDRICO |
| 29/07 | 0,3037 | 0,1950 | -0,2500 | ROJO_ESTRES_SEVERO | ROJO_ESTRES_HIDRICO |
| 10/08 | 0,2691 | 0,1742 | -0,1864 | ROJO_ESTRES_SEVERO | ROJO_ESTRES_HIDRICO |
| 23/08 | 0,2562 | 0,1608 | -0,2689 | ROJO_ESTRES_SEVERO | ROJO_ESTRES_HIDRICO |
| 17/09 | 0,2020 | 0,1314 | -0,3152 | GRIS_SUELO | GRIS_NO_APLICA |
| 09/10 | 0,3039 | 0,1626 | -0,3193 | ROJO_ESTRES_SEVERO | ROJO_ESTRES_HIDRICO |
| 27/10 | 0,4482 | 0,2495 | -0,1811 | AMARILLO_NUTRICION | ROJO_ESTRES_HIDRICO |

- **Lectura del valor:** el NDVI cae de 0,412 (25/05) a 0,202 (17/09) y se recupera a 0,448 (27/10). Ninguna foto llega al verde (NDVI ≥ 0,60). El NDRE siempre está por debajo de 0,35 y el NDMI siempre es negativo.
## SERIE · historial de cruces NASA + Sentinel-2, fotos de mayo a agosto

- **Zona:** parcela de papa, Toacaso / Sigchos. **Fuente:** `output.historial_cruces[]`. Cada fila une la foto con la semana NASA que termina ese día (T mín corregida a la parcela). En las 9 fotos el riego es `VERDE_OPTIMO` y el calor `VERDE`; solo cambia la helada.
- **Caída NDVI** con la convención del cruce: positivo = el NDVI bajó; negativo = subió.

| Foto | Ventana NASA | Helada | Alertas NASA | Vigor / humedad | Caída NDVI | Cruces |
|---|---|---|---|---|---|---|
| 25/05 | 19-25/05 | AMARILLO | NUTRIENTES, HELADAS | amarillo / rojo | — | NUTRICION_PROBABLE (confirmada), HUMEDAD_DISCREPANTE |
| 29/06 | 23-29/06 | AMARILLO | HELADAS | rojo / rojo | 0,111 | HUMEDAD_DISCREPANTE |
| 14/07 | 08-14/07 | AMARILLO | HELADAS | rojo / rojo | 0,0042 | HUMEDAD_DISCREPANTE |
| 29/07 | 23-29/07 | ROJO | HELADAS | rojo / rojo | -0,0067 | HUMEDAD_DISCREPANTE, HELADA_SIN_DANO |
| 10/08 | 04-10/08 | ROJO | HELADAS | rojo / rojo | 0,0345 | HUMEDAD_DISCREPANTE, HELADA_SIN_DANO |

## SERIE · historial de cruces NASA + Sentinel-2, fotos de agosto a octubre

- **Zona:** parcela de papa, Toacaso / Sigchos. **Fuente:** `output.historial_cruces[]`. Mismas columnas que la sección de mayo a agosto: riego `VERDE_OPTIMO` y calor `VERDE` en todas las fotos.

| Foto | Ventana NASA | Helada | Alertas NASA | Vigor / humedad | Caída NDVI | Cruces |
|---|---|---|---|---|---|---|
| 23/08 | 17-23/08 | AMARILLO | HELADAS | rojo / rojo | 0,0129 | HUMEDAD_DISCREPANTE |
| 17/09 | 11-17/09 | AMARILLO | HELADAS | gris / no aplica | 0,0542 | ninguno |
| 09/10 | 03-09/10 | AMARILLO | PLAGAS_LANCHA, HELADAS | rojo / rojo | -0,1019 | LANCHA_PREVENTIVA, HUMEDAD_DISCREPANTE |
| 27/10 | 21-27/10 | AMARILLO | PLAGAS_LANCHA, NUTRIENTES, HELADAS | amarillo / rojo | -0,1444 | NUTRICION_PROBABLE (confirmada), LANCHA_PREVENTIVA, HUMEDAD_DISCREPANTE |

- **Lectura del valor (las 9 fotos):** la alerta `HELADAS` aparece en las 9 ventanas; `PLAGAS_LANCHA` en 2 (09/10 y 27/10); `NUTRIENTES` en 2 (25/05 y 27/10). Solo las dos fotos con `NUTRICION_PROBABLE` quedaron como alerta confirmada.

## CLIMA · semana 05-11/11/2026 día por día (temperatura media y humedad relativa del aire)

- **Fuente:** NASA POWER, `input.nasa_power.ventana_7_dias_evaluada[]` (sin corregir por altura; celda a 2 501 m).
- **T media (T2M, °C):** 05/11 14,85 · 06/11 14,97 · 07/11 14,66 · 08/11 14,70 · 09/11 14,22 · 10/11 14,59 · 11/11 15,24.
- **Humedad relativa (RH2M, %):** 85,6 · 88,1 · 88,8 · 83,3 · 85,5 · 84,6 · 85,4. Los 7 días superan el 82 % del umbral de lancha.
- **Lluvia, T mín, T máx, EVPTRNS y humedad de suelo:** ver las secciones SUELO y CLIMA de más arriba.

## CLIMA · climatología base usada para la proyección a 30 días (diciembre)

- **Fuente:** `input.nasa_power.muestra_climatologica_mes_siguiente`. **Base:** 155 días de diciembre de 2021 a 2025 (5 años), NASA POWER sin corregir por altura.
- **Promedios diarios:** lluvia 3,9 mm · evaporación 0,57 (unidad no comparable con mm) · humedad relativa 83,9 % · T media 14,6 °C · T mín 10,5 °C.
- **Lectura del valor:** 3,9 mm/día × 30 = 117,1 mm esperados en diciembre. La humedad histórica de 83,9 % supera el 80 % que usa la condición de `PLAGAS_LANCHA`.
- **Histórico NASA cargado:** 2021-11-14 a 2026-11-11 (1 824 días válidos).

## CLIMA · alertas preventivas: textos que ve el agricultor

- **Fuente:** `…alertas_preventivas[]` (ventana 21-27/10/2026) y `output.proyeccion_vigente_nasa.alertas_preventivas` (semana 05-11/11/2026, solo `PLAGAS_LANCHA`).
- **PLAGAS_LANCHA, ALTO:** "Riesgo alto de Lancha (tizón tardío) para el próximo mes por alta humedad y lluvias esperadas. Revisa el envés de las hojas bajas y prepara control preventivo."
- **NUTRIENTES, MEDIO:** "Lluvias fuertes esperadas el próximo mes pueden lavar el nitrógeno y potasio del suelo. Considera fraccionar la fertilización."
- **HELADAS, MEDIO:** "Se esperan noches despejadas y frías en las próximas 3 semanas. Alta probabilidad de heladas en zonas bajas de la parcela."
- **Lectura del valor:** son avisos de riesgo climático, no daño observado. Los textos hablan de "control preventivo" y "fertilización" como consejo del código; el RAG no debe repetirlos como dosis ni producto.

## SEMÁFOROS · textos de cada estado (27/10/2026)

- **estado_helada `AMARILLO` (temperatura corregida):** "PRECAUCIÓN - Madrugadas Frías". Sin corregir: `VERDE`, "NORMAL - Sin Heladas" ("Temperaturas nocturnas seguras para el follaje de la papa").
- **estado_riego `VERDE_OPTIMO`:** "ÓPTIMO - Humedad Ideal". Humedad adecuada en zona de raíces; no se requiere riego adicional.
- **estado_estres_calor `VERDE`:** "NORMAL - Temperatura Diurna Ideal". Días frescos ideales para el engrosamiento del tubérculo.
- **estado_vigor `AMARILLO_NUTRICION`:** "ALERTA - Nutrición". Baja clorofila; posible falta de nitrógeno o crecimiento lento.
- **estado_humedad_parcela `ROJO_ESTRES_HIDRICO`:** "CRÍTICO - Estrés hídrico". Mide el NDMI del follaje, no el suelo.

## MÉTODO · alineación NASA POWER con la parcela y corrección de temperatura

- **Altitudes:** la celda NASA está a 2 501 m y la parcela a 3 588 m (diferencia de 1 087 m). La corrección teórica por altura sería -7,06 °C.
- **Corrección aplicada:** sesgo medio NASA menos Open-Meteo en 1 690 días comunes: T2M -7,03 °C, T2M_MIN -6,47 °C, T2M_MAX -7,81 °C.
- **Qué se corrige:** solo se usa en `estado_helada`, `estado_estres_calor` y la alerta `HELADAS`. La lluvia, la humedad relativa y la humedad de suelo NO se corrigen por altura.
- **Criterio de fecha:** la ventana NASA de 7 días termina el día de cada foto Sentinel-2. Último dato NASA válido: 2026-11-11, 15 días después de la última foto limpia (27/10).
- **Limitación:** no hay estación meteorológica en la parcela; la temperatura de la parcela es una estimación.

## MÉTODO · parámetros de Sentinel-2

- **Producto:** Sentinel-2 L2A (reflectancia de superficie) vía Earth Search / AWS, resolución 10 m, polígono de 1,17 ha.
- **Bandas:** NDVI = B08 y B04; NDRE = B08 y B05; NDMI = B08 y B11; máscara de nubes con SCL.
- **Filtro:** nubosidad del polígono ≤ 20 %, una foto cada ~15 días. Rango revisado: 2026-05-15 a 2026-11-15. Se descargaron 23 recortes, 17 quedaron limpios y se seleccionaron 9.
- **Escenas de las 9 fotos (tile 17MQV):** 25/05 S2B, 29/06 S2C, 14/07 S2B, 29/07 S2C, 10/08 S2A, 23/08 S2B, 17/09 S2C, 09/10 S2A, 27/10 S2C.
- **Capas visuales:** recortes PNG de NDVI y NDMI del 27/10/2026 (`output.parcela_sentinel2.capas_visuales`).

## CRUCES · cómo se decide cada código (NASA dice el riesgo, Sentinel-2 confirma el daño)

- **Idea del match:** NASA POWER dice si hay RIESGO (celda de ~50 km). Sentinel-2 confirma si ya hay DAÑO visible en la parcela. Si coinciden, la alerta es *confirmada*.
- **Lancha:** alerta `PLAGAS_LANCHA` + caída de NDVI ≥ 0,08 (lote o sector) = `LANCHA_CONFIRMADA`; sin caída = `LANCHA_PREVENTIVA`.
- **Riego:** `ROJO_SECO` o alerta `SEQUIA` + humedad roja o NDMI cae ≥ 0,03 = `RIEGO_CONFIRMADO`; sin estrés = `RIEGO_PREVENTIVO`.
- **Exceso de agua:** `AZUL_SATURADO` + humedad azul o caída de vigor = `EXCESO_AGUA_CONFIRMADO`; sin daño = `EXCESO_AGUA_PREVENTIVO`.
- **Helada:** helada `ROJO` (T mín corregida ≤ 3 °C) + caída de vigor = `DANO_HELADA_CONFIRMADO`; sin caída = `HELADA_SIN_DANO`.
- **Calor:** calor `ROJO` (corregido) + NDMI cae ≥ 0,03 = `ESTRES_CALOR_CONFIRMADO`.
- **Nutrición:** sin helada roja, calor ni sequía, o alerta `NUTRIENTES`, + vigor amarillo (NDVI 0,35-0,59 o NDRE < 0,35) = `NUTRICION_PROBABLE`. Con helada, calor o sequía y vigor amarillo: `VIGOR_BAJO_POR_CLIMA` (no confirmada).
- **Humedad discrepante:** riego `VERDE_OPTIMO` o `AZUL_SATURADO` con humedad del follaje roja o amarilla = `HUMEDAD_DISCREPANTE` (no confirmada: revisar en campo).
- **Suelo desnudo:** con vigor gris (siembra o cosecha) no se evalúan lancha, riego, heladas ni nutrientes.
- **Altura:** solo heladas y calor usan la temperatura corregida; lancha, riego, sequía y nutrientes usan el modelo original (umbrales calibrados con NASA sin corregir).

## Cobertura y calidad de los datos

- **NASA POWER:** último día válido 2026-11-11. Los días 12, 13 y 14/11 vienen con valor de relleno.
- **Sentinel-2:** última foto limpia 2026-10-27 (19 días antes del 2026-11-15). El pase del 06/11 salió `dudosa (bruma)` (NDMI +0,30 y BSI -0,17 no son creíbles) y no se usa. Los pases del 29/10, 01/11, 08/11 y 11/11 están nublados.
- **No hay:** serie diaria de suelo para semanas anteriores, temperatura del suelo, humedad volumétrica, BSI/NDWI/MSI en el JSON del match, ni mediciones de campo.
