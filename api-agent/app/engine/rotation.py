"""Rotación: búsqueda exhaustiva en el grafo (ESPECIFICACION.md §5).

Se prefieren los caminos completos que terminan en un cultivo `ender`; entre ellos, el de mayor puntaje medio.
"""

from dataclasses import dataclass

from app.engine.filters import hard_filters
from app.engine.models import KnowledgeBase, PlotInput
from app.engine.scoring import round1, score_crop


@dataclass
class _Path:
    ids: list[str]
    steps: list[dict]
    total: float

    @property
    def mean(self) -> float:
        return self.total / len(self.ids)


def build_rotation(first: str, history: list[str], plot: PlotInput, kb: KnowledgeBase) -> dict | None:
    length = plot.rotation_cycles
    max_non_commercial = max(1, length // 4)
    best: list[_Path | None] = [None]

    def rank(p: _Path) -> int:
        return (2 if len(p.ids) == length else 0) + (1 if kb.crops[p.ids[-1]].has_tag("ender") else 0)

    def consider(p: _Path) -> None:
        b = best[0]
        if b is None or rank(p) > rank(b) or (rank(p) == rank(b) and p.mean > b.mean + 1e-9):
            best[0] = p

    def dfs(path: _Path, hist: list[str], non_commercial: int) -> None:
        if len(path.ids) == length:
            consider(path)
            return
        last = path.ids[-1]
        children = 0
        for edge in kb.edges.get(last, []):
            cid = edge.to_crop
            if cid in path.ids:  # un cultivo no se repite dentro de la rotación
                continue
            if edge.kind == "source5" and not plot.use_source5:
                continue
            is_nc = not kb.crops[cid].is_commercial
            if is_nc and non_commercial >= max_non_commercial:
                continue
            step_history = [last, *hist]
            if hard_filters(cid, step_history, plot, kb, first_step=False):
                continue
            s = score_crop(cid, step_history, plot, kb)
            children += 1
            dfs(_Path([*path.ids, cid], [*path.steps, s], path.total + s["score"]), step_history, non_commercial + int(is_nc))
        if children == 0:
            consider(path)  # callejón sin salida: camino parcial

    s0 = score_crop(first, history, plot, kb)
    dfs(_Path([first], [s0], s0["score"]), history, int(not kb.crops[first].is_commercial))
    b = best[0]
    if b is None:
        return None

    ends = kb.crops[b.ids[-1]].has_tag("ender")
    warnings = []
    if len(b.ids) < length:
        warnings.append(f"No se encontró una rotación de {length} ciclos que cumpla F1 y F2 con el grafo; se entrega una de {len(b.ids)}.")
    if not ends:
        warnings.append("La rotación no termina en un cultivo «ender» (no hay camino que cierre el ciclo con las reglas actuales).")
    if any(s["transition"] and s["transition"]["kind"] == "inferred" for s in b.steps):
        warnings.append("Algún paso usa una transición inferida (propuesta propia, sin fuente).")
    return {
        "cycles": len(b.ids), "ends_with_ender": ends,
        "sequence": [{"cycle": i + 1, "crop": s["crop"], "name": s["name"], "role": "/".join(kb.crops[s["crop"]].tags),
                      "score": s["score"], "transition": s["transition"], "confidence": s["confidence"]}
                     for i, s in enumerate(b.steps)],
        "average_score": round1(b.mean),
        "warnings": warnings,
    }
