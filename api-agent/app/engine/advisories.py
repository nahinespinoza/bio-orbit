"""Advertencias al agricultor (MVP): señal × sensibilidad del cultivo en su ficha.

La idea en una frase: si hay una señal (el clima de esta semana según el remote-sensing o lo que el agricultor ve en su
lote) y la ficha del cultivo dice —con cita de Ecuador o los Andes— que le afecta, el motor genera la advertencia. El
texto sale de una plantilla fija: el motor decide, el agente solo la repite.

- Las señales del clima vienen de `resultado_match.json` (salida del remote-sensing) y SOLO de su ventana más reciente
  (`proyeccion_vigente_nasa` / `clima_regional_nasa_power`). La ventana de la última foto Sentinel-2 es más vieja y no
  genera señales; sus cruces solo sirven para decir que el satélite ve algo si la señal sigue vigente. Aquí no se
  recalcula ningún clima.
- Esas señales son de una parcela monitoreada concreta (3 588 msnm, temperatura corregida a esa altura). Solo se usan
  si el lote está a ±200 m de ella o si su altitud es desconocida (y entonces así consta en la advertencia).
- Las observaciones vienen de lo que el agricultor cuenta (helada, lancha, suelo seco o encharcado). Valen siempre y
  cuentan como nivel ALTO: es lo que ve en su lote. Una observación sin sensibilidad en la ficha no genera nada.
- Las sensibilidades vienen de `knowledge/structured/sensibilidades.json`. Sin dato, sin cita o de otra región
  = no hay advertencia.
- Límite: las señales describen el clima de ahora (el cultivo en pie), no el del ciclo del cultivo que se va a sembrar
  (matriz de reglas, R-NV9 y D11). Por eso las plantillas dicen «ahora» y «si siembra pronto».
- Ninguna advertencia baja el puntaje. Los cruces no están calibrados en campo (requieren validación agronómica).
"""

from app.engine.models import KnowledgeBase

MAX_ADVISORIES = 2
LEVEL_RANK = {"ALTO": 2, "MEDIO": 1}
LEVEL_WORD = {"ALTO": "alto", "MEDIO": "medio"}
MIN_RELIABILITY = ("alta", "media")
ORIGINS = ("ecuador", "andes")
# Parcela monitoreada por el remote-sensing (Toacaso / Sigchos). Se usa si el JSON no trae `altitud_parcela_msnm`.
MONITORED_ALTITUDE_MASL = 3588.0
ALTITUDE_TOLERANCE_M = 200
PHASE = {"plantula": "la plántula", "eje_floral": "el eje floral", "floracion": "la floración",
         "fructificacion": "la fructificación", "emergencia": "la emergencia", "formacion_polen": "la formación de polen",
         "espigazon": "el espigado", "inicio_crecimiento": "el inicio del crecimiento",
         "inicio_estolonizacion": "el inicio de la formación de estolones"}
CLOSE = "Consulte con un experto para una revisión más a detalle."
BOTH = " Usted también nos contó que lo ve en su lote."
# Cruce de remote-sensing que confirma cada señal con Sentinel-2 (ver README de remote-sensing)
CONFIRMED_BY = {"HELADAS": "DANO_HELADA_CONFIRMADO", "PLAGAS_LANCHA": "LANCHA_CONFIRMADA", "NUTRIENTES": "NUTRICION_PROBABLE",
                "SEQUIA": "RIEGO_CONFIRMADO", "EXCESO_AGUA": "EXCESO_AGUA_CONFIRMADO"}
# Lo que el agricultor puede observar en su lote → señal con la que se cruza
OBSERVATIONS = {"frost": "HELADAS", "blight": "PLAGAS_LANCHA", "dry_soil": "SEQUIA", "waterlogging": "EXCESO_AGUA"}


# --- Señales: qué dice hoy el remote-sensing ------------------------------------------------------------

