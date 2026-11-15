"""Preprocesa TODOS los datos Sentinel-2 que se muestran en el Streamlit, SIN descargar nada.

Parte de lo que ya está en datos_sentinel/ (lo dejó monitoreo.py):
  - imagenes/tif/S2_*.tif          recortes con las 10 bandas + SCL
  - datos/indices_por_fecha.csv    lista de pases del satélite
  - datos/clima_diario.csv         clima del periodo (Open-Meteo)
  - datos/clima_historico_diario.csv  clima 2011-2025 (climatología)
  - datos/parcela.json             parcela y periodo

y regenera:
  1. datos/indices_por_fecha.csv        índices por pase (recalculados desde los TIF)
  2. salida_s2/                         sentinel2_parcela.json/.csv, entregable_sentinel2.json, PNG y TIF por fecha
  3. datos/climatologia_mensual.csv     promedios mensuales y clases seco/lluvioso
  4. reportes/ + datos/historico_semanal.csv + imagenes/series_tiempo.png
  5. resultado_prototipo_sentinel_2.json   (formato input/output igual al de nasa-power)
     resultado_integrado.json              (si existe ../nasa-power/resultado_prototipo.json)
  6. api_sentinel_2.json                   todo junto, para consumir como API

Uso:
    python preprocesar.py

Para bajar escenas nuevas primero corre monitoreo.py (descarga + este mismo preprocesado).
"""
import json
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd  # noqa: E402

import monitoreo as m  # noqa: E402  (arregla PROJ y define rutas)
import precision_s2  # noqa: E402

API_JSON = m.HERE / "api_sentinel_2.json"


def _registros(df):
    """DataFrame -> lista de dicts con NaN como null."""
    return json.loads(df.to_json(orient="records", date_format="iso", force_ascii=False))


def _con_prefijo(rutas):
    """Rutas relativas a datos_sentinel/ -> relativas a la carpeta sentinel_2/."""
    return {k: f"{m.DATA.name}/{v}" for k, v in rutas.items()}


