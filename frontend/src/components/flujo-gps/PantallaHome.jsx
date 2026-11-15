import { useMemo } from 'react'
import { MapContainer, Polygon, TileLayer } from 'react-leaflet'
import { ChevronRight, MapPin, Pencil, Plus, ScanLine } from 'lucide-react'
import L from '../../lib/leaflet.js'
import { TILE_SATELITE, formatoNumero } from './geo.js'

const saludo = () => {
  const h = new Date().getHours()
  return h < 12 ? 'Buenos días' : h < 19 ? 'Buenas tardes' : 'Buenas noches'
}

// Los botones dentro de una tarjeta tocable no deben abrirla.
const sinAbrir = (fn) => (e) => {
  e.stopPropagation()
  fn()
}

// Tarjeta de una finca: mini mapa con sus parcelas + nombre y resumen.
// Sin `onAgregarParcela` no se muestra el botón "Añadir parcela"; sin `onEditar`, el de "Editar".
// Con `onAbrir`, toda la tarjeta es tocable (abre el análisis de esa finca).
function TarjetaFinca({ titulo, insignia, detalle, parcelas, onAgregarParcela, onEditar, onAbrir, retraso }) {
  const limites = useMemo(() => L.latLngBounds(parcelas.flatMap((p) => p.poligono)), [parcelas])
  const areaTotal = parcelas.reduce((s, p) => s + p.area, 0)
  const texto = parcelas.length > 1
    ? `${parcelas.length} parcelas · ${formatoNumero(areaTotal, 1)} ha en total`
    : detalle ?? `${formatoNumero(areaTotal)} ha`

  const tocable = onAbrir
    ? {
        role: 'button',
        tabIndex: 0,
        'aria-label': `Ver el análisis de ${titulo}`,
        onClick: onAbrir,
        onKeyDown: (e) => {
          if (e.target !== e.currentTarget) return
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            onAbrir()
          }
        },
      }
    : {}

  return (
    <article
      className={`fg-tarjeta-finca fg-aparecer${onAbrir ? ' tocable' : ''}`}
      style={retraso ? { '--retraso': retraso } : undefined}
      {...tocable}
    >
      <div className="fg-mini-mapa">
        <MapContainer
          // Al agregar o editar parcelas cambian los límites: se vuelve a encuadrar
          key={limites.toBBoxString()}
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
              interactive={false}
              pathOptions={{ color: '#fff', weight: 2, fillColor: '#10b981', fillOpacity: 0.4 }}
            />
          ))}
        </MapContainer>
        <span className="fg-insignia">
          <ScanLine size={14} /> {insignia}
        </span>
        {onEditar && (
          <button type="button" className="fg-btn-editar" onClick={sinAbrir(onEditar)} aria-label={`Editar ${titulo}`}>
            <Pencil size={14} /> Editar
          </button>
        )}
      </div>
      <div className="fg-tarjeta-finca-info">
        <div className="fg-tarjeta-finca-texto">
          <h2>{titulo}</h2>
          <p>
            <MapPin size={14} />
            {texto}
          </p>
        </div>
        {onAgregarParcela && (
          <button type="button" className="fg-btn-anadir" onClick={sinAbrir(onAgregarParcela)}>
            <Plus size={18} /> Añadir parcela
          </button>
        )}
        {onAbrir && <ChevronRight size={20} className="fg-tarjeta-flecha" aria-hidden="true" />}
      </div>
    </article>
  )
}

// Inicio: la finca registrada (una o varias parcelas). Cada tarjeta se toca para ver su análisis
// y tiene "Editar"; "Añadir parcela" es una acción de la pantalla (cabecera).
// `fincasExtra` (ruta /prueba): más tarjetas de finca debajo de la principal.
export default function PantallaHome({
  nombre, ubicacion, parcelas, nombrePrincipal = 'Mi finca', fincasExtra = [], onAgregarParcela, onEditarFinca, onVerFinca,
}) {
  const primerNombre = nombre.split(' ')[0]
  const porGps = ubicacion.precision != null
  const areaPrincipal = parcelas.reduce((s, p) => s + p.area, 0)

  return (
    <div className="fg-pantalla fg-home">
      <header className="fg-home-cabecera">
        <div>
          <p>{saludo()},</p>
          <h1>{primerNombre}</h1>
        </div>
        <div className="fg-home-acciones">
          {onAgregarParcela && (
            <button type="button" className="fg-btn-anadir fg-btn-anadir-cabecera" onClick={onAgregarParcela}>
              <Plus size={18} /> Añadir parcela
            </button>
          )}
          <span className="vm-avatar" aria-hidden="true">
            {primerNombre.charAt(0).toUpperCase()}
          </span>
        </div>
      </header>

      <div className="fg-home-contenido">
        <TarjetaFinca
          titulo={nombrePrincipal}
          insignia={porGps ? 'Contorno aproximado' : ubicacion.zona || ubicacion.fija ? 'Satélite' : 'Dibujada por ti'}
          detalle={
            porGps
              ? `Ubicada con el GPS del celular (±${Math.round(ubicacion.precision)} m)`
              : ubicacion.zona
                ? `${ubicacion.zona} · ${formatoNumero(areaPrincipal)} ha`
                : ubicacion.fija
                  ? `${formatoNumero(areaPrincipal)} ha`
                  : 'Ubicada dibujándola en el mapa'
          }
          parcelas={parcelas}
          onEditar={onEditarFinca && (() => onEditarFinca('principal'))}
          onAbrir={onVerFinca && (() => onVerFinca('principal'))}
        />

        {fincasExtra.map((f, i) => (
          <TarjetaFinca
            key={f.id}
            titulo={f.nombre}
            insignia={f.insignia ?? 'Satélite'}
            detalle={[f.zona, `${formatoNumero(f.parcelas.reduce((s, p) => s + p.area, 0))} ha`].filter(Boolean).join(' · ')}
            parcelas={f.parcelas}
            onEditar={onEditarFinca && (() => onEditarFinca(i))}
            onAbrir={onVerFinca && (() => onVerFinca(i))}
            retraso={`${0.05 * (i + 1)}s`}
          />
        ))}
      </div>
    </div>
  )
}
