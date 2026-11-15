"""Monitoreo semanal de una parcela con Sentinel-2 + clima (Open-Meteo).

DESCARGA + PREPROCESADO completo (para solo preprocesar lo ya descargado: python preprocesar.py)

Uso (ambiente ecofolia-frontend):
    python monitoreo.py                       # últimos 6 meses hasta hoy
    python monitoreo.py --inicio 2026-05-01 --fin 2026-11-14
    python monitoreo.py --parcela otra.geojson

Es incremental: las escenas ya procesadas y el clima histórico quedan guardados en datos/,
así que correrlo cada semana solo descarga lo nuevo y regenera los reportes.
"""
import argparse
import importlib.util
import json
import math
import os
import pathlib
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta


def _arreglar_proj():
    # En este Windows PROJ_LIB apunta al PROJ de PostGIS (versión vieja) y rompe rasterio.
    for pkg, sub in (("rasterio", "proj_data"), ("pyproj", "proj_dir/share/proj")):
        spec = importlib.util.find_spec(pkg)
        if spec:
            p = pathlib.Path(spec.origin).parent / sub
            if (p / "proj.db").exists():
                os.environ["PROJ_LIB"] = os.environ["PROJ_DATA"] = str(p)
                return


_arreglar_proj()
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("AWS_NO_SIGN_REQUEST", "YES")
os.environ.setdefault("GDAL_HTTP_MAX_RETRY", "4")
os.environ.setdefault("GDAL_HTTP_RETRY_DELAY", "2")

import geopandas as gpd  # noqa: E402
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import rasterio  # noqa: E402
import requests  # noqa: E402
from pystac_client import Client  # noqa: E402
from rasterio.enums import Resampling  # noqa: E402
from rasterio.features import geometry_mask  # noqa: E402
from rasterio.transform import from_origin  # noqa: E402
from rasterio.warp import transform_geom  # noqa: E402
from rasterio.windows import from_bounds  # noqa: E402
from shapely.geometry import mapping, shape  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
DATA = HERE / "datos_sentinel"  # todos los datos (recortes, csv, reportes, salidas) van aquí
import precision_s2  # noqa: E402
import reglas  # noqa: E402

DATOS = DATA / "datos"
TIF = DATA / "imagenes" / "tif"
PNG = DATA / "imagenes" / "png"
REP = DATA / "reportes"
for d in (DATOS, TIF, PNG, REP):
    d.mkdir(parents=True, exist_ok=True)

STAC = "https://earth-search.aws.element84.com/v1"
COLECCION = "sentinel-2-l2a"
BUFFER_M = 200          # margen alrededor de la parcela en los recortes
MIN_VALIDA = 0.8        # fracción mínima de la parcela sin nubes (nubosidad < 20 % sobre el polígono)
MAX_AZUL = 0.12         # reflectancia azul mediana sobre esto = bruma/nube fina no detectada
SCL_VALIDAS = [4, 5, 6]  # vegetación, suelo desnudo, agua
SCL_NUBE = [8, 9, 10]   # nube media, nube alta, cirros
SCL_SOMBRA = [3]
BANDAS = {  # asset Earth Search -> banda Sentinel-2
    "blue": "B02", "green": "B03", "red": "B04", "rededge1": "B05", "rededge2": "B06",
    "rededge3": "B07", "nir": "B08", "nir08": "B8A", "swir16": "B11", "swir22": "B12",
}
INDICES = ["ndvi", "ndmi", "ndre", "evi", "savi", "bsi", "ndwi", "msi"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]
TZ = "America/Guayaquil"
HIST_INI, HIST_FIN = "2011-01-01", "2025-12-31"


# ======================================================================= parcela
def cargar_parcela(path):
    g = gpd.read_file(path).to_crs(4326)
    pol = g[g.geom_type.isin(["Polygon", "MultiPolygon"])]
    if pol.empty:
        sys.exit(f"{path} no tiene polígonos")
    geom = pol.union_all()
    c = geom.centroid
    area_ha = gpd.GeoSeries([geom], crs=4326).to_crs(pol.estimate_utm_crs()).area.iloc[0] / 1e4
    return geom, c.y, c.x, area_ha


# ======================================================================= Sentinel-2
def buscar_escenas(geom, ini, fin):
    cat = Client.open(STAC)
    items = list(cat.search(collections=[COLECCION], intersects=mapping(geom),
                            datetime=f"{ini}/{fin}", max_items=1000).items())
    # Earth Search tiene duplicados del mismo pase (reprocesados _0/_1): quedarse con el último
    por_clave = {}
    for it in sorted(items, key=lambda i: i.id):
        clave = (it.datetime.date(), it.properties.get("grid:code", it.id.split("_")[1]))
        por_clave[clave] = it
    return sorted(por_clave.values(), key=lambda i: i.datetime)


