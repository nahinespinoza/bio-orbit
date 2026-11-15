import { ListChecks, Presentation } from 'lucide-react'

// Tarjeta "Resumen de la semana" dentro de los resultados de cada finca.
// Abre el resumen interactivo (carrusel, una pantalla por dato) o el resumido (todo en una pantalla).
export default function TarjetaResumenSemana({ periodo, ejemplo, onInteractivo, onResumido }) {
  return (
    <section className="fg-fila-resumen rs-resumen-semana" aria-label="Resumen de la semana">
      <span className="fg-fila-resumen-texto">
        <strong>Resumen de la semana</strong>
        <span>
          {periodo ?? 'Última semana con datos'}
          {ejemplo && ' · Datos de ejemplo'}
        </span>
      </span>
      <div className="rs-resumen-semana-botones">
        <button type="button" className="principal" onClick={onInteractivo}>
          <Presentation size={16} aria-hidden="true" /> Interactivo
        </button>
        <button type="button" onClick={onResumido}>
          <ListChecks size={16} aria-hidden="true" /> Resumido
        </button>
      </div>
    </section>
  )
}
