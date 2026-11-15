# Pool de cultivos con tags: starter, follower, ender

La base de conocimiento se limita a la **papa** y a las rotaciones en las que aparece. Este pool lista la papa y los cultivos que aparecen en secuencias de las fuentes donde figura la papa (antes, después o entre otros pasos de la misma rotación). Las fichas de los acompañantes traen suelo, clima, ciclo, plagas, efecto en la rotación y un bloque de indicadores (helada, agua, siembra, nutrientes, sanidad) para leer los datos de remote-sensing. Incluyen también mano de obra, mercado y facilidad de cultivo cuando hay dato con fuente.

Cada cultivo lleva **uno o varios tags** según los lugares que puede ocupar en una **iteración** (un ciclo completo de rotación en un lote).

| Tag | Significado | Criterio |
|---|---|---|
| **starter** | Puedes **iniciar** la iteración con este cultivo. | Abre el ciclo en alguna secuencia de las fuentes, o es un cultivo exigente que va en suelo descansado. |
| **follower** | Puede ir **en medio**. | Aparece entre otros cultivos: sigue a uno y prepara el siguiente. |
| **ender** | Puedes **terminar** la iteración con este cultivo. | Cierra el ciclo: recupera el suelo (pasto, abono verde, barbecho) o es el último cultivo antes de reiniciar o de un descanso. |

> **Origen de los tags:** el sistema de tags es una **propuesta propia**. Un cultivo recibe un tag si **alguna secuencia de las fuentes** lo pone en esa posición.
> **Alcance:** sierra andina. Fuentes: 1 = FAO producción orgánica (Ecuador), 2 = FAO guía de campo (Perú y Bolivia), 3 = MAGAP.

---

## Papa

| Cultivo | Tags | Base |
|---|---|---|
| Papa | `starter` `follower` | Starter: va tras el pasto en el Cuadro 5 y exige terreno descansado (fuente 1). Follower: la segunda siembra de papa del Cuadro 5, y «cebada o papa» en el año 3 de la variante B (fuente 1). |

## Cultivos acompañantes

Cultivos que aparecen en secuencias de las fuentes donde figura la papa (antes, después o entre otros pasos de la misma rotación). Sus fichas completas están en `cultivos.json`.

| Cultivo | Familia | Tags |
|---|---|---|
| Oca | Oxalidáceas | `follower` |
| Lizas | Baselláceas | `follower` |
| Olluco / añu | Baselláceas | `follower` |
| Cebada | Gramíneas | `follower` `ender` |
| Trigo | Gramíneas | `follower` `ender` |
| Avena | Gramíneas | `follower` `ender` |
| Maíz | Gramíneas | `starter` `follower` `ender` |
| Quinua | Amarantáceas | `follower` |
| Amaranto / ataco | Amarantáceas | `follower` |
| Qañiwa (cañihua) | Amarantáceas | `follower` |
| Haba | Leguminosas | `starter` `follower` `ender` |
| Chocho (tarwi) | Leguminosas | `starter` `follower` `ender` |
| Arveja | Leguminosas | `follower` `ender` |
| Lenteja | Leguminosas | `follower` |
| Abono verde (vicia, tarwi, tréboles) | Leguminosas | `follower` `ender` |
| Pasto / pradera | Pastos | `starter` `ender` |
| Barbecho / descanso | Descanso | `starter` `ender` |

---

## Cómo se arma una iteración con los tags

Una iteración válida:
1. **Empieza con un cultivo que tenga el tag `starter`.**
2. **Lleva cultivos intermedios con `follower`**, sin repetir cultivo ni familia seguidos (filtros F1 y F2 de [01-reglas-elegir-siguiente-cultivo.md](01-reglas-elegir-siguiente-cultivo.md)).
3. **Termina con un cultivo que tenga `ender`.**

Un cultivo con varios tags puede ocupar cualquiera de sus posiciones, pero solo **una por vez** en la misma iteración.

Ejemplos (todos incluyen papa):

| Iteración | Secuencia |
|---|---|
| Cuadro 5 (fuente 1), 4 etapas | Papa (starter), cebada (follower), haba (follower), pasto (ender) |
| Rotación de haba (fuente 1) | Haba (starter), papa (follower), cebada (follower), chocho (ender) |
| Variante *(propuesta)* | Papa (starter), quinua (follower), chocho (follower), pasto (ender) |
| Variante con otros tubérculos *(propuesta)* | Papa (starter), cebada (follower), oca (follower), pasto (ender) |

## Límites

- **Tags propios:** ninguna fuente usa estos tres tags. Un cultivo puede ocupar otra posición en una finca concreta.
- **Tag no implica recomendación:** que un cultivo tenga `ender` o `starter` solo dice que alguna fuente lo pone ahí. La conveniencia en un lote concreto se decide con [03-tabla-de-puntaje.md](03-tabla-de-puntaje.md).
- **Rotaciones sin descanso:** la rotación de haba de la fuente 1 termina en un cultivo (chocho), no en un descanso. Por eso `ender` incluye también cultivos, no solo descanso.

Documentos relacionados: [01-reglas-elegir-siguiente-cultivo.md](01-reglas-elegir-siguiente-cultivo.md), [03-tabla-de-puntaje.md](03-tabla-de-puntaje.md), [05-calendario-4-anos-por-lote.md](05-calendario-4-anos-por-lote.md), [07-indicadores-remote-sensing.md](07-indicadores-remote-sensing.md).
