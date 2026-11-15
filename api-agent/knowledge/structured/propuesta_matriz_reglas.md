# Propuesta: matriz de reglas de advertencias (paso 2)

> **Superada por el MVP** (`app/engine/advisories.py`, ver README): esta matriz de 11 reglas parte de agregados mensuales de 5 años que NO salen del remote-sensing (su JSON es un reporte de ventanas de 7 días). El MVP usa solo las alertas del JSON y 5 reglas. Se conserva como análisis de qué datos hay y cuáles faltan.

Estado original: **propuesta, sin código**. No toca el motor, el esquema SQL, `ingestion/` ni `app/`. Depende de `propuesta_campos_tipados.json` (paso 1). Hay una versión en JSON (`propuesta_matriz_reglas.json`) con las mismas reglas, plantillas y casos.

## 1. Cómo funciona

1. El **motor** (reglas deterministas) decide si existe una advertencia: cruza un campo tipado de la ficha con un indicador de la parcela.
2. El **LLM** solo redacta la advertencia ya decidida, con la evidencia que le pasa el motor.
3. Un **validador** comprueba el texto: todo número está en la evidencia, nombra al cultivo candidato, máximo 2 advertencias, sin dosis ni productos. Si falla, se usa la **plantilla fija** de la regla (las de abajo).
4. Lenguaje de riesgo, trato de usted, frases cortas, siempre se remite a un técnico o al INIAP. Campo sin tipar, de otra región o de fiabilidad baja: no hay advertencia (a lo sumo R8, "no hay dato confiable").

## 2. Datos de la parcela que usan las reglas (3588 msnm)

Solo los agregados del encargo. `—` = no está en el resumen y se trata como *sin dato* (nunca como 0). Lluvia y HR vienen como rango del grupo de meses, no por mes.

| Mes | Noches ≤3 °C (temp. corregida) | Lluvia (mm/mes) | Días con HR>82 % | T máx diaria máxima (recálculo propio) |
|---|---|---|---|---|
| enero | 3,8 | 121-216 | 70-95 % | 15,8 °C |
| febrero | — | 121-216 | 70-95 % | 15,1 °C |
| marzo | — | 121-216 | 70-95 % | 15,8 °C |
| abril | 1,2 | 121-216 | 70-95 % | 16 °C |
| mayo | — | — | — | 15,5 °C |
| junio | 10,4 | — | — | 15,5 °C |
| julio | 16,4 | 43-62 | 5-13 % | 14,9 °C |
| agosto | 17 | 43-62 | 5-13 % | 16 °C |
| septiembre | 12,8 | 43-62 | 5-13 % | 16,3 °C |
| octubre | 4,4 | 121-216 | — | 16,5 °C |
| noviembre | — | 121-216 | — | 15,5 °C |
| diciembre | 3,8 | 121-216 | 70-95 % | 16 °C |

No entran en ninguna regla: NDVI/NDRE/NDMI, humedad de suelo (ver §6). **Aviso (D7):** mi recálculo desde `response_*.json` no coincide exactamente con estos agregados; hay que fijar la versión canónica.

## 3. Parámetros propuestos (ninguno viene de una fuente agronómica)

| Parámetro | Valor | De dónde sale |
|---|---|---|
| `UMBRAL_NOCHE_C` | 3 | umbral del indicador de la parcela (`process_2.py`: rojo si T mín ≤ 3 °C); **no** es un umbral de daño |
| `NOCHES_FRECUENTES_MIN` | 10 | hueco en los datos: ocasionales ≤4,4; frecuentes ≥10,4 (jun-sep) |
| `HR_UMBRAL_PCT` | 82 | umbral del indicador (`process_2.py:196`) |
| `HR_ALTA_MIN_PCT` | 70 | mínimo observado en dic-abr (70-95 %) |
| `R5_MESES_INFO / R5_MESES_ATENCION` | 2 / 4 | propuesta; sin fuente |
| `LLUVIA_LLUVIOSO_MIN_MM` | 121 | mínimo observado en oct-abr (121-216) |
| `LLUVIA_SECO_MAX_MM` | 62 | máximo observado en jul-sep (43-62) |
| `MAX_ADVERTENCIAS` | 2 | decisión del diseño aprobado |

## 4. Resumen de reglas

| Regla | Qué cruza | Severidad | ¿Baja puntaje? | Umbral calibrado en campo | Requiere validación agronómica | Viable hoy | Activa en la parcela (3588 m) |
|---|---|---|---|---|---|---|---|
| **R1** Altitud mas alta (o mas baja) que el rango de las fuentes de Ecuador/Andes | `altitud_msnm` × Altitud de la parcela | atencion | no | no | **no** | si | cebada, haba, chocho |
| **R2** Noches frias en el ciclo de un cultivo que no aguanta el frio | `temperatura_minima_tolerada_c` × Noches <= 3 C por mes | atencion | no | no | **si** | si | ninguno |
| **R3** Noches frias en el ciclo de la quinua (esterilidad de polen en floracion) | `umbral_frio_floracion_c` × Noches <= 3 C por mes | atencion | no | no | **si** | si | ninguno |
| **R4** Mucha lluvia mensual para un cultivo que no soporta el agua estancada | `tolerancia_exceso_agua` × Lluvia mensual | info (siempre) | no | no | **si** | si | haba, chocho |
| **R5** Aire muy humedo durante el ciclo de un hospedero de la lancha | `hospedero_lancha` × Presion de lancha: % de dias del mes con HR > 82 % | info con 2-3 meses de HR alta | no | no | **si** | si | papa |
| **R6** Siembra fuera de los meses documentados para la sierra | `meses_siembra` × Lluvia mensual del mes de siembra | atencion | no | no | **si** | si | cebada, haba, chocho |
| **R7** Siembra de chocho con menos lluvia que la minima que pide la ficha | `siembra_condicion_lluvia` × Lluvia mensual del mes de siembra | atencion | no | no | **si** | si | chocho |
| **R8** Noches frias y no hay dato confiable de tolerancia al frio del cultivo | `tolerancia_helada` × Noches <= 3 C por mes | info | no | no | **no** | si | papa, oca, cebada |
| **R9** Calor por encima de lo que tolera el cultivo | `temperatura_maxima_tolerada_c` × T max diaria maxima del mes | atencion | no | no | **no** | si en el diseno; NUNCA se activa con los datos de la parcela | oca |
| **R10** Poca lluvia en la etapa sensible a la sequia | `fase_sensible_sequia` × Lluvia mensual como proxy de deficit de agua | info | no | no | **si** | si | cebada, chocho |
| **R11** Mucha lluvia en el ciclo de un cultivo muy exigente en nitrogeno (posible perdida de nitrogeno) | `perdida_nitrogeno_por_lluvia` × Lluvia mensual | info | no | no | **si** | si | papa |

Candidatos probables a 3588 m (filtro de altitud del motor, ±200 m, sobre `clima.altitud_msnm` de la ficha): papa, oca, lizas, olluco, cebada, haba, chocho, avena. **Quinua, maíz, amaranto, arveja, trigo, lenteja y qaniwa quedan fuera**, así que R2 y R3 no tienen efecto práctico en esta parcela mientras no se resuelva D1. Además R9 (calor) no se activa nunca con los datos actuales (máxima diaria corregida 16,5 °C frente a topes de 28, 30 y 35 °C) y R10 (sequía) solo se activa si se siembra fuera de las ventanas documentadas. Las reglas con efecto real hoy son R1, R4, R5, R6, R7, R8 y R11.

## 5. Detalle por regla

### R1 · Altitud mas alta (o mas baja) que el rango de las fuentes de Ecuador/Andes

