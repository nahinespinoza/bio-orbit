"""Acceso a los datos de la parcela: JSON simulado o cálculo en vivo con integrar()."""
import json
import pathlib

from . import match_nasa_sentinel as m


class DatosFaltantes(Exception):
    """Falta un archivo de datos necesario para calcular el match."""

    def __init__(self, faltan: list[str]):
        self.faltan = faltan
        super().__init__("Faltan datos: " + ", ".join(faltan))


def _rel(p: pathlib.Path) -> str:
    try:
        return p.relative_to(m.DATA_DIR).as_posix()
    except ValueError:  # ruta fuera de data/ (p. ej. en tests)
        return p.as_posix()


def resultado_simulado() -> dict:
    ruta = m.DATA_DIR / "resultado_match.json"
    if not ruta.exists():
        raise DatosFaltantes([_rel(ruta)])
    return json.loads(ruta.read_text(encoding="utf-8"))


def resultado_en_vivo() -> dict:
    rutas = {
        "nasa": m.NASA_DIR / "resultado_prototipo.json",
        "s2": m.S2_DIR / "resultado_prototipo_sentinel_2.json",
        "s2_full": m.S2_DATOS / "salida_s2" / "sentinel2_parcela.json",
        "parcela": m.S2_DATOS / "datos" / "parcela.json",
    }
    faltan = [_rel(p) for p in rutas.values() if not p.exists()]
    if not (m.NASA_DIR / "process_2.py").exists():
        faltan.append(_rel(m.NASA_DIR / "process_2.py"))
    if not list(m.NASA_DIR.glob("response_*.json")):
        faltan.append("nasa-power/response_*.json")
    if faltan:
        raise DatosFaltantes(faltan)

    leer = lambda p: json.loads(p.read_text(encoding="utf-8"))  # noqa: E731
    parcela = leer(rutas["parcela"])
    out = m.integrar(leer(rutas["s2"]), leer(rutas["s2_full"]), leer(rutas["nasa"]),
                     m.NASA_DIR, m.S2_DATOS / "datos", parcela.get("altitud_msnm"))
    if out is None:  # integrar() devuelve None si no hay módulo/datos crudos de NASA
        raise DatosFaltantes(["nasa-power/process_2.py", "nasa-power/response_*.json"])
    return out