def read_signals(rs: dict) -> dict[str, dict]:
    """resultado_match.json → {código: {nivel, mensaje, confirmed}} + metadatos `_fecha_datos` y `_parcela`.

    Solo cuenta la ventana más reciente: sus alertas preventivas y su semáforo de riego (ROJO_SECO → SEQUIA,
    AZUL_SATURADO → EXCESO_AGUA). Las alertas de la ventana de la última foto ya no están vigentes y no se usan.
    `confirmed` = el cruce con Sentinel-2 de ese tema salió confirmado en la última foto Y la señal sigue en la ventana
    más reciente (si no sigue, no hay señal que confirmar).
    """
    out = rs["output"]
    regional = out["clima_regional_nasa_power"]
    recent = out.get("proyeccion_vigente_nasa") or regional.get("proyeccion_30d") or {}
    signals: dict[str, dict] = {}
    for a in recent.get("alertas_preventivas", []):
        if LEVEL_RANK.get(a["nivel"], 0) > LEVEL_RANK.get(signals.get(a["codigo"], {}).get("nivel"), 0):
            signals[a["codigo"]] = {"nivel": a["nivel"], "mensaje": a["mensaje"]}
    riego = regional["semaforos"]["estado_riego"]
    if riego["codigo"] == "ROJO_SECO":
        signals.setdefault("SEQUIA", {"nivel": "ALTO", "mensaje": riego["mensaje"]})
    if riego["codigo"] == "AZUL_SATURADO":
        signals.setdefault("EXCESO_AGUA", {"nivel": "ALTO", "mensaje": riego["mensaje"]})
    cruces = out.get("cruces_evaluados") or out.get("cruce_ultima_captura", {}).get("cruces_evaluados", [])
    confirmed = {c["codigo"] for c in cruces if c.get("confirmada")}
    for code, sig in signals.items():
        sig["confirmed"] = CONFIRMED_BY.get(code) in confirmed
    signals["_fecha_datos"] = {"nivel": None, "mensaje": regional["fecha_fin"], "confirmed": False}
    signals["_parcela"] = {"altitud_msnm": out.get("altitud_parcela_msnm") or MONITORED_ALTITUDE_MASL}
    return signals


def remote_sensing_scope(signals: dict, altitude_masl: float | None) -> dict:
    """¿Valen las señales del remote-sensing para este lote? Solo si su altitud es desconocida o está a ±200 m de la
    parcela monitoreada. Devuelve {applies, plot_altitude: within|outside|unknown, monitored_altitude_masl, data_date}."""
    ref = signals.get("_parcela", {}).get("altitud_msnm") or MONITORED_ALTITUDE_MASL
    if altitude_masl is None:
        status = "unknown"
    else:
        status = "within" if abs(altitude_masl - ref) <= ALTITUDE_TOLERANCE_M else "outside"
    return {"applies": status != "outside", "plot_altitude": status, "monitored_altitude_masl": ref,
            "data_date": signals.get("_fecha_datos", {}).get("mensaje")}


def with_observations(signals: dict[str, dict], observations: list[str] | tuple[str, ...]) -> dict[str, dict]:
    """Suma lo que el agricultor ve en su lote a las señales del clima. Cada señal queda marcada con su origen."""
    merged = {code: {**sig, "remote": True, "farmer": False, "remote_level": sig["nivel"]} for code, sig in signals.items()
              if not code.startswith("_")}
    for obs in observations:
        code = OBSERVATIONS.get(obs)
        if code is None:
            continue
        base = merged.get(code, {"mensaje": "Observación del agricultor", "confirmed": False, "remote": False, "remote_level": None})
        merged[code] = {**base, "nivel": "ALTO", "farmer": True}      # lo que ve en su lote cuenta como nivel alto
    return merged


# --- Sensibilidades de la ficha -------------------------------------------------------------------------

def _sens(crop_sens: dict, name: str):
    """Valor de un campo solo si es de Ecuador/Andes y de fiabilidad alta o media; si no, None."""
    f = crop_sens.get(name)
    if f and f.get("valor") is not None and f.get("origen") in ORIGINS and f.get("fiabilidad") in MIN_RELIABILITY:
        return f["valor"]
    return None


def _fases(fases: list[str]) -> str:
    return " y ".join(PHASE.get(f, f) for f in fases)


# Cada regla: señal que se cruza, campo de la ficha y plantilla. El texto tiene cuatro partes:
# `clima` (si avisa el remote-sensing: es el clima de AHORA), `lote` (si solo lo vio el agricultor), `satelite` (si el
# cruce con Sentinel-2 salió confirmado: solo lo que el satélite ve de verdad) y `text` (qué le pasaría al cultivo si
# lo siembra pronto). `cruce(sens)` devuelve (campo usado, detalle) si el cultivo es sensible, o None.
def _helada(sens):
    if _sens(sens, "tolerancia_helada") == "baja":
        return "tolerancia_helada", "no resiste bien las heladas"
    fases = _sens(sens, "fase_sensible_helada")
    return ("fase_sensible_helada", f"es sensible a la helada en {_fases(fases)}") if fases else None


def _si(campo, esperado):
    return lambda sens: (campo, "") if _sens(sens, campo) == esperado else None


def _sequia(sens):
    fases = _sens(sens, "fase_sensible_sequia")
    return ("fase_sensible_sequia", _fases(fases)) if fases else None


