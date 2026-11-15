import { ChevronRight } from 'lucide-react'

// Fila "Resumen de la semana" dentro de los resultados de cada finca: abre el carrusel
// (una pantalla por dato, se desliza hacia arriba).
export default function TarjetaResumenSemana({ periodo, ejemplo, onAbrir }) {
  return (
    <button type="button" className="fg-fila-resumen" onClick={onAbrir}>
      <span className="fg-fila-resumen-texto">
        <strong>Resumen de la semana</strong>
        <span>
          {periodo ?? 'Última semana con datos'}
          {ejemplo && ' · Datos de ejemplo'}
        </span>
      </span>
      <ChevronRight size={20} aria-hidden="true" />
    </button>
  )
}
