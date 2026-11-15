import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}


def limpiar_datos_nasa(nasa_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Limpia el JSON local de NASA POWER ignorando cualquier fecha donde alguna
    variable requerida tenga el valor de relleno (-999).
    """
    fill_value = nasa_json.get("header", {}).get("fill_value", -999)
    params = nasa_json["properties"]["parameter"]

    vars_requeridas = [
        "T2M", "T2M_MIN", "T2M_MAX",
        "PRECTOTCORR", "EVPTRNS",
        "GWETROOT", "RH2M"
    ]
    tiene_gwettop = "GWETTOP" in params

    registros = []
    for f_str in sorted(params["T2M"].keys()):
        if any(params.get(v, {}).get(f_str, fill_value) == fill_value for v in vars_requeridas):
            continue
        if tiene_gwettop and params["GWETTOP"].get(f_str, fill_value) == fill_value:
            continue

        registros.append({
            "fecha_str": f_str,
            "fecha": datetime.strptime(f_str, "%Y%m%d"),
            "T2M": float(params["T2M"][f_str]),
            "T2M_MIN": float(params["T2M_MIN"][f_str]),
            "T2M_MAX": float(params["T2M_MAX"][f_str]),
            "PRECTOTCORR": float(params["PRECTOTCORR"][f_str]),
            "EVPTRNS": float(params["EVPTRNS"][f_str]),
            "GWETROOT": float(params["GWETROOT"][f_str]) * 100.0,  # Escala 0-100 %
            "GWETTOP": (
                float(params["GWETTOP"][f_str]) * 100.0
                if tiene_gwettop
                else float(params["GWETROOT"][f_str]) * 100.0
            ),
            "RH2M": float(params["RH2M"][f_str]),
        })
    return registros


def procesar_prototipo(
    nasa_json: Dict[str, Any],
    registros_validos: List[Dict[str, Any]],
    fecha_corte: Optional[str] = None
) -> Dict[str, Any]:
    """
    Ejecuta el modelo agroclimático y devuelve tanto el `input` procesado
    como el `output` estandarizado en 3 bloques.
    """
    coords = nasa_json.get("geometry", {}).get("coordinates", [-78.68, -0.75, 3340])
    altitud = round(float(coords[2])) if len(coords) >= 3 and coords[2] is not None else 3340

    if fecha_corte:
        subconjunto = [d for d in registros_validos if d["fecha_str"] <= fecha_corte]
    else:
        subconjunto = registros_validos

    if len(subconjunto) < 7:
        raise ValueError("No hay al menos 7 días válidos antes de la fecha de corte seleccionada.")

    ultimos_7 = subconjunto[-7:]
    n = len(ultimos_7)

    # =========================================================================
    # BLOQUE A: INDICADORES DE ESTADO ACTUAL (ÚLTIMOS 7 DÍAS)
    # =========================================================================
    lluvia_7d = sum(d["PRECTOTCORR"] for d in ultimos_7)
    evap_7d = sum(d["EVPTRNS"] for d in ultimos_7)
    balance_hidrico_7d = lluvia_7d - evap_7d

    humedad_raiz_pct = sum(d["GWETROOT"] for d in ultimos_7) / n
    humedad_superficial_pct = sum(d["GWETTOP"] for d in ultimos_7) / n
    humedad_relativa_pct = sum(d["RH2M"] for d in ultimos_7) / n
    temp_min_semana = min(d["T2M_MIN"] for d in ultimos_7)
    temp_max_semana = max(d["T2M_MAX"] for d in ultimos_7)

    # =========================================================================
    # BLOQUE B: SEMÁFOROS DE DIAGNÓSTICO SEMANAL
    # =========================================================================
    # 1. Riesgo de Heladas
    if temp_min_semana <= 3.0:
        estado_helada = {
            "codigo": "ROJO",
            "color": "rojo",
            "estado": "CRÍTICO - Riesgo de Helada",
            "mensaje": "Alerta de helada reciente. Revisa quemaduras en hojas superiores y activa riego nocturno o barreras de humo si el cielo está despejado."
        }
    elif temp_min_semana <= 6.0:
        estado_helada = {
            "codigo": "AMARILLO",
            "color": "amarillo",
            "estado": "PRECAUCIÓN - Madrugadas Frías",
            "mensaje": "Madrugadas frías detectadas. Mantén el suelo con buena humedad para retener calor."
        }
    else:
        estado_helada = {
            "codigo": "VERDE",
            "color": "verde",
            "estado": "NORMAL - Sin Heladas",
            "mensaje": "Temperaturas nocturnas seguras para el follaje de la papa."
        }

    # 2. Necesidad de Riego y Humedad del Suelo
    if humedad_raiz_pct < 45.0 and lluvia_7d < 10.0:
        estado_riego = {
            "codigo": "ROJO_SECO",
            "color": "rojo",
            "estado": "SECO - Regar Urgente",
            "mensaje": "Déficit hídrico en raíces. El suelo perdió más agua de la que recibió; programa riego esta semana."
        }
    elif humedad_raiz_pct > 85.0 and lluvia_7d > 45.0:
        estado_riego = {
            "codigo": "AZUL_SATURADO",
            "color": "azul",
            "estado": "EXCESO - Suelo Saturado",
            "mensaje": "Suelo saturado. Riesgo de pudrición de tubérculos; revisa los canales de drenaje."
        }
    elif humedad_raiz_pct <= 60.0:
        estado_riego = {
            "codigo": "AMARILLO_VIGILAR",
            "color": "amarillo",
            "estado": "MONITOREAR - Humedad Moderada",
            "mensaje": "Humedad moderada. Haz la prueba del puño a 20 cm antes de decidir el riego."
        }
    elif humedad_raiz_pct <= 85.0:
        estado_riego = {
            "codigo": "VERDE_OPTIMO",
            "color": "verde",
            "estado": "ÓPTIMO - Humedad Ideal",
            "mensaje": "Humedad adecuada en zona de raíces. No se requiere riego adicional."
        }
    else:
        estado_riego = {
            "codigo": "AMARILLO_VIGILAR",
            "color": "amarillo",
            "estado": "ALTA HUMEDAD - Vigilar",
            "mensaje": "Suelo muy húmedo sin lluvias extremas recientes. Suspende riegos y revisa drenajes."
        }

    # 3. Estrés por Calor (3 o más días seguidos con T2M_MAX > 22.0 °C)
    racha, max_racha = 0, 0
    for d in ultimos_7:
        racha = racha + 1 if d["T2M_MAX"] > 22.0 else 0
        max_racha = max(max_racha, racha)

    if max_racha >= 3:
        estado_estres_calor = {
            "codigo": "ROJO",
            "color": "rojo",
            "estado": "ALERTA - Golpe de Calor",
            "mensaje": "Golpe de calor diurno. La planta consume energía en respirar y frena el llenado de papa."
        }
    else:
        estado_estres_calor = {
            "codigo": "VERDE",
            "color": "verde",
            "estado": "NORMAL - Temperatura Diurna Ideal",
            "mensaje": "Días frescos ideales para el engrosamiento del tubérculo."
        }

    # =========================================================================
    # BLOQUE C: PROYECCIÓN PREVENTIVA A 30 DÍAS (HISTÓRICO 5 AÑOS)
    # =========================================================================
    fecha_actual = ultimos_7[-1]["fecha"]
    mes_objetivo = 1 if fecha_actual.month == 12 else fecha_actual.month + 1
    nombre_mes = MESES_ES[mes_objetivo]

    dias_hist = [d for d in registros_validos if d["fecha"].month == mes_objetivo]
    n_h = len(dias_hist)
    anios_hist = sorted({d["fecha"].year for d in dias_hist})

    # Acumulados mensuales esperados a 30 días (mm/mes) y promedios históricos
    lluvia_esperada_proximo_mes = (sum(d["PRECTOTCORR"] for d in dias_hist) / n_h) * 30.0
    evap_esperada_proximo_mes = (sum(d["EVPTRNS"] for d in dias_hist) / n_h) * 30.0
    hist_rh2m = sum(d["RH2M"] for d in dias_hist) / n_h
    hist_t2m = sum(d["T2M"] for d in dias_hist) / n_h
    temp_min_esperada = sum(d["T2M_MIN"] for d in dias_hist) / n_h

    alertas_preventivas = []

    # 1. Plagas y Hongos (Tizón tardío / Lancha)
    if (
        humedad_relativa_pct > 82.0
        and (lluvia_esperada_proximo_mes > 90.0 or hist_rh2m > 80.0)
        and (10.0 <= hist_t2m <= 18.0)
    ):
        alertas_preventivas.append({
            "codigo": "PLAGAS_LANCHA",
            "nivel": "ALTO",
            "titulo": "Plagas y Hongos (Tizón tardío / Lancha)",
            "mensaje": "Riesgo alto de Lancha (tizón tardío) para el próximo mes por alta humedad y lluvias esperadas. Revisa el envés de las hojas bajas y prepara control preventivo."
        })

    # 2. Sequía Prolongada
    if humedad_raiz_pct < 55.0 and lluvia_esperada_proximo_mes < evap_esperada_proximo_mes:
        alertas_preventivas.append({
            "codigo": "SEQUIA",
            "nivel": "ALTO" if humedad_raiz_pct < 45.0 else "MEDIO",
            "titulo": "Sequía Prolongada",
            "mensaje": "Tendencia seca para los próximos 30 días (evaporación mayor a la lluvia histórica). Asegura reservas de agua y prioriza el riego en floración."
        })

    # 3. Riesgo de Heladas Futuras
    if temp_min_semana < 5.5 and temp_min_esperada < 4.5:
        alertas_preventivas.append({
            "codigo": "HELADAS",
            "nivel": "ALTO" if temp_min_semana <= 3.0 else "MEDIO",
            "titulo": "Riesgo de Heladas Futuras",
            "mensaje": "Se esperan noches despejadas y frías en las próximas 3 semanas. Alta probabilidad de heladas en zonas bajas de la parcela."
        })

    # 4. Lavado de Nutrientes (Fertilización)
    if lluvia_esperada_proximo_mes > 120.0 and humedad_superficial_pct > 75.0:
        alertas_preventivas.append({
            "codigo": "NUTRIENTES",
            "nivel": "MEDIO",
            "titulo": "Lavado de Nutrientes (Fertilización)",
            "mensaje": "Lluvias fuertes esperadas el próximo mes pueden lavar el nitrógeno y potasio del suelo. Considera fraccionar la fertilización."
        })

    # =========================================================================
    # ESTRUCTURA FINAL: INPUT + OUTPUT
    # =========================================================================
    input_modelo = {
        "fuente_datos": nasa_json.get("header", {}).get("title", "NASA/POWER Daily Data"),
        "ubicacion": {
            "zona": "Toacaso / Sigchos",
            "longitud": coords[0],
            "latitud": coords[1],
            "altitud_msnm": altitud
        },
        "parametros_ejecucion": {
            "fecha_corte_simulada": ultimos_7[-1]["fecha"].strftime("%Y-%m-%d"),
            "total_dias_validos_historico": len(registros_validos),
            "rango_historico_json": {
                "inicio": registros_validos[0]["fecha"].strftime("%Y-%m-%d"),
                "fin": registros_validos[-1]["fecha"].strftime("%Y-%m-%d")
            }
        },
        "ventana_7_dias_evaluada": [
            {
                "fecha": d["fecha"].strftime("%Y-%m-%d"),
                "T2M_c": round(d["T2M"], 2),
                "T2M_MIN_c": round(d["T2M_MIN"], 2),
                "T2M_MAX_c": round(d["T2M_MAX"], 2),
                "PRECTOTCORR_mm": round(d["PRECTOTCORR"], 2),
                "EVPTRNS_mm": round(d["EVPTRNS"], 2),
                "GWETROOT_pct": round(d["GWETROOT"], 1),
                "GWETTOP_pct": round(d["GWETTOP"], 1),
                "RH2M_pct": round(d["RH2M"], 1),
            }
            for d in ultimos_7
        ],
        "muestra_climatologica_mes_siguiente": {
            "mes_evaluado": nombre_mes,
            "anios_incluidos": anios_hist,
            "total_dias_historicos_analizados": n_h,
            "promedios_diarios_base": {
                "lluvia_diaria_hist_mm": round(sum(d["PRECTOTCORR"] for d in dias_hist) / n_h, 2),
                "evap_diaria_hist_mm": round(sum(d["EVPTRNS"] for d in dias_hist) / n_h, 2),
                "humedad_relativa_hist_pct": round(hist_rh2m, 1),
                "temp_media_hist_c": round(hist_t2m, 1),
                "temp_min_hist_c": round(temp_min_esperada, 1),
            }
        }
    }

    output_modelo = {
        "zona": "Toacaso / Sigchos",
        "altitud": altitud,
        "fecha_inicio": ultimos_7[0]["fecha"].strftime("%d/%m/%Y"),
        "fecha_fin": ultimos_7[-1]["fecha"].strftime("%d/%m/%Y"),
        "estado_actual_7d": {
            "lluvia_7d": round(lluvia_7d, 1),
            "balance_hidrico_7d": round(balance_hidrico_7d, 1),
            "humedad_raiz_pct": round(humedad_raiz_pct, 1),
            "humedad_superficial_pct": round(humedad_superficial_pct, 1),
            "humedad_relativa_pct": round(humedad_relativa_pct, 1),
            "temp_min_semana": round(temp_min_semana, 1),
            "temp_max_semana": round(temp_max_semana, 1),
        },
        "semaforos": {
            "estado_helada": estado_helada,
            "estado_riego": estado_riego,
            "estado_estres_calor": estado_estres_calor,
        },
        "proyeccion_30d": {
            "mes": nombre_mes,
            "lluvia_esperada_proximo_mes": round(lluvia_esperada_proximo_mes, 1),
            "evap_esperada_proximo_mes": round(evap_esperada_proximo_mes, 1),
            "temp_min_esperada": round(temp_min_esperada, 1),
            "alertas_preventivas": alertas_preventivas,
        },
        "serie_7d": [
            {
                "dia": d["fecha"].strftime("%d/%m"),
                "tmin": round(d["T2M_MIN"], 1),
                "tmax": round(d["T2M_MAX"], 1),
                "lluvia": round(d["PRECTOTCORR"], 1)
            }
            for d in ultimos_7
        ]
    }

    return {
        "input": input_modelo,
        "output": output_modelo
    }


def buscar_escenarios_demo(nasa_json: Dict[str, Any], registros_validos: List[Dict[str, Any]]) -> None:
    """
    Escanea el histórico 2021-2026 para sugerirte fechas reales con alertas
    que puedas usar durante la presentación para demostrar el valor del sistema.
    """
    ejemplos = {"helada_roja": None, "sequia_roja": None, "lancha_30d": None, "exceso_azul": None}

    for idx in range(7, len(registros_validos), 7):
        f_str = registros_validos[idx]["fecha_str"]
        out = procesar_prototipo(nasa_json, registros_validos, fecha_corte=f_str)["output"]
        sem = out["semaforos"]
        alertas = out["proyeccion_30d"]["alertas_preventivas"]

        if not ejemplos["helada_roja"] and sem["estado_helada"]["codigo"] == "ROJO":
            ejemplos["helada_roja"] = f_str
        if not ejemplos["sequia_roja"] and sem["estado_riego"]["codigo"] == "ROJO_SECO":
            ejemplos["sequia_roja"] = f_str
        if not ejemplos["exceso_azul"] and sem["estado_riego"]["codigo"] == "AZUL_SATURADO":
            ejemplos["exceso_azul"] = f_str
        if not ejemplos["lancha_30d"] and any(a["codigo"] == "PLAGAS_LANCHA" for a in alertas):
            ejemplos["lancha_30d"] = f_str

    print("\n--- FECHAS REALES EN TU JSON PARA DEMOSTRACIÓN EN VIVO ---")
    for tipo, fecha in ejemplos.items():
        print(f" • {tipo:15s} -> {fecha if fecha else 'No detectado en cortes semanales'}")
    print("---------------------------------------------------------\n")


if __name__ == "__main__":
    ruta_json_entrada = Path("response_1794715361072.json")  # Cambia por el nombre de tu JSON original
    ruta_json_salida = Path("resultado_prototipo.json")

    if not ruta_json_entrada.exists():
        print(f"No se encontró '{ruta_json_entrada}'. Coloca tu archivo JSON en la misma carpeta.")
    else:
        with ruta_json_entrada.open("r", encoding="utf-8") as f:
            datos_nasa = json.load(f)

        registros = limpiar_datos_nasa(datos_nasa)

        # 1. Muestra en consola fechas reales de tu histórico con alertas para probar en el demo
        buscar_escenarios_demo(datos_nasa, registros)

        # 2. Procesa el corte (cambia fecha_corte=None por "YYYYMMDD" para simular otra fecha)
        resultado_completo = procesar_prototipo(datos_nasa, registros, fecha_corte=None)

        # 3. Exporta el JSON con estructura {"input": ..., "output": ...}
        with ruta_json_salida.open("w", encoding="utf-8") as f_out:
            json.dump(resultado_completo, f_out, indent=2, ensure_ascii=False)

        print(f"JSON generado (input + output): {ruta_json_salida.resolve()}")