def _escala(item, asset):
    rb = (asset.extra_fields.get("raster:bands") or [{}])[0]
    off = rb.get("offset", 0.0)
    # Earth Search ya restó el offset de -0.1 (baseline >= 04.00) cuando boa_offset_applied es True,
    # aunque raster:bands lo siga anunciando: aplicarlo otra vez da reflectancias negativas.
    if item.properties.get("earthsearch:boa_offset_applied"):
        off = 0.0
    return rb.get("scale", 1e-4), off


def calcular_indices(b):
    """Fórmulas acordadas con el equipo: NIR = B08 en NDVI, NDRE y NDMI."""
    with np.errstate(divide="ignore", invalid="ignore"):
        return {
            "ndvi": (b["nir"] - b["red"]) / (b["nir"] + b["red"]),
            "ndmi": (b["nir"] - b["swir16"]) / (b["nir"] + b["swir16"]),
            "ndre": (b["nir"] - b["rededge1"]) / (b["nir"] + b["rededge1"]),
            "evi": 2.5 * (b["nir"] - b["red"]) / (b["nir"] + 6 * b["red"] - 7.5 * b["blue"] + 1),
            "savi": 1.5 * (b["nir"] - b["red"]) / (b["nir"] + b["red"] + 0.5),
            "bsi": ((b["swir16"] + b["red"]) - (b["nir"] + b["blue"])) /
                   ((b["swir16"] + b["red"]) + (b["nir"] + b["blue"])),
            "ndwi": (b["green"] - b["nir"]) / (b["green"] + b["nir"]),
            "msi": b["swir16"] / b["nir"],
        }


def resumir_indices(idx, valida):
    out = {}
    for k, a in idx.items():
        v = a[valida & np.isfinite(a)]
        out[k] = round(float(np.mean(v)), 4) if v.size else None
        if k in ("ndvi", "ndmi"):
            out[f"{k}_p10"] = round(float(np.percentile(v, 10)), 4) if v.size else None
            out[f"{k}_p90"] = round(float(np.percentile(v, 90)), 4) if v.size else None
    return out


def recalcular_desde_tif(df, geom):
    """Recalcula índices y estado con los recortes locales (sin red), para que un cambio de
    fórmula o de umbral se aplique también a las escenas ya descargadas."""
    df = df.copy()
    for i, r in df.iterrows():
        if not isinstance(r.get("tif"), str) or not (DATA / r["tif"]).exists():
            continue
        with rasterio.open(DATA / r["tif"]) as s:
            a = s.read()
            g_utm = transform_geom("EPSG:4326", s.crs, mapping(geom))
            parcela = geometry_mask([g_utm], a.shape[1:], s.transform, invert=True)
        b = {k: a[j] for j, k in enumerate(BANDAS)}
        scl = a[len(BANDAS)]
        n = parcela.sum()
        fisico = np.all([np.isfinite(b[k]) & (b[k] > 0) for k in BANDAS], axis=0)
        valida = parcela & np.isin(scl, SCL_VALIDAS) & fisico
        df.loc[i, "frac_valida"] = round(valida.sum() / n, 3)
        df.loc[i, "azul_mediana"] = round(float(np.nanmedian(b["blue"][valida])), 4) if valida.any() else None
        for k, v in resumir_indices(calcular_indices(b), valida).items():
            df.loc[i, k] = v
        fv, az = df.loc[i, "frac_valida"], df.loc[i, "azul_mediana"]
        df.loc[i, "estado"] = ("parcial (nubes)" if fv < MIN_VALIDA else
                               "dudosa (bruma)" if (az is not None and az > MAX_AZUL) else "ok")
    return df


