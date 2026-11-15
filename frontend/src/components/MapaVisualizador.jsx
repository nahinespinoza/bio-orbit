import { useState } from 'react'
import { LayersControl, MapContainer, Marker, Popup, TileLayer } from 'react-leaflet'
import { X } from 'lucide-react'
import '../lib/leaflet.js'
import HerramientasDibujo from './HerramientasDibujo.jsx'

const CENTRO_INICIAL = [-17.3895, -66.1568]

export default function MapaVisualizador({ ubicacion, modo, onFigurasChange, onEvento }) {
  const [verAyuda, setVerAyuda] = useState(true)
  const centro = ubicacion ? [ubicacion.lat, ubicacion.lng] : CENTRO_INICIAL

  return (
    <>
      <MapContainer center={centro} zoom={ubicacion ? 16 : 13} className="map" zoomControl={false}>
        <LayersControl position="topright">
          <LayersControl.BaseLayer checked name="Satélite">
            <TileLayer
              attribution="Tiles &copy; Esri"
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
              maxZoom={19}
            />
          </LayersControl.BaseLayer>
          <LayersControl.BaseLayer name="Mapa">
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              maxZoom={19}
            />
          </LayersControl.BaseLayer>
        </LayersControl>
        {ubicacion && (
          <Marker position={centro}>
            <Popup>Tu ubicación actual</Popup>
          </Marker>
        )}
        <HerramientasDibujo onFigurasChange={onFigurasChange} onEvento={onEvento} />
      </MapContainer>

      {verAyuda && (
        <div className="map-ayuda" role="status">
          <span>
            {modo === 'gps'
              ? 'Esta es tu ubicación actual. Dibuja el contorno de tu finca con la herramienta de polígono.'
              : 'Navega hasta tu finca y dibuja su contorno con la herramienta de polígono o marca un puntero.'}
          </span>
          <button className="map-ayuda-cerrar" onClick={() => setVerAyuda(false)} aria-label="Cerrar ayuda">
            <X size={16} />
          </button>
        </div>
      )}
    </>
  )
}
