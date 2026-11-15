"""[COPIA para el backend: solo cambian las rutas (data/) y se quitó la generación de HTML; la lógica es la original.]

MATCH FINAL: NASA POWER (clima regional) + Sentinel-2 (parcela a 10 m).

Script aparte: no modifica ninguno de los dos módulos, solo lee lo que cada uno ya generó.

  Datos de NASA POWER (nasa-power/):
    process_2.py                 modelo agroclimático del compañero (se reutiliza, no se copia)
    response_*.json              datos diarios crudos de NASA POWER (5 años)
    resultado_prototipo.json     resultado de la última semana
  Datos de Sentinel-2 (sentinel_2/):
    resultado_prototipo_sentinel_2.json
    datos_sentinel/salida_s2/sentinel2_parcela.json   serie completa de capturas limpias
    datos_sentinel/datos/parcela.json                 altitud de la parcela
    datos_sentinel/datos/clima_*.csv                  Open-Meteo, para medir el sesgo de temperatura

  Salida: resultado_match.json (en esta carpeta)

Uso (desde remote-sensing/):
    python nasa-power/process_2.py      # (desde nasa-power/) si cambian los datos de NASA
    python sentinel_2/preprocesar.py    # si cambian los datos de Sentinel-2
    python match_nasa_sentinel.py

Correcciones para que los dos módulos hablen de lo mismo:
  1. MISMA FECHA: el modelo de NASA (procesar_prototipo de ../nasa-power/process_2.py, sin copiarlo) se
     corre con la ventana de 7 días que termina el día de cada foto Sentinel-2, no con la última semana.
  2. MISMA ALTURA: NASA ubica la parcela a la altura media de su celda (~2 500 m), pero la parcela está a
     ~3 600 m. Las temperaturas de NASA se bajan con el sesgo medido contra Open-Meteo (que sí corrige por
     altura) en los días que tienen ambos. Si no hay datos para medirlo: gradiente de 6,5 °C por km.
     La temperatura corregida se usa SOLO en las reglas de temperatura absoluta (heladas y calor).
     Lancha, riego, sequía y nutrientes se dejan con el modelo original del compañero, porque sus umbrales
     se calibraron con los datos de NASA sin corregir.

Cruces: NASA dice si hay RIESGO; Sentinel-2 confirma si ya hay DAÑO visible en la parcela.
"""
import copy
import sys
import importlib.util
import json
import pathlib
from datetime import date

import pandas as pd

GRADIENTE_C_KM = 6.5   # °C que baja la temperatura por cada km de altura
CAIDA_NDVI = 0.08      # caída de NDVI que cuenta como pérdida de vigor (= límite verde de la regla A)
CAIDA_NDMI = 0.03      # caída de NDMI que cuenta como pérdida de agua del follaje (= regla R1)
NIVEL = {"ALTO": 0, "MEDIO": 1, "BAJO": 2}


