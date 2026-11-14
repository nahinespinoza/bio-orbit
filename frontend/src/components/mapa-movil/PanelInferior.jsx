import { useState } from 'react'
import { ChevronUp, History, Layers, MapPin, Pentagon, Zap } from 'lucide-react'

const ICONOS = { Rápido: Zap, Profundo: Layers, Polígono: Pentagon, Puntero: MapPin, Ubicación: MapPin }

const formatoHora = (fecha) => fecha.toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' })

function ItemHistorial({ item }) {
  const Icono = ICONOS[item.tipo] ?? History
  return (
    <li className="vm-item">
      <span className={`vm-item-icono ${item.tipo === 'Profundo' ? 'azul' : ''}`}>
        <Icono size={16} />
      </span>
      <div className="vm-item-texto">
        <strong>{item.tipo}</strong>
        <span>{item.detalle}</span>
      </div>
      <small>{formatoHora(item.fecha)}</small>
    </li>
  )
}

// Panel tipo "bottom sheet": historial plegable arriba y procesos abajo.
export default function PanelInferior({ historial, onProceso }) {
  const [abierto, setAbierto] = useState(false)
  const visibles = abierto ? historial : historial.slice(0, 1)

  return (
    <section className="vm-panel">
      <button
        className="vm-panel-cabecera"
        onClick={() => setAbierto((v) => !v)}
        aria-expanded={abierto}
        aria-controls="vm-historial"
      >
        <span className="vm-asa" aria-hidden="true" />
        <span className="vm-panel-titulo">
          <History size={16} /> Historial
          {historial.length > 0 && <span className="vm-badge">{historial.length}</span>}
        </span>
        <ChevronUp size={18} className={`vm-chevron ${abierto ? 'abierto' : ''}`} />
      </button>

      <div id="vm-historial" className={`vm-historial ${abierto ? 'abierto' : ''}`}>
        {historial.length === 0 ? (
          <p className="vm-vacio">Sin actividad todavía.</p>
        ) : (
          <ul className="vm-lista">
            {visibles.map((item) => (
              <ItemHistorial key={item.id} item={item} />
            ))}
          </ul>
        )}
      </div>

      <h2 className="vm-panel-titulo vm-procesos-titulo">Procesos</h2>
      <div className="vm-procesos">
        <button className="vm-proceso" onClick={() => onProceso('Rápido')}>
          <Zap size={20} />
          <span>Rápido</span>
        </button>
        <button className="vm-proceso azul" onClick={() => onProceso('Profundo')}>
          <Layers size={20} />
          <span>Profundo</span>
        </button>
      </div>
    </section>
  )
}