def procesar_escena(item, geom):
    fecha = item.datetime.date()
    tile = item.properties.get("grid:code", "").replace("MGRS-", "")
    reg = dict(fecha=fecha.isoformat(), escena=item.id, tile=tile,
               nubes_escena=item.properties.get("eo:cloud_cover"))

    with rasterio.open(item.assets["red"].href) as s:
        crs = s.crs
    g_utm = transform_geom("EPSG:4326", crs, mapping(geom))
    minx, miny, maxx, maxy = shape(g_utm).bounds
    # rejilla de 10 m alineada a múltiplos de 20 m (así 10 m y 20 m caen exactos)
    minx = math.floor((minx - BUFFER_M) / 20) * 20
    miny = math.floor((miny - BUFFER_M) / 20) * 20
    maxx = math.ceil((maxx + BUFFER_M) / 20) * 20
    maxy = math.ceil((maxy + BUFFER_M) / 20) * 20
    W, H = int((maxx - minx) / 10), int((maxy - miny) / 10)
    tr = from_origin(minx, maxy, 10, 10)

    def leer(key, resampling):
        with rasterio.open(item.assets[key].href) as s:
            win = from_bounds(minx, miny, maxx, maxy, s.transform)
            return s.read(1, window=win, out_shape=(H, W), resampling=resampling,
                          boundless=True, fill_value=0)

    scl = leer("scl", Resampling.nearest)
    parcela = geometry_mask([g_utm], (H, W), tr, invert=True)
    if parcela.sum() < 4:
        parcela = geometry_mask([g_utm], (H, W), tr, invert=True, all_touched=True)
    n = int(parcela.sum())
    valida = parcela & np.isin(scl, SCL_VALIDAS)
    reg.update(pix_parcela=n,
               frac_valida=round(valida.sum() / n, 3),
               frac_nube=round((parcela & np.isin(scl, SCL_NUBE)).sum() / n, 3),
               frac_sombra=round((parcela & np.isin(scl, SCL_SOMBRA)).sum() / n, 3),
               frac_sin_dato=round((parcela & (scl == 0)).sum() / n, 3))
    if (parcela & (scl == 0)).sum() == n:   # la parcela cae fuera de esta tesela
        reg["estado"] = "fuera de tesela"
        return reg
    if valida.sum() == 0:
        reg["estado"] = "nublado (sin descarga)"
        return reg

    def leer_refl(key):
        dn = leer(key, Resampling.bilinear).astype("float32")
        sc, off = _escala(item, item.assets[key])
        r = dn * sc + off
        r[dn == 0] = np.nan
        return key, r

    with ThreadPoolExecutor(6) as ex:
        b = dict(ex.map(leer_refl, BANDAS))
    # píxel con alguna banda <= 0 o sin dato: no es una reflectancia física, se descarta
    fisico = np.all([np.isfinite(b[k]) & (b[k] > 0) for k in BANDAS], axis=0)
    valida = valida & fisico
    reg["frac_valida"] = round(valida.sum() / n, 3)
    reg["azul_mediana"] = round(float(np.nanmedian(b["blue"][valida])), 4) if valida.any() else None

    # ---------------- guardar recorte multibanda (reflectancia) + SCL
    out_tif = TIF / f"S2_{fecha:%Y%m%d}_{tile}.tif"
    with rasterio.open(out_tif, "w", driver="GTiff", height=H, width=W, count=len(BANDAS) + 1,
                       dtype="float32", crs=crs, transform=tr, compress="deflate", nodata=np.nan) as dst:
        for i, k in enumerate(BANDAS, 1):
            dst.write(b[k], i)
            dst.set_band_description(i, f"{BANDAS[k]} ({k}) reflectancia")
        dst.write(scl.astype("float32"), len(BANDAS) + 1)
        dst.set_band_description(len(BANDAS) + 1, "SCL (clasificación de escena)")
        dst.update_tags(fecha=fecha.isoformat(), escena=item.id)
    reg["tif"] = out_tif.relative_to(DATA).as_posix()

    # ---------------- índices
    idx = calcular_indices(b)
    reg.update(resumir_indices(idx, valida))
    if reg["frac_valida"] < MIN_VALIDA:
        reg["estado"] = "parcial (nubes)"
    elif reg["azul_mediana"] is not None and reg["azul_mediana"] > MAX_AZUL:
        reg["estado"] = "dudosa (bruma)"  # nube fina que la SCL no marcó: el azul se dispara
    else:
        reg["estado"] = "ok"

    # ---------------- vista rápida PNG: color real | NDVI | NDMI
    ring = np.array(g_utm["coordinates"][0] if g_utm["type"] == "Polygon" else g_utm["coordinates"][0][0])
    px, py = (ring[:, 0] - minx) / 10 - 0.5, (maxy - ring[:, 1]) / 10 - 0.5
    rgb = np.dstack([b["red"], b["green"], b["blue"]])
    rgb = np.clip(np.nan_to_num(rgb) / 0.25, 0, 1) ** 0.8
    nubes = np.isin(scl, SCL_NUBE + SCL_SOMBRA)
    fig, ax = plt.subplots(1, 3, figsize=(12, 4.4))
    ax[0].imshow(rgb)
    ax[0].set_title("Color real")
    im1 = ax[1].imshow(np.where(nubes, np.nan, idx["ndvi"]), cmap="RdYlGn", vmin=0, vmax=0.9)
    ax[1].set_title("NDVI (vigor)")
    im2 = ax[2].imshow(np.where(nubes, np.nan, idx["ndmi"]), cmap="BrBG", vmin=-0.3, vmax=0.5)
    ax[2].set_title("NDMI (humedad de la vegetación)")
    for a in ax:
        a.plot(px, py, color="cyan" if a is ax[0] else "black", lw=1.6)
        a.set_xticks([]), a.set_yticks([])
    fig.colorbar(im1, ax=ax[1], fraction=0.046)
    fig.colorbar(im2, ax=ax[2], fraction=0.046)
    fig.suptitle(f"{fecha:%d/%m/%Y}  ·  {item.id}  ·  parcela sin nubes: {reg['frac_valida']:.0%}"
                 f"  (gris = nube/sombra)", fontsize=10)
    fig.tight_layout()
    out_png = PNG / f"S2_{fecha:%Y%m%d}_{tile}.png"
    fig.savefig(out_png, dpi=90)
    plt.close(fig)
    reg["png"] = out_png.relative_to(DATA).as_posix()
    return reg


