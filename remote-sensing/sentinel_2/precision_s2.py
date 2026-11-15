"""Ojo de precisión Sentinel-2 (10 m) dentro del polígono exacto de la parcela.

Criterios acordados con el equipo:
  - Sentinel-2 L2A, últimos 6 meses, nubosidad < 20 % SOBRE EL POLÍGONO (máscara SCL)
  - 1 imagen limpia cada 15 días (la más despejada de cada ventana)
  - NDVI = (B08-B04)/(B08+B04) · NDRE = (B08-B05)/(B08+B05) · NDMI = (B08-B11)/(B08+B11)
  - Cada fecha se compara con la imagen limpia anterior (~15 días antes)
  - Reglas A (vigor y plagas: NDVI + NDRE) y B (humedad: NDMI), píxel a píxel y para el promedio

Usa los recortes que deja monitoreo.py en imagenes/tif/ (no descarga nada).
Salida: salida_s2/sentinel2_parcela.json (+ .csv), PNG coloreados para pintar sobre el mapa
y GeoTIFF con índices y estados.

    python precision_s2.py        # o se llama solo desde monitoreo.py
"""
import importlib.util
import json
import math
import os
import pathlib
from datetime import date, datetime


def _arreglar_proj():
    for pkg, sub in (("rasterio", "proj_data"), ("pyproj", "proj_dir/share/proj")):
        spec = importlib.util.find_spec(pkg)
        if spec:
            p = pathlib.Path(spec.origin).parent / sub
            if (p / "proj.db").exists():
                os.environ["PROJ_LIB"] = os.environ["PROJ_DATA"] = str(p)
                return


_arreglar_proj()

import geopandas as gpd  # noqa: E402
import matplotlib  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import rasterio  # noqa: E402
from PIL import Image  # noqa: E402
from rasterio.features import geometry_mask  # noqa: E402
from rasterio.warp import transform_bounds, transform_geom  # noqa: E402
from shapely.geometry import mapping, shape  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "datos_sentinel"
TIF_IN = DATA / "imagenes" / "tif"
SAL = DATA / "salida_s2"
SAL_PNG = SAL / "png"
SAL_TIF = SAL / "tif"

# ------------------------------------------------------------------ criterios
MAX_NUBE_POLIGONO = 0.20   # < 20 % de nubes/sombras/sin dato dentro del polígono
VENTANA_DIAS = 15          # objetivo: 1 imagen limpia cada 15 días
MIN_SEPARACION = 12        # días mínimos entre imágenes elegidas (tolerancia por el paso de ~5 días)
MAX_DIAS_COMPARACION = 35  # si la imagen anterior es más vieja, no se evalúa "caída"
SCL_VALIDAS = [4, 5, 6]
NDMI_SOLO_CON_CULTIVO = True  # con NDVI < 0.25 (suelo desnudo) el NDMI no indica estrés de la planta
ESCALA_PNG = 10            # cada píxel de 10 m se dibuja como 10x10 px (bordes nítidos en el mapa)

# orden de bandas en los recortes de monitoreo.py
B = {"B02": 0, "B03": 1, "B04": 2, "B05": 3, "B06": 4, "B07": 5, "B08": 6, "B8A": 7, "B11": 8, "B12": 9, "SCL": 10}

# ------------------------------------------------------------------ regla A: vigor / plagas
U_A = dict(ndvi_gris=0.25, ndvi_verde=0.60, caida_verde=0.08, ndvi_amarillo_min=0.35,
           ndre_amarillo=0.35, caida_rojo=0.12, ndvi_rojo=0.35)
