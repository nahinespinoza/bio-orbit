# Pool de cultivos con tags: starter, follower, ender

Cada cultivo lleva **uno o varios tags** según los lugares que puede ocupar en una **iteración** (un ciclo completo de rotación en un lote).

| Tag | Significado | Criterio |
|---|---|---|
| **starter** | Puedes **iniciar** la iteración con este cultivo. | Abre el ciclo en alguna secuencia de las fuentes, o es un cultivo exigente que va en suelo descansado. |
| **follower** | Puede ir **en medio**. | Aparece entre otros cultivos: sigue a uno y prepara el siguiente. |
| **ender** | Puedes **terminar** la iteración con este cultivo. | Cierra el ciclo: recupera el suelo (pasto, abono verde, barbecho) o es el último cultivo antes de reiniciar o de un descanso en alguna secuencia de las fuentes. |

> **Origen de los tags:** el sistema de tags es una **propuesta propia**. Un cultivo recibe un tag si **alguna secuencia de las fuentes** lo pone en esa posición. Donde la fuente no dice el orden, el tag es **inferencia mía** y lo marco.
> **Alcance:** sierra andina. Fuentes: 1 = FAO producción orgánica (Ecuador), 2 = FAO guía de campo (Perú y Bolivia), 3 = MAGAP, 4 = Redalyc (Tumbaco), 5 = blog Radeco (baja fiabilidad).

---

## Pool con tags

### Tubérculos y raíces
| Cultivo | Tags | Base |
|---|---|---|
| Papa | `starter` `follower` | Starter: va tras el pasto en el Cuadro 5 y exige terreno descansado (fuente 1). Follower: la segunda siembra de papa del Cuadro 5, y «cebada o papa» en el año 3 de la variante B (fuente 1). |
| Melloco | `follower` | Se siembra después de haba, chocho, quinua o cereales (fuente 1). |
| Oca | `follower` | Igual que melloco (fuente 1). En el muyuy de Cusco va tras la papa (fuente 2). |
| Mashua | `follower` | Alternar con leguminosas y cereales (fuente 1). |
| Olluco / añu | `follower` | En el muyuy de Cusco sigue a oca o lizas (fuente 2). |
| Lizas | `follower` | Muyuy de Cusco, tras la papa (fuente 2). |
| Achira | `follower` | Tras haba, chocho o cereales (fuente 1). |
| Jícama | `follower` | Tras haba, chocho o cereales (fuente 1). |
| Zanahoria blanca (arracacha) | `follower` | Se rota con leguminosas (fuente 1). |

### Cereales
| Cultivo | Tags | Base |
|---|---|---|
| Cebada | `follower` `ender` | Follower: sigue a la papa en el Cuadro 5 (fuente 1). Ender: cierra el muyuy de Cusco antes del descanso (fuente 2). |
| Trigo | `follower` `ender` | Follower: sigue a la papa (fuente 1). Ender: «haba o trigo» en el año 4 de la variante B de haba (fuente 1). |
| Avena | `follower` `ender` | Follower: entra tras cereal en Puno (fuente 2). Ender: «haba o avena» antes del barbecho en la zona circunlacustre (fuente 2). |
| Maíz | `starter` `follower` `ender` | Starter y ender: en Cusco la secuencia maíz, trigo, haba, maíz abre y cierra con maíz (fuente 2). Follower: sigue a papa o leguminosa; máximo 2 temporadas seguidas (fuente 1). |

### Pseudocereales
| Cultivo | Tags | Base |
|---|---|---|
| Quinua | `follower` | Máximo 2 temporadas seguidas; rota con haba, chocho, papa o maíz (fuente 1). |
| Amaranto / ataco / kiwicha | `follower` | Papa, amaranto, cereales, haba (fuente 1). |
| Qañiwa (cañihua) | `follower` | Puno: papa, qañiwa, cebada (fuente 2). |

### Leguminosas de grano
| Cultivo | Tags | Base |
|---|---|---|
| Haba | `starter` `follower` `ender` | Starter: abre la rotación de haba (haba, papa, cebada, haba o chocho) (fuente 1). Follower: sigue al cereal en el Cuadro 5. Ender: la leguminosa es la última etapa cultivada antes del pasto en el Cuadro 5, y cierra la variante de haba. |
| Chocho (tarwi) | `starter` `follower` `ender` | Starter: antes de papa mejora su vigor y baja la pulguilla (fuente 1). Follower: entra tras cereales. Ender: cierra la rotación de haba («haba o chocho», fuente 1). |
| Arveja | `follower` `ender` | Es la leguminosa del Cuadro 5, última etapa cultivada antes del pasto (fuente 1). |
| Lenteja | `follower` | Rotación de zanahoria blanca (fuente 1). |
| Fréjol | `starter` `follower` | Rotación fréjol-maíz en Tumbaco: abre en el ciclo 1 y alterna con maíz (fuente 4). |

### Abonos verdes
| Cultivo | Tags | Base |
|---|---|---|
| Vicia (abono verde) | `follower` `ender` | Se incorpora en floración (fuente 2). *Inferencia mía: sirve entre cultivos o al cierre.* |
| Tarwi (abono verde) | `follower` `ender` | Aporta 60 a 80 kg N/ha al cultivo siguiente (fuente 2). *Inferencia mía.* |
| Trébol de carretilla | `follower` `ender` | Abono verde para los Andes (fuente 2). *Inferencia mía.* |
| Trébol de flor amarilla | `follower` `ender` | Idem (fuente 2). *Inferencia mía.* |
| Vicia villosa | `follower` `ender` | Idem (fuente 2). *Inferencia mía.* |

