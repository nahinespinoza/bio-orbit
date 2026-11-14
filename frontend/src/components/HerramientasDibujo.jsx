import { useEffect } from 'react'
import { useMap } from 'react-leaflet'
import L from '../lib/leaflet.js'
import 'leaflet-draw'

const ESTILO = { color: '#ffffff', weight: 3, fillColor: '#4caf50', fillOpacity: 0.45 }

const NOMBRES = { polygon: 'Polígono', rectangle: 'Polígono', marker: 'Puntero' }

// Se coloca dentro de <MapContainer>. Agrega la barra para dibujar/editar
// polígonos, rectángulos y punteros.
export default function HerramientasDibujo({ onFigurasChange, onEvento }) {
  const map = useMap()

  useEffect(() => {
    const capas = new L.FeatureGroup().addTo(map)

    const control = new L.Control.Draw({
      position: 'topleft',
      draw: {
        polygon: { allowIntersection: false, shapeOptions: ESTILO },
        rectangle: { shapeOptions: ESTILO },
        marker: true,
        polyline: false,
        circle: false,
        circlemarker: false,
      },
      edit: { featureGroup: capas },
    })
    map.addControl(control)

    const actualizar = () => onFigurasChange?.(capas.getLayers().length)

    const alCrear = (e) => {
      capas.addLayer(e.layer)
      actualizar()
      const nombre = NOMBRES[e.layerType] ?? e.layerType
      const detalle =
        e.layerType === 'marker'
          ? `${e.layer.getLatLng().lat.toFixed(5)}, ${e.layer.getLatLng().lng.toFixed(5)}`
          : `${(L.GeometryUtil.geodesicArea(e.layer.getLatLngs()[0]) / 10000).toFixed(2)} ha`
      onEvento?.(nombre, detalle)
    }

    map.on(L.Draw.Event.CREATED, alCrear)
    map.on(L.Draw.Event.EDITED, actualizar)
    map.on(L.Draw.Event.DELETED, actualizar)

    return () => {
      map.off(L.Draw.Event.CREATED, alCrear)
      map.off(L.Draw.Event.EDITED, actualizar)
      map.off(L.Draw.Event.DELETED, actualizar)
      map.removeControl(control)
      map.removeLayer(capas)
    }
  }, [map, onFigurasChange, onEvento])

  return null
}