- **Viable hoy:** si
- **Campo de la ficha:** `altitud_msnm {min, max, max_con_variedades_especiales | max_reportado}`
- **Indicador de la parcela:** Altitud de la parcela (3588 msnm). Es un dato fijo de la parcela, no un indicador de remote sensing.
- **Umbral:** altitud_parcela > max, o < min, del campo tipado. Solo con fiabilidad >= media.
- **Ventana de tiempo:** No aplica (condicion estatica).
- **Severidad:** atencion si fiabilidad=alta y esta fuera incluso de max_con_variedades_especiales/max_reportado; info si fiabilidad=media o si esta dentro de max_con_variedades_especiales/max_reportado.
- **Puntaje:** solo advertencia. El motor ya descarta con +-200 m (filtro F4) y emite 'adaptacion marginal' dentro del margen usando la ficha; R1 solo agrega los casos en que el campo tipado es MAS restrictivo que la ficha (haba, chocho, cebada).
- **No se genera si:** campo null o fiabilidad baja (avena); altitud dentro del rango; el cultivo no es candidato; el motor ya emitio la advertencia 'marginal' para ese cultivo (evitar duplicado; decision D5).
- **Fuente del umbral:** Rangos publicados por INIAP/FAO/CIP citados en propuesta_campos_tipados.json (campo altitud_msnm). No hay umbral inventado.
- **Calibrado en campo:** no (literatura y fichas de variedad; no medido en Toacaso). **Origen del umbral:** ecuador (haba, chocho, cebada, maiz, arveja, amaranto, oca, papa) / andes (trigo, lizas, lenteja, qaniwa).
- **Requiere validación agronómica: no.** El mensaje solo repite un rango publicado. Lo que si necesita decision es D1 (rangos en conflicto dentro de la ficha).
- **Cultivos que cumplen la condición estática:** cebada, trigo, maiz, quinua, amaranto, qaniwa, haba, chocho, arveja, lenteja; **activa en 3588 m:** cebada, haba, chocho.
- **Plantilla(s) fija(s):**
  - `sobre`: {Cultivo} se cultiva, según {fuente}, hasta unos {max} metros de altura. Su parcela está a {altitud_parcela} metros. A esa altura podría rendir menos de lo esperado. Consulte a un técnico o al INIAP antes de decidir.
  - `sobre_extra`: {Cultivo} se cultiva, según {fuente}, hasta unos {max} metros de altura. Hay reportes de cultivo hasta {extra} metros. Su parcela está a {altitud_parcela} metros, en el límite. Pregunte a un técnico o al INIAP qué conviene.
  - `bajo`: {Cultivo} se da, según {fuente}, desde unos {min} metros de altura. Su parcela está a {altitud_parcela} metros, más abajo. Podría no darse bien. Consulte a un técnico o al INIAP.
- **Ejemplo renderizado** (caso T01, pasa el validador): El chocho se cultiva, según una fuente de Ecuador, hasta unos 3400 metros de altura. Hay reportes de cultivo hasta 3600 metros. Su parcela está a 3588 metros, en el límite. Pregunte a un técnico o al INIAP qué conviene.
- **Casos de prueba:** T01, T02, T03, T04, T05, T06, T16, T19, T20, T26, T28, T35, T36

### R2 · Noches frias en el ciclo de un cultivo que no aguanta el frio

- **Viable hoy:** si (sin efecto en la parcela de 3588 m: maiz y amaranto los descarta el filtro de altitud)
- **Campo de la ficha:** `temperatura_minima_tolerada_c (valor_c >= 3) o tolerancia_helada = baja`
- **Indicador de la parcela:** Noches <= 3 C por mes (temperatura corregida por altura).
- **Umbral:** Solo se cruza si el cultivo tolera una minima >= 3 C (cualquier noche contada esta por debajo) o es 'baja' cualitativa con fiabilidad >= media. Si la minima tolerada es < 3 C (quinua -5, arveja -3, haba 1) el indicador no discrimina y NO se advierte. Frecuentes = >= 10 noches/mes; ocasionales = 1-9.
- **Ventana de tiempo:** Meses del ciclo: ceil(ciclo_meses.max) meses desde el mes de siembra. Meses sin dato se ignoran (no cuentan como 0).
- **Severidad:** atencion si algun mes de la ventana es 'frecuente'; info si solo hay 'ocasionales'.
- **Puntaje:** solo advertencia
- **No se genera si:** tolerancia null / minima tolerada < 3 C / fiabilidad baja; ningun mes de la ventana tiene dato de noches; cultivo no candidato; el ciclo no esta tipado.
- **Fuente del umbral:** El umbral de 3 C es el del indicador de la parcela (remote-sensing/nasa-power/process_2.py: ROJO si T min <= 3 C), NO un umbral de dano de ningun cultivo. El corte 10 noches/mes es un hueco en los datos (ocasionales <= 4,4; frecuentes >= 10,4). La minima tolerada del maiz (8 C) es una frase ambigua de F1 (FAO Ecuador).
- **Calibrado en campo:** no. **Origen del umbral:** ecuador (maiz, amaranto); cortes de frecuencia: datos de la parcela.
- **Requiere validación agronómica: si.** Validar (a) la lectura 'soporta minimas hasta 8 C', (b) si 3 C corregidos equivalen a riesgo para el cultivo, (c) el corte de 10 noches.
- **Cultivos que cumplen la condición estática:** maiz, amaranto; **activa en 3588 m:** ninguno.
- **Plantilla(s) fija(s):**
  - `minima`: {Cultivo} no resiste bien el frío: {fuente} dice que aguanta mínimas de hasta {minima_tolerada_c} °C. En su zona se estiman noches de {umbral_noche_c} °C o menos en estos meses del cultivo: {lista}. Podría dañarse. Consulte a un técnico o al INIAP.
  - `cualitativa`: {Cultivo} es sensible al frío, según {fuente}. En su zona se estiman noches de {umbral_noche_c} °C o menos en estos meses del cultivo: {lista}. Podría dañarse. Consulte a un técnico o al INIAP.
- **Ejemplo renderizado** (caso T15, pasa el validador): El maíz no resiste bien el frío: una fuente de Ecuador dice que aguanta mínimas de hasta 8 °C. En su zona se estiman noches de 3 °C o menos en estos meses del cultivo: junio (10,4 noches). Podría dañarse. Consulte a un técnico o al INIAP.
- **Casos de prueba:** T15, T16, T17, T18, T29, T39

### R3 · Noches frias en el ciclo de la quinua (esterilidad de polen en floracion)

- **Viable hoy:** si (sin efecto hoy: la ficha de quinua tiene altitud 2200-3000 y el motor la descarta a 3588 m; ver D1)
- **Campo de la ficha:** `umbral_frio_floracion_c (quinua = 5) y fase_sensible_helada = floracion`
- **Indicador de la parcela:** Noches <= 3 C por mes (temperatura corregida).
- **Umbral:** El umbral de la ficha (5 C) es mayor que el del indicador (3 C): toda noche contada esta por debajo de 5 C. Si el campo fuera <= 3 la regla no se aplica.
- **Ventana de tiempo:** Ciclo completo (ceil(ciclo_meses.max) meses desde la siembra): NO hay dias a floracion de Ecuador para quinua, asi que no se puede acotar a la floracion; el mensaje lo dice ('si la floracion cae en esos meses').
- **Severidad:** atencion si hay un mes 'frecuente' en la ventana; info si solo 'ocasionales'.
- **Puntaje:** solo advertencia
- **No se genera si:** umbral null o fiabilidad baja; umbral <= 3 C; sin datos de noches en la ventana; cultivo no candidato.
- **Fuente del umbral:** Manual CIP/INIAP 2002 (Cultivo de granos andinos en Ecuador): 'temperaturas ambientales bajas (por debajo de 5 C), especialmente durante la floracion, producen esterilidad de polen'. Es temperatura ambiental, no se aclara si es aire a 2 m.
- **Calibrado en campo:** no. **Origen del umbral:** ecuador (el ensayo de Jacobsen 2000 es de cultivares peruanos y no se usa como umbral).
- **Requiere validación agronómica: si.** Falta confirmar el 5 C y la fase; sin dias a floracion la ventana es todo el ciclo (puede sobreavisar).
- **Cultivos que cumplen la condición estática:** quinua; **activa en 3588 m:** ninguno.
- **Plantilla(s) fija(s):**
  - `floracion`: En la floración, {cultivo} es sensible al frío. {Fuente} indica que por debajo de {umbral_frio_floracion_c} °C la flor puede quedar estéril. En su zona se estiman noches de {umbral_noche_c} °C o menos en: {lista}. Podría afectar la cosecha si la floración cae en esos meses. Consulte a un técnico o al INIAP.
