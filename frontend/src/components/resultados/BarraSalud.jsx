import { ESTADOS } from './analisis.js'
import { ICONO_ESTADO } from './iconos.js'
import { ETIQUETAS_SALUD } from './salud.js'

// Barra segmentada + leyenda con ícono, nombre y porcentaje (el color nunca va solo).
// `segmentos`: [{ estado: 'bien'|'atencion'|'problema'|'grave', porcentaje }]
// `etiquetas`: nombre de cada estado (por defecto, el de la salud del cultivo)
// `compacta`: leyenda en una línea, para tarjetas. `leyenda={false}`: solo la barra (el detalle trae su propia leyenda).
export default function BarraSalud({ segmentos, etiquetas = ETIQUETAS_SALUD, compacta = false, leyenda = true }) {
  const visibles = segmentos.filter((s) => s.porcentaje > 0)
  if (!visibles.length) {
    return <p className="rs-barra-vacia">Sin datos de salud para esta fecha.</p>
  }
  const resumen = visibles.map((s) => `${etiquetas[s.estado]} ${Math.round(s.porcentaje)}%`).join(', ')

  return (
    <div className={`rs-barra-salud${compacta ? ' compacta' : ''}`}>
      <div className="rs-barra-segmentos" role="img" aria-label={resumen}>
        {visibles.map((s) => (
          <span key={s.estado} style={{ flexGrow: s.porcentaje, background: ESTADOS[s.estado].color }} />
        ))}
      </div>
      {leyenda && (
      <ul className="rs-barra-leyenda" aria-hidden="true">
        {visibles.map((s) => {
          const Icono = ICONO_ESTADO[s.estado]
          return (
            <li key={s.estado}>
              <Icono size={14} style={{ color: ESTADOS[s.estado].color }} />
              <span>{etiquetas[s.estado]}</span>
              <strong>{Math.round(s.porcentaje)}%</strong>
            </li>
          )
        })}
      </ul>
      )}
    </div>
  )
}
