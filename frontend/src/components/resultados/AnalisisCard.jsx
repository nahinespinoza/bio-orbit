import { ChevronRight } from 'lucide-react'
import '../ui/ui.css'

// Como FilaAnalisis, con una etiqueta del riesgo relacionado ("Lancha · alto (preventivo)")
// y un cuerpo libre (texto o una BarraSalud). Toda la fila se toca.
// `riesgo`: { texto, nivel: 'alto' | 'medio' | 'bajo' } o null.
export default function AnalisisCard({ tono, Icono, titulo, riesgo, nota, notaTipo, onClick, children }) {
  return (
    <button type="button" className={`ui-fila rs-analisis tono-${tono}`} onClick={onClick}>
      <span className="ui-fila-mosaico" aria-hidden="true">
        <span>
          <Icono size={22} strokeWidth={1.9} />
        </span>
      </span>
      <span className="ui-fila-texto">
        <span className="rs-analisis-titulo">
          <strong>{titulo}</strong>
          {riesgo && <span className={`rs-chip riesgo nivel-${riesgo.nivel}`}>{riesgo.texto}</span>}
        </span>
        <span className="rs-analisis-cuerpo">{children}</span>
        {nota && <small className={notaTipo ? `nota-${notaTipo}` : ''}>{nota}</small>}
      </span>
      <ChevronRight size={20} className="ui-fila-flecha" aria-hidden="true" />
    </button>
  )
}