# --------------------------------------------------------------------- carga del módulo NASA
def cargar_modulo_nasa(carpeta):
    """Importa process_2.py del compañero para usar su modelo tal cual."""
    ruta = pathlib.Path(carpeta) / "process_2.py"
    if not ruta.exists():
        return None
    spec = importlib.util.spec_from_file_location("nasa_process_2", ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def cargar_respuesta_nasa(carpeta):
    """El JSON crudo de NASA POWER (response_*.json más reciente)."""
    rs = sorted(pathlib.Path(carpeta).glob("response_*.json"), key=lambda p: p.stat().st_mtime)
    return json.loads(rs[-1].read_text(encoding="utf-8")) if rs else None


# --------------------------------------------------------------------- corrección por altura
def sesgo_temperatura(registros, carpeta_datos, alt_nasa, alt_parcela):
    """°C que hay que RESTAR a cada temperatura de NASA para llevarla a la altura de la parcela."""
    teorico = round(GRADIENTE_C_KM * (alt_parcela - alt_nasa) / 1000, 2) if alt_parcela else 0.0
    om = []
    for f in ("clima_historico_diario.csv", "clima_diario.csv"):
        p = pathlib.Path(carpeta_datos) / f
        if p.exists():
            om.append(pd.read_csv(p, index_col="fecha", parse_dates=True))
    sesgo = dict(T2M=teorico, T2M_MIN=teorico, T2M_MAX=teorico)
    metodo, n = f"gradiente {GRADIENTE_C_KM} °C/km", 0
    if om:
        o = pd.concat(om)
        o = o[~o.index.duplicated(keep="last")]
        nasa = pd.DataFrame(registros).set_index("fecha")[["T2M", "T2M_MIN", "T2M_MAX"]]
        j = nasa.join(o[["tmedia", "tmin", "tmax"]], how="inner").dropna()
        if len(j) >= 60:
            n = len(j)
            sesgo = {k: round(float((j[k] - j[v]).mean()), 2)
                     for k, v in (("T2M", "tmedia"), ("T2M_MIN", "tmin"), ("T2M_MAX", "tmax"))}
            metodo = "sesgo medio NASA - Open-Meteo en días comunes"
    return dict(altitud_nasa_msnm=round(alt_nasa), altitud_parcela_msnm=alt_parcela,
                diferencia_m=None if not alt_parcela else round(alt_parcela - alt_nasa),
                correccion_teorica_c=-teorico, correccion_aplicada_c={k: -v for k, v in sesgo.items()},
                metodo=metodo, dias_comparados=n,
                se_usa_en=["estado_helada", "estado_estres_calor", "alerta HELADAS"]), sesgo


def _corregir(registros, sesgo):
    out = []
    for d in registros:
        d = dict(d)
        for k, s in sesgo.items():
            d[k] = d[k] - s
        out.append(d)
    return out


# --------------------------------------------------------------------- NASA alineado a la foto
def nasa_en_fecha(mod, nasa_json, reg, reg_corr, alt_parcela, fecha):
    """Modelo NASA con la ventana de 7 días que termina en `fecha` (YYYY-MM-DD).
    Riego, lancha, sequía y nutrientes: modelo original. Heladas y calor: temperatura corregida."""
    corte = fecha.replace("-", "")
    if not reg or reg[0]["fecha_str"] > corte:
        return None
    orig = mod.procesar_prototipo(nasa_json, reg, fecha_corte=corte)["output"]
    js = copy.deepcopy(nasa_json)
    if alt_parcela:
        js["geometry"]["coordinates"][2] = alt_parcela
    corr = mod.procesar_prototipo(js, reg_corr, fecha_corte=corte)["output"]
    alertas = [a for a in orig["proyeccion_30d"]["alertas_preventivas"] if a["codigo"] != "HELADAS"]
    alertas += [a for a in corr["proyeccion_30d"]["alertas_preventivas"] if a["codigo"] == "HELADAS"]
    return {
        "fecha_inicio": orig["fecha_inicio"], "fecha_fin": orig["fecha_fin"],
        "estado_actual_7d": dict(orig["estado_actual_7d"],
                                 temp_min_semana_parcela=corr["estado_actual_7d"]["temp_min_semana"],
                                 temp_max_semana_parcela=corr["estado_actual_7d"]["temp_max_semana"]),
        "semaforos": {"estado_helada": corr["semaforos"]["estado_helada"],
                      "estado_riego": orig["semaforos"]["estado_riego"],
                      "estado_estres_calor": corr["semaforos"]["estado_estres_calor"]},
        "semaforos_sin_corregir": {k: orig["semaforos"][k]["codigo"] for k in ("estado_helada", "estado_estres_calor")},
        "alertas_preventivas": alertas,
        "mes_proyectado": orig["proyeccion_30d"]["mes"],
    }


# --------------------------------------------------------------------- reglas de cruce
def _cruce(codigo, nivel, confirmada, titulo, mensaje, nasa, s2):
    return dict(codigo=codigo, nivel=nivel, confirmada=confirmada, titulo=titulo, mensaje=mensaje,
                evidencia={"nasa_power": nasa, "sentinel2": s2})


def evaluar_cruces(n, f, prev):
    """n: NASA alineado (nasa_en_fecha) · f: captura Sentinel-2 · prev: captura anterior (o None)."""
    sem = n["semaforos"]
    helada, riego, calor = (sem[k]["codigo"] for k in ("estado_helada", "estado_riego", "estado_estres_calor"))
    alertas = {a["codigo"]: a for a in n["alertas_preventivas"]}
    e7 = n["estado_actual_7d"]

    caida = f.get("caida_ndvi")                     # positivo = el NDVI bajó
    sec = {k: v["caida_ndvi"] for k, v in f["sectores"].items() if v.get("caida_ndvi") is not None}
    peor = max(sec, key=sec.get) if sec else None
    cae_lote = caida is not None and caida >= CAIDA_NDVI
    cae_sector = peor is not None and sec[peor] >= CAIDA_NDVI
    pierde_vigor = cae_lote or cae_sector
    donde = "en todo el lote" if cae_lote else (f"en el sector {peor}" if cae_sector else "")
    d_ndmi = None if prev is None or f["dias_desde_anterior"] is None else round(f["ndmi"] - prev["ndmi"], 4)
    pierde_agua = d_ndmi is not None and d_ndmi <= -CAIDA_NDMI
    vig, hum = f["estado_vigor"], f["estado_humedad"]
    suelo = vig == "gris"
    s2 = dict(fecha=f["fecha"], estado_vigor=vig, estado_humedad=hum, ndvi=f["ndvi"], ndre=f["ndre"],
              ndmi=f["ndmi"], caida_ndvi_lote=caida, caida_ndvi_peor_sector=sec.get(peor) if peor else None,
              peor_sector=peor, cambio_ndmi=d_ndmi)
    c = []

    # 1. Lancha: clima favorable (NASA) + pérdida de vigor (S2)
    if "PLAGAS_LANCHA" in alertas and not suelo:
        nv = dict(alerta="PLAGAS_LANCHA", humedad_relativa_pct=e7["humedad_relativa_pct"])
        if pierde_vigor:
            c.append(_cruce("LANCHA_CONFIRMADA", "ALTO", True, "Alerta Confirmada de Lancha",
                            f"Clima favorable para Lancha y pérdida de vigor {donde} de tu parcela. "
                            "Aplica control preventivo hoy.", nv, s2))
        else:
            c.append(_cruce("LANCHA_PREVENTIVA", alertas["PLAGAS_LANCHA"]["nivel"], False,
                            "Lancha: riesgo climático, sin daño visible aún",
                            "El clima favorece la Lancha, pero el satélite no ve caída de vigor. Mantén el "
                            "control preventivo e inspecciona " +
                            (f"el sector {f['sector_mas_afectado']}, que tiene más zonas en rojo."
                             if f["sector_mas_afectado"] else "las hojas bajas."), nv, s2))

    # 2. Riego / sequía: suelo seco (NASA) + follaje seco (S2)
    seco_nasa = riego == "ROJO_SECO" or "SEQUIA" in alertas
    seco_s2 = hum == "rojo" or pierde_agua
    nv = dict(estado_riego=riego, humedad_raiz_pct=e7["humedad_raiz_pct"], lluvia_7d=e7["lluvia_7d"],
              alerta_sequia="SEQUIA" in alertas)
    if not suelo and seco_nasa and seco_s2:
        c.append(_cruce("RIEGO_CONFIRMADO", "ALTO", True, "Alerta Confirmada de Riego",
                        "Déficit hídrico en la zona y el follaje de la parcela está perdiendo agua. "
                        "Activa riego esta semana.", nv, s2))
    elif not suelo and seco_nasa:
        c.append(_cruce("RIEGO_PREVENTIVO", "MEDIO", False, "Suelo secándose, la planta aún resiste",
                        "El suelo de la zona se está secando, pero el satélite no ve estrés en el follaje. "
                        "Prepara el riego y haz la prueba del puño a 20 cm.", nv, s2))
    elif not suelo and riego in ("VERDE_OPTIMO", "AZUL_SATURADO") and hum in ("rojo", "amarillo"):
        c.append(_cruce("HUMEDAD_DISCREPANTE", "MEDIO", False, "Clima húmedo, pero la parcela se ve seca",
                        "La humedad regional del suelo es adecuada, pero el satélite ve poca agua en el follaje. "
                        "Revisa el lote en campo: puede ser estrés local, drenaje o poca cobertura del cultivo.",
                        nv, s2))

    # 3. Exceso de agua: suelo saturado (NASA) + encharcamiento o pérdida de vigor (S2)
    if riego == "AZUL_SATURADO":
        if hum == "azul" or pierde_vigor:
            c.append(_cruce("EXCESO_AGUA_CONFIRMADO", "ALTO", True, "Alerta Confirmada de Exceso de Agua",
                            "Suelo saturado en la zona y " + ("agua acumulada en la parcela" if hum == "azul"
                                                              else f"pérdida de vigor {donde}") +
                            ". Riesgo de pudrición de tubérculos: abre los canales de drenaje.", nv, s2))
        else:
            c.append(_cruce("EXCESO_AGUA_PREVENTIVO", "MEDIO", False, "Suelo saturado, sin daño visible",
                            "Las lluvias saturaron el suelo de la zona. Revisa drenajes antes de que afecte "
                            "a los tubérculos.", nv, s2))

    # 4. Heladas (temperatura corregida a la altura de la parcela) + pérdida de vigor
    nv = dict(estado_helada=helada, temp_min_semana_parcela=e7["temp_min_semana_parcela"],
              temp_min_semana_nasa=e7["temp_min_semana"])
    if helada == "ROJO" and not suelo:
        if pierde_vigor:
            c.append(_cruce("DANO_HELADA_CONFIRMADO", "ALTO", True, "Daño por Helada Confirmado",
                            f"Helada en la semana (mínima estimada {e7['temp_min_semana_parcela']} °C en la parcela) "
                            f"y pérdida de vigor {donde}. Revisa quemaduras en las hojas superiores.", nv, s2))
        else:
            c.append(_cruce("HELADA_SIN_DANO", "MEDIO", False, "Helada sin daño visible",
                            f"Mínima estimada de {e7['temp_min_semana_parcela']} °C en la parcela, pero el "
                            "satélite no ve pérdida de vigor. Mantén el suelo húmedo para retener calor.", nv, s2))

    # 5. Calor: racha de calor (corregida) + follaje perdiendo agua
    if calor == "ROJO" and pierde_agua:
        c.append(_cruce("ESTRES_CALOR_CONFIRMADO", "ALTO", True, "Estrés por Calor Confirmado",
                        "Racha de días calurosos y el follaje está perdiendo agua. Riega temprano en la mañana.",
                        dict(estado_estres_calor=calor, temp_max_semana_parcela=e7["temp_max_semana_parcela"]),
                        s2))

    # 6. Nutrientes: poco vigor (S2) con el clima descartado como causa (NASA)
    if vig == "amarillo":
        clima_ok = helada != "ROJO" and calor == "VERDE" and riego in ("VERDE_OPTIMO", "AMARILLO_VIGILAR")
        lavado = "NUTRIENTES" in alertas
        nv = dict(estado_helada=helada, estado_riego=riego, estado_estres_calor=calor, alerta_lavado=lavado)
        if clima_ok or lavado:
            c.append(_cruce("NUTRICION_PROBABLE", "MEDIO", True, "Déficit de Nutrientes Probable",
                            ("Lluvias fuertes pueden haber lavado el nitrógeno y el satélite ve poca clorofila. "
                             if lavado else
                             "El clima no explica la falta de vigor (sin helada, calor ni falta de agua). ") +
                            "Evalúa una fertilización foliar fraccionada.", nv, s2))
        else:
            c.append(_cruce("VIGOR_BAJO_POR_CLIMA", "BAJO", False, "Vigor bajo, posiblemente por el clima",
                            "El satélite ve poco vigor, pero coincide con " +
                            ("heladas" if helada == "ROJO" else "calor" if calor != "VERDE" else "falta de agua") +
                            ". Espera la próxima imagen antes de fertilizar.", nv, s2))

    c.sort(key=lambda x: (not x["confirmada"], NIVEL.get(x["nivel"], 9)))
    return c


# --------------------------------------------------------------------- integración
def integrar(s2_resultado, s2_completo, nasa_resultado, carpeta_nasa, carpeta_datos, alt_parcela):
    """Arma resultado_integrado.json. Devuelve None si no está el módulo NASA."""
    mod = cargar_modulo_nasa(carpeta_nasa)
    crudo = cargar_respuesta_nasa(carpeta_nasa)
    if mod is None or crudo is None:
        return None
    reg = mod.limpiar_datos_nasa(crudo)
    alt_nasa = float(crudo["geometry"]["coordinates"][2])
    alineacion, sesgo = sesgo_temperatura(reg, carpeta_datos, alt_nasa, alt_parcela)
    reg_corr = _corregir(reg, sesgo)

    historial, prev = [], None
    for f in s2_completo["fechas"]:
        n = nasa_en_fecha(mod, crudo, reg, reg_corr, alt_parcela, f["fecha"])
        if n is not None:
            cr = evaluar_cruces(n, f, prev)
            historial.append(dict(
                fecha_captura=f["fecha"], ventana_nasa=[n["fecha_inicio"], n["fecha_fin"]],
                nasa={k: v["codigo"] for k, v in n["semaforos"].items()},
                alertas_nasa=[a["codigo"] for a in n["alertas_preventivas"]],
                sentinel2=dict(vigor=f["estado_vigor"], humedad=f["estado_humedad"], ndvi=f["ndvi"],
                               caida_ndvi=f["caida_ndvi"]),
                cruces=[x["codigo"] for x in cr],
                alerta_confirmada=next((x["codigo"] for x in cr if x["confirmada"]), None),
                _nasa=n, _cruces=cr))
        prev = f

    ult = historial[-1] if historial else None
    fin_nasa = reg[-1]["fecha"].date() if reg else None
    desfase = None if not (ult and fin_nasa) else (fin_nasa - date.fromisoformat(ult["fecha_captura"])).days
    alineacion.update(criterio_fecha="ventana NASA de 7 días que termina el día de cada foto Sentinel-2",
                      ultimo_dato_nasa=fin_nasa.isoformat() if fin_nasa else None,
                      dias_entre_ultima_foto_y_ultimo_dato_nasa=desfase)

    o = s2_resultado["output"]
    out = {
        "input": {"nasa_power": nasa_resultado["input"] if nasa_resultado else None,
                  "sentinel2": s2_resultado["input"], "alineacion": alineacion},
        "output": {
            "zona": o["zona"],
            "altitud_parcela_msnm": alt_parcela,
            "clima_regional_nasa_power": nasa_resultado["output"] if nasa_resultado else None,
            "parcela_sentinel2": o,
            "cruce_ultima_captura": None if not ult else {
                "fecha_captura": ult["fecha_captura"],
                "clima_nasa_alineado": ult["_nasa"],
                "cruces_evaluados": ult["_cruces"],
            },
            "alerta_cruzada_confirmada": next((x for x in ult["_cruces"] if x["confirmada"]), None) if ult else None,
            "cruces_evaluados": ult["_cruces"] if ult else [],
            "proyeccion_vigente_nasa": None if not nasa_resultado else dict(
                nasa_resultado["output"]["proyeccion_30d"], fecha_corte=nasa_resultado["output"]["fecha_fin"],
                nota=f"Clima de la semana más reciente; la última foto limpia es {desfase} días anterior."
                if desfase else None),
            "historial_cruces": [{k: v for k, v in h.items() if not k.startswith("_")} for h in historial],
        },
    }
    return out


# --------------------------------------------------------------------- main
HERE = pathlib.Path(__file__).resolve().parent
DATA_DIR = HERE / "data"  # copia de los datos de remote-sensing/ (ver backend/README.md)
NASA_DIR = DATA_DIR / "nasa-power"
S2_DIR = DATA_DIR / "sentinel_2"
S2_DATOS = S2_DIR / "datos_sentinel"
SALIDA = DATA_DIR / "resultado_match.json"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    leer = lambda p: json.loads(p.read_text(encoding="utf-8")) if p.exists() else None  # noqa: E731
    nasa = leer(NASA_DIR / "resultado_prototipo.json")
    s2 = leer(S2_DIR / "resultado_prototipo_sentinel_2.json")
    s2_full = leer(S2_DATOS / "salida_s2" / "sentinel2_parcela.json")
    parcela = leer(S2_DATOS / "datos" / "parcela.json") or {}
    if s2 is None or s2_full is None:
        sys.exit("Faltan los datos de Sentinel-2: corre  python sentinel_2/preprocesar.py")
    alt = parcela.get("altitud_msnm")
    if alt is None:
        print("Aviso: parcela.json no tiene altitud_msnm; las temperaturas de NASA no se corrigen por altura.")

    out = integrar(s2, s2_full, nasa, NASA_DIR, S2_DATOS / "datos", alt)
    if out is None:
        sys.exit("Faltan los datos de NASA POWER: nasa-power/process_2.py y nasa-power/response_*.json")
    SALIDA.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    al = out["input"]["alineacion"]
    print(f"Altura: NASA {al['altitud_nasa_msnm']} m, parcela {al['altitud_parcela_msnm']} m -> "
          f"temperaturas corregidas {al['correccion_aplicada_c']} °C ({al['metodo']}, {al['dias_comparados']} días)")
    print(f"Fechas: NASA alineado a cada foto; último dato NASA {al['ultimo_dato_nasa']}, "
          f"{al['dias_entre_ultima_foto_y_ultimo_dato_nasa']} días después de la última foto")
    print("\nCaptura     Vigor     Humedad     NASA (helada/riego/calor)        Cruces")
    for h in out["output"]["historial_cruces"]:
        n = h["nasa"]
        nasa_txt = f"{n['estado_helada']}/{n['estado_riego']}/{n['estado_estres_calor']}"
        print(f"{h['fecha_captura']}  {h['sentinel2']['vigor']:9s} {h['sentinel2']['humedad']:11s} {nasa_txt:32s} "
              f"{', '.join(h['cruces']) or '-'}")
    c = out["output"]["alerta_cruzada_confirmada"]
    print(f"\nÚltima captura: {'CONFIRMADA ' + c['codigo'] + ' - ' + c['titulo'] if c else 'sin alerta confirmada'}")
    for x in out["output"]["cruces_evaluados"]:
        print(f"  [{x['nivel']}] {x['codigo']}: {x['mensaje']}")
    print(f"\nGuardado: {SALIDA.name}")


if __name__ == "__main__":
    main()