### Pastos y descanso
| Cultivo | Tags | Base |
|---|---|---|
| Pasto | `starter` `ender` | Abre y cierra el ciclo en el Cuadro 5 (fuente 1). |
| Barbecho / descanso | `starter` `ender` | Descansos de 3 a 10 años en sistemas comunales (fuente 2). Precede a la papa. *Inferencia mía en el tag starter.* |
| Alfalfa | `ender` | Tras 6 a 8 años, suelo muy enriquecido; luego un cultivo alimenticio (fuente 2). |
| Trébol blanco con raigrás y dactilo | `ender` | 3 a 5 años enriquecen el suelo (fuente 2). Propuestos para los años de descanso de layme y aynoka. |

### Cultivos especiales
| Cultivo | Tags | Base |
|---|---|---|
| Maca | `ender` | Extrae muchos nutrientes y requiere hasta 10 años de descanso después (fuente 2). *Inferencia mía: el cultivo que precede al descanso largo.* |

### Solo en la fuente 5 (baja fiabilidad, usar como referencia)
| Cultivo | Tags | Base |
|---|---|---|
| Tomate | `starter` `follower` | Solanácea exigente; en la secuencia intensiva va tras maíz y fréjol (fuente 5). |
| Soya | `follower` `ender` | Secuencia de costa maíz y soya en 2 años (fuente 5). |
| Arroz, sorgo | `follower` | Gramíneas (fuente 5). |
| Brócoli, coliflor, col | `follower` `ender` | «Cultivos de limpieza»; el brócoli cierra la secuencia intensiva de 4 cultivos (fuente 5). |
| Zanahoria | `follower` | Umbelífera, tras gramíneas o leguminosas (fuente 5). |
| Brachiaria (pastura) | `ender` | Cultivo-pastura de 3 a 6 años (fuente 5). |

---

## Índice inverso: qué cultivos tiene cada tag

| Tag | Cultivos |
|---|---|
| **starter** | Papa, maíz, haba, chocho, fréjol, pasto, barbecho. Tomate (fuente 5). |
| **follower** | Papa, melloco, oca, mashua, olluco, lizas, achira, jícama, arracacha, cebada, trigo, avena, maíz, quinua, amaranto, qañiwa, haba, chocho, arveja, lenteja, fréjol, abonos verdes. Tomate, soya, arroz, sorgo, brócoli, coliflor, col y zanahoria (fuente 5). |
| **ender** | Cebada, trigo, avena, maíz, haba, chocho, arveja, abonos verdes, pasto, barbecho, alfalfa, tréboles de pasto, maca. Soya, brócoli, coliflor, col y brachiaria (fuente 5). |

---

## Cómo se arma una iteración con los tags

Una iteración válida:
1. **Empieza con un cultivo que tenga el tag `starter`.**
2. **Lleva cultivos intermedios con `follower`**, sin repetir cultivo ni familia seguidos (filtros F1 y F2 de [01-reglas-elegir-siguiente-cultivo.md](01-reglas-elegir-siguiente-cultivo.md)).
3. **Termina con un cultivo que tenga `ender`.**

Un cultivo con varios tags puede ocupar cualquiera de sus posiciones, pero solo **una por vez** en la misma iteración.

Ejemplos:

| Iteración | Secuencia |
|---|---|
| Cuadro 5 (fuente 1), 4 etapas | Papa (starter), cebada (follower), haba (follower), pasto (ender) |
| Rotación de haba (fuente 1) | Haba (starter), papa (follower), cebada (follower), chocho (ender) |
| Maíz en Cusco (fuente 2), 4 años | Maíz (starter), trigo (follower), haba (follower), maíz (ender) |
| Variante *(propuesta)* | Papa (starter), quinua (follower), chocho (follower), abono verde de vicia (ender) |
| Variante con otros tubérculos *(propuesta)* | Papa (starter), cebada (follower), oca (follower), pasto (ender) |

## Límites

- **Tags propios:** ninguna fuente usa estos tres tags. Un cultivo puede ocupar otra posición en una finca concreta.
- **Tag no implica recomendación:** que un cultivo tenga `ender` o `starter` solo dice que alguna fuente lo pone ahí. La conveniencia en un lote concreta se decide con [03-tabla-de-puntaje.md](03-tabla-de-puntaje.md).
- **Ciclos con el mismo cultivo al inicio y al final:** el ejemplo del maíz de Cusco (fuente 2) repite maíz al reiniciar, lo que choca con la regla F1; la fuente lo presenta como un sistema real, con riego.
- **Rotaciones sin descanso:** la rotación de haba de la fuente 1 termina en un cultivo (chocho), no en un descanso. Por eso `ender` incluye también cultivos, no solo descanso.

Documentos relacionados: [03-tabla-de-puntaje.md](03-tabla-de-puntaje.md), [05-calendario-4-anos-por-lote.md](05-calendario-4-anos-por-lote.md).
