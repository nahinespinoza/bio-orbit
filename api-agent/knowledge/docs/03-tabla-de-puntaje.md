# Tabla de puntaje para elegir el siguiente cultivo en rotaciones con papa

> **Aviso:** este documento describe cómo puntúa el motor del agente. Los pesos, las fórmulas y las escalas son una **propuesta propia** *(propuesta)*: ninguna fuente define un método de puntuación. Los datos que se puntúan salen de las fichas de cada cultivo, que citan sus fuentes (sobre todo 1 y 2).

## 1. Cómo se usa

1. **Candidatos:** los cultivos que el grafo de transiciones pone después del cultivo anterior. Si el lote es tierra nueva, los cultivos con tag `starter` (ver [06-pool-de-cultivos-con-tags.md](06-pool-de-cultivos-con-tags.md)).
2. **Filtros:** se descartan los que fallan F1 a F4 de [01-reglas-elegir-siguiente-cultivo.md](01-reglas-elegir-siguiente-cultivo.md) (mismo cultivo, misma familia, hospedero de la plaga, falta de adaptación).
3. **Puntaje de 0 a 100:** **puntaje = 0,75 · P + 0,25 · A**.
   - **P** = prioridades del agricultor (75 %).
   - **A** = aptitud agronómica (25 %).
4. **Orden:** de mayor a menor puntaje. Si hay empate exacto, el motor ordena por nombre; no desempata por semilla ni maquinaria.
5. **Cultivos sin mercado** (abono verde, pasto, barbecho): solo se proponen para el ciclo inmediato si el suelo es pobre, está compactado o los dos ciclos previos fueron muy exigentes. *(propuesta)*

---

## 2. Prioridades del agricultor (P, 75 %)

El agricultor elige de 1 a 3 prioridades, en orden. Cada una da un subpuntaje de 0 a 100. P es la suma de peso × subpuntaje.

| N.º de prioridades | Pesos |
|---|---|
| 1 | 1,0 |
| 2 | 0,6 y 0,4 |
| 3 | 0,5, 0,3 y 0,2 |

La primera prioridad pesa más sin anular a las demás. Si el agricultor cambia el orden de sus prioridades, cambia el cultivo recomendado.

### Qué mide cada prioridad

| Prioridad | Nombre en el motor | Qué mide | Cálculo (0 a 100) | Datos de la ficha |
|---|---|---|---|---|
| **Valor de mercado** | `market_value` | Cuánto vale el producto. | (nivel − 1) ÷ 4 × 100. Cultivo sin mercado = 0. | Nivel de mercado de 1 a 5, precio de referencia con fecha y volatilidad. |
| **Rapidez** | `speed` | Ciclo corto, de la siembra a la cosecha. | Con la media del ciclo en meses (m): 100 × (1 − (m − 3) ÷ 9). 3 meses o menos = 100; 12 meses o más = 0. | Ciclo mínimo y máximo en meses. |
| **Menos plagas** | `fewer_pests` | Presión de plagas del cultivo y su efecto sanitario tras el cultivo anterior. | 60 % presión propia + 40 % efecto sanitario (ver abajo). | Plagas, enfermedades, hospederos y ciclos que rompe. |
| **Menor mano de obra** | `low_labor` | Trabajo que pide el cultivo. | (5 − nivel) ÷ 4 × 100. | Nivel de mano de obra de 1 a 5, jornales por hectárea y si es mecanizable. |

**Detalle de «menos plagas»:**
- **Presión propia:** 100 − 10 × número de plagas y enfermedades principales de la ficha (mínimo 0). Un cultivo poco documentado puede parecer con menos plagas.
- **Efecto sanitario tras el cultivo anterior:** comparte hospedero = 15; rompe un ciclo de plaga del anterior = 95; otra familia botánica = 70; otro caso = 60.
- Ejemplo: tras la papa, el chocho rompe el ciclo de la pulguilla (*Epitrix*), según la fuente 1.

**Valor de mercado:** el nivel de 1 a 5 es una inferencia a partir de precios y demanda; cada ficha anota el criterio y la fecha del precio.

---

## 3. Aptitud agronómica (A, 25 %)

A es el **promedio** de los componentes que aplican. Hace que un suelo pobre y uno fértil den resultados distintos, y que la secuencia agronómica pese aunque la prioridad sea económica.

| Componente | Qué mide | Valores |
|---|---|---|
| **Fertilidad vs. exigencia** | Fertilidad del suelo (baja, media, alta) frente a la exigencia del cultivo. | Suelo bajo: exigente 15, medio 50, poco exigente 85. Suelo medio: 50, 80, 90. Suelo alto: 95, 90, 85. Suelo bajo con leguminosa que fija nitrógeno: al menos 95. |
| **Secuencia en el grafo** | Si la transición desde el cultivo anterior tiene respaldo. | Con fuente 100; generalización de una fuente 85; inferida 55; solo fuente 5: 40. Tierra nueva 80. |
| **Balance de nitrógeno** | Qué deja el cultivo anterior y qué pide el nuevo. | Anterior agotador + leguminosa 100. Anterior leguminosa + cultivo agotador 90. Anterior agotador + cultivo poco agotador 80. Agotador + agotador 15. Otro caso 60. Sin cultivo anterior: 80 si fija nitrógeno, 60 si no. |
| **Textura** (solo si se conoce) | Si la ficha admite la textura del suelo (arenosa, franca, arcillosa). | 95 si la admite; 35 si no. |
| **Compactación** (solo si el suelo está compactado) | Si el cultivo mejora la estructura del suelo. | 95. |

---

## 4. Datos faltantes y confianza

- **Dato faltante = 50 (neutro).** Un dato que falta en la ficha o en la entrada no descarta ni favorece.
- **Confianza** de cada cultivo: alta, media o baja. Es la menor entre la confianza de la ficha y el tipo de transición (con fuente = alta; generalización = media; inferida o solo fuente 5 = baja).
- **Cada dato faltante baja la confianza un nivel** y se lista en las advertencias del cultivo.
- También se advierte si la altitud o el pH están fuera del rango de la ficha pero dentro del margen (200 m y 0,5 de pH).

---

## 5. Cómo se aplica con papa

- **Papa como cultivo anterior:** la papa agota mucho el suelo. En balance de nitrógeno, una leguminosa tras la papa saca 100 y un cultivo también agotador (como el maíz) saca 15. Los candidatos salen del grafo y del Cuadro 5 de la fuente 1 (cereal y después leguminosa), filtrados por altitud.
- **Papa como cultivo siguiente:** tras una leguminosa o un pasto con leguminosa, la papa saca 90 en balance de nitrógeno. La papa no puede volver hasta que pasen 3 ciclos sin solanáceas (filtro F2).
- **Un paso o la rotación completa:** el puntaje evalúa un paso. Para la rotación de varios ciclos, el motor puntúa cada paso con la misma fórmula y elige la secuencia completa que termina en un cultivo `ender` con el mayor puntaje medio.
- **Fichas de los acompañantes:** todos los cultivos del pool tienen ficha con suelo, clima, ciclo, plagas y efecto en la rotación. Mano de obra, mercado y facilidad de cultivo se incluyen cuando hay dato con fuente; si faltan, esa prioridad puntúa 50.
