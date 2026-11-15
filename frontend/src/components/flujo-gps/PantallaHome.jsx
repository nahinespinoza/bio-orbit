import { useMemo } from 'react'
import { MapContainer, Polygon, TileLayer } from 'react-leaflet'
import {
  Activity, BarChart3, ChevronRight, House, Layers, LandPlot, Map as MapIcon, MapPin, Plus, Ruler, ScanLine, UserRound, Zap,
} from 'lucide-react'
import L from '../../lib/leaflet.js'
import { TILE_SATELITE, formatoNumero } from './geo.js'
import { ESTADOS, MENSAJE_ESTADO } from '../resultados/analisis.js'

const ICONOS = { Rápido: Zap, Profundo: Layers, Ubicación: MapPin, Superficie: Ruler, Parcela: ScanLine }

const saludo = () => {
  const h = new Date().getHours()
  return h < 12 ? 'Buenos días' : h < 19 ? 'Buenas tardes' : 'Buenas noches'
}

const hora = (fecha) => fecha.toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' })

// `listo: false` = pantalla aún no construida: se muestra apagada para no
// dejar al agricultor tocando un botón que no hace nada.
const NAVEGACION = [
  { nombre: 'Inicio', Icono: House, listo: true },
  { nombre: 'Mapa', Icono: MapIcon, listo: false },
  { nombre: 'Análisis', Icono: BarChart3, listo: true },
  { nombre: 'Perfil', Icono: UserRound, listo: false },
]

// Home simulada: resumen de la finca recién registrada.
export default function PantallaHome({
  nombre, ubicacion, parcelas, historial, analisis, onProceso, onVerResultados, onAgregarParcela,
}) {
  const limites = useMemo(() => L.latLngBounds(parcelas.flatMap((p) => p.poligono)), [parcelas])
  const areaTotal = parcelas.reduce((s, p) => s + p.area, 0)
  const varias = parcelas.length > 1
  const primerNombre = nombre.split(' ')[0]
  const porGps = ubicacion.precision != null

  return (
    <div className="fg-pantalla fg-home">
      <header className="fg-home-cabecera">
        <div>
          <p>{saludo()},</p>
          <h1>{primerNombre}</h1>
        </div>
        <span className="vm-avatar" aria-hidden="true">
          {primerNombre.charAt(0).toUpperCase()}
        </span>
      </header>

      <div className="fg-home-contenido">
        <article className="fg-tarjeta-finca fg-aparecer">
          <div className="fg-mini-mapa">
            <MapContainer
              key={parcelas.length}
              bounds={limites}
              boundsOptions={{ padding: [20, 20] }}
              className="map"
              zoomControl={false}
              dragging={false}
              scrollWheelZoom={false}
              doubleClickZoom={false}
              touchZoom={false}
              keyboard={false}
              attributionControl={false}
            >
              <TileLayer url={TILE_SATELITE.url} maxZoom={19} />
              {parcelas.map((p, i) => (
                <Polygon
                  key={i}
                  positions={p.poligono}
                  pathOptions={{ color: '#fff', weight: 2, fillColor: '#10b981', fillOpacity: 0.4 }}
                />
              ))}
            </MapContainer>
            <span className="fg-insignia">
              <ScanLine size={14} /> {porGps ? 'Contorno aproximado' : 'Dibujada por ti'}
            </span>
          </div>
          <div className="fg-tarjeta-finca-info">
            <div className="fg-tarjeta-finca-texto">
              <h2>Mi finca</h2>
              <p>
                <MapPin size={14} />
                {varias
                  ? `${parcelas.length} parcelas · ${formatoNumero(areaTotal, 1)} ha en total`
                  : porGps
                    ? `Ubicada con el GPS del celular (±${Math.round(ubicacion.precision)} m)`
                    : 'Ubicada dibujándola en el mapa'}
              </p>
            </div>
            <button className="fg-btn-anadir" onClick={onAgregarParcela}>
              <Plus size={18} /> Añadir parcela
            </button>
          </div>
        </article>

        <section className="fg-aparecer" style={{ '--retraso': '0.1s' }}>
          <h2 className="fg-seccion-titulo">Analiza tu finca</h2>
          <div className="fg-analisis">
            <button className="fg-analisis-btn" onClick={() => onProceso('Rápido')}>
              <span className="fg-analisis-icono"><Zap size={22} /></span>
              <span className="fg-analisis-texto">
                <strong>Rápido</strong>
                <small>Cómo está tu finca y qué lluvia viene</small>
              </span>
              <ChevronRight size={20} />
            </button>
            <button className="fg-analisis-btn azul" onClick={() => onProceso('Profundo')}>
              <span className="fg-analisis-icono"><Layers size={22} /></span>
              <span className="fg-analisis-texto">
                <strong>Profundo</strong>
                <small>Además, qué sembrar en los próximos 4 años</small>
              </span>
              <ChevronRight size={20} />
            </button>
          </div>
        </section>

        <div className="fg-stats fg-aparecer" style={{ '--retraso': '0.2s' }}>
          <div className="fg-stat">
            <LandPlot size={18} />
            <span>{varias ? 'Tamaño total' : 'Tamaño'}</span>
            <strong>{formatoNumero(areaTotal)} ha</strong>
          </div>
          <div className="fg-stat">
            {varias ? <ScanLine size={18} /> : <Ruler size={18} />}
            <span>{varias ? 'Parcelas' : 'Contorno'}</span>
            <strong>{varias ? parcelas.length : `${formatoNumero(parcelas[0].perimetro, 0)} m`}</strong>
          </div>
          <button className="fg-stat ancho fg-stat-boton" onClick={onVerResultados}>
            <Activity size={18} />
            <span>Salud del cultivo</span>
            {analisis?.simulado ? (
              <strong className="fg-salud">
                <i className="fg-salud-sim" />
                Ejemplo simulado · ver resultados
              </strong>
            ) : analisis ? (
              <strong className="fg-salud">
                <i style={{ background: ESTADOS[analisis.estado].color }} />
                {MENSAJE_ESTADO[analisis.estado].titulo} · {analisis.puntaje}/100
              </strong>
            ) : (
              <strong className="fg-pendiente">Sin análisis todavía · Toca para analizar</strong>
            )}
            <ChevronRight size={18} className="fg-stat-flecha" />
          </button>
        </div>

        <section className="fg-aparecer" style={{ '--retraso': '0.3s' }}>
          <h2 className="fg-seccion-titulo">Actividad reciente</h2>
          <ul className="vm-lista">
            {historial.slice(0, 5).map((item) => {
              const Icono = ICONOS[item.tipo] ?? Activity
              return (
                <li key={item.id} className="vm-item">
                  <span className={`vm-item-icono ${item.tipo === 'Profundo' ? 'azul' : ''}`}>
                    <Icono size={16} />
                  </span>
                  <div className="vm-item-texto">
                    <strong>{item.tipo}</strong>
                    <span>{item.detalle}</span>
                  </div>
                  <small>{hora(item.fecha)}</small>
                </li>
              )
            })}
          </ul>
        </section>
      </div>

      <nav className="fg-nav" aria-label="Navegación principal">
        {NAVEGACION.map(({ nombre: n, Icono, listo }, i) => (
          <button
            key={n}
            className={i === 0 ? 'activo' : ''}
            aria-current={i === 0 ? 'page' : undefined}
            disabled={!listo}
            title={listo ? undefined : 'Disponible pronto'}
            onClick={n === 'Análisis' ? onVerResultados : undefined}
          >
            <Icono size={22} />
            <span>{n}</span>
          </button>
        ))}
      </nav>
    </div>
  )
}
