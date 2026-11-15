# Reporte semanal 2026-S33: 10/08/2026 al 16/08/2026
**Parcela:** papas_parcela · 1.17 ha · centro -0.749029, -78.773999  

## Alertas para el agricultor
- 🔴 **Heladas**: "Alta probabilidad de heladas en las próximas 2 a 4 semanas. Prepara sistemas de prevención."  
  _Porque:_ T mínima de la semana 1.1 °C (7 noches < 6 °C); septiembre: madrugadas históricamente despejado.

## Sentinel-2 de precisión (10 m, polígono exacto)
**Última captura satelital limpia: hace 6 días** (10/08/2026, nubosidad en el polígono 0 %)  
Comparada con la imagen limpia anterior: 29/07/2026 (12 días antes), cambio de NDVI -0.035

| | Estado | Mensaje para el agricultor |
|---|---|---|
| **Vigor y plagas** (NDVI 0.27, NDRE 0.17) | 🔴 rojo | Alerta de estrés severo o ataque de plagas/lancha en focos específicos. Inspecciona las zonas rojas del mapa. |
| **Humedad** (NDMI -0.19) | 🔴 rojo | Estrés hídrico detectado en las hojas de la parcela. El cultivo está perdiendo turgencia; activa riego. |

**Salud del lote:** 0 % del área sana (verde) · 38 % con estrés (amarillo + rojo) · ⚪ gris 62 % · 🟡 amarillo 14 % · 🔴 rojo 24 %
  
**Sector más afectado:** este (38 % de sus píxeles en rojo)

![Vigor 2026-08-10](../salida_s2/png/vigor_20260810.png) ![Humedad 2026-08-10](../salida_s2/png/humedad_20260810.png)

## Detalle de todos los pases del satélite (Sentinel-2 L2A)
| Fecha | Escena | Parcela sin nubes | Nubes | Estado |
|---|---|---|---|---|
| 10/08 | S2A_17MQV_20260810_0_L2A | 100% | 0% | ok |
| 13/08 | S2B_17MQV_20260813_0_L2A | 100% | 0% | ok |

**Último dato válido:** 13/08/2026  
**Comparado con:** 29/07/2026 (15 días antes)

| Índice | Valor | Anterior | Cambio | Qué indica |
|---|---|---|---|---|
| NDVI | 0.294 | 0.304 | -0.010 | vigor / biomasa verde |
| NDMI | -0.256 | -0.250 | -0.006 | humedad de la vegetación |
| NDRE | 0.194 | 0.195 | -0.002 | clorofila / nitrógeno (red edge) |
| EVI | 0.161 | 0.166 | -0.005 | vigor, corrige suelo y atmósfera |
| SAVI | 0.156 | 0.160 | -0.004 | vigor con suelo expuesto |
| BSI | 0.235 | 0.230 | 0.005 | suelo desnudo (más alto = más suelo) |
| NDWI | -0.389 | -0.386 | -0.003 | agua superficial / encharcamiento |
| MSI | 1.754 | 1.733 | 0.021 | estrés hídrico (más alto = más seco) |

![13/08/2026](../imagenes/png/S2_20260813_17MQV.png)

## Clima de la semana (Open-Meteo)
| T mín | T máx | T media | HR media | Lluvia | Radiación | Noches < 6 °C |
|---|---|---|---|---|---|---|
| 1.1 °C | 13.8 °C | 7.3 °C | 83 % | 12.0 mm | 20.2 MJ/m²/día | 7 de 7 |

_Fuente: ERA5 (reanálisis); 7 días con dato._

## Tendencia histórica del próximo mes: septiembre (promedio 2011-2025)
| Lluvia | T mín media | Radiación | Nubes de madrugada | Días con T mín < 6 °C |
|---|---|---|---|---|
| 80 mm (seco) | 3.7 °C | 21.1 MJ/m²/día (alta) | 80 % (despejado) | 28 |

## Reglas evaluadas (provisionales, ver `reglas.py`)
| Regla | Si hoy ocurre esto | ¿Se cumple? | + Próximo mes | ¿Se cumple? | Resultado |
|---|---|---|---|---|---|
| R1 Riesgo de sequía | Humedad baja en Sentinel-2 (NDMI cayendo): NDMI -0.26 (cambio -0.01 en 15 días) | ❌ | Mes históricamente seco: septiembre: 80 mm históricos (seco) | ✅ | ninguna |
| R2 Plagas y hongos (lancha / tizón tardío) | Humedad alta + temperaturas templadas (15-20 °C): HR media 83 %, T media 7.3 °C | ❌ | Mes históricamente lluvioso: septiembre: 80 mm históricos (seco) | ❌ | ninguna |
| R3 Déficit de nutrientes | Vigor (NDVI) estancado en etapa de crecimiento: NDVI 0.29 (cambio -0.01 en 15 días) | ❌ | Alta radiación solar esperada: septiembre: radiación histórica alta | ✅ | ninguna |
| R4 Heladas | Temperaturas mínimas actuales < 6 °C: T mínima de la semana 1.1 °C (7 noches < 6 °C) | ✅ | Mes de cielos despejados nocturnos: septiembre: madrugadas históricamente despejado | ✅ | ALERTA |
