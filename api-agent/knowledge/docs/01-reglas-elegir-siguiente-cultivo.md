# Reglas claras para elegir el siguiente cultivo

Reglas de decisión para escoger el cultivo de la próxima siembra en un lote, limitadas a la **papa** y a las rotaciones en las que aparece. Parten de las fuentes listadas en [04-contexto-rotacion-de-cultivos.md](04-contexto-rotacion-de-cultivos.md) y coinciden con los filtros del motor del agente.

> **Alcance:** casi todo el respaldo es de la **sierra andina** (Ecuador, Perú, Bolivia). Para costa o Amazonía hay muy poca evidencia confiable.
> **Marcas:** las reglas con fuente citan el número de la fuente. Lo marcado como *(propuesta)* es una síntesis propia o una regla del motor, no lo afirma ninguna fuente.

---

## 1. Filtros: si falla uno, el cultivo se descarta

| Filtro | Regla | Fuente |
|---|---|---|
| **F1. No repetir cultivo** | No sembrar el mismo cultivo en el mismo lote en el ciclo siguiente. **Excepción (F1b):** maíz y quinua admiten hasta 2 temporadas seguidas; la tercera se descarta. | 1 (regla general). Excepción del maíz: fuente 2, Cuadro 25 (Cusco), con secuencias maíz, maíz, maíz, papa. Excepción de la quinua: sin fuente *(propuesta del motor)*. |
| **F2. No repetir familia botánica** | No sembrar seguidas especies de la misma familia (pasto y descanso no cuentan). Para las solanáceas, como la papa, deben pasar **3 ciclos** sin solanáceas antes de repetir: la papa puede volver en el cuarto ciclo. | 5 (sin respaldo técnico; coincide con el principio de 1 y 2). La fuente 5 habla de 3 a 4 años; la ventana de 3 ciclos es regla del motor *(propuesta)* y se cuenta en ciclos, no en años. |
| **F3. No hospedar la plaga actual** | Elegir un cultivo que no sea hospedero de la plaga o enfermedad del ciclo anterior. El motor usa la lista de hospederos de cada ficha: por ejemplo, descarta el haba si la plaga fue el gorgojo de los Andes. | 1, 2 |
| **F4. Adaptación** | El cultivo debe adaptarse a la altitud del lote, al agua disponible (riego o secano) y al suelo (pH, drenaje, profundidad). | 1, 2 (rangos de cada ficha) |

**Nota sobre la papa repetida:** el Cuadro 5 de la fuente 1 pone 2 siembras de papa tras el pasto. El motor no permite papa tras papa (F1), así que propone otro cultivo en el ciclo siguiente.

---

## 2. Reglas por cultivo anterior

| Si el cultivo anterior fue... | Elegir como siguiente | Fuente |
|---|---|---|
| **Papa** | Un cereal (cebada, trigo, maíz, quinua, ataco) y después una leguminosa (haba, arveja, vicia). Secuencia del Cuadro 5. En zonas altas no todos sirven: ver la sección 3. | 1 |
| **Leguminosa (haba, chocho) antes de papa** | Papa u otro cultivo exigente. El chocho antes de la papa mejora su vigor y baja la pulguilla. | 1 |
| **Amaranto** | En la secuencia papa, amaranto, cereales, haba, el amaranto sigue a la papa. | 1 |

---

## 3. Altitud: qué cultivos quedan en zonas altas

El Cuadro 5 es para la sierra en general. El motor revisa la altitud del lote contra el rango de la ficha de cada cultivo, con un **margen de 200 m**: fuera del rango pero dentro del margen da una advertencia; más allá del margen, descarta (filtro F4).

| Cultivo | Rango de la ficha (msnm) | El motor lo descarta por encima de |
|---|---|---|
| Arveja | 1 700 a 2 800 | 3 000 m |
| Maíz | 2 200 a 3 000 | 3 200 m |
| Quinua | 2 200 a 3 000 | 3 200 m |
| Lenteja | 1 000 a 3 000 | 3 200 m |
| Amaranto / ataco | 2 700 a 3 200 | 3 400 m |
| Trigo | 0 a 3 300 | 3 500 m |
| Haba, chocho, abono verde | hasta 3 600 | 3 800 m |
| Papa | 2 400 a 3 700 | 3 900 m |
| Cebada | 0 a 3 900 | 4 100 m |
| Avena | 500 a 4 000 | 4 200 m |

- **Por encima de unos 3 500 m**, los cereales que quedan son **cebada y avena**. Maíz, quinua y ataco se descartan desde 3 200 a 3 400 m, y el trigo desde 3 500 m.
- De las leguminosas quedan **haba, chocho y abono verde** (con advertencia sobre 3 600 m). La arveja y la lenteja se descartan.
- También pasan **oca** (hasta 4 000 m), **olluco / lizas** (hasta 4 200 m), **pasto** y **barbecho**.
- La **qañiwa** va al revés: su ficha da 3 800 a 4 200 m, así que el motor la descarta por **debajo** de 3 600 m.
- La ficha de quinua cita variedades de altura (Taruka Chaqui, 2 800 a 3 800 m, fuente 1), pero el motor usa el rango general de 2 200 a 3 000 m.

---

## 4. Reglas de fertilidad y sanidad

1. **Después de un cultivo exigente en nutrientes como la papa, poner una leguminosa.** Fuentes 1, 2.
2. **Contra enfermedades del suelo de la papa (nematodos y otras), alternar con cereales, arveja y haba.** Fuente 2.
3. **Contra el gorgojo de los Andes, rotar con cultivos que no lo hospedan.** La fuente 2 da como ejemplo la secuencia papa, cebada, tarwi. También nombra como plantas hospederas del gorgojo el **haba**, el **ataco**, el nabo, el alfilerillo, el kikuyo y las papas «huachas» que quedan tras la cosecha. Por eso el motor descarta el haba (filtro F3) si la plaga del ciclo anterior fue el gorgojo. Fuente 2.
4. **El pasto o el barbecho cierran el ciclo.** En papa, pasto durante varios años. En sistemas comunales andinos, descansos de 3 a 10 años. Fuentes 1, 2.
5. **Si el descanso previo fue mayor de 5 años, reducir el fertilizante en papa.** Fuente 2.

---

## 5. Proceso de decisión

1. **Registrar** los últimos 3 años del lote y el cultivo actual. *(propuesta, apoyada en fuente 5)*
2. **Aplicar los filtros F1 a F4** a la lista de candidatos.
3. **Puntuar** los que pasan con el método de la [tabla de puntaje](03-tabla-de-puntaje.md).
4. **Desempatar** por disponibilidad de semilla, maquinaria y mercado. *(propuesta; el motor no lo hace)*
5. **Anotar el resultado** del ciclo en una bitácora por lote para decidir mejor la siguiente vez.

---

## 6. Lo que estas reglas no dicen

- No hay periodos obligatorios de rotación en ninguna fuente. La ventana de 3 ciclos entre solanáceas es del motor, no de una fuente.
- Ninguna fuente compara rotaciones entre sí con rendimientos.
- Las secuencias de Perú y Bolivia (fuente 2) vienen de sistemas comunales; no se copian tal cual a una finca familiar de Ecuador.

Documentos relacionados: [02-rotacion-explicacion-beneficios-caracteristicas.md](02-rotacion-explicacion-beneficios-caracteristicas.md), [03-tabla-de-puntaje.md](03-tabla-de-puntaje.md), [05-calendario-4-anos-por-lote.md](05-calendario-4-anos-por-lote.md), [06-pool-de-cultivos-con-tags.md](06-pool-de-cultivos-con-tags.md).