- **Ejemplo renderizado** (caso T12, pasa el validador): En la floración, la quinua es sensible al frío. Una fuente de Ecuador indica que por debajo de 5 °C la flor puede quedar estéril. En su zona se estiman noches de 3 °C o menos en: junio (10,4 noches), julio (16,4 noches), agosto (17 noches). Podría afectar la cosecha si la floración cae en esos meses. Consulte a un técnico o al INIAP.
- **Casos de prueba:** T12, T13, T14

### R4 · Mucha lluvia mensual para un cultivo que no soporta el agua estancada

- **Viable hoy:** si (activa hoy para haba y chocho; quinua, maiz, amaranto y arveja los descarta el filtro de altitud)
- **Campo de la ficha:** `tolerancia_exceso_agua = baja (+ fase_sensible_exceso_agua)`
- **Indicador de la parcela:** Lluvia mensual (mm/mes).
- **Umbral:** Mes 'lluvioso' = 121 mm o mas (minimo observado en el grupo oct-abr: 121-216). No hay cifra agronomica de que lluvia mensual dana a estos cultivos.
- **Ventana de tiempo:** Si fase_sensible_exceso_agua incluye 'plantula' (amaranto): mes de siembra y el siguiente. Si no: todo el ciclo.
- **Severidad:** info (siempre)
- **Puntaje:** solo advertencia
- **No se genera si:** tolerancia null / no es 'baja' / fiabilidad baja; ningun mes de la ventana es lluvioso (los meses sin dato no cuentan); cultivo no candidato.
- **Fuente del umbral:** La parte del cultivo (no soporta excesos de agua) tiene cita de Ecuador/Andes. El corte de 121 mm es un corte de los datos de la parcela (y coincide con el 120 mm de la alerta NUTRIENTES de process_2.py), sin respaldo agronomico.
- **Calibrado en campo:** no. **Origen del umbral:** cultivo: ecuador/andes; corte de lluvia: datos de la parcela.
- **Requiere validación agronómica: si.** Regla ruidosa: las ventanas de siembra recomendadas ya caen en la epoca de lluvias, asi que casi siempre se activa. Ver D6.
- **Cultivos que cumplen la condición estática:** maiz, quinua, amaranto, haba, chocho, arveja; **activa en 3588 m:** haba, chocho.
- **Plantilla(s) fija(s):**
  - `ciclo`: En {meses} llueve mucho en su zona (entre {lluvia_min_mm} y {lluvia_max_mm} mm al mes). {Cultivo} no soporta bien el agua estancada, según {fuente}. Revise que el terreno drene bien. Si tiene dudas, consulte a un técnico.
  - `plantula`: Al inicio del cultivo, cuando la planta es chica, llueve mucho en su zona (entre {lluvia_min_mm} y {lluvia_max_mm} mm al mes) en {meses}. {Cultivo} no soporta bien el agua estancada, según {fuente}. Revise que el terreno drene bien. Si tiene dudas, consulte a un técnico.
- **Ejemplo renderizado** (caso T01, pasa el validador): En diciembre, enero, febrero, marzo, abril, octubre y noviembre llueve mucho en su zona (entre 121 y 216 mm al mes). El chocho no soporta bien el agua estancada, según una fuente de Ecuador. Revise que el terreno drene bien. Si tiene dudas, consulte a un técnico.
- **Casos de prueba:** T01, T05, T06, T12, T13, T14, T15, T16, T17, T18, T19, T20, T21, T26, T29, T34, T35, T39

### R5 · Aire muy humedo durante el ciclo de un hospedero de la lancha

- **Viable hoy:** si (activa hoy para papa)
- **Campo de la ficha:** `hospedero_lancha = true`
- **Indicador de la parcela:** Presion de lancha: % de dias del mes con HR > 82 %.
- **Umbral:** Mes de 'HR alta' = al menos 70 % de dias con HR > 82 % (minimo del grupo dic-abr: 70-95 %; jul-sep: 5-13 %). Se advierte con >= 2 meses de HR alta en el ciclo (info) y >= 4 (atencion).
- **Ventana de tiempo:** Ciclo completo: ceil(ciclo_meses.max) meses desde el mes de siembra.
- **Severidad:** info con 2-3 meses de HR alta; atencion con 4 o mas.
- **Puntaje:** solo advertencia
- **No se genera si:** hospedero_lancha null o false; menos de 2 meses de HR alta en el ciclo; sin dato de HR en los meses del ciclo; cultivo no candidato.
- **Fuente del umbral:** Que la papa es hospedera: ficha (Ecuador, alta). Los cortes de 70 %, 2 y 4 meses son de los datos de la parcela, sin fuente agronomica. El HR>80 % de FONTAGRO cita una referencia mexicana y CIP Quito asocia el inoculo NEGATIVAMENTE con la HR: evidencia contradictoria. Tampoco hay dato de lancha sobre 3500 m (huecos_indicadores).
- **Calibrado en campo:** no. **Origen del umbral:** hospedero: ecuador; cortes: datos de la parcela; HR>82 %: process_2.py.
- **Requiere validación agronómica: si.** Imprescindible un agronomo: el vinculo HR-lancha a 3588 m no esta confirmado en Ecuador. El mensaje se redacto como riesgo, no como hecho.
- **Cultivos que cumplen la condición estática:** papa; **activa en 3588 m:** papa.
- **Plantilla(s) fija(s):**
  - `base`: Para {cultivo}, de los {meses_ciclo} meses del ciclo, {meses_hr_alta} caen en meses de aire muy húmedo: en ellos, entre {hr_dias_min_pct} y {hr_dias_max_pct} % de los días tienen más de {hr_umbral_pct} % de humedad en el aire. Con esa humedad la lancha puede aparecer con más facilidad. Es un riesgo, no algo que ya pasó. Consulte a un técnico o al INIAP sobre cómo vigilar su lote.
- **Ejemplo renderizado** (caso T07, pasa el validador): Para la papa, de los 7 meses del ciclo, 5 caen en meses de aire muy húmedo: en ellos, entre 70 y 95 % de los días tienen más de 82 % de humedad en el aire. Con esa humedad la lancha puede aparecer con más facilidad. Es un riesgo, no algo que ya pasó. Consulte a un técnico o al INIAP sobre cómo vigilar su lote.
- **Casos de prueba:** T07, T09, T10, T25, T31, T37

### R6 · Siembra fuera de los meses documentados para la sierra

- **Viable hoy:** si (activa hoy para cebada, haba y chocho; papa se excluye por siembra todo el ano)
- **Campo de la ficha:** `meses_siembra (y siembra_condicion_lluvia)`
- **Indicador de la parcela:** Lluvia mensual del mes de siembra (como contexto).
- **Umbral:** mes de siembra no esta en meses_siembra (si hay 'sobre_3200_msnm' y la parcela esta a mas de 3200 m, se usa esa lista). El indicador solo sube la severidad: mes 'seco' = 62 mm o menos (jul-sep: 43-62).
- **Ventana de tiempo:** Mes de siembra.
- **Severidad:** atencion si el mes es seco y el cultivo tiene condicion de lluvia; info en el resto.
- **Puntaje:** solo advertencia
- **No se genera si:** meses_siembra null o fiabilidad baja; meses_siembra.todo_el_anio_en_algunas_zonas = true (papa); el mes esta en la lista; R7 se activo para el mismo cultivo (R7 la reemplaza); cultivo no candidato.
- **Fuente del umbral:** Los meses vienen de F1 (FAO Ecuador), INIAP y tesis UTC (citados). 'Seco' (<= 62 mm) es un corte de los datos de la parcela.
- **Calibrado en campo:** no (ficha da 'mes exacto para Toacaso no confirmado'). **Origen del umbral:** ecuador; corte de lluvia: datos de la parcela.
- **Requiere validación agronómica: si.** Los calendarios son generales para la sierra, no para Toacaso.
- **Cultivos que cumplen la condición estática:** cebada, maiz, quinua, amaranto, haba, chocho; **activa en 3588 m:** cebada, haba, chocho.
- **Plantilla(s) fija(s):**
  - `seco`: En la sierra de Ecuador, {cultivo} se siembra en {meses}, según {fuente}. Usted piensa sembrar en {mes}, cuando en su zona llueve poco (entre {lluvia_min_mm} y {lluvia_max_mm} mm al mes). Puede salir peor. Consulte a un técnico o al INIAP.
  - `fuera`: En la sierra de Ecuador, {cultivo} se siembra en {meses}, según {fuente}. Usted piensa sembrar en {mes}, fuera de ese tiempo. Puede salir peor. Consulte a un técnico o al INIAP.
  - `seco_sobre`: A más de {altitud_m} metros, {cultivo} se siembra en {meses}, según {fuente}. Usted piensa sembrar en {mes}, cuando en su zona llueve poco (entre {lluvia_min_mm} y {lluvia_max_mm} mm al mes). Puede salir peor. Consulte a un técnico o al INIAP.
  - `fuera_sobre`: A más de {altitud_m} metros, {cultivo} se siembra en {meses}, según {fuente}. Usted piensa sembrar en {mes}, fuera de ese tiempo. Puede salir peor. Consulte a un técnico o al INIAP.
