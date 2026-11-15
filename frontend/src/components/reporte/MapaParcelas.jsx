import { useMemo } from 'react'
import { ImageOverlay, MapContainer, Marker, Polygon, TileLayer, useMapEvents } from 'react-leaflet'
import L from '../../lib/leaflet.js'
import { TILE_SATELITE, centroide } from '../flujo-gps/geo.js'

const iconoNumero = (n, elegida) =>
  L.divIcon({
    className: `rp-numero${elegida ? ' elegida' : ''}`,
    html: `<span>${n}</span>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  })

// Tocar el mapa fuera de las parcelas quita la selección
function TocarFuera({ onElegir }) {
  useMapEvents({ click: () => onElegir?.(null) })
  return null
}

// Mapa satelital con las parcelas de la finca.
// - `color`: color de relleno (texto) o función `(indice) => color` para pintar cada parcela.
// - `capa`: { url, limites } con la imagen de zonas de Sentinel-2; con ella las parcelas
//   quedan solo con su borde blanco y se ve la imagen debajo.
// - `interactivo`: arrastre y zoom; tocar una parcela llama `onElegir(i)` y fuera, `onElegir(null)`.
export default function MapaParcelas({ parcelas, color, capa = null, interactivo = false, seleccionada = null, onElegir }) {
  const limites = useMemo(() => L.latLngBounds(parcelas.flatMap((p) => p.poligono)), [parcelas])
  const varias = parcelas.length > 1
  const colorDe = (i) => (typeof color === 'function' ? color(i) : color)

  return (
    <MapContainer
      // Al agregar una parcela cambian los límites: se vuelve a encuadrar
      key={parcelas.length}
      bounds={limites}
      boundsOptions={{ padding: [28, 28] }}
      className="map"
      zoomControl={false}
      dragging={interactivo}
      scrollWheelZoom={interactivo}
      doubleClickZoom={interactivo}
      touchZoom={interactivo}
      boxZoom={false}
      keyboard={false}
      attributionControl={false}
    >
      <TileLayer url={TILE_SATELITE.url} maxZoom={19} />
      {capa?.url && capa.limites && (
        <ImageOverlay url={capa.url} bounds={capa.limites} opacity={0.85} className="rp-capa" />
      )}
      {parcelas.map((p, i) => (
        <Polygon
          key={i}
          positions={p.poligono}
          interactive={interactivo}
          pathOptions={{
            color: '#fff',
            weight: seleccionada === i ? 5 : 2,
            fillColor: colorDe(i),
            // Con la imagen de zonas no se rellena (el relleno transparente sigue recibiendo el toque)
            fillOpacity: capa ? 0 : 0.5,
          }}
          eventHandlers={interactivo ? {
            click: (e) => {
              // Si no, el clic sigue al mapa y "tocar fuera" quita la selección
              L.DomEvent.stopPropagation(e)
              onElegir?.(i)
            },
          } : undefined}
        />
      ))}
      {varias &&
        parcelas.map((p, i) => (
          <Marker
            key={`n${i}`}
            position={centroide(p.poligono)}
            icon={iconoNumero(i + 1, seleccionada === i)}
            interactive={false}
            keyboard={false}
          />
        ))}
      {interactivo && <TocarFuera onElegir={onElegir} />}
    </MapContainer>
  )
}