def actualizar_escenas(geom, ini, fin):
    f = DATOS / "indices_por_fecha.csv"
    prev = pd.read_csv(f) if f.exists() else pd.DataFrame(columns=["escena"])
    hechas = set(prev["escena"])
    items = buscar_escenas(geom, ini, fin)
    nuevas = [it for it in items if it.id not in hechas]
    print(f"Sentinel-2: {len(items)} escenas en el periodo, {len(nuevas)} nuevas por procesar")
    regs = []
    for i, it in enumerate(nuevas, 1):
        try:
            r = procesar_escena(it, geom)
        except Exception as e:  # una escena rota no debe tumbar todo
            r = dict(fecha=it.datetime.date().isoformat(), escena=it.id, estado=f"error: {e}"[:200])
        print(f"  [{i}/{len(nuevas)}] {r['fecha']} {it.id}: {r.get('estado')} "
              f"(sin nubes {r.get('frac_valida', 0):.0%})", flush=True)
        regs.append(r)
    df = pd.concat([prev, pd.DataFrame(regs)], ignore_index=True) if regs else prev
    # reintentar en la próxima corrida las que dieron error
    df = df[~df["estado"].astype(str).str.startswith("error")] if regs else df
    df = df.sort_values(["fecha", "escena"]).reset_index(drop=True)
    df = recalcular_desde_tif(df, geom)
    df.to_csv(f, index=False)
    if regs and any(str(r.get("estado", "")).startswith("error") for r in regs):
        print("  (algunas escenas dieron error de red; se reintentan en la próxima corrida)")
    return df


# ======================================================================= clima
HOURLY = "temperature_2m,relative_humidity_2m,precipitation,shortwave_radiation,cloud_cover"


def _diario(js):
    h = pd.DataFrame(js["hourly"])
    h["time"] = pd.to_datetime(h["time"])
    h = h.dropna(subset=["temperature_2m"])
    h["fecha"] = h["time"].dt.date
    h["madrugada"] = h["time"].dt.hour.between(0, 5)
    g = h.groupby("fecha")
    d = pd.DataFrame({
        "tmin": g["temperature_2m"].min(), "tmax": g["temperature_2m"].max(),
        "tmedia": g["temperature_2m"].mean(), "hr": g["relative_humidity_2m"].mean(),
        "lluvia": g["precipitation"].sum(),
        "radiacion": g["shortwave_radiation"].sum() * 3600 / 1e6,  # MJ/m²/día
        "nubes_madrugada": h[h["madrugada"]].groupby("fecha")["cloud_cover"].mean(),
        "horas": g.size(),
    })
    d = d[d["horas"] >= 20].drop(columns="horas")
    d.index = pd.to_datetime(d.index)
    return d.round(2)


def _get(url, params):
    r = requests.get(url, params=params, timeout=120)
    r.raise_for_status()
    return r.json()


def clima_periodo(lat, lon, ini, fin):
    base = dict(latitude=lat, longitude=lon, hourly=HOURLY, timezone=TZ)
    d = _diario(_get("https://archive-api.open-meteo.com/v1/archive",
                     dict(base, start_date=ini, end_date=fin)))
    # el archivo (ERA5) llega con unos días de retraso: completar con el modelo de pronóstico
    rec = _diario(_get("https://api.open-meteo.com/v1/forecast", dict(base, past_days=21, forecast_days=1)))
    rec = rec[(rec.index > (d.index.max() if len(d) else pd.Timestamp(ini))) & (rec.index <= pd.Timestamp(fin))]
    rec["fuente"] = "pronóstico (reciente)"
    d["fuente"] = "ERA5 (reanálisis)"
    out = pd.concat([d, rec]).sort_index()
    out.index.name = "fecha"
    out.to_csv(DATOS / "clima_diario.csv")
    return out


def climatologia(lat, lon):
    f = DATOS / "clima_historico_diario.csv"
    if f.exists():
        d = pd.read_csv(f, index_col="fecha", parse_dates=True)
    else:
        print(f"Clima histórico {HIST_INI} a {HIST_FIN} (una sola vez)...", flush=True)
        d = _diario(_get("https://archive-api.open-meteo.com/v1/archive",
                         dict(latitude=lat, longitude=lon, hourly=HOURLY, timezone=TZ,
                              start_date=HIST_INI, end_date=HIST_FIN)))
        d.index.name = "fecha"
        d.to_csv(f)
    m = d.groupby(d.index.month).agg(tmin_media=("tmin", "mean"), tmedia=("tmedia", "mean"),
                                     hr=("hr", "mean"), radiacion=("radiacion", "mean"),
                                     nubes_madrugada=("nubes_madrugada", "mean"))
    n_anios = d.index.year.nunique()
    m["lluvia_mm"] = d.groupby(d.index.month)["lluvia"].sum() / n_anios
    m["dias_tmin_bajo_6"] = d.assign(f=d.tmin < 6).groupby(d.index.month)["f"].mean() * 30

    def terciles(s, bajo, alto):
        r = s.rank(method="first")
        return np.where(r <= 4, bajo, np.where(r > 8, alto, "normal"))

    m["clase_lluvia"] = terciles(m["lluvia_mm"], "seco", "lluvioso")
    m["clase_radiacion"] = terciles(m["radiacion"], "baja", "alta")
    m["clase_noches"] = terciles(m["nubes_madrugada"], "despejado", "nublado")
    m["nombre"] = [MESES[i - 1] for i in m.index]
    m.index.name = "mes"
    m.round(2).to_csv(DATOS / "climatologia_mensual.csv")
    return m