- **Ejemplo renderizado** (caso T03, pasa el validador): En la sierra de Ecuador, la cebada se siembra en octubre, noviembre y diciembre, según una fuente de Ecuador. Usted piensa sembrar en enero, fuera de ese tiempo. Puede salir peor. Consulte a un técnico o al INIAP.
- **Casos de prueba:** T03, T04, T06, T14, T18, T20, T29, T35, T36

### R7 · Siembra de chocho con menos lluvia que la minima que pide la ficha

- **Viable hoy:** si (activa hoy para chocho)
- **Campo de la ficha:** `siembra_condicion_lluvia {tipo: lluvia_acumulada_min_mm, mm: 100}`
- **Indicador de la parcela:** Lluvia mensual del mes de siembra.
- **Umbral:** La lluvia mensual maxima de la parcela en el mes de siembra es menor que 100 mm (jul-sep: 43-62). Si el mes no tiene dato, no se genera.
- **Ventana de tiempo:** Mes de siembra.
- **Severidad:** atencion
- **Puntaje:** solo advertencia
- **No se genera si:** campo null o de otro tipo; mes sin dato de lluvia (mayo, junio); lluvia maxima del mes >= 100 mm; cultivo no candidato.
- **Fuente del umbral:** 100 mm: clima.notas de la ficha de chocho ('sembrar tras acumular >=100 mm de lluvia'; la ficha no da la fuente numerada). Se compara lluvia ACUMULADA con la lluvia MENSUAL media: no es lo mismo.
- **Calibrado en campo:** no. **Origen del umbral:** ecuador (F1, sin numero de fuente en la frase).
- **Requiere validación agronómica: si.** Confirmar si '100 mm acumulados' se mide desde el inicio de lluvias o en el mes; la lluvia de NASA no esta corregida por altura.
- **Cultivos que cumplen la condición estática:** chocho; **activa en 3588 m:** chocho.
- **Plantilla(s) fija(s):**
  - `base`: Para {cultivo}, {fuente} dice sembrar cuando ya hayan caído unos {lluvia_min_siembra_mm} mm de lluvia. En {mes} en su zona llueve poco (entre {lluvia_min_mm} y {lluvia_max_mm} mm al mes). Considere esperar las lluvias. Consulte a un técnico.
- **Ejemplo renderizado** (caso T19, pasa el validador): Para el chocho, una fuente de Ecuador dice sembrar cuando ya hayan caído unos 100 mm de lluvia. En agosto en su zona llueve poco (entre 43 y 62 mm al mes). Considere esperar las lluvias. Consulte a un técnico.
- **Casos de prueba:** T19

### R8 · Noches frias y no hay dato confiable de tolerancia al frio del cultivo

- **Viable hoy:** si (activa hoy para papa, cebada, oca; lenteja y trigo sin ciclo o filtradas)
- **Campo de la ficha:** `tolerancia_helada, temperatura_minima_tolerada_c y umbral_frio_floracion_c (los tres null o de fiabilidad baja) + ciclo_meses`
- **Indicador de la parcela:** Noches <= 3 C por mes.
- **Umbral:** Algun mes de la ventana con >= 10 noches <= 3 C.
- **Ventana de tiempo:** Ciclo completo desde el mes de siembra.
- **Severidad:** info
- **Puntaje:** solo advertencia (nunca puntaje)
- **No se genera si:** el cultivo tiene algun dato de tolerancia al frio con fiabilidad >= media (aunque no discrimine); R2 o R3 ya se activaron; no hay mes frecuente en la ventana; ciclo no tipado; cultivo no candidato.
- **Fuente del umbral:** No hay umbral: es la ausencia de dato. Los cortes de frecuencia son de los datos de la parcela.
- **Calibrado en campo:** no aplica. **Origen del umbral:** datos de la parcela.
- **Requiere validación agronómica: no.** No afirma nada agronomico, solo dice que no hay dato. Es de baja prioridad y casi nunca cabe en las 2 advertencias (ver D6).
- **Cultivos que cumplen la condición estática:** papa, oca, cebada; **activa en 3588 m:** papa, oca, cebada.
- **Plantilla(s) fija(s):**
  - `base`: No hay datos confiables de Ecuador o los Andes sobre cuánto frío aguanta {cultivo}. En su zona hay noches de {umbral_noche_c} °C o menos en: {lista}. Consulte a un técnico o al INIAP.
- **Ejemplo renderizado** (caso T08, pasa el validador): No hay datos confiables de Ecuador o los Andes sobre cuánto frío aguanta la papa. En su zona hay noches de 3 °C o menos en: junio (10,4 noches), julio (16,4 noches), agosto (17 noches), septiembre (12,8 noches). Consulte a un técnico o al INIAP.
- **Casos de prueba:** T03, T04, T08, T10, T11, T24, T31, T36

### R9 · Calor por encima de lo que tolera el cultivo

- **Viable hoy:** si en el diseno; NUNCA se activa con los datos de la parcela (T max diaria maxima corregida en 5 anios: 16,5 C; los topes citados son 28, 30 y 35 C)
- **Campo de la ficha:** `temperatura_maxima_tolerada_c {valor_c, efecto}`
- **Indicador de la parcela:** T max diaria maxima del mes (corregida por altura). NO esta en los agregados del encargo: uso un recalculo propio desde response_*.json (T2M_MAX - 7,81 C, 2021-2025). El JSON del backend solo trae estado_estres_calor = VERDE en todas las ventanas (rojo si hay 3 dias seguidos con T max > 22 C).
- **Umbral:** T max diaria maxima del mes >= valor_c del campo (oca 28, maiz 30, arveja 35).
- **Ventana de tiempo:** Ciclo completo desde el mes de siembra.
- **Severidad:** atencion
- **Puntaje:** solo advertencia
- **No se genera si:** campo null o de otra region (lenteja: EcoCrop) o fiabilidad baja; ningun mes de la ventana alcanza el tope; sin dato de T max en los meses del ciclo; cultivo no candidato.
- **Fuente del umbral:** Topes de la ficha: oca 'mas de 28 C destruye la planta' (F1), maiz 'desde 30 C hay problemas de absorcion' (F1), arveja 'sobre 35 C' (F8, UTC). El 22 C del semaforo de calor del codigo no se usa: no es un dano de cultivo.
- **Calibrado en campo:** no. **Origen del umbral:** ecuador.
- **Requiere validación agronómica: no.** Solo repite un tope publicado y con los datos actuales no se activa. Su utilidad es dejar la puerta abierta si cambia la parcela o el clima. Ver D12 (la T max mensual es un recalculo mio).
- **Cultivos que cumplen la condición estática:** oca, maiz, arveja; **activa en 3588 m:** oca.
- **Plantilla(s) fija(s):**
  - `base`: {Cultivo} no aguanta bien el calor: {fuente} dice que desde {tmax_tolerada_c} °C {efecto_txt}. En su zona se estiman días de hasta esta temperatura en: {lista}. Podría afectarlo. Consulte a un técnico o al INIAP.
