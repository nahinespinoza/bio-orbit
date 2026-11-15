import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}


def limpiar_datos_nasa(nasa_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extrae y limpia los registros diarios válidos del JSON de NASA POWER,
    ignorando cualquier fecha donde alguna variable requerida tenga el valor de relleno (-999).
    """
    fill_value = nasa_json.get("header", {}).get("fill_value", -999)
    params = nasa_json["properties"]["parameter"]

    # Variables necesarias para ambos bloques de análisis
    vars_requeridas = [
        "T2M", "T2M_MIN", "T2M_MAX",
        "PRECTOTCORR", "EVPTRNS",
        "GWETROOT", "RH2M"
    ]
    # GWETTOP es necesaria para la alerta de lavado de nutrientes; si no viniera, usamos GWETROOT como respaldo
    tiene_gwettop = "GWETTOP" in params

    fechas_ordenadas = sorted(params["T2M"].keys())
    registros_validos = []

    for f_str in fechas_ordenadas:
        # Verificar que ninguna variable clave tenga dato faltante (-999)
        es_valido = all(
            params.get(var, {}).get(f_str, fill_value) != fill_value
            for var in vars_requeridas
        )
        if tiene_gwettop and params["GWETTOP"].get(f_str, fill_value) == fill_value:
            es_valido = False

        if not es_valido:
            continue

        fecha_dt = datetime.strptime(f_str, "%Y%m%d")
        registros_validos.append({
            "fecha_str": f_str,
            "fecha": fecha_dt,
            "T2M": float(params["T2M"][f_str]),
            "T2M_MIN": float(params["T2M_MIN"][f_str]),
            "T2M_MAX": float(params["T2M_MAX"][f_str]),
            "PRECTOTCORR": float(params["PRECTOTCORR"][f_str]),
            "EVPTRNS": float(params["EVPTRNS"][f_str]),
            "GWETROOT": float(params["GWETROOT"][f_str]) * 100.0,  # Convertir 0-1 a %
            "GWETTOP": float(params["GWETTOP"][f_str]) * 100.0 if tiene_gwettop else float(params["GWETROOT"][f_str]) * 100.0,
            "RH2M": float(params["RH2M"][f_str]),
        })

    return registros_validos


def evaluar_estado_actual(ultimos_7: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Bloque 1: Evalúa el corte de los últimos 7 días válidos (Heladas, Riego y Calor).
    """
    n = len(ultimos_7)
    lluvia_7d = sum(d["PRECTOTCORR"] for d in ultimos_7)
    evap_7d = sum(d["EVPTRNS"] for d in ultimos_7)
    balance_hidrico = lluvia_7d - evap_7d

    gwetroot_prom = sum(d["GWETROOT"] for d in ultimos_7) / n
    gwettop_prom = sum(d["GWETTOP"] for d in ultimos_7) / n
    rh2m_prom = sum(d["RH2M"] for d in ultimos_7) / n
    t2m_min_semana = min(d["T2M_MIN"] for d in ultimos_7)
    t2m_max_semana = max(d["T2M_MAX"] for d in ultimos_7)

    # A. Riesgo de Heladas
    if t2m_min_semana <= 3.0:
        helada = {
            "nivel": "ROJO (Crítico)",
            "mensaje": "Alerta de helada reciente. Revisa quemaduras en hojas superiores y activa riego nocturno o barreras de humo si el cielo está despejado."
        }
    elif t2m_min_semana <= 6.0:
        helada = {
            "nivel": "AMARILLO (Precaución)",
            "mensaje": "Madrugadas frías detectadas. Mantén el suelo con buena humedad para retener calor."
        }
    else:
        helada = {
            "nivel": "VERDE (Normal)",
            "mensaje": "Temperaturas nocturnas estables, sin riesgo inmediato de helada."
        }

    # B. Necesidad de Riego y Humedad del Suelo
    if gwetroot_prom < 45.0 and lluvia_7d < 10.0:
        riego = {
            "nivel": "ROJO (Seco - Regar urgente)",
            "mensaje": "Déficit hídrico en raíces. El suelo perdió más agua de la que recibió; programa riego esta semana."
        }
    elif gwetroot_prom > 85.0 and lluvia_7d > 45.0:
        riego = {
            "nivel": "AZUL (Exceso de humedad)",
            "mensaje": "Suelo saturado. Riesgo de pudrición de tubérculos; revisa los canales de drenaje."
        }
    elif gwetroot_prom <= 60.0:
        riego = {
            "nivel": "AMARILLO (Monitorear)",
            "mensaje": "Humedad moderada. Haz la prueba del puño a 20 cm antes de decidir el riego."
        }
    elif gwetroot_prom <= 85.0:
        riego = {
            "nivel": "VERDE (Óptimo)",
            "mensaje": "Humedad ideal en la zona de raíces para el desarrollo del cultivo."
        }
    else:
        # Caso borde: humedad > 85% pero lluvia < 45 mm
        riego = {
            "nivel": "AMARILLO (Humedad alta)",
            "mensaje": "Suelo muy húmedo aunque sin lluvias extremas recientes. Evita regar y vigila el drenaje."
        }

    # C. Estrés por Calor (3 o más días seguidos con T2M_MAX > 22.0 °C)
    racha_actual = 0
    max_racha_calor = 0
    for d in ultimos_7:
        if d["T2M_MAX"] > 22.0:
            racha_actual += 1
            max_racha_calor = max(max_racha_calor, racha_actual)
        else:
            racha_actual = 0

    if max_racha_calor >= 3:
        calor = {
            "nivel": "AMARILLO/ROJO (Estrés térmico)",
            "mensaje": "Golpe de calor diurno. La planta consume energía en respirar y frena el llenado de papa."
        }
    else:
        calor = {
            "nivel": "VERDE (Normal)",
            "mensaje": "Temperaturas diurnas favorables para el llenado de tubérculos."
        }

    return {
        "periodo": f"{ultimos_7[0]['fecha'].strftime('%Y-%m-%d')} al {ultimos_7[-1]['fecha'].strftime('%Y-%m-%d')}",
        "metricas": {
            "lluvia_7d_mm": round(lluvia_7d, 1),
            "evapotranspiracion_7d_mm": round(evap_7d, 1),
            "balance_hidrico_mm": round(balance_hidrico, 1),
            "humedad_raiz_pct": round(gwetroot_prom, 1),
            "humedad_superficial_pct": round(gwettop_prom, 1),
            "humedad_relativa_pct": round(rh2m_prom, 1),
            "temp_minima_c": round(t2m_min_semana, 1),
            "temp_maxima_c": round(t2m_max_semana, 1),
            "dias_seguidos_calor": max_racha_calor,
        },
        "evaluacion": {
            "heladas": helada,
            "riego": riego,
            "calor": calor,
        }
    }


def evaluar_proyeccion_30d(
    registros_validos: List[Dict[str, Any]],
    metricas_actuales: Dict[str, float]
) -> Dict[str, Any]:
    """
    Bloque 2: Cruza los promedios históricos del próximo mes con el estado actual
    para generar alertas preventivas a 30 días.
    """
    ultima_fecha = registros_validos[-1]["fecha"]
    mes_objetivo = 1 if ultima_fecha.month == 12 else ultima_fecha.month + 1
    nombre_mes = MESES_ES[mes_objetivo]

    # Filtrar todos los registros históricos correspondientes al mes siguiente
    dias_hist = [d for d in registros_validos if d["fecha"].month == mes_objetivo]

    if not dias_hist:
        return {
            "mes_proyectado": nombre_mes,
            "error": f"No hay registros históricos suficientes para el mes de {nombre_mes}."
        }

    n_hist = len(dias_hist)
    # Promedio diario multiplicado por 30 días para obtener el acumulado mensual esperado (mm/mes)
    hist_prectotcorr_mes = (sum(d["PRECTOTCORR"] for d in dias_hist) / n_hist) * 30.0
    hist_evptrns_mes = (sum(d["EVPTRNS"] for d in dias_hist) / n_hist) * 30.0
    hist_rh2m = sum(d["RH2M"] for d in dias_hist) / n_hist
    hist_t2m = sum(d["T2M"] for d in dias_hist) / n_hist
    hist_t2m_min = sum(d["T2M_MIN"] for d in dias_hist) / n_hist

    act_rh2m = metricas_actuales["humedad_relativa_pct"]
    act_gwetroot = metricas_actuales["humedad_raiz_pct"]
    act_gwettop = metricas_actuales["humedad_superficial_pct"]
    act_t2m_min = metricas_actuales["temp_minima_c"]

    alertas_activas = []

    # 1. Plagas y Hongos (Tizón tardío / Lancha)
    if (
        act_rh2m > 82.0
        and (hist_prectotcorr_mes > 90.0 or hist_rh2m > 80.0)
        and (10.0 <= hist_t2m <= 18.0)
    ):
        alertas_activas.append({
            "tipo": "Plagas y Hongos (Tizón tardío / Lancha)",
            "mensaje": "Riesgo alto de Lancha (tizón tardío) para el próximo mes por alta humedad y lluvias esperadas. Revisa el envés de las hojas bajas y prepara control preventivo."
        })

    # 2. Sequía Prolongada
    if act_gwetroot < 55.0 and hist_prectotcorr_mes < hist_evptrns_mes:
        alertas_activas.append({
            "tipo": "Sequía Prolongada",
            "mensaje": "Tendencia seca para los próximos 30 días (evaporación mayor a la lluvia histórica). Asegura reservas de agua y prioriza el riego en floración."
        })

    # 3. Riesgo de Heladas Futuras
    if act_t2m_min < 5.5 and hist_t2m_min < 4.5:
        alertas_activas.append({
            "tipo": "Riesgo de Heladas Futuras",
            "mensaje": "Se esperan noches despejadas y frías en las próximas 3 semanas. Alta probabilidad de heladas en zonas bajas de la parcela."
        })

    # 4. Lavado de Nutrientes (Fertilización)
    if hist_prectotcorr_mes > 120.0 and act_gwettop > 75.0:
        alertas_activas.append({
            "tipo": "Lavado de Nutrientes (Fertilización)",
            "mensaje": "Lluvias fuertes esperadas el próximo mes pueden lavar el nitrógeno y potasio del suelo. Considera fraccionar la fertilización."
        })

    anios_usados = sorted({d["fecha"].year for d in dias_hist})

    return {
        "mes_proyectado": nombre_mes,
        "anios_referencia": anios_usados,
        "climatologia_historica": {
            "lluvia_esperada_mes_mm": round(hist_prectotcorr_mes, 1),
            "evaporacion_esperada_mes_mm": round(hist_evptrns_mes, 1),
            "humedad_relativa_hist_pct": round(hist_rh2m, 1),
            "temp_media_hist_c": round(hist_t2m, 1),
            "temp_minima_hist_c": round(hist_t2m_min, 1),
        },
        "alertas_preventivas": alertas_activas
    }


def generar_reporte_agricultor(nasa_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Función principal que orquesta la limpieza y ambos análisis.
    """
    coords = nasa_json.get("geometry", {}).get("coordinates", [None, None, None])
    registros_validos = limpiar_datos_nasa(nasa_json)

    if len(registros_validos) < 7:
        raise ValueError("El archivo JSON no contiene al menos 7 días válidos para analizar.")

    ultimos_7 = registros_validos[-7:]
    estado_actual = evaluar_estado_actual(ultimos_7)
    proyeccion_30d = evaluar_proyeccion_30d(registros_validos, estado_actual["metricas"])

    return {
        "ubicacion": {
            "longitud": coords[0],
            "latitud": coords[1],
            "altitud_msnm": coords[2],
        },
        "estado_actual_7d": estado_actual,
        "proyeccion_30d": proyeccion_30d,
    }


def imprimir_boletin_consola(reporte: Dict[str, Any]) -> None:
    """
    Formatea el resultado en lenguaje claro y directo para mostrar al agricultor.
    """
    alt = reporte["ubicacion"]["altitud_msnm"]
    act = reporte["estado_actual_7d"]
    m = act["metricas"]
    ev = act["evaluacion"]
    proy = reporte["proyeccion_30d"]

    print("=" * 65)
    print(f"BOLETÍN AGROCLIMÁTICO - CULTIVO DE PAPA ({alt} m s.n.m.)")
    print(f"Corte semanal: {act['periodo']}")
    print("=" * 65)

    print("\n1. RESUMEN DE LOS ÚLTIMOS 7 DÍAS")
    print(f"   • Lluvia acumulada: {m['lluvia_7d_mm']} mm | Balance hídrico: {m['balance_hidrico_mm']} mm")
    print(f"   • Humedad en raíces: {m['humedad_raiz_pct']}% | Humedad relativa: {m['humedad_relativa_pct']}%")
    print(f"   • Temp. Mínima: {m['temp_minima_c']} °C | Temp. Máxima: {m['temp_maxima_c']} °C")

    print("\n2. DIAGNÓSTICO Y ACCIÓN INMEDIATA")
    print(f"   [HELADAS] -> {ev['heladas']['nivel']}")
    print(f"     {ev['heladas']['mensaje']}")
    print(f"   [RIEGO]   -> {ev['riego']['nivel']}")
    print(f"     {ev['riego']['mensaje']}")
    print(f"   [CALOR]   -> {ev['calor']['nivel']}")
    print(f"     {ev['calor']['mensaje']}")

    print("\n" + "-" * 65)
    print(f"3. PROYECCIÓN PREVENTIVA A 30 DÍAS ({proy['mes_proyectado'].upper()})")
    print("-" * 65)
    if not proy["alertas_preventivas"]:
        print("   Sin alertas críticas proyectadas para el próximo mes. Mantén el manejo habitual.")
    else:
        for i, alerta in enumerate(proy["alertas_preventivas"], 1):
            print(f"   {i}. {alerta['tipo'].upper()}:")
            print(f"      {alerta['mensaje']}")
    print("=" * 65)


if __name__ == "__main__":
    # Ejemplo de uso leyendo tu archivo real descargado de NASA POWER:
    ruta_archivo = Path("response_1794715361072.json")

    if ruta_archivo.exists():
        with ruta_archivo.open("r", encoding="utf-8") as f:
            datos_nasa = json.load(f)

        resultado = generar_reporte_agricultor(datos_nasa)
        imprimir_boletin_consola(resultado)

        # También puedes exportar `resultado` a JSON para consumirlo desde una app móvil/web:
        # print(json.dumps(resultado, indent=2, ensure_ascii=False))
    else:
        print(f"Coloca tu archivo JSON en '{ruta_archivo}' para ejecutar el análisis.")