# ======================================================================= reporte semanal
def _v(x, nd=2, pct=False):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "s/d"
    return f"{x:.0%}" if pct else f"{x:.{nd}f}"


INTERP = {
    "ndvi": "vigor / biomasa verde", "ndmi": "humedad de la vegetación",
    "ndre": "clorofila / nitrógeno (red edge)", "evi": "vigor, corrige suelo y atmósfera",
    "savi": "vigor con suelo expuesto", "bsi": "suelo desnudo (más alto = más suelo)",
    "ndwi": "agua superficial / encharcamiento", "msi": "estrés hídrico (más alto = más seco)",
}


EMOJI = {"gris": "⚪", "verde": "🟢", "amarillo": "🟡", "rojo": "🔴", "azul": "🔵", "no aplica": "⚪"}


def bloque_precision(prec, hasta):
    """Bloques 1 y 2 del reporte combinado: última imagen limpia (1 cada 15 días) hasta esa semana."""
    if not prec:
        return [], None
    previas = [f for f in prec["fechas"] if pd.Timestamp(f["fecha"]) <= hasta]
    if not previas:
        return ["\n## Sentinel-2 de precisión (10 m, polígono exacto)", "_Aún no hay imagen limpia._"], None
    f = previas[-1]
    dias = (hasta - pd.Timestamp(f["fecha"])).days
    L = ["\n## Sentinel-2 de precisión (10 m, polígono exacto)",
         f"**Última captura satelital limpia: hace {dias} días** ({pd.Timestamp(f['fecha']):%d/%m/%Y}, "
         f"nubosidad en el polígono {f['nubosidad_poligono_pct']:.0f} %)  ",
         f"Comparada con la imagen limpia anterior: "
         + (f"{pd.Timestamp(f['fecha_anterior']):%d/%m/%Y} ({f['dias_desde_anterior']} días antes), "
            + (f"cambio de NDVI {-f['caida_ndvi']:+.3f}" if f["caida_ndvi"] is not None else
               "demasiado lejana para medir caída")
            if f["fecha_anterior"] else "primera del periodo") + "\n",
         "| | Estado | Mensaje para el agricultor |\n|---|---|---|",
         f"| **Vigor y plagas** (NDVI {f['ndvi']:.2f}, NDRE {f['ndre']:.2f}) | {EMOJI[f['estado_vigor']]} "
         f"{f['estado_vigor']} | {f['mensaje_vigor']} |",
         f"| **Humedad** (NDMI {f['ndmi']:.2f}) | {EMOJI[f['estado_humedad']]} {f['estado_humedad']} | "
         f"{f['mensaje_humedad']} |",
         f"\n**Salud del lote:** {f['pct_area_sana']:.0f} % del área sana (verde) · "
         f"{f['pct_area_estres']:.0f} % con estrés (amarillo + rojo) · "
         + " · ".join(f"{EMOJI[k]} {k} {v:.0f} %" for k, v in f["pct_area_vigor"].items() if v > 0)]
    if f["sector_mas_afectado"]:
        s = f["sectores"][f["sector_mas_afectado"]]
        L.append(f"  \n**Sector más afectado:** {f['sector_mas_afectado']} ({s['pct_rojo']:.0f} % de sus píxeles en rojo)")
    L.append(f"\n![Vigor {f['fecha']}](../{f['imagenes']['vigor']}) ![Humedad {f['fecha']}](../{f['imagenes']['humedad']})")
    return L, f


