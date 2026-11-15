"""Lectura de fichas y grafo desde SQLite."""

import json
import sqlite3
from collections.abc import Sequence
from pathlib import Path

from app.engine.advisories import read_signals
from app.engine.models import Crop, KnowledgeBase, Transition, norm

STRUCTURED_DIR = Path(__file__).resolve().parents[2] / "knowledge" / "structured"


def _bool(value: int | None) -> bool | None:
    return None if value is None else bool(value)


def _crop(row: sqlite3.Row) -> Crop:
    return Crop(
        crop_id=row["crop_id"], name=row["name"], family=row["family"], crop_type=row["crop_type"],
        tags=tuple(json.loads(row["tags_json"])), source5_only=bool(row["source5_only"]),
        soil_texture_text=row["soil_texture_text"], ph_min=row["soil_ph_min"], ph_max=row["soil_ph_max"],
        drainage_required=row["soil_drainage_required"], min_depth_cm=row["soil_min_depth_cm"],
        fertility_demand=row["soil_fertility_demand"],
        altitude_min=row["altitude_min_masl"], altitude_max=row["altitude_max_masl"],
        requires_irrigation=_bool(row["requires_irrigation"]),
        cycle_min=row["cycle_months_min"], cycle_max=row["cycle_months_max"],
        pests=tuple(json.loads(row["pests_json"])), diseases=tuple(json.loads(row["diseases_json"])),
        fixes_nitrogen=bool(row["fixes_nitrogen"]), depletes_soil=row["depletes_soil"],
        host_of=tuple(norm(h) for h in json.loads(row["host_of_json"])),
        breaks_cycles_of=tuple(norm(h) for h in json.loads(row["breaks_cycles_of_json"])),
        improves_structure=_bool(row["improves_structure"]),
        labor_level=row["labor_level"], labor_days_per_ha=row["labor_days_per_ha"],
        labor_mechanizable=row["labor_mechanizable"], labor_data_type=row["labor_data_type"],
        market_level=row["market_level"], market_price=row["market_price"], market_unit=row["market_unit"],
        market_date=row["market_date"], market_volatility=row["market_volatility"],
        market_confidence=row["market_confidence"], market_source_ids=tuple(json.loads(row["market_source_ids_json"])),
        geographic_scope=row["geographic_scope"], confidence=row["confidence"],
        sources=tuple(json.loads(row["sources_json"])),
    )


def load_advisory_data(structured_dir: Path = STRUCTURED_DIR) -> tuple[dict, dict]:
    """(sensibilidades por cultivo, alertas vigentes del remote-sensing). Archivo ausente = sin advertencias (no es un error)."""
    sens_file, rs_file = structured_dir / "sensibilidades.json", structured_dir / "remote_sensing.json"
    sens = json.loads(sens_file.read_text(encoding="utf-8"))["cultivos"] if sens_file.exists() else {}
    signals = read_signals(json.loads(rs_file.read_text(encoding="utf-8"))) if rs_file.exists() else {}
    return sens, signals


def load_knowledge_base(conn: sqlite3.Connection, structured_dir: Path = STRUCTURED_DIR) -> KnowledgeBase:
    crops = {r["crop_id"]: _crop(r) for r in conn.execute("SELECT * FROM crops ORDER BY rowid")}
    edges: dict[str, list[Transition]] = {}
    for r in conn.execute("SELECT * FROM transitions ORDER BY rowid"):
        edges.setdefault(r["from_crop"], []).append(Transition(r["from_crop"], r["to_crop"], r["kind"], r["source_note"]))
    sensitivities, signals = load_advisory_data(structured_dir)
    return KnowledgeBase(crops=crops, edges=edges, sensitivities=sensitivities, signals=signals)


def list_crops(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT crop_id, name, family, crop_type, tags_json, confidence, source5_only FROM crops ORDER BY rowid"
    ).fetchall()
    return [{"crop_id": r["crop_id"], "name": r["name"], "family": r["family"], "crop_type": r["crop_type"],
             "tags": json.loads(r["tags_json"]), "confidence": r["confidence"],
             "source5_only": bool(r["source5_only"])} for r in rows]


def get_crop_profile(conn: sqlite3.Connection, crop_id: str) -> dict | None:
    """Ficha original (en español) + transiciones de salida + fuentes citadas."""
    row = conn.execute("SELECT * FROM crops WHERE crop_id = ?", (crop_id,)).fetchone()
    if row is None:
        return None
    sources = json.loads(row["sources_json"])
    ids = sorted({s["source_id"] for s in sources if isinstance(s.get("source_id"), int)}
                 | set(json.loads(row["market_source_ids_json"])))
    source_rows = conn.execute(
        f"SELECT source_id, title, reliability_level, url FROM sources WHERE source_id IN ({','.join('?' * len(ids))})", ids
    ).fetchall() if ids else []
    next_crops = [{"to_crop": r["to_crop"], "kind": r["kind"], "source_note": r["source_note"]}
                  for r in conn.execute("SELECT * FROM transitions WHERE from_crop = ? ORDER BY rowid", (crop_id,))]
    return {
        "crop_id": row["crop_id"], "name": row["name"], "family": row["family"], "crop_type": row["crop_type"],
        "tags": json.loads(row["tags_json"]), "confidence": row["confidence"],
        "profile": json.loads(row["profile_json"]),
        "next_crops": next_crops,
        "sources": [dict(r) for r in source_rows],
    }


# Secciones que el agente puede pedir. Los `indicadores*` de la ficha son notas de investigación: no se entregan
# (lo útil de ellos ya está depurado en `sensibilidades`).
PROFILE_SECTIONS: tuple[str, ...] = (
    "suelo", "clima", "ciclo_meses", "plagas", "enfermedades", "efecto_rotacion", "mano_obra", "facilidad_cultivo",
    "mercado", "huecos", "fuentes", "siguientes", "sensibilidades",
)
NO_SENSITIVITIES = {"valor": None, "nota": "Sin datos de sensibilidad con cita de Ecuador o los Andes."}


def get_crop_sections(conn: sqlite3.Connection, crop_id: str, sections: Sequence[str], sensitivities: dict) -> dict | None:
    """Cabecera corta del cultivo + solo las secciones pedidas. None si el cultivo no existe."""
    invalid = [s for s in sections if s not in PROFILE_SECTIONS]
    if invalid:
        raise ValueError(f"Secciones no válidas: {', '.join(invalid)}. Opciones: {', '.join(PROFILE_SECTIONS)}.")
    full = get_crop_profile(conn, crop_id)
    if full is None:
        return None
    profile = full["profile"]

    def value(section: str):
        if section == "siguientes":
            return full["next_crops"]
        if section == "fuentes":
            return {"citas": profile.get("fuentes"), "detalle": full["sources"]}
        if section == "sensibilidades":
            return sensitivities.get(crop_id) or NO_SENSITIVITIES
        return profile.get(section)

    return {
        **{k: full[k] for k in ("crop_id", "name", "family", "crop_type", "tags", "confidence")},
        "alcance_geografico": profile.get("alcance_geografico"),
        "sections": {s: value(s) for s in sections},
    }