- **Ejemplo renderizado** (caso T33, pasa el validador): La oca no aguanta bien el calor: una fuente de Ecuador dice que desde 28 °C puede destruir la planta. En su zona se estiman días de hasta esta temperatura en: enero (hasta 29 °C). Podría afectarlo. Consulte a un técnico o al INIAP.
- **Casos de prueba:** T33, T34

### R10 · Poca lluvia en la etapa sensible a la sequia

- **Viable hoy:** si (dormida: solo se activa si se siembra fuera de las ventanas documentadas; activa para chocho y cebada)
- **Campo de la ficha:** `fase_sensible_sequia (+ dias_a_floracion si la fase es floracion; no se aplica si tolerancia_sequia = alta)`
- **Indicador de la parcela:** Lluvia mensual como proxy de deficit de agua. No hay agregado mensual de humedad de raiz del lado seco; el JSON actual muestra humedad_raiz 75,4 %, estado_riego VERDE_OPTIMO en las 9 fotos y la alerta SEQUIA nunca activa.
- **Umbral:** Algun mes de la ventana con clase 'seco' (lluvia maxima <= 62 mm; jul-sep: 43-62).
- **Ventana de tiempo:** inicio_crecimiento: mes de siembra y el siguiente. floracion: mes de siembra + floor(dias_a_floracion / 30,4) (chocho: +3 meses). Otras fases (cebada): ciclo completo, y el mensaje dice que no se sabe en que mes cae la etapa.
- **Severidad:** info
- **Puntaje:** solo advertencia
- **No se genera si:** fase null o fiabilidad baja; tolerancia_sequia = alta; ningun mes de la ventana es seco (los meses sin dato no cuentan); ciclo no tipado y fase sin ubicacion; cultivo no candidato.
- **Fuente del umbral:** Las fases salen de INIAP (cebada, ficha de Ecuador), de la ficha de chocho (susceptible a sequia en floracion y fructificacion) y de F2 (qaniwa). El corte de 62 mm es de los datos de la parcela. No se usa la evapotranspiracion: el codigo la mezcla con mm de lluvia (doc 07).
- **Calibrado en campo:** no. **Origen del umbral:** fases: ecuador/andes; corte de lluvia: datos de la parcela.
- **Requiere validación agronómica: si.** Los dias a floracion del chocho son de un ensayo de abono verde a 2793-3200 msnm, no de 3588; el mes de floracion es aproximado.
- **Cultivos que cumplen la condición estática:** cebada, qaniwa, chocho; **activa en 3588 m:** cebada, chocho.
- **Plantilla(s) fija(s):**
  - `floracion`: {Cultivo} es sensible a la falta de agua en la floración, según {fuente}. Con su fecha de siembra la floración podría caer en {meses}, cuando en su zona llueve poco (entre {lluvia_min_mm} y {lluvia_max_mm} mm al mes). Podría rendir menos. Consulte a un técnico o al INIAP.
  - `inicio`: {Cultivo} es sensible a la falta de agua al inicio del crecimiento, según {fuente}. En {meses} en su zona llueve poco (entre {lluvia_min_mm} y {lluvia_max_mm} mm al mes). Podría crecer mal. Consulte a un técnico o al INIAP.
  - `ciclo`: {Cultivo} es sensible a la falta de agua en ciertas etapas, según {fuente}. En su ciclo hay meses de poca lluvia: {meses} (entre {lluvia_min_mm} y {lluvia_max_mm} mm al mes). No se sabe en qué mes cae esa etapa. Consulte a un técnico o al INIAP.
- **Ejemplo renderizado** (caso T35, pasa el validador): El chocho es sensible a la falta de agua en la floración, según una fuente de Ecuador. Con su fecha de siembra la floración podría caer en julio, cuando en su zona llueve poco (entre 43 y 62 mm al mes). Podría rendir menos. Consulte a un técnico o al INIAP.
- **Casos de prueba:** T04, T20, T35, T36, T38

### R11 · Mucha lluvia en el ciclo de un cultivo muy exigente en nitrogeno (posible perdida de nitrogeno)

- **Viable hoy:** si (activa hoy para papa)
- **Campo de la ficha:** `perdida_nitrogeno_por_lluvia = true + exigencia_nitrogeno = alta (y fija_nitrogeno distinto de true)`
- **Indicador de la parcela:** Lluvia mensual.
- **Umbral:** Algun mes del ciclo en clase 'lluvioso' (>= 121 mm). Coincide con los 120 mm de la alerta NUTRIENTES del codigo, que ademas exige GWETTOP > 75 % (humedad de capa superior de NASA, sin corregir por altura; no se usa aqui).
- **Ventana de tiempo:** Ciclo completo desde el mes de siembra (no hay dato de en que momento absorbe el N en Ecuador).
- **Severidad:** info
- **Puntaje:** solo advertencia
- **No se genera si:** perdida_nitrogeno_por_lluvia null (maiz, amaranto: no hay cita de lixiviacion para ellos); fija_nitrogeno = true (leguminosas); exigencia no es alta o fiabilidad baja; ningun mes lluvioso en el ciclo; sin dato de lluvia; cultivo no candidato.
- **Fuente del umbral:** Gaibor 2024 (suelos volcanicos de Chimborazo): el N 'puede perderse por nitrificacion, lixiviacion y volatilizacion', solo cualitativo; la ficha dice que no hay cifras de lavado con lluvia fuerte en papa de Sierra. El corte de 121 mm es de los datos de la parcela.
- **Calibrado en campo:** no. **Origen del umbral:** ecuador (cualitativo); corte de lluvia: datos de la parcela.
- **Requiere validación agronómica: si.** Se activa casi siempre que se siembra papa en la epoca lluviosa; ver D6. El mensaje no da dosis ni productos ni dice 'fraccione'.
- **Cultivos que cumplen la condición estática:** papa; **activa en 3588 m:** papa.
- **Plantilla(s) fija(s):**
  - `base`: En {meses} llueve mucho en su zona (entre {lluvia_min_mm} y {lluvia_max_mm} mm al mes). {Cultivo} necesita mucho nitrógeno y, según {fuente}, parte del nitrógeno puede perderse del suelo. Es un riesgo, no algo medido. Consulte a un técnico o al INIAP sobre cómo cuidar la fertilidad del lote.
- **Ejemplo renderizado** (caso T07, pasa el validador): En noviembre, diciembre, enero, febrero, marzo y abril llueve mucho en su zona (entre 121 y 216 mm al mes). La papa necesita mucho nitrógeno y, según una fuente de Ecuador, parte del nitrógeno puede perderse del suelo. Es un riesgo, no algo medido. Consulte a un técnico o al INIAP sobre cómo cuidar la fertilidad del lote.
- **Casos de prueba:** T07, T08, T09, T10, T11, T25, T31

## 6. Reglas que NO son viables hoy