RULES = [
    {"id": "helada", "signal": "HELADAS", "cruce": _helada,
     "clima": "Ahora el clima de su zona trae noches frías, con riesgo {nivel} de helada.",
     "lote": "Usted nos contó que hay heladas en su lote.",
     "satelite": " En su parcela el satélite también ve plantas que perdieron verdor, que puede ser daño por helada.",
     "text": "Si siembra pronto, el cultivo de {crop} {detalle} y podría dañarse."},
    {"id": "lancha", "signal": "PLAGAS_LANCHA", "cruce": _si("hospedero_lancha", True),
     "clima": "Ahora el clima de su zona trae riesgo {nivel} de lancha.",
     "lote": "Usted nos contó que vio lancha en su lote.",
     "satelite": " En su parcela el satélite también ve plantas que perdieron verdor, que puede ser por la lancha.",
     "text": "Si siembra pronto, el cultivo de {crop} puede enfermarse de lancha."},
    {"id": "nutrientes", "signal": "NUTRIENTES", "cruce": _si("perdida_nitrogeno_por_lluvia", True),
     "clima": "Ahora en su zona se esperan lluvias fuertes, con riesgo {nivel} de que laven el nitrógeno del suelo.",
     "lote": "",
     "satelite": " En su parcela el satélite también ve hojas con poco verdor, que puede ser falta de nitrógeno.",
     "text": "Si siembra pronto, el cultivo de {crop} puede perder nitrógeno con la lluvia."},
    {"id": "sequia", "signal": "SEQUIA", "cruce": _sequia,
     "clima": "Ahora el suelo de su zona está seco, con riesgo {nivel} de falta de agua.",
     "lote": "Usted nos contó que el suelo de su lote está seco.",
     "satelite": " En su parcela el satélite también ve hojas con poca agua.",
     "text": "Si siembra pronto, el cultivo de {crop} es sensible a la falta de agua en {detalle} y podría rendir menos."},
    {"id": "exceso_agua", "signal": "EXCESO_AGUA", "cruce": _si("tolerancia_exceso_agua", "baja"),
     "clima": "Ahora el suelo de su zona está muy mojado, con riesgo {nivel} de que el agua se empoce.",
     "lote": "Usted nos contó que el agua se queda empozada en su lote.",
     "satelite": " En su parcela el satélite también ve plantas que perdieron verdor o con mucha agua en las hojas, "
                 "que puede ser por el exceso de agua.",
     "text": "Si siembra pronto, el cultivo de {crop} no soporta bien el agua estancada: revise que el terreno drene bien."},
]


def _message(rule: dict, sig: dict, crop: str, detalle: str) -> str:
    if sig.get("remote"):
        intro = rule["clima"].format(nivel=LEVEL_WORD.get(sig["remote_level"], str(sig["remote_level"]).lower()))
        intro += BOTH if sig.get("farmer") and rule["lote"] else ""
        intro += rule["satelite"] if sig.get("confirmed") else ""
    else:
        intro = rule["lote"]
    return f"{intro} {rule['text'].format(crop=crop, detalle=detalle)} {CLOSE}".strip()


def advisories_for(crop_id: str, kb: KnowledgeBase, *, signals: dict | None = None,
                   observations: list[str] | tuple[str, ...] = (), altitude_masl: float | None = None) -> list[dict]:
    """Advertencias del cultivo: máximo 2, primero las de nivel ALTO. Lista vacía si no hay señal o no hay dato.

    `signals` (por defecto, las del kb) y `observations` (lo que cuenta el agricultor) se juntan. Las señales del
    remote-sensing se descartan si `altitude_masl` está a más de ±200 m de la parcela monitoreada; las observaciones
    del agricultor valen siempre."""
    signals = kb.signals if signals is None else signals
    scope = remote_sensing_scope(signals, altitude_masl)
    sigs = with_observations(signals if scope["applies"] else {}, observations)
    sens = kb.sensitivities.get(crop_id, {})
    found = []
    for order, rule in enumerate(RULES):
        sig = sigs.get(rule["signal"])
        hit = rule["cruce"](sens) if sig and sens else None
        if not hit or (not sig["remote"] and not rule["lote"]):
            continue
        campo, detalle = hit
        f = sens[campo]
        found.append((-LEVEL_RANK.get(sig["nivel"], 0), order, {
            "rule": rule["id"],
            "level": sig["nivel"],
            "message": _message(rule, sig, kb.crops[crop_id].name.lower(), detalle),
            "signal": {"code": rule["signal"], "level": sig["nivel"], "confirmed_by_satellite": bool(sig.get("confirmed")),
                       "sources": [s for s, on in (("remote_sensing", sig["remote"]), ("farmer", sig["farmer"])) if on],
                       "remote_sensing_message": sig["mensaje"] if sig["remote"] else None,
                       "data_date": scope["data_date"] if sig["remote"] else None,
                       "plot_altitude": scope["plot_altitude"] if sig["remote"] else None,
                       "monitored_altitude_masl": scope["monitored_altitude_masl"] if sig["remote"] else None},
            "crop_field": {"field": campo, "value": f["valor"], "origin": f["origen"], "reliability": f["fiabilidad"],
                           "sources": f.get("fuente", [])},
            "agronomic_validation_pending": True,
        }))
    return [a for _, _, a in sorted(found, key=lambda x: x[:2])][:MAX_ADVISORIES]