VIGOR = {  # código: (estado, color RGB, mensaje)
    1: ("gris", (160, 160, 160), "Suelo desnudo, emergencia inicial o parcela recién cosechada."),
    2: ("verde", (26, 152, 80), "Cultivo vigoroso y sano. Cobertura foliar óptima en desarrollo."),
    3: ("amarillo", (250, 200, 30), "Baja concentración de clorofila. Posible falta de nitrógeno o crecimiento "
                                    "lento; revisa fertilización."),
    4: ("rojo", (215, 48, 39), "Alerta de estrés severo o ataque de plagas/lancha en focos específicos. "
                               "Inspecciona las zonas rojas del mapa."),
}
# ------------------------------------------------------------------ regla B: humedad
U_B = dict(rojo=0.0, amarillo=0.20, verde=0.45)
HUMEDAD = {
    1: ("no aplica", (160, 160, 160), "Suelo desnudo: el NDMI no refleja el agua del cultivo."),
    2: ("rojo", (215, 48, 39), "Estrés hídrico detectado en las hojas de la parcela. El cultivo está perdiendo "
                               "turgencia; activa riego."),
    3: ("amarillo", (250, 200, 30), "Humedad interna moderada-baja. Vigila los sectores amarillos del lote."),
    4: ("verde", (26, 152, 80), "Buen contenido de agua en el cultivo y superficie."),
    5: ("azul", (44, 123, 182), "Saturación alta de agua en superficie. Riesgo de pudrición en surcos bajos."),
}


def clasificar_vigor(ndvi, ndre, caida):
    """caida = NDVI_anterior - NDVI (positivo = bajó). NaN si no hay imagen anterior comparable.
    Prioridad: gris > rojo > amarillo > verde. El hueco de la tabla (NDVI >= 0.60 con caída
    entre 0.08 y 0.12 y NDRE >= 0.35) cae en amarillo."""
    ndvi, ndre, caida = (np.asarray(x, dtype="float64") for x in (ndvi, ndre, caida))
    c = np.nan_to_num(caida, nan=0.0)
    return np.select(
        [~np.isfinite(ndvi),
         ndvi < U_A["ndvi_gris"],
         (c >= U_A["caida_rojo"]) | (ndvi < U_A["ndvi_rojo"]),
         (ndvi < U_A["ndvi_verde"]) | (ndre < U_A["ndre_amarillo"]),
         (ndvi >= U_A["ndvi_verde"]) & (c < U_A["caida_verde"])],
        [0, 1, 4, 3, 2], default=3).astype("uint8")


def clasificar_humedad(ndmi, ndvi):
    ndmi, ndvi = np.asarray(ndmi, dtype="float64"), np.asarray(ndvi, dtype="float64")
    sin_cultivo = (ndvi < U_A["ndvi_gris"]) if NDMI_SOLO_CON_CULTIVO else np.zeros(ndmi.shape, bool)
    return np.select(
        [~np.isfinite(ndmi), sin_cultivo, ndmi < U_B["rojo"], ndmi <= U_B["amarillo"], ndmi <= U_B["verde"]],
        [0, 1, 2, 3, 4], default=5).astype("uint8")


# ------------------------------------------------------------------ utilidades
def _png_clases(codigos, tabla, mascara, ruta):
    h, w = codigos.shape
    rgba = np.zeros((h, w, 4), "uint8")
    for k, (_, col, _) in tabla.items():
        rgba[codigos == k] = (*col, 230)
    rgba[mascara & (codigos == 0)] = (90, 90, 90, 140)  # nube dentro de la parcela
    rgba[~mascara] = 0
    _guardar(rgba, ruta)


from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

# colores pedidos por el equipo: NDVI rojo -> amarillo -> verde; NDMI naranja -> celeste -> azul
CMAPS = {
    "ndvi": LinearSegmentedColormap.from_list("ndvi", ["#d73027", "#fee08b", "#1a9850"]),
    "ndmi": LinearSegmentedColormap.from_list("ndmi", ["#f46d43", "#9ecae1", "#08519c"]),
}
COD_VIGOR = {"gris": "GRIS_SUELO", "verde": "VERDE_VIGOROSO", "amarillo": "AMARILLO_NUTRICION",
             "rojo": "ROJO_ESTRES_SEVERO"}
COD_HUMEDAD = {"rojo": "ROJO_ESTRES_HIDRICO", "amarillo": "AMARILLO_BAJA", "verde": "VERDE_OPTIMA",
               "azul": "AZUL_EXCESO", "no aplica": "GRIS_NO_APLICA"}


def _png_continuo(arr, cmap, vmin, vmax, mascara, ruta):
    norm = np.clip((arr - vmin) / (vmax - vmin), 0, 1)
    cm = CMAPS.get(cmap) or matplotlib.colormaps[cmap]
    rgba = (cm(np.nan_to_num(norm)) * 255).astype("uint8")
    rgba[..., 3] = 230
    rgba[mascara & ~np.isfinite(arr)] = (90, 90, 90, 140)
    rgba[~mascara] = 0
    _guardar(rgba, ruta)


