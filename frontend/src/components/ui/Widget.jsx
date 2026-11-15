import { ChevronRight } from 'lucide-react'
import './ui.css'

// Tarjeta de dato destacado al estilo de un widget del tiempo: degradado,
// ilustración a la izquierda, número grande a la derecha y pie con acción.
// `estado` (opcional): { nivel, texto }, una línea con punto de color bajo el detalle.
export default function Widget({ tono = 'azul', ilustracion, valor, unidad, detalle = [], estado, etiqueta, accion, insignia }) {
  return (
    <article className={`ui-widget tono-${tono}`}>
      <div className="ui-widget-ilustracion">{ilustracion}</div>
      <div className="ui-widget-dato">
        {insignia && <span className="ui-widget-insignia">{insignia}</span>}
        <p className="ui-widget-valor">
          <strong>{valor}</strong>
          {unidad && <sup>{unidad}</sup>}
        </p>
        {detalle.map((linea) => (
          <p key={linea} className="ui-widget-detalle">{linea}</p>
        ))}
        {estado && (
          <p className="ui-widget-estado">
            <span className={`ui-punto ui-nivel-${estado.nivel}`} aria-hidden="true" />
            {estado.texto}
          </p>
        )}
      </div>
      <footer className="ui-widget-pie">
        <span>{etiqueta}</span>
        {accion && (
          <button type="button" onClick={accion.onClick}>
            {accion.texto} <ChevronRight size={16} />
          </button>
        )}
      </footer>
    </article>
  )
}
