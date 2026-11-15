"""Reglas de alerta para el reporte semanal.

PROVISIONALES: son las 4 reglas de la tabla del challenge, con umbrales tentativos.
Cada regla combina:
  - condición ACTUAL (lo que pasa hoy en la parcela: satélite o clima de la semana)
  - TENDENCIA del próximo mes (climatología histórica 2011-2025 del mismo punto)
Si se cumplen ambas -> ALERTA.  Si solo se cumple la actual -> VIGILAR.

Para cambiar o agregar reglas, edita UMBRALES y la lista REGLAS. El contexto `c`
que recibe cada función tiene estas claves (None si no hay dato):
  ndvi, ndmi, ndre, bsi, msi       índices Sentinel-2 del último dato válido
  d_ndvi, d_ndmi, dias_delta       cambio respecto a la observación válida anterior (>= 7 días antes)
  sat_reciente                     True si el último dato válido tiene <= MAX_EDAD_SAT días
  fecha_sat                        fecha del último dato válido
  tmin, tmax, tmedia, hr, lluvia, radiacion, noches_bajo_6   clima de la semana
  mes_sig                          dict: nombre, lluvia_mm, clase_lluvia (seco/normal/lluvioso),
                                   clase_radiacion (baja/normal/alta), clase_noches (nublado/normal/despejado),
                                   tmin_media
"""

UMBRALES = {
    # Regla 1: sequía
    "ndmi_caida": -0.03,        # caída de NDMI entre observaciones para considerarlo "cayendo"
    "ndmi_bajo": None,          # opcional: NDMI absoluto que ya cuenta como "bajo". Desactivado porque
                                # con suelo expuesto el NDMI es negativo casi siempre y alertaba de más
    # Regla 2: plagas y hongos (lancha / tizón tardío)
    "hr_alta": 85.0,            # % humedad relativa media de la semana
    "t_templada_min": 15.0,     # °C (de la tabla). OJO: a ~3600 m la media rara vez llega a 15 °C
    "t_templada_max": 20.0,
    # Regla 3: vigor estancado
    "ndvi_estancado": 0.02,     # |cambio de NDVI| menor a esto = estancado
    "ndvi_crec_min": 0.30,      # rango de NDVI que tomamos como "etapa de crecimiento"
    "ndvi_crec_max": 0.75,
    # Regla 4: heladas
    "tmin_helada": 6.0,         # °C
}
MAX_EDAD_SAT = 14  # días; un dato satelital más viejo no se usa para reglas de satélite


def _fmt(v, nd=2):
    return "s/d" if v is None else f"{v:.{nd}f}"


# ---------------------------------------------------------------- regla 1
def r1_actual(c):
    if not c["sat_reciente"] or c["ndmi"] is None:
        return None, "sin dato satelital reciente"
    cae = c["d_ndmi"] is not None and c["d_ndmi"] <= UMBRALES["ndmi_caida"]
    bajo = UMBRALES["ndmi_bajo"] is not None and c["ndmi"] < UMBRALES["ndmi_bajo"]
    txt = f"NDMI {_fmt(c['ndmi'])} (cambio {_fmt(c['d_ndmi'])} en {c['dias_delta'] or 's/d'} días)"
    return cae or bajo, txt


def r1_tend(c):
    m = c["mes_sig"]
    return m["clase_lluvia"] == "seco", f"{m['nombre']}: {m['lluvia_mm']:.0f} mm históricos ({m['clase_lluvia']})"


# ---------------------------------------------------------------- regla 2
def r2_actual(c):
    if c["hr"] is None or c["tmedia"] is None:
        return None, "sin dato de clima"
    ok = c["hr"] >= UMBRALES["hr_alta"] and UMBRALES["t_templada_min"] <= c["tmedia"] <= UMBRALES["t_templada_max"]
    return ok, f"HR media {c['hr']:.0f} %, T media {c['tmedia']:.1f} °C"


def r2_tend(c):
    m = c["mes_sig"]
    return m["clase_lluvia"] == "lluvioso", f"{m['nombre']}: {m['lluvia_mm']:.0f} mm históricos ({m['clase_lluvia']})"


# ---------------------------------------------------------------- regla 3
def r3_actual(c):
    if not c["sat_reciente"] or c["ndvi"] is None or c["d_ndvi"] is None:
        return None, "sin dato satelital reciente o sin observación previa"
    en_crec = UMBRALES["ndvi_crec_min"] <= c["ndvi"] <= UMBRALES["ndvi_crec_max"]
    estanc = abs(c["d_ndvi"]) < UMBRALES["ndvi_estancado"]
    return en_crec and estanc, f"NDVI {_fmt(c['ndvi'])} (cambio {_fmt(c['d_ndvi'])} en {c['dias_delta']} días)"


def r3_tend(c):
    m = c["mes_sig"]
    return m["clase_radiacion"] == "alta", f"{m['nombre']}: radiación histórica {m['clase_radiacion']}"


# ---------------------------------------------------------------- regla 4
def r4_actual(c):
    if c["tmin"] is None:
        return None, "sin dato de clima"
    return c["tmin"] < UMBRALES["tmin_helada"], f"T mínima de la semana {c['tmin']:.1f} °C ({c['noches_bajo_6']} noches < 6 °C)"


def r4_tend(c):
    m = c["mes_sig"]
    return m["clase_noches"] == "despejado", f"{m['nombre']}: madrugadas históricamente {m['clase_noches']}"


REGLAS = [
    dict(id="R1", nombre="Riesgo de sequía", actual=r1_actual, tendencia=r1_tend,
         si="Humedad baja en Sentinel-2 (NDMI cayendo)", mas="Mes históricamente seco",
         mensaje="Riesgo alto de sequía el próximo mes. Programa riego suplementario desde esta semana."),
    dict(id="R2", nombre="Plagas y hongos (lancha / tizón tardío)", actual=r2_actual, tendencia=r2_tend,
         si="Humedad alta + temperaturas templadas (15-20 °C)", mas="Mes históricamente lluvioso",
         mensaje="Alerta preventiva de plagas y hongos (como la lancha/tizón tardío en papa) para las próximas 3 semanas."),
    dict(id="R3", nombre="Déficit de nutrientes", actual=r3_actual, tendencia=r3_tend,
         si="Vigor (NDVI) estancado en etapa de crecimiento", mas="Alta radiación solar esperada",
         mensaje="Posible déficit de nutrientes (nitrógeno/potasio) en las próximas semanas; evalúa fertilización foliar."),
    dict(id="R4", nombre="Heladas", actual=r4_actual, tendencia=r4_tend,
         si="Temperaturas mínimas actuales < 6 °C", mas="Mes de cielos despejados nocturnos",
         mensaje="Alta probabilidad de heladas en las próximas 2 a 4 semanas. Prepara sistemas de prevención."),
]


def evaluar(c):
    out = []
    for r in REGLAS:
        a_ok, a_txt = r["actual"](c)
        t_ok, t_txt = r["tendencia"](c)
        nivel = "ALERTA" if (a_ok and t_ok) else ("VIGILAR" if a_ok else None)
        out.append(dict(id=r["id"], nombre=r["nombre"], si=r["si"], mas=r["mas"], mensaje=r["mensaje"],
                        actual_ok=a_ok, actual_txt=a_txt, tend_ok=t_ok, tend_txt=t_txt, nivel=nivel))
    return out
