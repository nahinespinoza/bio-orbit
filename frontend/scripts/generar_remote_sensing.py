"""Genera los datos quemados de la Parcela 1 (ruta /prueba) a partir de remote-sensing/.

Lee (sin descargar nada):
  - remote-sensing/resultado_match.json                       cruce NASA POWER + Sentinel-2
  - remote-sensing/nasa-power/response_*.json                 NASA POWER diario de la parcela (5 años)
  - remote-sensing/sentinel_2/.../salida_s2/sentinel2_parcela.json   reparto por clase de la última foto
  - remote-sensing/sentinel_2/.../salida_s2/png/{vigor,humedad}_<fecha>.png   clases píxel a píxel

Escribe frontend/src/data/remote-sensing-parcela1.json.

Uso (desde la raíz del repo; solo necesita Pillow):
    python3 frontend/scripts/generar_remote_sensing.py
"""
import calendar
import json
from collections import defaultdict
from pathlib import Path

from PIL import Image

RAIZ = Path(__file__).resolve().parents[2]
RS = RAIZ / "remote-sensing"
S2 = RS / "sentinel_2" / "datos_sentinel" / "salida_s2"
SALIDA = RAIZ / "frontend" / "src" / "data" / "remote-sensing-parcela1.json"

RELLENO = -999
DIAS_FALTANTES_MAX = 5  # igual que src/lib/nasa.js: un mes con más días sin dato queda null
PIXEL = 10  # los PNG de precision_s2.py dibujan cada píxel Sentinel-2 (10 m) como un bloque de 10×10

# Colores de precision_s2.py → estados de la app (bien / atencion / problema / grave)
VIGOR = {(26, 152, 80): "bien", (250, 200, 30): "atencion", (215, 48, 39): "grave", (160, 160, 160): None}
HUMEDAD = {(26, 152, 80): "bien", (250, 200, 30): "atencion", (215, 48, 39): "grave",
           (44, 123, 182): "atencion", (160, 160, 160): None}


def mensual_nasa():
    """NASA POWER diario → {lluvia, humedad, temperatura}: {año: [12]} (lluvia en mm/mes, humedad 0–1, T en °C)."""
    archivo = next((RS / "nasa-power").glob("response_*.json"))
    p = json.loads(archivo.read_text())["properties"]["parameter"]

    def agrupar(serie, como):
        valores = defaultdict(list)
        for fecha, v in serie.items():
            if v is None or v == RELLENO:
                continue
            valores[(int(fecha[:4]), int(fecha[4:6]) - 1)].append(v)
        años = sorted({int(f[:4]) for f in serie})
        out = {}
        for año in años:
            fila = []
            for mes in range(12):
                v = valores.get((año, mes), [])
                dias = calendar.monthrange(año, mes + 1)[1]
                if dias - len(v) > DIAS_FALTANTES_MAX:
                    fila.append(None)
                else:
                    fila.append(round(sum(v)) if como == "suma" else round(sum(v) / len(v), 3))
            out[str(año)] = fila
        return out

    return {
        "lluvia": agrupar(p["PRECTOTCORR"], "suma"),
        "humedad": agrupar(p["GWETROOT"], "media"),
        "temperatura": agrupar(p["T2M"], "media"),
        "periodo": [min(p["T2M"])[:8], max(p["T2M"])[:8]],
    }


def celdas_sentinel(fecha, bounds):
    """Clases de vigor y humedad por píxel de 10 m, con sus límites [[sur, oeste], [norte, este]]."""
    (sur, oeste), (norte, este) = bounds
    vig = Image.open(S2 / "png" / f"vigor_{fecha}.png").convert("RGBA")
    hum = Image.open(S2 / "png" / f"humedad_{fecha}.png").convert("RGBA")
    ancho, alto = vig.size
    cols, filas = ancho // PIXEL, alto // PIXEL
    d_lng, d_lat = (este - oeste) / cols, (norte - sur) / filas
    celdas = []
    for f in range(filas):
        for c in range(cols):
            centro = (c * PIXEL + PIXEL // 2, f * PIXEL + PIXEL // 2)
            rv, gv, bv, av = vig.getpixel(centro)
            rh, gh, bh, ah = hum.getpixel(centro)
            if av == 0 and ah == 0:
                continue  # fuera de la parcela
            ev = VIGOR.get((rv, gv, bv)) if av else None
            eh = HUMEDAD.get((rh, gh, bh)) if ah else None
            if ev is None and eh is None:
                continue  # nube o suelo desnudo: sin dato
            n = norte - f * d_lat
            o = oeste + c * d_lng
            celdas.append({
                "limites": [[round(n - d_lat, 7), round(o, 7)], [round(n, 7), round(o + d_lng, 7)]],
                "verdor": ev,
                "humedad": eh,
            })
    return celdas


def main():
    match = json.loads((RS / "resultado_match.json").read_text())["output"]
    s2 = json.loads((S2 / "sentinel2_parcela.json").read_text())
    ultima = s2["fechas"][-1]
    fecha = ultima["fecha"].replace("-", "")

    clima = match["clima_regional_nasa_power"]
    parcela = match["parcela_sentinel2"]
    datos = {
        "fuente": {
            "zona": match["zona"],
            "altitud_parcela_msnm": match["altitud_parcela_msnm"],
            "altitud_nasa_msnm": clima["altitud"],
            "fecha_foto": ultima["fecha"],
            "dias_desde_foto": parcela["dias_desde_ultima_foto"],
            "nasa_semana": [clima["fecha_inicio"], clima["fecha_fin"]],
        },
        "clima": {
            "semana": clima["estado_actual_7d"],
            "serie_7d": clima["serie_7d"],
            "semaforos": clima["semaforos"],
            "proyeccion": match["proyeccion_vigente_nasa"],
        },
        "sentinel": {
            "estado": parcela["estado_actual_lote"],
            "semaforos": parcela["semaforos"],
            "sectores": parcela["sectores"],
            "pct_vigor": ultima["pct_area_vigor"],
            "pct_humedad": ultima["pct_area_humedad"],
            "serie": parcela["serie_fenologica"],
            "celdas": celdas_sentinel(fecha, ultima["bounds_latlon"]),
        },
        "alerta_cruzada": match.get("alerta_cruzada_confirmada"),
        # Título y mensaje de cada alerta por código (las del cruce con la última foto traen las tres)
        "alertas_textos": {
            a["codigo"]: {"titulo": a["titulo"], "mensaje": a["mensaje"]}
            for a in match["cruce_ultima_captura"]["clima_nasa_alineado"]["alertas_preventivas"]
            + match["proyeccion_vigente_nasa"]["alertas_preventivas"]
            + match["cruces_evaluados"]  # cruces clima + satélite (p. ej. NUTRICION_PROBABLE)
        },
        "mensual": mensual_nasa(),
    }
    SALIDA.write_text(json.dumps(datos, ensure_ascii=False, separators=(",", ":")))
    print(f"{SALIDA.relative_to(RAIZ)}: {len(datos['sentinel']['celdas'])} celdas, "
          f"{SALIDA.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
