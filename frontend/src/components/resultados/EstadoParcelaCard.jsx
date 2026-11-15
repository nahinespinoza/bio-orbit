import { useMemo } from 'react'
import { MapContainer, Polygon, Rectangle, TileLayer } from 'react-leaflet'
import { ChevronRight, Satellite, Sprout } from 'lucide-react'
import L from '../../lib/leaflet.js'
import { TILE_SATELITE } from '../flujo-gps/geo.js'
import { ESTADOS } from './analisis.js'
import BarraSalud from './BarraSalud.jsx'
import { segmentosSalud } from './salud.js'

// Tarjeta principal de resultados: cómo está la parcela y qué hacer. Toda la tarjeta abre el detalle.
// - `salud`: { sana, alerta, critico } en %; `zonas`: celdas del mapa (Sentinel-2 o simuladas).
// - `accion`: la línea de qué hacer; `meta`: fuente y fecha de la foto.
export default function EstadoParcelaCard({ parcela, zonas, salud, accion, meta, onAbrir }) {
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
          {accion && <p className="rs-estado-accion">{accion}</p>}
          <p className="rs-estado-meta">
            <Satellite size={14} aria-hidden="true" />
            <span>{meta}</span>
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
