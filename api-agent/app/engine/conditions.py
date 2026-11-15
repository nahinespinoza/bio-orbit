"""Condiciones de la parcela: resumen estructurado del `output` del remote-sensing y temas activos.

El agente lo recibe desde el primer turno (prompt dinámico) para comparar la parcela con la investigación de las fichas
de cada candidato. Los temas activos salen SOLO de los códigos del propio JSON (semáforos, alertas vigentes y cruces
confirmados): aquí no se inventa ningún umbral. Sin rutas de imágenes, series ni historial (≤ 1,5 KB).
"""

# Temas que cuentan para la regla «si ningún candidato tiene evidencia de los temas activos, se elige el primero del
# motor». `ciclo_siembra` está siempre activo, así que no cuenta.
ALERT_TOPICS: tuple[str, ...] = ("helada", "agua", "exceso_agua", "sanidad", "fertilidad")
ALWAYS_TOPICS: tuple[str, ...] = ("ciclo_siembra",)

CLIMA_FIELDS = ("lluvia_7d", "balance_hidrico_7d", "humedad_raiz_pct", "humedad_superficial_pct",
                "humedad_relativa_pct", "temp_min_semana", "temp_max_semana")
LOTE_FIELDS = ("ndvi_promedio", "ndre_promedio", "ndmi_promedio", "variacion_ndvi_15d", "distribucion_parcela_pct",
               "sector_mas_afectado")


def _code(semaforos: dict, name: str) -> str | None:
    s = semaforos.get(name)
    return s.get("codigo") if isinstance(s, dict) else s


def _active_topics(out: dict, extra: frozenset[str] = frozenset()) -> list[str]:
    regional = out.get("clima_regional_nasa_power") or {}
    sem = regional.get("semaforos") or {}
    lote_sem = (out.get("parcela_sentinel2") or {}).get("semaforos") or {}
    vigente = out.get("proyeccion_vigente_nasa") or regional.get("proyeccion_30d") or {}
    alerts = {a.get("codigo") for a in vigente.get("alertas_preventivas", [])}
    cruces = out.get("cruces_evaluados") or (out.get("cruce_ultima_captura") or {}).get("cruces_evaluados", [])
    confirmed = {c.get("codigo") for c in cruces if c.get("confirmada")}

    riego, vigor, humedad_lote = _code(sem, "estado_riego"), _code(lote_sem, "estado_vigor"), _code(lote_sem, "estado_humedad_parcela")
    rules = {
        "helada": (_code(sem, "estado_helada") not in (None, "VERDE")) or "HELADAS" in alerts,
        "agua": riego == "ROJO_SECO" or humedad_lote == "ROJO_ESTRES_HIDRICO" or "SEQUIA" in alerts,
        "exceso_agua": riego == "AZUL_SATURADO" or "EXCESO_AGUA" in alerts,
        "sanidad": "PLAGAS_LANCHA" in alerts or "LANCHA_CONFIRMADA" in confirmed,
        "fertilidad": vigor == "AMARILLO_NUTRICION" or "NUTRIENTES" in alerts or "NUTRICION_PROBABLE" in confirmed,
    }
    return [t for t in ALERT_TOPICS if rules[t] or t in extra] + list(ALWAYS_TOPICS)


def plot_conditions(rs: dict, extra_topics: frozenset[str] = frozenset()) -> dict:
    """`remote_sensing.json` completo → resumen para el agente (diseño de la elección con evidencia, punto 3).
    `extra_topics`: temas que activa lo que contó el agricultor (p. ej. agua empozada → `exceso_agua`)."""
    out = rs["output"]
    regional = out.get("clima_regional_nasa_power") or {}
    sem = regional.get("semaforos") or {}
    vigente = out.get("proyeccion_vigente_nasa") or regional.get("proyeccion_30d") or {}
    s2 = out.get("parcela_sentinel2") or {}
    lote = s2.get("estado_actual_lote") or {}
    cruzada = out.get("alerta_cruzada_confirmada") or {}
    return {
        "parcela": {"zona": out.get("zona"), "altitud_msnm": out.get("altitud_parcela_msnm")},
        "clima_semana": {
            "desde": regional.get("fecha_inicio"), "hasta": regional.get("fecha_fin"),
            **{k: (regional.get("estado_actual_7d") or {}).get(k) for k in CLIMA_FIELDS},
            "semaforos": {k: _code(sem, k) for k in ("estado_helada", "estado_riego", "estado_estres_calor")},
        },
        "proyeccion": {
            "mes": vigente.get("mes"), "lluvia_esperada_mm": vigente.get("lluvia_esperada_proximo_mes"),
            "temp_min_esperada": vigente.get("temp_min_esperada"),
            "alertas": [{"codigo": a.get("codigo"), "nivel": a.get("nivel"), "titulo": a.get("titulo")}
                        for a in vigente.get("alertas_preventivas", [])],
        },
        "lote_satelite": {
            "ultima_foto": s2.get("fecha_ultima_captura"), "dias_desde_foto": s2.get("dias_desde_ultima_foto"),
            **{k: lote.get(k) for k in LOTE_FIELDS},
            "semaforos": {k: _code(s2.get("semaforos") or {}, k) for k in ("estado_vigor", "estado_humedad_parcela")},
        },
        "alerta_cruzada": ({"codigo": cruzada.get("codigo"), "nivel": cruzada.get("nivel"),
                            "foto": (out.get("cruce_ultima_captura") or {}).get("fecha_captura")} if cruzada else None),
        "temas_activos": _active_topics(out, extra_topics),
    }
