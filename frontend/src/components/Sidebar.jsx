import { History, Zap, Layers, MapPin, Pentagon } from 'lucide-react'

const ICONOS = {
  Rápido: Zap,
  Profundo: Layers,
  Polígono: Pentagon,
  Puntero: MapPin,
  Ubicación: MapPin,
}

const formatoHora = (fecha) =>
  fecha.toLocaleString('es', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })

export default function Sidebar({ historial, onProceso }) {
  return (
    <aside className="sidebar">
      <section className="sidebar-section historial">
        <h2 className="section-title">
          <History size={16} /> Historial
        </h2>
        {historial.length === 0 ? (
          <p className="empty">Sin actividad todavía. Dibuja un área en el mapa o ejecuta un proceso.</p>
        ) : (
          <ul className="historial-list">
            {historial.map((item) => {
              const Icono = ICONOS[item.tipo] ?? History
              return (
                <li key={item.id} className="historial-item">
                  <span className={`historial-icon tipo-${item.tipo === 'Profundo' ? 'profundo' : 'rapido'}`}>
                    <Icono size={16} />
                  </span>
                  <div className="historial-text">
                    <strong>{item.tipo}</strong>
                    <span>{item.detalle}</span>
                    <small>{formatoHora(item.fecha)}</small>
                  </div>
                </li>
              )
            })}
          </ul>
        )}
      </section>

      <section className="sidebar-section procesos">
        <h2 className="section-title">Procesos</h2>
        <div className="procesos-botones">
          <button className="btn btn-rapido" onClick={() => onProceso('Rápido')}>
            <Zap size={22} />
            <span>Rápido</span>
            <small>Análisis general</small>
          </button>
          <button className="btn btn-profundo" onClick={() => onProceso('Profundo')}>
            <Layers size={22} />
            <span>Profundo</span>
            <small>Análisis detallado</small>
          </button>
        </div>
      </section>
    </aside>
  )
}
