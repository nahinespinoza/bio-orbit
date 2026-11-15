"""Datos de la ficha del cultivo recomendado que el agente puede usar para dar un matiz con lo que el agricultor cuenta.

Son textos ya redactados en español sencillo, para citarlos tal cual. Lo que la ficha no trae va en `no_hay_dato`
(así el agente dice «no tengo dato de…» en vez de inventar). Lo que las fuentes contradicen va en `en_conflicto`.
"""

from app.engine.models import Crop

LABOR = {1: "muy poca", 2: "poca", 3: "media", 4: "mucha", 5: "muchísima"}
FERTILITY = {"high": "exigente (alta)", "medium": "media", "low": "poco exigente (baja)"}

# Datos de la ficha que otra fuente ya citada contradice: no se entregan como un hecho.
CONFLICTS = {
    ("amaranto", "fertilidad"): "la ficha dice «baja», pero un ensayo de Ecuador dice que extrae altas cantidades de nitrógeno",
}


def crop_facts(c: Crop) -> dict:
    facts: dict = {}
    missing: list[str] = []
    conflict: dict[str, str] = {}

    if c.labor_days_per_ha:
        source = "dato de la FAO" if c.labor_data_type == "source" else "estimación"
        facts["mano_de_obra"] = f"{LABOR.get(c.labor_level, '')} (nivel {c.labor_level} de 5), unos {c.labor_days_per_ha:g} jornales por hectárea ({source})"
    else:
        missing.append("mano_de_obra")

    if c.requires_irrigation is None:
        missing.append("riego")
    else:
        facts["riego"] = "necesita riego" if c.requires_irrigation else "no necesita riego"

    if c.cycle_min and c.cycle_max:
        facts["ciclo"] = f"{c.cycle_min:g} a {c.cycle_max:g} meses de la siembra a la cosecha"
    else:
        missing.append("ciclo")

    if (c.crop_id, "fertilidad") in CONFLICTS:
        conflict["fertilidad"] = CONFLICTS[(c.crop_id, "fertilidad")]
    elif c.fertility_demand:
        facts["fertilidad"] = FERTILITY[c.fertility_demand]
    else:
        missing.append("fertilidad")

    facts["no_hay_dato"] = missing
    if conflict:
        facts["en_conflicto"] = conflict
    return facts
