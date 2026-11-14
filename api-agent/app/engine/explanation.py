"""Explicación en español del resultado del motor (plantilla de ESPECIFICACION.md §6)."""

PRIORITY_LABEL = {"market_value": "valor de mercado", "speed": "rapidez (ciclo corto)",
                  "fewer_pests": "menos plagas", "low_labor": "menor mano de obra"}
APTITUDE_LABEL = {"fertility_vs_demand": "fertilidad frente a exigencia", "graph_sequence": "secuencia en el grafo",
                  "nitrogen_balance": "balance de nitrógeno", "texture": "textura", "compaction": "compactación"}
CONFIDENCE_LABEL = {"high": "alta", "medium": "media", "low": "baja"}


def _pct(x: float) -> str:
    return f"{round(x * 100)} %"


def explain(result: dict) -> str:
    lines: list[str] = []
    status = result["status"]
    if status == "invalid_input":
        lines.append("No puedo recomendar todavía; necesito corregir lo siguiente:")
        for e in result["errors"]:
            sug = f" ¿Quiso decir: {', '.join(e['suggestions'])}?" if e.get("suggestions") else ""
            lines.append(f"- {e['message']}{sug}")
        return "\n".join(lines)
    if status == "no_candidates":
        lines += [result["message"], "", "Descartados:"]
        lines += [f"- {d['crop']}: {d['filter']} — {d['reason']}" for d in result["discarded"]]
        return "\n".join(lines)

    inp = result["input"]
    situation = "tierra nueva" if inp.get("new_land") else "cultivos previos (reciente → antiguo): " + \
        ", ".join(c or "desconocido" for c in inp.get("previous_crops", []))
    lines.append("## Recomendación para el lote")
    lines.append(f"Situación: {situation}.")
    lines.append("Prioridades (en orden): " + ", ".join(
        f"{PRIORITY_LABEL[p['priority']]} ({_pct(p['weight'])})" for p in result["priority_weights"]) + ".")
    soil = ", ".join(f"{k}: {v}" for k, v in inp.get("soil", {}).items())
    climate = inp.get("climate", {})
    lines.append(f"Suelo: {soil}. Altitud: {climate.get('altitude_masl') or 'desconocida'} m. Riego: {climate.get('irrigation')}.")
    lines.append("")

    def block(t: dict, title: str) -> None:
        lines.append(f"### {title}: {t['name']} — puntaje {t['score']:g}/100 (confianza {CONFIDENCE_LABEL[t['confidence']]})")
        lines.append("Por qué:")
        for p in t["breakdown"]["priorities"]:
            flag = " · DATO FALTANTE" if p["missing"] else ""
            lines.append(f"- {PRIORITY_LABEL[p['priority']]} (peso {_pct(p['weight'])}, subpuntaje {round(p['value'])}/100): "
                         f"{p['detail']}. Fuente: {p['source'] or 'sin dato'}; confianza {CONFIDENCE_LABEL[p['confidence']]}{flag}.")
        for a in t["breakdown"]["aptitude"]:
            lines.append(f"- agronomía · {APTITUDE_LABEL.get(a['name'], a['name'])} ({round(a['value'])}/100): {a['detail']}.")
        if t["transition"]:
            lines.append(f"- Transición desde el cultivo anterior: {t['transition']['kind']} — {t['transition']['source_note']}.")
        lines.extend(f"- ⚠ {w}" for w in t["warnings"])
        lines.append("")

    block(result["recommendation"], "Sembrar ahora")
    for i, alt in enumerate(result["alternatives"], start=1):
        block(alt, f"Alternativa {i}")

    rot = result["rotation"]
    if rot:
        lines.append(f"### Rotación sugerida ({rot['cycles']} ciclos)")
        for s in rot["sequence"]:
            tr = f"{s['transition']['kind']} ({s['transition']['source_note']})" if s["transition"] else "inicio"
            lines.append(f"{s['cycle']}. {s['name']} [{s['role']}] — puntaje {s['score']:g}; transición: {tr}; "
                         f"confianza {CONFIDENCE_LABEL[s['confidence']]}")
        lines.append("Cierra con un cultivo «ender»." if rot["ends_with_ender"] else "⚠ No cierra con un cultivo «ender».")
        lines += [f"⚠ {w}" for w in rot["warnings"]]
        lines.append("")
    if result["discarded"]:
        lines.append("### Descartados por filtros")
        lines += [f"- {d['crop']}: {d['filter']} — {d['reason']}" for d in result["discarded"]]
        lines.append("")
    if result["warnings"] or result["missing_data"]:
        lines.append("### Advertencias y datos que faltan")
        lines += [f"- {w['message']}" for w in result["warnings"]]
        lines += [f"- Falta dato: {m}" for m in result["missing_data"]]
        lines.append("")
    lines.append(f"_{result['note']}_")
    return "\n".join(lines)
