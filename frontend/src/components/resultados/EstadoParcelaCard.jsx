import { useMemo } from 'react'
import { MapContainer, Polygon, Rectangle, TileLayer } from 'react-leaflet'
import { ChevronRight, Satellite, Sprout } from 'lucide-react'
import L from '../../lib/leaflet.js'
import { TILE_SATELITE } from '../flujo-gps/geo.js'
import { ESTADOS, textoZona } from './analisis.js'
import BarraSalud from './BarraSalud.jsx'
import { segmentosSalud } from './salud.js'

const fechaCorta = (iso) => iso.split('-').reverse().join('/')
const haceDias = (d) => (d === 0 ? 'hoy' : d === 1 ? 'hace 1 día' : `hace ${d} días`)

// Tarjeta principal de resultados: cómo está la parcela y qué hacer.
// `salud`: resumen.salud; `zonas`: celdas del mapa (Sentinel-2). Toda la tarjeta abre el detalle.
export default function EstadoParcelaCard({ parcela, zonas, salud, onAbrir }) {
  const limites = useMemo(() => L.latLngBounds(parcela.poligono), [parcela])
  const lienzo = useMemo(() => L.canvas({ padding: 0.5 }), [])

  const abrirConTeclado = (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      onAbrir()
    }
  }

  return (
    <article
      className="rs-estado"
      role="button"
      tabIndex={0}
      aria-label="Estado de tu parcela. Ver el detalle de la salud del cultivo"
      onClick={onAbrir}
      onKeyDown={abrirConTeclado}
    >
      <header className="rs-estado-cabecera">
        <span className="rs-estado-icono" aria-hidden="true"><Sprout size={18} /></span>
        <h2>Estado de tu parcela</h2>
      </header>

      <div className="rs-estado-mapa" aria-hidden="true">
        <MapContainer
          bounds={limites}
          boundsOptions={{ padding: [16, 16] }}
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
          {zonas.celdas.map((c, i) => c.estado.verdor && (
            <Rectangle
              key={i}
              bounds={c.limites}
              interactive={false}
              pathOptions={{ renderer: lienzo, stroke: false, fillColor: ESTADOS[c.estado.verdor].color, fillOpacity: 0.7 }}
            />
          ))}
          <Polygon positions={parcela.poligono} interactive={false} pathOptions={{ color: '#fff', weight: 2.5, fill: false }} />
        </MapContainer>
      </div>

      {salud ? (
        <div className="rs-estado-cuerpo">
          <BarraSalud segmentos={segmentosSalud(salud)} compacta />
          <p className="rs-estado-accion">
            <strong>{salud.mensaje}</strong>
            {salud.sectorMasAfectado && <> · revisa {textoZona(salud.sectorMasAfectado)}</>}
          </p>
          <p className="rs-estado-meta">
            <Satellite size={14} aria-hidden="true" />
            <span>
              Sentinel-2 · {fechaCorta(salud.fecha)}
              {salud.diasDesdeFoto != null && <> · {haceDias(salud.diasDesdeFoto)}</>}
            </span>
            <span className="rs-estado-ver">
              Ver detalle <ChevronRight size={16} aria-hidden="true" />
            </span>
          </p>
        </div>
      ) : (
        <p className="rs-estado-vacio">Todavía no hay una foto de satélite limpia de tu parcela.</p>
      )}
    </article>
  )
}
