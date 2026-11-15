# Reporte semanal 2026-S24: 08/06/2026 al 14/06/2026
**Parcela:** papas_parcela · 1.17 ha · centro -0.749029, -78.773999  

## Alertas para el agricultor
- 🔴 **Heladas**: "Alta probabilidad de heladas en las próximas 2 a 4 semanas. Prepara sistemas de prevención."  
  _Porque:_ T mínima de la semana 2.3 °C (6 noches < 6 °C); julio: madrugadas históricamente despejado.

## Sentinel-2 de precisión (10 m, polígono exacto)
**Última captura satelital limpia: hace 20 días** (25/05/2026, nubosidad en el polígono 0 %)  
Comparada con la imagen limpia anterior: primera del periodo

| | Estado | Mensaje para el agricultor |
|---|---|---|
| **Vigor y plagas** (NDVI 0.41, NDRE 0.24) | 🟡 amarillo | Baja concentración de clorofila. Posible falta de nitrógeno o crecimiento lento; revisa fertilización. |
| **Humedad** (NDMI -0.09) | 🔴 rojo | Estrés hídrico detectado en las hojas de la parcela. El cultivo está perdiendo turgencia; activa riego. |

**Salud del lote:** 0 % del área sana (verde) · 85 % con estrés (amarillo + rojo) · ⚪ gris 15 % · 🟡 amarillo 71 % · 🔴 rojo 14 %
  
**Sector más afectado:** sur (31 % de sus píxeles en rojo)

![Vigor 2026-05-25](../salida_s2/png/vigor_20260525.png) ![Humedad 2026-05-25](../salida_s2/png/humedad_20260525.png)

## Detalle de todos los pases del satélite (Sentinel-2 L2A)
| Fecha | Escena | Parcela sin nubes | Nubes | Estado |
|---|---|---|---|---|
| 09/06 | S2C_17MQV_20260609_0_L2A | 0% | 100% | nublado (sin descarga) |
| 14/06 | S2B_17MQV_20260614_0_L2A | 0% | 100% | nublado (sin descarga) |

**Último dato válido:** 25/05/2026 ⚠️ **dato de hace 20 días** (nubes): no se usa para las reglas de satélite.  
**Comparado con:** 15/05/2026 (10 días antes)

| Índice | Valor | Anterior | Cambio | Qué indica |
|---|---|---|---|---|
| NDVI | 0.412 | 0.475 | -0.063 | vigor / biomasa verde |
| NDMI | -0.093 | 0.005 | -0.097 | humedad de la vegetación |
| NDRE | 0.237 | 0.272 | -0.035 | clorofila / nitrógeno (red edge) |
| EVI | 0.253 | 0.341 | -0.088 | vigor, corrige suelo y atmósfera |
| SAVI | 0.238 | 0.299 | -0.061 | vigor con suelo expuesto |
| BSI | 0.106 | 0.017 | 0.088 | suelo desnudo (más alto = más suelo) |
| NDWI | -0.484 | -0.498 | 0.014 | agua superficial / encharcamiento |
| MSI | 1.254 | 1.067 | 0.186 | estrés hídrico (más alto = más seco) |

![25/05/2026](../imagenes/png/S2_20260525_17MQV.png)

## Clima de la semana (Open-Meteo)
| T mín | T máx | T media | HR media | Lluvia | Radiación | Noches < 6 °C |
|---|---|---|---|---|---|---|
| 2.3 °C | 15.4 °C | 8.2 °C | 83 % | 30.7 mm | 19.9 MJ/m²/día | 6 de 7 |

_Fuente: ERA5 (reanálisis); 7 días con dato._

## Tendencia histórica del próximo mes: julio (promedio 2011-2025)
| Lluvia | T mín media | Radiación | Nubes de madrugada | Días con T mín < 6 °C |
|---|---|---|---|---|
| 52 mm (seco) | 4.0 °C | 17.8 MJ/m²/día (baja) | 87 % (despejado) | 26 |

## Reglas evaluadas (provisionales, ver `reglas.py`)
| Regla | Si hoy ocurre esto | ¿Se cumple? | + Próximo mes | ¿Se cumple? | Resultado |
|---|---|---|---|---|---|
| R1 Riesgo de sequía | Humedad baja en Sentinel-2 (NDMI cayendo): sin dato satelital reciente | ➖ | Mes históricamente seco: julio: 52 mm históricos (seco) | ✅ | ninguna |
| R2 Plagas y hongos (lancha / tizón tardío) | Humedad alta + temperaturas templadas (15-20 °C): HR media 83 %, T media 8.2 °C | ❌ | Mes históricamente lluvioso: julio: 52 mm históricos (seco) | ❌ | ninguna |
| R3 Déficit de nutrientes | Vigor (NDVI) estancado en etapa de crecimiento: sin dato satelital reciente o sin observación previa | ➖ | Alta radiación solar esperada: julio: radiación histórica baja | ❌ | ninguna |
| R4 Heladas | Temperaturas mínimas actuales < 6 °C: T mínima de la semana 2.3 °C (6 noches < 6 °C) | ✅ | Mes de cielos despejados nocturnos: julio: madrugadas históricamente despejado | ✅ | ALERTA |
