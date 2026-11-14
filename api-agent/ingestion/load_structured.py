"""Carga cultivos.json y transiciones.json (claves en español) en tablas con nombres en inglés.

Los archivos de origen NO se modifican. Un valor ausente o desconocido se guarda como NULL.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any

LEVEL = {"alta": "high", "alto": "high", "media": "medium", "medio": "medium", "baja": "low", "bajo": "low"}
EDGE_KIND = {"fuente": "source", "general": "general", "inferida": "inferred", "fuente5": "source5"}
MECHANIZABLE = {"si": "yes", "sí": "yes", "parcial": "partial", "no": "no"}
DATA_TYPE = {"fuente": "source", "inferencia": "inference"}


def _level(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return LEVEL.get(value.strip().lower())


def _reliability_level(text: str | None) -> str:
    """'alta', 'alta en lo medido…', 'baja: NO es evidencia' → high | medium | low."""
    t = (text or "").strip().lower()
    for key, level in (("baja", "low"), ("media", "medium"), ("alta", "high")):
        if t.startswith(key):
            return level
    return "medium"


def _num(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _int(value: Any) -> int | None:
    n = _num(value)
    return int(round(n)) if n is not None else None


def _list(value: Any) -> list:
    return value if isinstance(value, list) else []


def load_sources(conn: sqlite3.Connection, raw_sources: dict[str, dict]) -> None:
    rows = []
    for key, s in raw_sources.items():
        rows.append((
            int(key), s.get("titulo") or f"Fuente {key}", s.get("fiabilidad"),
            _reliability_level(s.get("fiabilidad")), s.get("region"), s.get("url"), s.get("fecha_consulta"),
        ))
    conn.executemany("INSERT INTO sources VALUES (?,?,?,?,?,?,?)", rows)


def crop_row(crop_id: str, f: dict, node: dict) -> tuple:
    soil, climate = f.get("suelo") or {}, f.get("clima") or {}
    cycle, rot = f.get("ciclo_meses") or {}, f.get("efecto_rotacion") or {}
    labor, ease, market = f.get("mano_obra") or {}, f.get("facilidad_cultivo") or {}, f.get("mercado") or {}
    req_irr = climate.get("requiere_riego")
    sources = [
        {"source_id": s.get("fuente"), "location": s.get("ubicacion"), "detail": s.get("dato")}
        for s in _list(f.get("fuentes"))
    ]
    market_sources = sorted({s.get("n") for s in _list(market.get("fuentes")) if isinstance(s.get("n"), int)})
    return (
        crop_id, node.get("nombre") or f.get("nombre"), node.get("familia") or f.get("familia"),
        "non_commercial" if f.get("tipo") == "no_comercial" else "commercial",
        json.dumps(node.get("tags", [])), int(bool(node.get("solo_fuente5"))),
        soil.get("textura"), _num(soil.get("ph_min")), _num(soil.get("ph_max")), soil.get("drenaje"),
        "good" if soil.get("drenaje_requerido") == "bueno" else None, _num(soil.get("profundidad_min_cm")),
        _level(soil.get("exigencia_fertilidad")),
        _num(climate.get("altitud_msnm_min")), _num(climate.get("altitud_msnm_max")),
        None if req_irr is None else int(req_irr == "si"), climate.get("temperatura_c"), climate.get("lluvia_mm"),
        _num(cycle.get("min")), _num(cycle.get("max")),
        json.dumps(_list(f.get("plagas")), ensure_ascii=False), json.dumps(_list(f.get("enfermedades")), ensure_ascii=False),
        int(rot.get("fija_nitrogeno") is True), _level(rot.get("agota_suelo")),
        json.dumps(_list(rot.get("hospedero_de")), ensure_ascii=False),
        json.dumps(_list(rot.get("rompe_ciclos_de")), ensure_ascii=False),
        None if rot.get("mejora_estructura") is None else int(rot.get("mejora_estructura") is True),
        _int(labor.get("nivel_1a5")), _num(labor.get("jornales_ha")),
        MECHANIZABLE.get(str(labor.get("mecanizable") or "").lower()), DATA_TYPE.get(labor.get("tipo_dato")),
        _int(ease.get("nivel_1a5")),
        None if market.get("sin_mercado") else _int(market.get("nivel_1a5")),
        _num(market.get("precio_referencia")), market.get("unidad"), market.get("fecha_dato"),
        _level(market.get("volatilidad")), _level(market.get("confianza")), json.dumps(market_sources),
        f.get("alcance_geografico"), _level(f.get("confianza")) or "low",
        json.dumps(_list(f.get("huecos")), ensure_ascii=False), json.dumps(sources, ensure_ascii=False),
        json.dumps(f, ensure_ascii=False),
    )


def load_structured(conn: sqlite3.Connection, data_dir: Path) -> dict[str, int]:
    crops_doc = json.loads((data_dir / "cultivos.json").read_text(encoding="utf-8"))
    graph = json.loads((data_dir / "transiciones.json").read_text(encoding="utf-8"))
    load_sources(conn, crops_doc.get("fuentes", {}))

    nodes = {n["id"]: n for n in graph["nodos"]}
    profiles = crops_doc["cultivos"]
    missing = set(nodes) - set(profiles)
    if missing:
        raise ValueError(f"Nodos del grafo sin ficha: {sorted(missing)}")
    rows = [crop_row(cid, profiles[cid], nodes[cid]) for cid in nodes]
    conn.executemany(f"INSERT INTO crops VALUES ({','.join('?' * len(rows[0]))})", rows)

    edges = [(e["de"], e["a"], EDGE_KIND[e["tipo"]], e["fuente"]) for e in graph["aristas"]]
    conn.executemany("INSERT INTO transitions VALUES (?,?,?,?)", edges)
    return {"sources": len(crops_doc.get("fuentes", {})), "crops": len(nodes), "transitions": len(edges)}