- **R-NV1 · Vigor/fenologia (NDVI, NDRE, NDMI) contra la fase del cultivo.** indicadores.fenologia_indices.ndvi_por_fase_numerico, ndre y ndmi son null en todas las fichas (la ficha de papa lo lista en huecos_indicadores: no hay valores numericos por fase, y menos en altura andina). Sin un campo tipado con cita no hay contra que comparar la serie de NDVI de la parcela (0,202-0,448; nunca verde). *Falta:* Curvas NDVI por fase para papa/cultivos de Sierra con Sentinel-2 y fuente andina.
- **R-NV2 · Umbral de lluvia que provoca perdida de nitrogeno.** R11 solo avisa de forma cualitativa (papa). La ficha: 'perdidas_lavado: solo cualitativo; no se hallaron cifras de lavado con lluvia fuerte en papa de sierra'. El corte de 121 mm es de los datos de la parcela, no de un estudio. Maiz y amaranto son exigentes en N pero no tienen cita de perdida por lluvia. *Falta:* Estudio de lixiviacion de N en suelos volcanicos de la Sierra con cifras, y citas para maiz y amaranto.
- **R-NV3 · Helada en floracion acotada al mes de floracion (papa, lizas, chocho, arveja).** Hay dias a floracion (papa 104 d, lizas 98-130 d, chocho 97-110 d, arveja 76-81 d) pero ninguno de esos cultivos tiene a la vez tolerancia/umbral de helada con fiabilidad >= media y una fase sensible conocida: papa (fase solo de Puno, fiabilidad baja), lizas (evidencia mixta), chocho (sin umbral), arveja (helada solo de Australia). Los dias a floracion son de otras altitudes (3050, 2850, 2793-3200 msnm), no de 3588. *Falta:* Umbral de helada por fase para papa de la Sierra (la ficha: 'no encontrado; tesis USFQ inaccesible').
- **R-NV4 · Helada de la papa (el cultivo de la parcela).** tolerancia_helada de papa = null: 'variedades sensibles y tolerantes' (F2, Peru) sin dato para Fripapa ni Superchola; -2,5 C y -1 C son de origen no confirmado o periodistico. Solo R8 ('no hay dato confiable') puede mencionarla. *Falta:* Ficha INIAP de helada por variedad y fase.
- **R-NV5 · Lluvia anual de la parcela contra el rango anual de la ficha.** El resumen no trae lluvia de mayo y junio, la lluvia NASA (celda de ~50 km a 2501 m) no esta corregida por altura y los rangos de la ficha mezclan base anual y base ciclo (papa 700-1200 anual; arveja 250-380 por ciclo). Ademas, con los meses conocidos la parcela recibe 121-216 mm/mes durante 7 meses: los totales del ciclo casi siempre superan los minimos de la ficha, asi que no discriminarian; lo que importa es la distribucion (R10). *Falta:* Tabla mensual completa y corregida por altura; campo tipado con base explicita (anual|ciclo).
- **R-NV6 · Que otro cultivo 'no es hospedero' de la lancha (mensaje tranquilizador).** Ninguna ficha tiene cita explicita de que un cultivo NO sea hospedero de P. infestans (cebada, quinua: inferencia o conocimiento general). Un mensaje 'no hay riesgo de lancha' seria una afirmacion sin fuente. hospedero_lancha = null no equivale a false. *Falta:* Cita de Ecuador/Andes por cultivo.
- **R-NV8 · NDRE bajo (poca clorofila) contra la exigencia de nitrogeno del cultivo.** fenologia_indices.ndre es null en todas las fichas (no hay NDRE por fase). Ademas el NDRE de hoy (0,2495; semaforo AMARILLO_NUTRICION y cruce NUTRICION_PROBABLE) es del cultivo en pie a mitad de ciclo y no dice cuanto nitrogeno tiene el suelo para el SIGUIENTE cultivo. El umbral de 0,35 es del codigo, no de un cultivo. *Falta:* NDRE por fase en papa de la Sierra y una relacion NDRE-nitrogeno del suelo validada.
- **R-NV9 · Reglas con el estado actual (humedad de raiz, estado_riego, alertas de la semana).** Las reglas de esta matriz son de PLANIFICACION (que cultivo sembrar y cuando) y usan la climatologia mensual. El estado de hoy (humedad_raiz 75,4 %, estado_riego VERDE_OPTIMO en las 9 fotos, SEQUIA y calor sin alerta) describe el cultivo en curso y no cambia la eleccion del siguiente; ademas la humedad de raiz de NASA no se corrige por altura y el semaforo casi no varia. *Falta:* Un conjunto aparte de reglas de MONITOREO del cultivo en curso (mensajes ya presentes en el JSON del backend), con su propia validacion.
- **R-NV7 · Calibracion de R5 con las condiciones de lancha del ensayo de Carchi.** condiciones_lancha_referencia (2650 msnm, HR 86,7 %, 128 mm/mes, 12,4 C) es de un ensayo, no un umbral, tiene fiabilidad baja y la ficha no da su URL. Se tipa pero ninguna regla lo usa. *Falta:* Fuente del ensayo y umbral de lancha para altura.

## 7. Casos de prueba

Comprobados con un evaluador de referencia (no es el motor). Parcela = §2. Tope de 2 advertencias por defecto. "Omitidas" = reglas que se activan pero quedan fuera por el tope.

