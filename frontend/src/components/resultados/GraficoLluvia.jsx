import { useState } from 'react'
import { MESES, MESES_LARGOS } from './analisis.js'

const ANCHO = 340
const ALTO = 172
const M = { arriba: 22, abajo: 26, izq: 34, der: 4 }

// Rótulos de mes: uno sí y uno no (más el seleccionado) para que no se encimen
// en pantallas angostas; el recuadro superior nombra el mes tocado.
// Barras: lluvia normal (mediana) de cada mes. Bigote: rango en el que cayó
// 6 de cada 10 años (percentiles 20–80). Datos GPM IMERG vía NASA POWER.
export default function GraficoLluvia({ lluvia, mesActual }) {
  const [sel, setSel] = useState(mesActual)
  const { meses } = lluvia
  const tope = Math.max(50, Math.ceil(Math.max(0, ...meses.map((m) => m.p80 ?? 0)) / 50) * 50)
  const alto = ALTO - M.arriba - M.abajo
  const y = (v) => M.arriba + alto - (v / tope) * alto
  const paso = (ANCHO - M.izq - M.der) / 12
  const anchoBarra = paso - 7
  const marcas = [0, tope / 2, tope]
  const { promedioMes } = lluvia
  const m = meses[sel]
  const nombreSel = MESES_LARGOS[sel].replace(/^./, (c) => c.toUpperCase())

  return (
    <div className="rs-grafico">
      <div className="rs-grafico-info" aria-live="polite">
        <strong>{nombreSel}{sel === mesActual ? ' (este mes)' : ''}</strong>
        {m.mediana == null ? (
          <span>
            {m.n ? `Solo hay datos de ${m.n} de ${lluvia.años} años: no alcanza para saber qué es lo normal.` : 'Sin datos de lluvia para este mes.'}
          </span>
        ) : (
          <span>
            Lo normal: <b>{m.mediana} mm</b>. En 6 de cada 10 años cayeron entre {m.p20} y {m.p80} mm
            {m.n < lluvia.años ? ` (hay datos de ${m.n} de ${lluvia.años} años)` : ''}.
          </span>
        )}
      </div>

      <svg viewBox={`0 0 ${ANCHO} ${ALTO}`} role="img" aria-label="Lluvia normal de cada mes en milímetros">
        {marcas.map((v) => (
          <g key={v}>
            <line x1={M.izq} x2={ANCHO - M.der} y1={y(v)} y2={y(v)} className={v === 0 ? 'rs-eje' : 'rs-rejilla'} />
            <text x={M.izq - 6} y={y(v) + 3.5} className="rs-tick" textAnchor="end">{v}</text>
          </g>
        ))}
        <text x={M.izq - 6} y={11} className="rs-tick" textAnchor="end">mm</text>

        {meses.map((d, i) => {
          const x = M.izq + i * paso + 4
          const cx = x + anchoBarra / 2
          const vacio = d.mediana == null
          const seco = !vacio && promedioMes != null && d.mediana < promedioMes * 0.6
          const altura = vacio ? 0 : Math.max(2, y(0) - y(d.mediana))
          const r = Math.min(4, anchoBarra / 2, altura)
          const top = y(0) - altura
          return (
            <g key={i} className={`rs-mes ${i === sel ? 'sel' : ''} ${seco ? 'seco' : ''}`}>
              {vacio ? (
                <text x={cx} y={y(0) - 6} textAnchor="middle" className="rs-tick">—</text>
              ) : (
                <>
                  <path
                    className="rs-barra"
                    d={`M${x},${y(0)} V${top + r} Q${x},${top} ${x + r},${top} H${x + anchoBarra - r} Q${x + anchoBarra},${top} ${x + anchoBarra},${top + r} V${y(0)} Z`}
                  />
                  <line className="rs-bigote" x1={cx} x2={cx} y1={y(d.p80)} y2={y(d.p20)} />
                  <line className="rs-bigote" x1={cx - 3} x2={cx + 3} y1={y(d.p80)} y2={y(d.p80)} />
                  <line className="rs-bigote" x1={cx - 3} x2={cx + 3} y1={y(d.p20)} y2={y(d.p20)} />
                </>
              )}
              {(i === sel || (i % 2 === 0 && Math.abs(i - sel) !== 1)) && (
                <text x={cx} y={ALTO - 9} textAnchor="middle" className={`rs-tick rs-tick-mes ${i === sel ? 'fuerte' : ''}`}>
                  {MESES[i]}
                </text>
              )}
              {i === mesActual && <circle cx={cx} cy={ALTO - 1.8} r={2} className="rs-hoy" />}
              <rect
                x={M.izq + i * paso}
                y={0}
                width={paso}
                height={ALTO}
                className="rs-zona-toque"
                tabIndex={0}
                role="button"
                aria-label={vacio ? `${MESES_LARGOS[i]}: sin datos` : `${MESES_LARGOS[i]}: ${d.mediana} milímetros`}
                onClick={() => setSel(i)}
                onMouseEnter={() => setSel(i)}
                onFocus={() => setSel(i)}
              />
            </g>
          )
        })}
      </svg>

      <div className="rs-grafico-leyenda">
        <span><i className="rs-muestra-barra" /> Lluvia normal</span>
        <span><i className="rs-muestra-bigote" /> Años secos y lluviosos</span>
        <span><i className="rs-muestra-seca" /> Meses secos</span>
      </div>

      <details className="rs-tabla">
        <summary>Ver los números</summary>
        <table>
          <thead>
            <tr><th>Mes</th><th>Normal</th><th>Rango (6 de 10 años)</th><th>Mín – Máx</th></tr>
          </thead>
          <tbody>
            {meses.map((d, i) => (
              <tr key={i}>
                <td>{MESES[i]}</td>
                {d.mediana == null ? (
                  <td colSpan={3}>Sin datos</td>
                ) : (
                  <>
                    <td>{d.mediana} mm</td>
                    <td>{d.p20}–{d.p80} mm</td>
                    <td>{d.min}–{d.max} mm</td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  )
}