def exportar_api():
    """Junta en un solo JSON todo lo que usa el Streamlit (mapa, evolución, reportes, entregables)."""
    D, SAL = m.DATOS, precision_s2.SAL
    leer = lambda p: json.loads(p.read_text(encoding="utf-8")) if p.exists() else None  # noqa: E731
    s2 = leer(SAL / "sentinel2_parcela.json")
    if s2 is None:
        raise SystemExit("No hay salida_s2/sentinel2_parcela.json: corre primero el preprocesado.")
    info = leer(D / "parcela.json") or {}
    geo = leer(m.DATA / "papas_parcela.geojson")
    integrado = leer(precision_s2.INTEGRADO_JSON)

    sem = pd.read_csv(D / "historico_semanal.csv") if (D / "historico_semanal.csv").exists() else pd.DataFrame()
    if not sem.empty:
        sem["reporte_md"] = f"{m.DATA.name}/reportes/semana_" + sem["semana"].astype(str) + ".md"

    capturas = []
    for f in s2["fechas"]:
        c = dict(f)
        c["imagenes"] = _con_prefijo(f["imagenes"])
        capturas.append(c)
    ult = capturas[-1]

    api = {
        "api": {
            "modulo": "sentinel_2",
            "version": "1.0",
            "generado": datetime.now().isoformat(timespec="seconds"),
            "fuente": "Copernicus Sentinel-2 L2A (Earth Search / AWS) + Open-Meteo (ERA5)",
            "rutas_relativas_a": "bio-orbit/sentinel_2/",
            "recursos": {
                "parcela": "Polígono, centro, área y periodo analizado",
                "ultima_captura": "Diagnóstico de la última imagen limpia (semáforos vigor/humedad, % de área, capas)",
                "capturas": "Serie de imágenes limpias (~1 cada 15 días) con índices, estados, sectores e imágenes",
                "pases_satelite": "Todos los pases del periodo con % de nubes y 8 índices (NDVI, NDMI, NDRE, EVI, SAVI, BSI, NDWI, MSI)",
                "semanas": "Resumen semanal: índices, clima, alertas y ruta del reporte .md",
                "clima_diario": "T mín/máx/media, HR, lluvia, radiación y nubes de madrugada por día",
                "climatologia_mensual": "Promedios 2011-2025 por mes y clases seco/lluvioso, radiación, noches",
                "alerta_cruzada": "Cruce NASA POWER (clima regional) + Sentinel-2 (parcela), si existe",
                "archivos": "Rutas de los entregables",
            },
        },
        "parcela": {
            "nombre": info.get("nombre"), "centro_lat_lon": s2["parcela"]["centro"],
            "area_ha": None if info.get("area_ha") is None else round(info["area_ha"], 2),
            "periodo": {"inicio": info.get("inicio"), "fin": info.get("fin")},
            "geojson": geo,
        },
        "criterios": s2["criterios"],
        "ultima_captura": dict(s2["ultima"], imagenes=ult["imagenes"], bounds_latlon=ult["bounds_latlon"],
                               ndvi=ult["ndvi"], ndre=ult["ndre"], ndmi=ult["ndmi"],
                               pct_area_vigor=ult["pct_area_vigor"], pct_area_humedad=ult["pct_area_humedad"],
                               sectores=ult["sectores"]),
        "capturas": capturas,
        "pases_satelite": _registros(pd.read_csv(D / "indices_por_fecha.csv")),
        "semanas": _registros(sem),
        "clima_diario": _registros(pd.read_csv(D / "clima_diario.csv")),
        "climatologia_mensual": _registros(pd.read_csv(D / "climatologia_mensual.csv")),
        "alerta_cruzada": None if integrado is None else {
            "confirmada": integrado["output"]["alerta_cruzada_confirmada"],
            "cruces_evaluados": integrado["output"]["cruces_evaluados"],
        },
        "archivos": {
            "resultado_prototipo": precision_s2.RESULTADO_JSON.name,
            "resultado_integrado": precision_s2.INTEGRADO_JSON.name if integrado else None,
            "entregable_equipo": f"{m.DATA.name}/salida_s2/entregable_sentinel2.json",
            "serie_completa_json": f"{m.DATA.name}/salida_s2/sentinel2_parcela.json",
            "serie_completa_csv": f"{m.DATA.name}/salida_s2/sentinel2_parcela.csv",
            "reporte_indice": f"{m.DATA.name}/reportes/INDICE.md",
            "grafico_series": f"{m.DATA.name}/imagenes/series_tiempo.png",
        },
    }
    API_JSON.write_text(json.dumps(api, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"API: {API_JSON.name} ({API_JSON.stat().st_size / 1024:.0f} KB)")
    return api


def main():
    info = json.loads((m.DATOS / "parcela.json").read_text(encoding="utf-8"))
    parcela = m.DATA / "papas_parcela.geojson"
    geom, *_ = m.cargar_parcela(parcela)
    fin = info["fin"]

    print("1/5 Índices por pase (desde los TIF locales)...")
    esc = m.recalcular_desde_tif(pd.read_csv(m.DATOS / "indices_por_fecha.csv"), geom)
    esc.to_csv(m.DATOS / "indices_por_fecha.csv", index=False)
    print(f"    {(esc['estado'] == 'ok').sum()} válidas de {len(esc)}")

    print("2/5 Precisión 10 m (salida_s2 + resultado_prototipo_sentinel_2.json)...")
    prec = precision_s2.procesar(parcela)

    print("3/5 Clima y climatología (desde los CSV guardados)...")
    clima = pd.read_csv(m.DATOS / "clima_diario.csv", index_col="fecha", parse_dates=True)
    clim = m.climatologia(info["lat"], info["lon"])  # lee clima_historico_diario.csv si existe

    print("4/5 Reportes semanales y series...")
    sem = m.generar_reportes(esc, clima, clim, info, fin, prec)
    print(f"    {len(sem)} semanas, última {sem.iloc[-1]['semana']}")

    print("5/5 JSON tipo API...")
    exportar_api()
    print("Listo.")


if __name__ == "__main__":
    main()