| ID | Situación | Entrada | Advertencias esperadas | Omitidas | Por qué |
|---|---|---|---|---|---|
| T01 | Chocho a 3588 m, siembra en diciembre | candidatos: chocho; siembra: diciembre; altitud: 3588 m | R1 info (chocho); R4 info (chocho) | — | 3588 > 3400 (INIAP) pero <= 3600 (reportado): info. Diciembre es mes de siembra (R6 no) y llueve 121-216 mm (R7 no). R4: sensible al exceso de agua y hay meses lluviosos en el ciclo. |
| T02 | Cebada, siembra en octubre | candidatos: cebada; siembra: octubre; altitud: 3588 m | R1 info (cebada) | — | 3588 > 3500 pero <= 3600 de variedades especiales: info. Octubre esta en la ventana. Sin tolerancia al exceso de agua tipada (R4 no). R8: sin noches frecuentes en octubre-marzo (max 4,4). |
| T03 | Cebada, siembra en enero (fuera de ventana, mes lluvioso) | candidatos: cebada; siembra: enero; altitud: 3588 m | R1 info (cebada); R6 info (cebada) | R8 | R6 info: enero no esta en oct-dic y llueve (no es mes seco). R8 (junio 10,4 noches) queda fuera por el tope de 2. |
| T04 | Cebada, siembra en agosto (mes seco) | candidatos: cebada; siembra: agosto; altitud: 3588 m | R6 atencion (cebada); R1 info (cebada) | R10, R8 | R6 atencion: agosto fuera de ventana, llueve 43-62 mm y la cebada se siembra al inicio de lluvias. El orden pone atencion antes que info. R10 (sequia) y R8 quedan fuera por el tope. |
| T05 | Haba, siembra en octubre | candidatos: haba; siembra: octubre; altitud: 3588 m | R1 info (haba); R4 info (haba) | — | A mas de 3200 m la ventana es solo octubre: R6 no. Altitud 3588 > 3400 con fiabilidad media: info. Sin R8: el haba SI tiene temperatura minima tolerada tipada (1 C), aunque no discrimina con el indicador <=3 C. |
| T06 | Haba, siembra en marzo (fuera de la ventana de >3200 m) | candidatos: haba; siembra: marzo; altitud: 3588 m | R1 info (haba); R6 info (haba) | R4 | R6 info (sobre 3200 m solo octubre; el haba no tiene condicion de lluvia tipada, por eso no sube a atencion). |
| T07 | Papa, siembra en noviembre | candidatos: papa; siembra: noviembre; altitud: 3588 m | R5 atencion (papa); R11 info (papa) | — | Ciclo de 7 meses (noviembre-mayo): diciembre-abril son 5 meses con 70-95 % de dias con HR>82 % (>=4: atencion). R6 no aplica: la fuente dice que en ciertas zonas se siembra todo el ano. |
| T08 | Papa, siembra en junio | candidatos: papa; siembra: junio; altitud: 3588 m | R11 info (papa); R8 info (papa) | — | Junio-diciembre: solo diciembre tiene HR alta (1 mes < 2): R5 no. Junio-septiembre tienen 10-17 noches <=3 C y no hay tolerancia a helada tipada: R8 'no hay dato confiable'. |
| T09 | Papa, siembra en octubre | candidatos: papa; siembra: octubre; altitud: 3588 m | R5 atencion (papa); R11 info (papa) | — | Octubre-abril: 5 meses de HR alta y todo el ciclo en meses lluviosos (R11). |
| T10 | Papa, siembra en diciembre | candidatos: papa; siembra: diciembre; altitud: 3588 m | R5 atencion (papa); R11 info (papa) | R8 | Diciembre-junio: 5 meses de HR alta; junio (10,4 noches) activa R8. |
| T11 | Papa, siembra en mayo | candidatos: papa; siembra: mayo; altitud: 3588 m | R11 info (papa); R8 info (papa) | — | Mayo-noviembre: ningun mes de HR alta; junio-septiembre con noches frecuentes -> R8. |
| T12 | Quinua, altitud forzada 3000 m (aislar R3), siembra en enero | candidatos: quinua; siembra: enero; altitud: 3000 m | R3 atencion (quinua); R4 info (quinua) | — | Aislamiento de regla: a 3588 m el filtro del motor descarta la quinua. Enero-agosto incluye jun-ago con 10-17 noches (<5 C en floracion): atencion. |
| T13 | Quinua, altitud forzada 3000 m, siembra en octubre | candidatos: quinua; siembra: octubre; altitud: 3000 m | R3 info (quinua); R4 info (quinua) | — | Octubre-mayo: solo noches ocasionales (<=4,4): info. |
| T14 | Quinua, altitud forzada 3000 m, siembra en julio (mes seco, fuera de ventana) | candidatos: quinua; siembra: julio; altitud: 3000 m | R3 atencion (quinua); R6 atencion (quinua) | R4 | Julio: seco y fuera de oct-ene con condicion 'inicio de lluvias': R6 atencion; julio-septiembre con noches frecuentes: R3 atencion. |
| T15 | Maiz, altitud forzada 3000 m, siembra en octubre | candidatos: maiz; siembra: octubre; altitud: 3000 m | R2 atencion (maiz); R4 info (maiz) | — | Minima tolerada 8 C >= 3: cualquier noche <=3 C esta por debajo. Octubre-junio incluye junio (10,4): atencion. |
| T16 | Maiz a 3588 m (si el filtro F4 lo dejara pasar), siembra en octubre | candidatos: maiz; siembra: octubre; altitud: 3588 m | R1 atencion (maiz); R2 atencion (maiz) | R4 | R1 atencion (3588 > 3000, fiabilidad alta). Caso hipotetico: ver T-NC1, el motor lo descarta. |
| T17 | Amaranto, altitud forzada 2800 m, siembra en octubre | candidatos: amaranto; siembra: octubre; altitud: 2800 m | R2 info (amaranto); R4 info (amaranto) | — | Sensibilidad cualitativa (sin cifra). Octubre-abril: solo noches ocasionales. R4 con ventana de plantula (octubre-noviembre). |
| T18 | Amaranto, altitud forzada 2800 m, siembra en enero | candidatos: amaranto; siembra: enero; altitud: 2800 m | R2 atencion (amaranto); R6 info (amaranto) | R4 | Enero-julio incluye junio-julio (10-16 noches): atencion. R6 info: fuera de octubre-noviembre pero es mes lluvioso. |
| T19 | Chocho, siembra en agosto (seco, menos de 100 mm) | candidatos: chocho; siembra: agosto; altitud: 3588 m | R7 atencion (chocho); R1 info (chocho) | R4 | R7 reemplaza a R6 (misma causa): la ficha pide >=100 mm acumulados y agosto da 43-62 mm. |
| T20 | Chocho, siembra en mayo (la lluvia de mayo NO esta en el resumen) | candidatos: chocho; siembra: mayo; altitud: 3588 m | R1 info (chocho); R6 info (chocho) | R10, R4 | Adversario: sin dato de lluvia para mayo. R7 no se activa (no se inventa), R6 solo informa que esta fuera de la ventana. |
| T21 | Arveja, altitud forzada 2800 m, siembra en noviembre | candidatos: arveja; siembra: noviembre; altitud: 2800 m | R4 info (arveja) | — | El dato de helada de Australia no esta tipado: no hay R2/R3/R8. La arveja tiene minima tolerada -3 C (<3): el indicador <=3 C no discrimina. |
| T22 | Lenteja, altitud forzada 3000 m, siembra en julio (campos vacios) | candidatos: lenteja; siembra: julio; altitud: 3000 m | **ninguna** | — | Adversario: ciclo, tolerancias y meses son null (datos de otra region). Ninguna advertencia, ni siquiera R8 (sin ventana de ciclo). |
| T23 | Oca, siembra en octubre | candidatos: oca; siembra: octubre; altitud: 3588 m | **ninguna** | — | Dentro del rango 3000-3800. Su tolerancia a helada es 'media' con fiabilidad baja: cuenta como no confiable, pero octubre-mayo no tiene noches frecuentes. |
| T24 | Oca, siembra en junio | candidatos: oca; siembra: junio; altitud: 3588 m | R8 info (oca) | — | Junio-enero: junio-septiembre con noches frecuentes y dato de fiabilidad baja -> 'no hay dato confiable'. |
| T25 | Cultivo no candidato | candidatos: papa; siembra: octubre; altitud: 3588 m | R5 atencion (papa); R11 info (papa) | — | Quinua, maiz y amaranto cumplen condiciones de R2-R4 pero no estan en candidatos (el filtro de altitud los descarto): no se evalua nada para ellos. |
| T26 | Haba con dato de helada solo de Australia (mostrar todas) | candidatos: haba; siembra: octubre; altitud: 3588 m; tope 5 | R1 info (haba); R4 info (haba) | — | Adversario: el dato de Australia no entro a la ficha tipada. Aun mostrando hasta 5 advertencias no hay R2/R3/R8 para el haba. |
| T27 | Avena a 3588 m: altitud de fiabilidad baja | candidatos: avena; siembra: octubre; altitud: 3588 m | **ninguna** | — | Adversario: el rango 2000-3400 de la avena viene de una nota de prensa (fiabilidad baja): R1 no advierte. Sin ciclo tipado: R8 tampoco. |
| T28 | Qaniwa a 3588 m (por debajo de su rango) | candidatos: qaniwa; siembra: octubre; altitud: 3588 m | R1 atencion (qaniwa) | — | 3588 < 3800 (F2 Peru/Bolivia, fiabilidad alta): atencion 'bajo'. El motor la descarta por el margen de 200 m: caso hipotetico. |
| T29 | Maiz, altitud forzada 3000 m, siembra en febrero, datos incompletos | candidatos: maiz; siembra: febrero; altitud: 3000 m | R2 atencion (maiz); R6 info (maiz) | R4 | Feb-oct: febrero, marzo y mayo no estan en el resumen de noches: se ignoran (no cuentan como 0) y aun asi junio-septiembre activan atencion. |
| T30 | Parcela sin datos de clima | candidatos: papa; siembra: octubre; altitud: 3588 m; parcela sin datos | **ninguna** | — | Adversario: sin datos de HR ni de noches no hay R5 ni R8. Nunca se genera una advertencia sin evidencia. |
| T31 | Papa, siembra en agosto (limite R5: 3 meses de HR alta) | candidatos: papa; siembra: agosto; altitud: 3588 m | R5 info (papa); R11 info (papa) | R8 | Agosto-febrero: diciembre, enero y febrero = 3 meses (>=2 y <4): info. R6 no aplica a la papa (siembra todo el ano). |
| T32 | Lizas/olluco, siembra en octubre | candidatos: lizas, olluco; siembra: octubre; altitud: 3588 m | **ninguna** | — | Dentro del rango 2800-4000, tolerancia a helada 'media' con fiabilidad media, sin tolerancia al exceso de agua tipada: ninguna regla aplica. |
| T33 | Oca con un enero hipotetico de 29 C de maxima (aislar R9) | candidatos: oca; siembra: octubre; altitud: 3588 m | R9 atencion (oca) | — | Hipotetico: con los datos reales la maxima diaria corregida de 5 anios es 16,5 C y R9 nunca se activa (oca tolera hasta 28 C, F1). |
| T34 | Arveja (altitud forzada 2800 m) con un enero hipotetico de 36 C | candidatos: arveja; siembra: noviembre; altitud: 2800 m | R9 atencion (arveja); R4 info (arveja) | — | Hipotetico: 36 >= 35 C en un mes del ciclo (noviembre-febrero). R9 va antes que R4 por severidad. |
| T35 | Chocho sembrado en abril: la floracion cae en julio (mostrar todas) | candidatos: chocho; siembra: abril; altitud: 3588 m; tope 5 | R1 info (chocho); R6 info (chocho); R10 info (chocho); R4 info (chocho) | — | 97-110 dias = 3 meses despues de abril: julio, mes seco (43-62 mm). Abril esta fuera de la ventana de siembra (R6 info, es lluvioso). |
| T36 | Cebada sembrada en agosto (mostrar todas) | candidatos: cebada; siembra: agosto; altitud: 3588 m; tope 5 | R6 atencion (cebada); R1 info (cebada); R10 info (cebada); R8 info (cebada) | — | Sin dias a floracion la fase sensible a la sequia no se ubica: R10 usa todo el ciclo (agosto-enero tiene agosto y septiembre secos) y lo dice. |
| T37 | Papa sin dato de lluvia en la parcela | candidatos: papa; siembra: octubre; altitud: 3588 m | R5 atencion (papa) | — | Adversario: sin lluvia no hay R11; R5 sigue porque la HR si tiene dato. Cada regla usa solo su indicador. |
| T38 | Qaniwa (hipotetico, altitud forzada 3900 m) sembrada en julio | candidatos: qaniwa; siembra: julio; altitud: 3900 m | R10 info (qaniwa) | — | Sensible a la falta de agua al inicio del crecimiento (F2): julio-agosto son secos (43-62 mm). |
| T39 | Maiz exigente en N pero sin cita de perdida por lluvia (altitud forzada 3000 m, mostrar todas) | candidatos: maiz; siembra: octubre; altitud: 3000 m; tope 5 | R2 atencion (maiz); R4 info (maiz) | — | Adversario: el maiz tiene exigencia de nitrogeno alta pero perdida_nitrogeno_por_lluvia es null (la cita de lixiviacion es solo de papa): no hay R11. |

