# Reporte semanal 2026-S30: 20/07/2026 al 26/07/2026
**Parcela:** papas_parcela · 1.17 ha · centro -0.749029, -78.773999  

## Alertas para el agricultor
- 🔴 **Riesgo de sequía**: "Riesgo alto de sequía el próximo mes. Programa riego suplementario desde esta semana."  
  _Porque:_ NDMI -0.25 (cambio -0.03 en 15 días); agosto: 56 mm históricos (seco).
- 🔴 **Heladas**: "Alta probabilidad de heladas en las próximas 2 a 4 semanas. Prepara sistemas de prevención."  
  _Porque:_ T mínima de la semana 2.6 °C (7 noches < 6 °C); agosto: madrugadas históricamente despejado.

## Sentinel-2 de precisión (10 m, polígono exacto)
**Última captura satelital limpia: hace 12 días** (14/07/2026, nubosidad en el polígono 0 %)  
Comparada con la imagen limpia anterior: 29/06/2026 (15 días antes), cambio de NDVI -0.004

| | Estado | Mensaje para el agricultor |
|---|---|---|
| **Vigor y plagas** (NDVI 0.30, NDRE 0.19) | 🔴 rojo | Alerta de estrés severo o ataque de plagas/lancha en focos específicos. Inspecciona las zonas rojas del mapa. |
| **Humedad** (NDMI -0.25) | 🔴 rojo | Estrés hídrico detectado en las hojas de la parcela. El cultivo está perdiendo turgencia; activa riego. |

**Salud del lote:** 2 % del área sana (verde) · 55 % con estrés (amarillo + rojo) · ⚪ gris 42 % · 🟢 verde 2 % · 🟡 amarillo 19 % · 🔴 rojo 36 %
  
**Sector más afectado:** norte (70 % de sus píxeles en rojo)

![Vigor 2026-07-14](../salida_s2/png/vigor_20260714.png) ![Humedad 2026-07-14](../salida_s2/png/humedad_20260714.png)

## Detalle de todos los pases del satélite (Sentinel-2 L2A)
| Fecha | Escena | Parcela sin nubes | Nubes | Estado |
|---|---|---|---|---|
| 21/07 | S2A_17MQV_20260721_0_L2A | 6% | 94% | parcial (nubes) |
| 24/07 | S2B_17MQV_20260724_0_L2A | 0% | 100% | nublado (sin descarga) |

**Último dato válido:** 14/07/2026  
**Comparado con:** 29/06/2026 (15 días antes)

| Índice | Valor | Anterior | Cambio | Qué indica |
|---|---|---|---|---|
| NDVI | 0.297 | 0.301 | -0.004 | vigor / biomasa verde |
| NDMI | -0.254 | -0.221 | -0.033 | humedad de la vegetación |
| NDRE | 0.192 | 0.191 | 0.001 | clorofila / nitrógeno (red edge) |
| EVI | 0.158 | 0.192 | -0.034 | vigor, corrige suelo y atmósfera |
| SAVI | 0.150 | 0.176 | -0.026 | vigor con suelo expuesto |
| BSI | 0.226 | 0.201 | 0.025 | suelo desnudo (más alto = más suelo) |
| NDWI | -0.377 | -0.382 | 0.005 | agua superficial / encharcamiento |
| MSI | 1.729 | 1.600 | 0.129 | estrés hídrico (más alto = más seco) |

![14/07/2026](../imagenes/png/S2_20260714_17MQV.png)

## Clima de la semana (Open-Meteo)
| T mín | T máx | T media | HR media | Lluvia | Radiación | Noches < 6 °C |
|---|---|---|---|---|---|---|
| 2.6 °C | 14.4 °C | 7.4 °C | 86 % | 11.4 mm | 20.4 MJ/m²/día | 7 de 7 |

_Fuente: ERA5 (reanálisis); 7 días con dato._

## Tendencia histórica del próximo mes: agosto (promedio 2011-2025)
| Lluvia | T mín media | Radiación | Nubes de madrugada | Días con T mín < 6 °C |
|---|---|---|---|---|
| 56 mm (seco) | 3.7 °C | 19.8 MJ/m²/día (alta) | 81 % (despejado) | 27 |

## Reglas evaluadas (provisionales, ver `reglas.py`)
| Regla | Si hoy ocurre esto | ¿Se cumple? | + Próximo mes | ¿Se cumple? | Resultado |
|---|---|---|---|---|---|
| R1 Riesgo de sequía | Humedad baja en Sentinel-2 (NDMI cayendo): NDMI -0.25 (cambio -0.03 en 15 días) | ✅ | Mes históricamente seco: agosto: 56 mm históricos (seco) | ✅ | ALERTA |
| R2 Plagas y hongos (lancha / tizón tardío) | Humedad alta + temperaturas templadas (15-20 °C): HR media 86 %, T media 7.4 °C | ❌ | Mes históricamente lluvioso: agosto: 56 mm históricos (seco) | ❌ | ninguna |
| R3 Déficit de nutrientes | Vigor (NDVI) estancado en etapa de crecimiento: NDVI 0.30 (cambio -0.00 en 15 días) | ❌ | Alta radiación solar esperada: agosto: radiación histórica alta | ✅ | ninguna |
| R4 Heladas | Temperaturas mínimas actuales < 6 °C: T mínima de la semana 2.6 °C (7 noches < 6 °C) | ✅ | Mes de cielos despejados nocturnos: agosto: madrugadas históricamente despejado | ✅ | ALERTA |
