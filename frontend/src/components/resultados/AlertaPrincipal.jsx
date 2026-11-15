import { useId, useState } from 'react'
import { ChevronDown, CircleAlert, OctagonAlert, ShieldCheck } from 'lucide-react'

const RANGO = { ALTO: 3, MEDIO: 2, BAJO: 1 }
const NIVEL = {
  ALTO: { clase: 'alto', texto: 'Alto', Icono: OctagonAlert },
  MEDIO: { clase: 'medio', texto: 'Medio', Icono: CircleAlert },
  BAJO: { clase: 'bajo', texto: 'Bajo', Icono: CircleAlert },
}

// Severidad primero; a igual severidad, lo confirmado (clima + satélite) antes que lo preventivo.
const ordenarAlertas = (alertas) =>
  [...alertas].sort((a, b) => (RANGO[b.nivel] ?? 0) - (RANGO[a.nivel] ?? 0) || Number(b.confirmada) - Number(a.confirmada))

function FilaAlerta({ alerta, abierta }) {
  const n = NIVEL[alerta.nivel] ?? NIVEL.MEDIO
  return (
    <li className={`rs-alerta nivel-${n.clase}`}>
      <n.Icono size={20} className="rs-alerta-icono" aria-hidden="true" />
      <div className="rs-alerta-texto">
        <strong>{alerta.titulo}</strong>
        <span className="rs-alerta-etiquetas">
          <span className="rs-chip nivel">Riesgo {n.texto.toLowerCase()}</span>
          <span className={`rs-chip ${alerta.confirmada ? 'confirmada' : 'preventiva'}`}>
            {alerta.confirmada ? <ShieldCheck size={12} aria-hidden="true" /> : null}
            {alerta.confirmada ? 'Confirmada' : 'Preventiva'}
          </span>
        </span>
        {alerta.texto && <p className={abierta ? '' : 'recortado'}>{alerta.texto}</p>}
      </div>
    </li>
  )
}

// Franja de alertas: los riesgos altos siempre a la vista (al menos una alerta);
// el resto se abre con "Ver N alertas". `alertas`: [{ id, nivel, confirmada, titulo, texto }]
export default function AlertaPrincipal({ alertas }) {
  const [abierta, setAbierta] = useState(false)
  const idLista = useId()
  if (!alertas.length) return null // sin alertas no se muestra nada

  const ordenadas = ordenarAlertas(alertas)
  const altas = ordenadas.filter((a) => a.nivel === 'ALTO')
  const siempre = altas.length ? altas : ordenadas.slice(0, 1)
  const resto = ordenadas.slice(siempre.length)

  return (
    <section className="rs-alertas" aria-label="Alertas de tu parcela">
      <ul className="rs-alertas-lista" id={idLista}>
        {siempre.map((a) => <FilaAlerta key={a.id} alerta={a} abierta={abierta} />)}
        {abierta && resto.map((a) => <FilaAlerta key={a.id} alerta={a} abierta />)}
      </ul>
      {resto.length > 0 && (
        <button
          type="button"
          className="rs-alertas-toggle"
          aria-expanded={abierta}
          aria-controls={idLista}
          onClick={() => setAbierta((v) => !v)}
        >
          {abierta ? 'Ver menos' : `Ver ${ordenadas.length} alertas`}
          <ChevronDown size={18} className={abierta ? 'girado' : ''} aria-hidden="true" />
        </button>
      )}
    </section>
  )
}
