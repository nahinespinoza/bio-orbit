import { Bug, Check, Droplets, Minus, Sparkles, Sprout, X } from 'lucide-react'
import { CULTIVOS, MESES, estadoDePuntaje, ESTADOS } from './analisis.js'

const PREGUNTAS = [
  {
    id: 'riego',
    texto: '¿Tienes agua para regar?',
    opciones: [['si', 'Sí'], ['aveces', 'A veces'], ['no', 'No']],
  },
  {
    id: 'maiz',
    texto: '¿Necesitas cosechar maíz (para comer o vender)?',
    opciones: [['si', 'Sí'], ['no', 'No']],
  },
  {
    id: 'prioridad',
    texto: '¿Qué es lo más importante para ti?',
    opciones: [['suelo', 'Cuidar el suelo'], ['agua', 'Ahorrar agua'], ['plagas', 'Menos plagas']],
  },
]

const MEDIDORES = [
  { id: 'suelo', nombre: 'Salud del suelo', Icono: Sprout },
  { id: 'agua', nombre: 'Agua suficiente', Icono: Droplets },
  { id: 'plagas', nombre: 'Control de plagas', Icono: Bug },
]

// "Maíz, Maíz, Maíz, Maíz" → [{ id: 'maiz', veces: 4 }]: más corto y fácil de leer.
const tramos = (secuencia) =>
  secuencia.reduce((acc, id) => {
    const ultimo = acc[acc.length - 1]
    if (ultimo?.id === id) ultimo.veces++
    else acc.push({ id, veces: 1 })
    return acc
  }, [])

const palabra = (p) => (p == null ? 'Sin datos' : p >= 75 ? 'Bueno' : p >= 55 ? 'Regular' : 'Bajo')
// Campaña octubre → septiembre, rotulada por trimestres para que se lea bien.
const TRIMESTRES = [0, 3, 6, 9].map((i) => `${MESES[(i + 9) % 12]}–${MESES[(i + 11) % 12]}`)

function Calendario({ plan }) {
  return (
    <div className="rs-calendario" role="img" aria-label={`Calendario de 4 años: ${plan.secuencia.map((id) => CULTIVOS[id].nombre).join(', ')}`}>
      <div className="rs-cal-fila rs-cal-cabecera">
        <span />
        {TRIMESTRES.map((t) => <span key={t}>{t}</span>)}
      </div>
      {[0, 1, 2, 3].map((año) => (
        <div key={año} className="rs-cal-fila">
          <span className="rs-cal-año">Año {año + 1}</span>
          {plan.meses.slice(año * 12, año * 12 + 12).map((m, i) => (
            <span
              key={i}
              className={`rs-cal-mes ${m.cultivo ? '' : 'vacio'}`}
              style={m.cultivo ? { background: CULTIVOS[m.cultivo].color } : undefined}
            >
              {m.sensible && m.riesgo >= 0.3 && <i className="rs-cal-riesgo" />}
            </span>
          ))}
        </div>
      ))}
    </div>
  )
}