def generar_reportes(esc, clima, clim, info_parcela, fin, prec=None):
    ok = esc[esc["estado"] == "ok"].copy()
    ok["fecha"] = pd.to_datetime(ok["fecha"])
    ok = ok.sort_values("fecha").drop_duplicates("fecha", keep="last")
    esc = esc.copy()
    esc["fecha"] = pd.to_datetime(esc["fecha"])

    fin = pd.Timestamp(fin)
    ini = pd.Timestamp(clima.index.min())
    lunes = ini - pd.Timedelta(days=ini.weekday())
    semanas = []
    while lunes <= fin:
        semanas.append((lunes, lunes + pd.Timedelta(days=6)))
        lunes += pd.Timedelta(days=7)

    filas = []
    for w0, w1 in semanas:
        iso = w0.isocalendar()
        sid = f"{iso.year}-S{iso.week:02d}"
        hasta = min(w1, fin)
        # --------------- satélite: último dato válido hasta el fin de la semana
        prev_ok = ok[ok["fecha"] <= hasta]
        act = prev_ok.iloc[-1] if len(prev_ok) else None
        ant = None
        if act is not None:
            cand = ok[(ok["fecha"] <= act["fecha"] - pd.Timedelta(days=7)) &
                      (ok["fecha"] >= act["fecha"] - pd.Timedelta(days=40))]
            ant = cand.iloc[-1] if len(cand) else None
        edad = (hasta - act["fecha"]).days if act is not None else None
        obs_sem = esc[(esc["fecha"] >= w0) & (esc["fecha"] <= w1)]

        # --------------- clima de la semana
        cs = clima[(clima.index >= w0) & (clima.index <= w1)]
        mes_sig_n = (w1 + pd.DateOffset(months=1)).month
        ms = clim.loc[mes_sig_n]

        def g(row, k):
            return None if row is None or pd.isna(row.get(k)) else float(row[k])

        ctx = dict(
            ndvi=g(act, "ndvi"), ndmi=g(act, "ndmi"), ndre=g(act, "ndre"), bsi=g(act, "bsi"), msi=g(act, "msi"),
            d_ndvi=(g(act, "ndvi") - g(ant, "ndvi")) if ant is not None else None,
            d_ndmi=(g(act, "ndmi") - g(ant, "ndmi")) if ant is not None else None,
            dias_delta=(act["fecha"] - ant["fecha"]).days if ant is not None else None,
            sat_reciente=edad is not None and edad <= reglas.MAX_EDAD_SAT,
            fecha_sat=act["fecha"].date() if act is not None else None,
            tmin=float(cs["tmin"].min()) if len(cs) else None,
            tmax=float(cs["tmax"].max()) if len(cs) else None,
            tmedia=float(cs["tmedia"].mean()) if len(cs) else None,
            hr=float(cs["hr"].mean()) if len(cs) else None,
            lluvia=float(cs["lluvia"].sum()) if len(cs) else None,
            radiacion=float(cs["radiacion"].mean()) if len(cs) else None,
            noches_bajo_6=int((cs["tmin"] < 6).sum()) if len(cs) else 0,
            mes_sig=dict(nombre=ms["nombre"], lluvia_mm=float(ms["lluvia_mm"]), clase_lluvia=ms["clase_lluvia"],
                         clase_radiacion=ms["clase_radiacion"], clase_noches=ms["clase_noches"],
                         tmin_media=float(ms["tmin_media"])),
        )
        res = reglas.evaluar(ctx)
        alertas = [r for r in res if r["nivel"] == "ALERTA"]
        vigilar = [r for r in res if r["nivel"] == "VIGILAR"]

        # --------------- markdown
        L = []
        L.append(f"# Reporte semanal {sid}: {w0:%d/%m/%Y} al {w1:%d/%m/%Y}")
        L.append(f"**Parcela:** {info_parcela['nombre']} · {info_parcela['area_ha']:.2f} ha · "
                 f"centro {info_parcela['lat']:.6f}, {info_parcela['lon']:.6f}  ")
        if w1 > fin:
            L.append(f"_Semana en curso: datos hasta {fin:%d/%m/%Y}._")
        L.append("\n## Alertas para el agricultor")
        if alertas:
            for r in alertas:
                L.append(f"- 🔴 **{r['nombre']}**: \"{r['mensaje']}\"  \n  _Porque:_ {r['actual_txt']}; {r['tend_txt']}.")
        else:
            L.append("- 🟢 Sin alertas esta semana.")
        for r in vigilar:
            L.append(f"- 🟡 **Vigilar: {r['nombre']}**: se cumple la condición actual ({r['actual_txt']}), "
                     f"pero no la tendencia del próximo mes ({r['tend_txt']}).")

        bp, fp = bloque_precision(prec, hasta)
        L.extend(bp)

        L.append("\n## Detalle de todos los pases del satélite (Sentinel-2 L2A)")
        if len(obs_sem):
            L.append("| Fecha | Escena | Parcela sin nubes | Nubes | Estado |\n|---|---|---|---|---|")
            for _, o in obs_sem.iterrows():
                L.append(f"| {o['fecha']:%d/%m} | {o['escena']} | {_v(o.get('frac_valida'), pct=True)} | "
                         f"{_v(o.get('frac_nube'), pct=True)} | {o['estado']} |")
        else:
            L.append("_No hubo pase del satélite esta semana._")
        if act is None:
            L.append("\nTodavía no hay ninguna observación sin nubes.")
        else:
            aviso = "" if ctx["sat_reciente"] else \
                f" ⚠️ **dato de hace {edad} días** (nubes): no se usa para las reglas de satélite."
            L.append(f"\n**Último dato válido:** {act['fecha']:%d/%m/%Y}{aviso}  ")
            if ant is not None:
                L.append(f"**Comparado con:** {ant['fecha']:%d/%m/%Y} ({ctx['dias_delta']} días antes)\n")
            L.append("| Índice | Valor | Anterior | Cambio | Qué indica |\n|---|---|---|---|---|")
            for k in INDICES:
                a, p = g(act, k), g(ant, k)
                d = _v(a - p, 3) if (a is not None and p is not None) else "s/d"
                L.append(f"| {k.upper()} | {_v(a, 3)} | {_v(p, 3)} | {d} | {INTERP[k]} |")
            if isinstance(act.get("png"), str):
                L.append(f"\n![{act['fecha']:%d/%m/%Y}](../{act['png']})")

        L.append("\n## Clima de la semana (Open-Meteo)")
        if len(cs):
            fuentes = ", ".join(sorted(cs["fuente"].unique()))
            L.append(f"| T mín | T máx | T media | HR media | Lluvia | Radiación | Noches < 6 °C |\n"
                     f"|---|---|---|---|---|---|---|\n"
                     f"| {ctx['tmin']:.1f} °C | {ctx['tmax']:.1f} °C | {ctx['tmedia']:.1f} °C | {ctx['hr']:.0f} % | "
                     f"{ctx['lluvia']:.1f} mm | {ctx['radiacion']:.1f} MJ/m²/día | {ctx['noches_bajo_6']} de {len(cs)} |")
            L.append(f"\n_Fuente: {fuentes}; {len(cs)} días con dato._")
        else:
            L.append("_Sin datos de clima para esta semana._")

        L.append(f"\n## Tendencia histórica del próximo mes: {ms['nombre']} (promedio 2011-2025)")
        L.append(f"| Lluvia | T mín media | Radiación | Nubes de madrugada | Días con T mín < 6 °C |\n|---|---|---|---|---|\n"
                 f"| {ms['lluvia_mm']:.0f} mm ({ms['clase_lluvia']}) | {ms['tmin_media']:.1f} °C | "
                 f"{ms['radiacion']:.1f} MJ/m²/día ({ms['clase_radiacion']}) | "
                 f"{ms['nubes_madrugada']:.0f} % ({ms['clase_noches']}) | {ms['dias_tmin_bajo_6']:.0f} |")

        L.append("\n## Reglas evaluadas (provisionales, ver `reglas.py`)")
        L.append("| Regla | Si hoy ocurre esto | ¿Se cumple? | + Próximo mes | ¿Se cumple? | Resultado |\n"
                 "|---|---|---|---|---|---|")
        sym = {True: "✅", False: "❌", None: "➖"}
        for r in res:
            L.append(f"| {r['id']} {r['nombre']} | {r['si']}: {r['actual_txt']} | {sym[r['actual_ok']]} | "
                     f"{r['mas']}: {r['tend_txt']} | {sym[r['tend_ok']]} | {r['nivel'] or 'ninguna'} |")

        (REP / f"semana_{sid}.md").write_text("\n".join(L) + "\n", encoding="utf-8")
        filas.append(dict(
            semana=sid, inicio=w0.date(), fin=w1.date(), pases=len(obs_sem),
            pases_validos=int((obs_sem["estado"] == "ok").sum()) if len(obs_sem) else 0,
            fecha_sat=ctx["fecha_sat"], edad_sat_dias=edad, ndvi=ctx["ndvi"], ndmi=ctx["ndmi"], ndre=ctx["ndre"],
            bsi=ctx["bsi"], d_ndvi=ctx["d_ndvi"], d_ndmi=ctx["d_ndmi"],
            tmin=ctx["tmin"], tmedia=ctx["tmedia"], hr=ctx["hr"], lluvia=ctx["lluvia"], radiacion=ctx["radiacion"],
            noches_bajo_6=ctx["noches_bajo_6"], mes_siguiente=ms["nombre"],
            alertas="; ".join(r["id"] for r in alertas), vigilar="; ".join(r["id"] for r in vigilar),
            s2_fecha=fp["fecha"] if fp else None, s2_vigor=fp["estado_vigor"] if fp else None,
            s2_humedad=fp["estado_humedad"] if fp else None, s2_pct_sana=fp["pct_area_sana"] if fp else None,
            s2_pct_estres=fp["pct_area_estres"] if fp else None,
            s2_sector=fp["sector_mas_afectado"] if fp else None,
        ))

    sem = pd.DataFrame(filas)
    sem.round(4).to_csv(DATOS / "historico_semanal.csv", index=False)

    # --------------- índice con todo el histórico + gráfico de series
    graficar_series(ok, clima)
    L = [f"# Monitoreo de la parcela: {info_parcela['nombre']}",
         f"{info_parcela['area_ha']:.2f} ha · centro {info_parcela['lat']:.6f}, {info_parcela['lon']:.6f} · "
         f"periodo {semanas[0][0]:%d/%m/%Y} al {fin:%d/%m/%Y}\n",
         "![Series](../imagenes/series_tiempo.png)\n",
         "| Semana | Del | Pases S2 (válidos) | Imagen limpia | Vigor | Humedad | % sana / estrés | NDVI | NDMI "
         "| T mín | HR | Lluvia | Alertas | Vigilar |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in reversed(filas):
        s2 = (f"{pd.Timestamp(r['s2_fecha']):%d/%m} | {EMOJI[r['s2_vigor']]} {r['s2_vigor']} | "
              f"{EMOJI[r['s2_humedad']]} {r['s2_humedad']} | {r['s2_pct_sana']:.0f} / {r['s2_pct_estres']:.0f}"
              if r["s2_fecha"] else "s/d | - | - | -")
        L.append(f"| [{r['semana']}](semana_{r['semana']}.md) | {r['inicio']:%d/%m} | {r['pases']} ({r['pases_validos']}) | "
                 f"{s2} | {_v(r['ndvi'])} | {_v(r['ndmi'])} | "
                 f"{_v(r['tmin'], 1)} | {_v(r['hr'], 0)} | {_v(r['lluvia'], 1)} | "
                 f"{('🔴 ' + r['alertas']) if r['alertas'] else '-'} | {('🟡 ' + r['vigilar']) if r['vigilar'] else '-'} |")
    (REP / "INDICE.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    return sem


def graficar_series(ok, clima):
    fig, ax = plt.subplots(3, 1, figsize=(11, 8.5), sharex=True)
    for k, c in (("ndvi", "tab:green"), ("ndmi", "tab:blue"), ("ndre", "tab:olive"), ("bsi", "tab:brown")):
        if k in ok:
            ax[0].plot(ok["fecha"], ok[k], "o-", color=c, label=k.upper(), ms=4)
    if "ndvi_p10" in ok:
        ax[0].fill_between(ok["fecha"], ok["ndvi_p10"], ok["ndvi_p90"], color="tab:green", alpha=0.15,
                           label="NDVI p10-p90")
    ax[0].set_ylabel("Índice")
    ax[0].legend(ncol=5, fontsize=8)
    ax[0].set_title("Sentinel-2 (solo fechas con ≥60 % de la parcela sin nubes)")
    ax[1].plot(clima.index, clima["tmax"], color="tab:red", lw=0.8, label="T máx")
    ax[1].plot(clima.index, clima["tmin"], color="tab:blue", lw=0.8, label="T mín")
    ax[1].axhline(6, color="tab:blue", ls="--", lw=0.8, label="6 °C (helada)")
    ax[1].set_ylabel("°C")
    ax[1].legend(ncol=3, fontsize=8)
    ax[2].bar(clima.index, clima["lluvia"], color="tab:cyan", label="Lluvia (mm)")
    a2 = ax[2].twinx()
    a2.plot(clima.index, clima["hr"], color="gray", lw=0.8, label="HR %")
    ax[2].set_ylabel("mm")
    a2.set_ylabel("HR %")
    ax[2].legend(loc="upper left", fontsize=8)
    a2.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(DATA / "imagenes" / "series_tiempo.png", dpi=90)
    plt.close(fig)


# ======================================================================= main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parcela", default=str(DATA / "papas_parcela.geojson"))
    ap.add_argument("--fin", default=date.today().isoformat())
    ap.add_argument("--inicio", default=None, help="por defecto: 6 meses antes de --fin")
    a = ap.parse_args()
    fin = date.fromisoformat(a.fin)
    ini = date.fromisoformat(a.inicio) if a.inicio else (pd.Timestamp(fin) - pd.DateOffset(months=6)).date()

    geom, lat, lon, area = cargar_parcela(a.parcela)
    info = dict(nombre=pathlib.Path(a.parcela).stem, lat=lat, lon=lon, area_ha=area)
    print(f"Parcela {info['nombre']}: {area:.2f} ha, centro {lat:.6f}, {lon:.6f}; periodo {ini} a {fin}")
    (DATOS / "parcela.json").write_text(json.dumps(dict(info, inicio=str(ini), fin=str(fin)), indent=2),
                                        encoding="utf-8")

    esc = actualizar_escenas(geom, ini.isoformat(), fin.isoformat())
    print(f"Escenas: {(esc['estado'] == 'ok').sum()} válidas de {len(esc)}")
    prec = precision_s2.procesar(a.parcela)
    print("Clima del periodo...", flush=True)
    clima = clima_periodo(lat, lon, ini.isoformat(), fin.isoformat())
    clim = climatologia(lat, lon)
    sem = generar_reportes(esc, clima, clim, info, fin, prec)
    ult = sem.iloc[-1]
    print(f"\n{len(sem)} reportes semanales en {REP}")
    print(f"Semana actual {ult['semana']}: alertas [{ult['alertas'] or 'ninguna'}], vigilar [{ult['vigilar'] or 'nada'}]")
    print((REP / f"semana_{ult['semana']}.md").read_text(encoding="utf-8"))
    from preprocesar import exportar_api
    exportar_api()


if __name__ == "__main__":
    main()