Casos adversarios: dato de otra región (T21, T26), campo vacío (T22, T30), fiabilidad baja (T27), mes sin dato (T20, T29), cultivo no candidato (T25), papa sin ventana de siembra (T07, T31), reglas aisladas con altitud forzada (T12-T15, T17, T18, T21, T29, T34, T38, T39: a 3588 m el motor descarta esos cultivos), calor hipotético (T33, T34), lluvia ausente (T37) y cultivo exigente en N sin cita de pérdida (T39).

## 8. Decisiones que necesito de usted

- **D1 · Conflicto de altitud entre la ficha y 'indicadores'.** quinua: clima 2200-3000 (F1) vs indicadores 2300-3700 y 'a 3588 msnm es viable pero con riesgo de helada' (manual CIP/INIAP 2002); amaranto: 2700-3200 vs 1500-2800 (INIAP/CIP); haba: 3600 vs 3400 (variedad Sultana); chocho: 3600 vs 3400; cebada: 3900 vs 3500 (3600 con variedades de limite alto). El filtro F4 del motor usa clima.altitud_msnm: descarta la quinua a 3588 m aunque la propia ficha la da por viable con riesgo. *Recomendación:* Revision agronomica de la ficha de quinua antes de usar R3. Mientras tanto, los campos tipados usan el valor mas restrictivo bien citado (menos para quinua, donde se dejo el de la ficha y se anoto el conflicto).
- **D2 · Cortes de las reglas que no vienen de una fuente agronomica.** 10 noches/mes (frecuentes), 70 % de dias con HR>82 % (HR alta), 2 y 4 meses (R5), 121 mm (lluvioso), 62 mm (seco). Son cortes de los agregados de la parcela. Ademas el umbral de 3 C es el del indicador, no un dano de cultivo. *Recomendación:* Aceptarlos como provisionales con 'requiere validacion: si' y severidad info/atencion sin tocar puntaje, o esperar al agronomo. No inventar otros.
- **D3 · Fiabilidad minima para emitir una advertencia.** Hoy: fiabilidad >= media. Con 'baja' (avena, papa fase de helada, oca tolerancia) el campo existe pero no dispara nada. *Recomendación:* Mantener >= media; con 'baja' a lo sumo R8.
- **D4 · Puede alguna regla bajar puntaje?.** Todas estan como 'solo advertencia'. El unico candidato razonable a futuro es R1 (dato duro de altitud), pero el motor ya lo hace con la ficha. *Recomendación:* Ninguna baja puntaje hasta que un agronomo valide los cortes.
- **D5 · Duplicidad con las advertencias que ya emite el motor.** scoring.py ya avisa 'altitud fuera de rango (dentro del margen)', 'comparte hospedero de plagas' y 'datos con respaldo de otra region'. R1 podria repetir la primera. *Recomendación:* Deduplicar por (cultivo, tipo) en el paso 3; R1 solo cuando el campo tipado sea mas restrictivo que la ficha.
- **D6 · Reglas ruidosas (R4 y R8).** R4 casi siempre se activa (las siembras recomendadas ya caen en lluvias); R11 se activa para la papa en cualquier siembra con meses lluviosos; R8 sale para cualquier cultivo sin dato de helada con noches frecuentes en el ciclo; R9 nunca se activa y R10 solo con siembras fuera de ventana. Con el tope de 2, R8 casi nunca se muestra. *Recomendación:* Mostrar R4, R8 y R11 solo en el registro/al tecnico, no al agricultor, o desactivarlas.
- **D7 · Datos mensuales de la parcela: version canonica.** El script que usted indico (backend/src/match_nasa_sentinel.py) NO calcula estos agregados mensuales: solo alinea la ventana NASA de 7 dias con cada foto, corrige la temperatura con el sesgo medio contra Open-Meteo y evalua los cruces; tampoco estan en resultado_match.json. Su origen sigue sin identificar. El resumen no trae noches de feb, mar, may, nov, ni lluvia de may-jun, ni HR de may, jun, oct, nov. Mi recalculo independiente desde response_1794715361072.json (T min - 6,47 C, 2021-2025, mes calendario) NO coincide exactamente con los agregados del encargo: noches ene 3,6 / jun 9,2 / jul 15,6 / ago 16,4 / sep 12,6 (encargo 3,8 / 10,4 / 16,4 / 17,0 / 12,8); lluvia oct 106, nov 102, dic 119, ene 117 mm/mes (encargo >= 121 en oct-abr). No es un error mio ni suyo comprobado: puede ser la ventana de anios o la definicion de mes. *Recomendación:* Indicarme el script y la ventana que generan los agregados y publicar una tabla mensual completa (12 meses x 3 indicadores) como entrada de las reglas. Las reglas usan hoy SOLO los valores del encargo y tratan los meses sin dato como 'sin dato'.
- **D8 · Incertidumbre de la temperatura corregida.** Las noches <= 3 C usan T min NASA (celda de ~50 km a 2501 m) corregida con un sesgo medio de -6,47 C contra Open-Meteo (1690 dias): no hay estacion en la parcela y el error por noche no esta cuantificado. *Recomendación:* Mensajes con 'se estiman' (ya asi) y no usar el conteo como diagnostico.
- **D9 · Interpretaciones propias en la ficha tipada.** oca.tolerancia_helada = media (fiabilidad baja), maiz.tolerancia_helada = baja y maiz.temperatura_minima_tolerada_c = 8 (media) son lecturas mias de frases de la ficha, marcadas en su nota. *Recomendación:* Que el agronomo las confirme o se pasen a null. Hoy no activan nada practico en la parcela (maiz lo filtra la altitud; oca en R8 cuenta como 'no confiable').
- **D11 · Planificacion frente a monitoreo.** Las reglas cruzan la ficha con la climatologia mensual para decidir el siguiente cultivo. Varios indicadores del JSON del backend (humedad de raiz, estado_riego, NDRE/NDVI de hoy, alertas de la semana) describen el cultivo en curso y no entran (R-NV8, R-NV9). *Recomendación:* Tratar el monitoreo del cultivo en curso como un conjunto de reglas aparte, con sus propias fichas y validacion.
- **D12 · T max mensual de la parcela (R9).** El encargo no trae T max por mes. Use un recalculo propio desde response_*.json (T2M_MAX - 7,81 C, 2021-2025; maxima diaria por mes entre 14,9 y 16,5 C). No coincide necesariamente con el script canonico (D7). Con estos valores R9 nunca se activa aunque cambiara en unos grados. *Recomendación:* Aceptarlo como dato provisional o entregarme la T max mensual canonica.
- **D10 · Fichas duplicadas 'lizas' y 'olluco'.** Contenido identico (mismo cultivo). Se tiparon igual y los casos de prueba las tratan juntas. *Recomendación:* Decidir en el paso 5 si se fusionan o se mantienen como alias.