export default function Rotaciones({ comparacion, prefs, onPrefs }) {
  const recomendado = comparacion.planes.find((p) => p.id === comparacion.recomendado)
  const cultivosUsados = [...new Set(comparacion.planes.flatMap((p) => p.secuencia))]

  return (
    <>
      <div className="rs-tarjeta rs-preguntas">
        <p className="rs-preguntas-intro">Cuéntanos de tu finca y ajustamos la recomendación:</p>
        {PREGUNTAS.map((q) => (
          <fieldset key={q.id}>
            <legend>{q.texto}</legend>
            <div className="rs-opciones">
              {q.opciones.map(([valor, etiqueta]) => (
                <button
                  key={valor}
                  type="button"
                  className={`fg-chip ${prefs[q.id] === valor ? 'activo' : ''}`}
                  aria-pressed={prefs[q.id] === valor}
                  onClick={() => onPrefs({ ...prefs, [q.id]: valor })}
                >
                  {etiqueta}
                </button>
              ))}
            </div>
          </fieldset>
        ))}
      </div>

      {recomendado && (
        <div className="rs-recomendacion" key={recomendado.id}>
          <Sparkles size={22} />
          <div>
            <span>Te recomendamos</span>
            <strong>{recomendado.nombre}</strong>
            <p>{recomendado.secuencia.map((id) => CULTIVOS[id].nombre).join(' → ')}</p>
            {comparacion.ejemplo && (
              <p className="rs-recomendacion-aviso">Calculada con lluvia de ejemplo (sin conexión). No la uses para decidir.</p>
            )}
          </div>
        </div>
      )}

      <div className="rs-planes">
        {comparacion.planes.map((plan) => {
          const esRec = plan.id === comparacion.recomendado
          return (
            <article key={plan.id} className={`rs-tarjeta rs-plan ${esRec ? 'recomendado' : ''} ${plan.descartado ? 'descartado' : ''}`}>
              <header className="rs-plan-cabecera">
                <div>
                  <h3>{plan.nombre}</h3>
                  <p className="rs-secuencia" aria-label={plan.secuencia.map((id) => CULTIVOS[id].nombre).join(', ')}>
                    {tramos(plan.secuencia).map((t, i) => (
                      <span key={i}>
                        <i style={{ background: CULTIVOS[t.id].color }} />
                        {CULTIVOS[t.id].nombre}
                        {t.veces > 1 && <b>×{t.veces}</b>}
                      </span>
                    ))}
                  </p>
                </div>
                {plan.descartado ? (
                  <span className="rs-plan-nota">No aplica</span>
                ) : (
                  <span className="rs-plan-puntaje">
                    <strong>{plan.total}</strong>
                    <small>/100</small>
                  </span>
                )}
              </header>
              {esRec && <span className="rs-plan-cinta">Recomendada para ti</span>}
              {plan.descartado && <p className="rs-plan-descartado">{plan.descartado}</p>}

              <Calendario plan={plan} />

              <div className="rs-medidores">
                {MEDIDORES.map(({ id, nombre, Icono }) => {
                  const v = plan.puntajes[id]
                  return (
                    <div key={id} className="rs-medidor">
                      <span className="rs-medidor-nombre"><Icono size={14} /> {nombre}</span>
                      <span className="rs-medidor-barra">
                        {v != null && <span style={{ width: `${v}%`, background: ESTADOS[estadoDePuntaje(v)].color }} />}
                      </span>
                      <span className="rs-medidor-valor">{palabra(v)}</span>
                    </div>
                  )
                })}
              </div>

              <ul className="rs-razones">
                {plan.razones.map((r, i) => (
                  <li key={i} className={r.tipo}>
                    {r.tipo === 'bien' ? <Check size={15} /> : r.tipo === 'mal' ? <X size={15} /> : <Minus size={15} />}
                    <span>
                      {r.texto}
                      {r.fuente && (
                        <em className={`rs-fuente-chip ${comparacion.ejemplo ? 'ejemplo' : ''}`}>
                          {comparacion.ejemplo ? 'Lluvia de ejemplo' : 'NASA GPM'}
                        </em>
                      )}
                    </span>
                  </li>
                ))}
              </ul>
            </article>
          )
        })}
      </div>

      <div className="rs-cal-leyenda">
        {cultivosUsados.map((id) => (
          <span key={id}><i style={{ background: CULTIVOS[id].color }} /> {CULTIVOS[id].nombre}</span>
        ))}
        <span><i className="vacio" /> Suelo sin cultivo</span>
        <span><i className="riesgo" /> Etapa delicada, suele faltar lluvia</span>
      </div>
      <p className="rs-nota">
        Fechas de siembra y consumo de agua de referencia (INIAP, ensayos UCE en Tumbaco). Confírmalos con un técnico de tu zona.
      </p>
    </>
  )
}