def _guardar(rgba, ruta):
    big = np.kron(rgba, np.ones((ESCALA_PNG, ESCALA_PNG, 1), "uint8"))
    Image.fromarray(big).save(ruta, optimize=True)


def _pct(codigos, tabla, n):
    return {tabla[k][0]: round(100 * float((codigos == k).sum()) / n, 1) for k in tabla} | \
        {"sin dato": round(100 * float((codigos == 0).sum()) / n, 1)}


def _r(x, nd=4):
    return None if x is None or not np.isfinite(x) else round(float(x), nd)


# ------------------------------------------------------------------ principal
def procesar(parcela_path=None, verbose=True):
    parcela_path = pathlib.Path(parcela_path or DATA / "papas_parcela.geojson")
    g = gpd.read_file(parcela_path).to_crs(4326)
    geom = g[g.geom_type.isin(["Polygon", "MultiPolygon"])].union_all()
    for d in (SAL_PNG, SAL_TIF):
        d.mkdir(parents=True, exist_ok=True)

    # ---------------- 1. candidatas: nubosidad < 20 % sobre el polígono
    cand = []
    for f in sorted(TIF_IN.glob("S2_*.tif")):
        with rasterio.open(f) as s:
            a = s.read()
            crs, tr = s.crs, s.transform
            escena = s.tags().get("escena", f.stem)
        g_utm = transform_geom("EPSG:4326", crs, mapping(geom))
        dentro = geometry_mask([g_utm], a.shape[1:], tr, invert=True)
        n = int(dentro.sum())
        bandas_ok = np.all(np.isfinite(a[:10]) & (a[:10] > 0), axis=0)
        valida = dentro & np.isin(a[B["SCL"]], SCL_VALIDAS) & bandas_ok
        nube = 1 - valida.sum() / n
        azul = float(np.nanmedian(a[B["B02"]][valida])) if valida.any() else 9
        fecha = datetime.strptime(f.stem.split("_")[1], "%Y%m%d").date()
        cand.append(dict(fecha=fecha, archivo=f, escena=escena, nube=nube, azul=azul, n=n))
    cand = pd.DataFrame(cand)
    # bruma que la SCL no marca (azul alto) tampoco cuenta como limpia
    limpias = cand[(cand["nube"] < MAX_NUBE_POLIGONO) & (cand["azul"] <= 0.12)].copy()
    if verbose:
        print(f"Precisión S2: {len(cand)} recortes, {len(limpias)} con < {MAX_NUBE_POLIGONO:.0%} de nubes en el polígono")
    if limpias.empty:
        return None

    # ---------------- 2. ~1 imagen cada 15 días: desde la más reciente hacia atrás, separadas al menos
    # MIN_SEPARACION días (Sentinel-2 pasa cada ~5 días, así que la separación real queda en 12-20 días).
    # Así la última captura limpia siempre entra y cada fecha se compara con una de ~15 días antes.
    limpias = limpias.sort_values(["fecha", "nube", "azul"]).drop_duplicates("fecha")
    elegidas, ultima = [], None
    for _, r in limpias.sort_values("fecha", ascending=False).iterrows():
        if ultima is None or (ultima - r["fecha"]).days >= MIN_SEPARACION:
            elegidas.append(r)
            ultima = r["fecha"]
    sel = pd.DataFrame(elegidas).sort_values("fecha").reset_index(drop=True)
    if verbose:
        print(f"  seleccionadas {len(sel)} fechas (~1 cada {VENTANA_DIAS} días): "
              + ", ".join(f"{d:%d/%m}" for d in sel["fecha"]))

    # ---------------- 3. índices, reglas y sectores por fecha
    fechas, prev = [], None
    for _, r in sel.iterrows():
        with rasterio.open(r["archivo"]) as s:
            a = s.read().astype("float64")
            crs, tr, prof = s.crs, s.transform, s.profile
            bounds = s.bounds
        g_utm = transform_geom("EPSG:4326", crs, mapping(geom))
        dentro = geometry_mask([g_utm], a.shape[1:], tr, invert=True)               # estadística: centro del píxel
        dibujo = geometry_mask([g_utm], a.shape[1:], tr, invert=True, all_touched=True)  # mapa: cubre el borde
        ok = np.isin(a[B["SCL"]], SCL_VALIDAS) & np.all(np.isfinite(a[:10]) & (a[:10] > 0), axis=0)
        b04, b05, b08, b11 = a[B["B04"]], a[B["B05"]], a[B["B08"]], a[B["B11"]]
        with np.errstate(divide="ignore", invalid="ignore"):
            ndvi = np.where(ok, (b08 - b04) / (b08 + b04), np.nan)
            ndre = np.where(ok, (b08 - b05) / (b08 + b05), np.nan)
            ndmi = np.where(ok, (b08 - b11) / (b08 + b11), np.nan)

        dias_prev = (r["fecha"] - prev["fecha"]).days if prev is not None else None
        comparable = prev is not None and dias_prev <= MAX_DIAS_COMPARACION
        caida_px = (prev["ndvi"] - ndvi) if comparable else np.full(ndvi.shape, np.nan)

        vig_px = clasificar_vigor(ndvi, ndre, caida_px)
        hum_px = clasificar_humedad(ndmi, ndvi)
        vig_px[~dentro & ~dibujo] = 0
        n = int(dentro.sum())

        m = {k: float(np.nanmean(v[dentro])) for k, v in (("ndvi", ndvi), ("ndre", ndre), ("ndmi", ndmi))}
        caida = (prev["m"]["ndvi"] - m["ndvi"]) if comparable else float("nan")
        vig = int(clasificar_vigor(m["ndvi"], m["ndre"], caida))
        hum = int(clasificar_humedad(m["ndmi"], m["ndvi"]))
        pv = _pct(vig_px[dentro], VIGOR, n)
        ph = _pct(hum_px[dentro], HUMEDAD, n)

        # sectores respecto al centro de la parcela (N/S/E/O según el eje dominante)
        rows, cols = np.nonzero(dentro)
        xs, ys = rasterio.transform.xy(tr, rows, cols)
        cx, cy = shape(g_utm).centroid.x, shape(g_utm).centroid.y
        dx, dy = np.asarray(xs) - cx, np.asarray(ys) - cy
        sect = np.where(np.abs(dy) >= np.abs(dx), np.where(dy >= 0, "norte", "sur"),
                        np.where(dx >= 0, "este", "oeste"))
        sectores = {}
        for s_ in ("norte", "sur", "este", "oeste"):
            k = sect == s_
            if k.sum() == 0:
                continue
            v = vig_px[rows[k], cols[k]]
            cd = caida_px[rows[k], cols[k]]
            sectores[s_] = dict(pixeles=int(k.sum()),
                                pct_rojo=round(100 * float((v == 4).sum()) / k.sum(), 1),
                                pct_estres=round(100 * float(np.isin(v, [3, 4]).sum()) / k.sum(), 1),
                                ndvi=_r(np.nanmean(ndvi[rows[k], cols[k]])),
                                caida_ndvi=_r(np.nanmean(cd)) if comparable else None)
        peor = max(sectores, key=lambda s_: (sectores[s_]["pct_rojo"], sectores[s_]["caida_ndvi"] or -9))
        hay_rojo = sectores[peor]["pct_rojo"] > 0

        # ---------------- salidas visuales
        tag = f"{r['fecha']:%Y%m%d}"
        imgs = {}
        for nombre, fn in (
            ("vigor", lambda p: _png_clases(vig_px, VIGOR, dibujo, p)),
            ("humedad", lambda p: _png_clases(hum_px, HUMEDAD, dibujo, p)),
            ("ndvi", lambda p: _png_continuo(ndvi, "ndvi", 0.0, 0.9, dibujo, p)),
            ("ndre", lambda p: _png_continuo(ndre, "YlGn", 0.0, 0.6, dibujo, p)),
            ("ndmi", lambda p: _png_continuo(ndmi, "ndmi", -0.3, 0.6, dibujo, p)),
        ):
            pref = f"recorte_{nombre}" if nombre in ("ndvi", "ndmi") else nombre
            p = SAL_PNG / f"{pref}_{tag}.png"
            fn(p)
            imgs[nombre] = p.relative_to(DATA).as_posix()
        rgb = np.dstack([a[B["B04"]], a[B["B03"]], a[B["B02"]]])
        rgb = (np.clip(np.nan_to_num(rgb) / 0.25, 0, 1) ** 0.8 * 255).astype("uint8")
        p = SAL_PNG / f"rgb_{tag}.png"
        _guardar(np.dstack([rgb, np.full(rgb.shape[:2], 255, "uint8")]), p)
        imgs["rgb"] = p.relative_to(DATA).as_posix()

        prof.update(count=5, dtype="float32", nodata=np.nan)
        p = SAL_TIF / f"s2_{tag}_indices.tif"
        with rasterio.open(p, "w", **prof) as dst:
            for i, (k, v) in enumerate((("NDVI", ndvi), ("NDRE", ndre), ("NDMI", ndmi),
                                        ("estado_vigor (1 gris 2 verde 3 amarillo 4 rojo)", vig_px),
                                        ("estado_humedad (1 n/a 2 rojo 3 amarillo 4 verde 5 azul)", hum_px)), 1):
                dst.write(np.where(dibujo, v, np.nan).astype("float32"), i)
                dst.set_band_description(i, k)
        imgs["tif"] = p.relative_to(DATA).as_posix()
        s_, w_, n_, e_ = (transform_bounds(crs, "EPSG:4326", *bounds)[i] for i in (1, 0, 3, 2))

        fechas.append(dict(
            fecha=r["fecha"].isoformat(), escena=r["escena"],
            nubosidad_poligono_pct=round(100 * r["nube"], 1), pixeles_parcela=n,
            fecha_anterior=prev["fecha"].isoformat() if prev is not None else None,
            dias_desde_anterior=dias_prev,
            ndvi=_r(m["ndvi"]), ndre=_r(m["ndre"]), ndmi=_r(m["ndmi"]),
            caida_ndvi=_r(caida),
            estado_vigor=VIGOR[vig][0], mensaje_vigor=VIGOR[vig][2],
            estado_humedad=HUMEDAD[hum][0], mensaje_humedad=HUMEDAD[hum][2],
            pct_area_vigor=pv, pct_area_humedad=ph,
            pct_area_sana=pv["verde"], pct_area_estres=round(pv["amarillo"] + pv["rojo"], 1),
            sectores=sectores, sector_mas_afectado=peor if hay_rojo else None,
            imagenes=imgs, bounds_latlon=[[s_, w_], [n_, e_]],
        ))
        prev = dict(fecha=r["fecha"], ndvi=ndvi, m=m)

    hoy = date.today()
    ult = fechas[-1]
    salida = dict(
        generado=datetime.now().isoformat(timespec="seconds"),
        parcela=dict(archivo=parcela_path.name, centro=[round(geom.centroid.y, 6), round(geom.centroid.x, 6)]),
        criterios=dict(coleccion="sentinel-2-l2a (Earth Search / AWS)", max_nubosidad_poligono=MAX_NUBE_POLIGONO,
                       ventana_dias=VENTANA_DIAS, separacion_minima_dias=MIN_SEPARACION, ndvi="(B08-B04)/(B08+B04)", ndre="(B08-B05)/(B08+B05)",
                       ndmi="(B08-B11)/(B08+B11)", umbrales_vigor=U_A, umbrales_humedad=U_B,
                       ndmi_solo_con_cultivo=NDMI_SOLO_CON_CULTIVO),
        ultima=dict(fecha=ult["fecha"], dias_desde_hoy=(hoy - date.fromisoformat(ult["fecha"])).days,
                    estado_vigor=ult["estado_vigor"], mensaje_vigor=ult["mensaje_vigor"],
                    estado_humedad=ult["estado_humedad"], mensaje_humedad=ult["mensaje_humedad"],
                    pct_area_sana=ult["pct_area_sana"], pct_area_estres=ult["pct_area_estres"],
                    caida_ndvi=ult["caida_ndvi"], sector_mas_afectado=ult["sector_mas_afectado"]),
        fechas=fechas,
    )
    (SAL / "sentinel2_parcela.json").write_text(json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8")
    exportar_contrato(salida)
    exportar_resultado(salida, g, dict(recortes=len(cand), limpias=len(limpias)))
    plano = pd.json_normalize(fechas, sep="_").drop(columns=[c for c in pd.json_normalize(fechas, sep="_").columns
                                                            if c.startswith(("imagenes", "sectores", "bounds"))])
    plano.to_csv(SAL / "sentinel2_parcela.csv", index=False, encoding="utf-8-sig")
    if verbose:
        print(f"  última limpia {ult['fecha']} (hace {salida['ultima']['dias_desde_hoy']} días): "
              f"vigor {ult['estado_vigor']}, humedad {ult['estado_humedad']}, "
              f"{ult['pct_area_sana']}% sana / {ult['pct_area_estres']}% con estrés")
    return salida


def exportar_contrato(s):
    """JSON con los nombres exactos del contrato del equipo (secciones A, B y C).
    Las rutas de imagen son relativas a la carpeta del JSON (salida_s2/)."""
    def rel(p):
        return (DATA / p).relative_to(SAL).as_posix()

    def capa(f):
        return dict(recorte_ndvi_png=rel(f["imagenes"]["ndvi"]), recorte_ndmi_png=rel(f["imagenes"]["ndmi"]),
                    bounds_latlon=f["bounds_latlon"])

    u = s["fechas"][-1]
    pv = u["pct_area_vigor"]
    out = {
        "modulo": "sentinel2_parcela_10m",
        "generado": s["generado"],
        "parcela": {"centro_lat_lon": s["parcela"]["centro"], "archivo": s["parcela"]["archivo"]},
        "A_capas_visuales": dict(
            fecha_captura=u["fecha"], **capa(u),
            nota="PNG RGBA transparente fuera del polígono. bounds_latlon = [[sur, oeste], [norte, este]] en "
                 "EPSG:4326, listo para L.imageOverlay / folium.ImageOverlay. NDVI: rojo->amarillo->verde "
                 "(0 a 0.9). NDMI: naranja->celeste->azul (-0.3 a 0.6).",
        ),
        "B_serie_fenologica": [
            dict(fecha_captura=f["fecha"], ndvi_promedio=f["ndvi"], ndre_promedio=f["ndre"],
                 ndmi_promedio=f["ndmi"], **capa(f))
            for f in s["fechas"]
        ],
        "C_diagnostico_ultima_captura": dict(
            fecha_captura=u["fecha"],
            dias_desde_ultima_foto=s["ultima"]["dias_desde_hoy"],
            variacion_ndvi_15d=None if u["caida_ndvi"] is None else round(-u["caida_ndvi"], 4),
            fecha_comparacion=u["fecha_anterior"], dias_entre_fotos=u["dias_desde_anterior"],
            estado_vigor_lote=COD_VIGOR[u["estado_vigor"]],
            estado_humedad_lote=COD_HUMEDAD[u["estado_humedad"]],
            mensaje_vigor=u["mensaje_vigor"], mensaje_humedad=u["mensaje_humedad"],
            distribucion_parcela_pct=dict(sano=pv["verde"], alerta=pv["amarillo"], critico=pv["rojo"],
                                          suelo_desnudo=pv["gris"], sin_dato=pv["sin dato"]),
            sector_mas_afectado=u["sector_mas_afectado"],
        ),
    }
    (SAL / "entregable_sentinel2.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


ESTADO_VIGOR_TXT = {"gris": "INICIO/COSECHA - Suelo desnudo", "verde": "ÓPTIMO - Vigor alto",
                    "amarillo": "ALERTA - Nutrición", "rojo": "CRÍTICO - Estrés severo / plaga"}
ESTADO_HUM_TXT = {"rojo": "CRÍTICO - Estrés hídrico", "amarillo": "ALERTA - Humedad baja",
                  "verde": "ÓPTIMO - Humedad ideal", "azul": "EXCESO - Encharcamiento",
                  "no aplica": "NO APLICA - Suelo desnudo"}
NASA_JSON = HERE.parent / "nasa-power" / "resultado_prototipo.json"  # resultado del módulo NASA POWER (opcional)
RESULTADO_JSON = HERE / "resultado_prototipo_sentinel_2.json"  # misma forma input/output que el de nasa-power
INTEGRADO_JSON = HERE / "resultado_integrado.json"


def exportar_resultado(s, parcela_gdf, conteo):
    """resultado_sentinel2.json con la misma forma input/output que resultado_prototipo.json (NASA POWER).
    Si ese archivo existe, también escribe resultado_integrado.json con la alerta cruzada."""
    nasa = json.loads(NASA_JSON.read_text(encoding="utf-8")) if NASA_JSON.exists() else None
    zona = nasa["input"]["ubicacion"]["zona"] if nasa else "Toacaso / Sigchos"
    meta = DATA / "datos" / "parcela.json"
    per = json.loads(meta.read_text(encoding="utf-8")) if meta.exists() else {}
    pol = parcela_gdf[parcela_gdf.geom_type.isin(["Polygon", "MultiPolygon"])]
    area = float(pol.to_crs(pol.estimate_utm_crs()).area.sum() / 1e4)
    u = s["fechas"][-1]
    pv = u["pct_area_vigor"]
    lat, lon = s["parcela"]["centro"]

    out = {
        "input": {
            "fuente_datos": "Copernicus Sentinel-2 L2A (reflectancia de superficie), Earth Search / AWS",
            "ubicacion": {
                "zona": zona, "longitud": lon, "latitud": lat, "area_ha": round(area, 2),
                "poligono_geojson": json.loads(pol[["geometry"]].to_json()),
            },
            "parametros_ejecucion": {
                "fecha_corte": per.get("fin", date.today().isoformat()),
                "rango_analizado": {"inicio": per.get("inicio"), "fin": per.get("fin")},
                "resolucion_m": 10,
                "bandas": {"NDVI": "B08, B04", "NDRE": "B08, B05", "NDMI": "B08, B11", "mascara_nubes": "SCL"},
                "max_nubosidad_poligono_pct": MAX_NUBE_POLIGONO * 100,
                "frecuencia_objetivo_dias": VENTANA_DIAS,
                "total_recortes_descargados": conteo["recortes"],
                "total_capturas_limpias": conteo["limpias"],
                "total_capturas_seleccionadas": len(s["fechas"]),
            },
            "capturas_evaluadas": [
                {"fecha": f["fecha"], "escena": f["escena"], "nubosidad_poligono_pct": f["nubosidad_poligono_pct"],
                 "pixeles_10m": f["pixeles_parcela"]} for f in s["fechas"]
            ],
        },
        "output": {
            "zona": zona,
            "fecha_ultima_captura": pd.Timestamp(u["fecha"]).strftime("%d/%m/%Y"),
            "dias_desde_ultima_foto": s["ultima"]["dias_desde_hoy"],
            "estado_actual_lote": {
                "ndvi_promedio": u["ndvi"], "ndre_promedio": u["ndre"], "ndmi_promedio": u["ndmi"],
                "variacion_ndvi_15d": None if u["caida_ndvi"] is None else round(-u["caida_ndvi"], 4),
                "fecha_comparacion": u["fecha_anterior"],
                "distribucion_parcela_pct": {"sano": pv["verde"], "alerta": pv["amarillo"], "critico": pv["rojo"],
                                             "suelo_desnudo": pv["gris"], "sin_dato": pv["sin dato"]},
                "sector_mas_afectado": u["sector_mas_afectado"],
            },
            "semaforos": {
                "estado_vigor": {"codigo": COD_VIGOR[u["estado_vigor"]], "color": u["estado_vigor"],
                                 "estado": ESTADO_VIGOR_TXT[u["estado_vigor"]], "mensaje": u["mensaje_vigor"]},
                "estado_humedad_parcela": {"codigo": COD_HUMEDAD[u["estado_humedad"]],
                                           "color": u["estado_humedad"].replace("no aplica", "gris"),
                                           "estado": ESTADO_HUM_TXT[u["estado_humedad"]],
                                           "mensaje": u["mensaje_humedad"]},
            },
            "sectores": u["sectores"],
            "capas_visuales": {"recorte_ndvi_png": f"{DATA.name}/{u['imagenes']['ndvi']}",
                               "recorte_ndmi_png": f"{DATA.name}/{u['imagenes']['ndmi']}",
                               "bounds_latlon": u["bounds_latlon"]},
            "serie_fenologica": [
                {"dia": pd.Timestamp(f["fecha"]).strftime("%d/%m"), "fecha": f["fecha"], "ndvi": f["ndvi"],
                 "ndre": f["ndre"], "ndmi": f["ndmi"],
                 "vigor": COD_VIGOR[f["estado_vigor"]], "humedad": COD_HUMEDAD[f["estado_humedad"]]}
                for f in s["fechas"]
            ],
        },
    }
    RESULTADO_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    if nasa:
        cruzar(nasa, out)
    return out


def cruzar(nasa, s2):
    """Alerta cruzada: clima regional (NASA POWER) + lectura a 10 m de la parcela (Sentinel-2)."""
    o, e = s2["output"], s2["output"]["estado_actual_lote"]
    var = e["variacion_ndvi_15d"]
    sector = e["sector_mas_afectado"]
    sec_caida = {k: v["caida_ndvi"] for k, v in o["sectores"].items() if v.get("caida_ndvi") is not None}
    peor_caida = max(sec_caida, key=sec_caida.get) if sec_caida else None
    cae_lote = var is not None and var <= -0.08
    cae_sector = peor_caida is not None and sec_caida[peor_caida] >= 0.08
    alertas = nasa["output"].get("proyeccion_30d", {}).get("alertas_preventivas", [])
    lancha = next((a for a in alertas if a["codigo"] == "PLAGAS_LANCHA" and a["nivel"] in ("ALTO", "MEDIO")), None)
    riego = nasa["output"]["semaforos"].get("estado_riego", {})
    hum_s2 = o["semaforos"]["estado_humedad_parcela"]["codigo"]

    cruces = []
    if lancha:
        if cae_lote or cae_sector:
            donde = f"en el sector {peor_caida}" if cae_sector else "en todo el lote"
            cruces.append(dict(codigo="LANCHA_CONFIRMADA", nivel="ALTO", confirmada=True,
                               titulo="Alerta Confirmada de Lancha",
                               mensaje=f"Condiciones climáticas favorables para Lancha y pérdida de vigor detectada "
                                       f"{donde} de tu parcela. Aplica control preventivo hoy."))
        else:
            cruces.append(dict(codigo="LANCHA_PREVENTIVA", nivel=lancha["nivel"], confirmada=False,
                               titulo="Lancha: riesgo climático, sin daño visible aún",
                               mensaje="El clima favorece la Lancha, pero el satélite no detecta caída de vigor "
                                       "en la parcela. Mantén el control preventivo e inspecciona"
                                       + (f" el sector {sector}, que tiene más zonas en rojo." if sector else
                                          " las hojas bajas.")))
    if riego and hum_s2 in ("ROJO_ESTRES_HIDRICO", "AMARILLO_BAJA") and riego.get("codigo", "").startswith("VERDE"):
        cruces.append(dict(codigo="HUMEDAD_DISCREPANTE", nivel="MEDIO", confirmada=False,
                           titulo="Clima húmedo, pero la parcela se ve seca",
                           mensaje="La humedad regional del suelo es adecuada, pero el satélite ve poca agua en el "
                                   "follaje de la parcela. Revisa el lote en campo: puede ser estrés local, "
                                   "drenaje o poca cobertura del cultivo."))
    elif riego and hum_s2 == "ROJO_ESTRES_HIDRICO" and not riego.get("codigo", "").startswith("VERDE"):
        cruces.append(dict(codigo="RIEGO_CONFIRMADO", nivel="ALTO", confirmada=True,
                           titulo="Alerta Confirmada de Riego",
                           mensaje="Déficit hídrico en la región y estrés hídrico visible en la parcela. "
                                   "Activa riego esta semana."))

    integrado = {
        "input": {"nasa_power": nasa["input"], "sentinel2": s2["input"]},
        "output": {
            "zona": o["zona"],
            "clima_regional_nasa_power": nasa["output"],
            "parcela_sentinel2": o,
            "alerta_cruzada_confirmada": next((c for c in cruces if c["confirmada"]), None),
            "cruces_evaluados": cruces,
        },
    }
    INTEGRADO_JSON.write_text(json.dumps(integrado, ensure_ascii=False, indent=2),
                                                  encoding="utf-8")
    return integrado


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    procesar(sys.argv[1] if len(sys.argv) > 1 else None)
