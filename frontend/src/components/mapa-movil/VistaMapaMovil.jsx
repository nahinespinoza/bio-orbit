import { useEffect, useMemo, useState } from 'react'
import { CircleMarker, LayersControl, MapContainer, Polygon, Polyline, TileLayer, useMap, useMapEvents } from 'react-leaflet'
import { Check, ChevronLeft, Hand, Pencil, RotateCcw, Undo2 } from 'lucide-react'
import '../../lib/leaflet.js'
import { TILE_SATELITE, areaHa, formatoNumero, perimetroM } from '../flujo-gps/geo.js'
import './mapa-movil.css'

const CENTRO_INICIAL = [-17.3895, -66.1568]
const AREA_MINIMA = 0.02 // ha; menos que esto suele ser un toque por error
const hectareas = (ha) => formatoNumero(ha, ha < 1 ? 2 : 1)

// Mientras se dibuja, cada toque en el mapa agrega una esquina. Mover el mapa
// con el dedo no agrega puntos (Leaflet no dispara "click" tras arrastrar).
function CapturaToques({ activo, onPunto }) {
  const map = useMap()
  useMapEvents({
    click: (e) => activo && onPunto([e.latlng.lat, e.latlng.lng]),
  })
  useEffect(() => {
    // Doble toque = dos esquinas, no zoom.
    if (activo) map.doubleClickZoom.disable()
    else map.doubleClickZoom.enable()
  }, [activo, map])
  return null
}

function Encuadrar({ puntos, listo }) {
  const map = useMap()
  useEffect(() => {
    if (listo && puntos.length >= 3) map.fitBounds(puntos, { padding: [40, 40], maxZoom: 18 })
  }, [listo, puntos, map])
  return null
}

const ESTILO = { color: '#ffffff', weight: 3, fillColor: '#10b981', fillOpacity: 0.35 }

// Modo manual: el agricultor busca su finca y la dibuja tocando sus esquinas.
// Al guardar, sigue el mismo camino que el flujo GPS (inicio → resultados).
export default function VistaMapaMovil({ sesion, onVolver, onEvento, onParcelaLista }) {
  const [estado, setEstado] = useState('explorar') // explorar | dibujando | listo
  const [puntos, setPuntos] = useState([])
  const primerNombre = sesion.nombre.split(' ')[0]

  const area = useMemo(() => (puntos.length >= 3 ? areaHa(puntos) : 0), [puntos])
  const muyChica = estado === 'listo' && area < AREA_MINIMA

  const empezar = () => {
    setPuntos([])
    setEstado('dibujando')
  }
  const terminar = () => setEstado('listo')
  const guardar = () => {
    const centro = puntos.reduce((acc, [lat, lng]) => [acc[0] + lat / puntos.length, acc[1] + lng / puntos.length], [0, 0])
    const parcela = { poligono: puntos, area, perimetro: perimetroM(puntos) }
    onEvento?.('Parcela', `Dibujada en el mapa: ${hectareas(area)} ha`)
    onParcelaLista({ ubicacion: { lat: centro[0], lng: centro[1], precision: null }, parcela })
  }

  const listo = estado === 'listo'

  return (
    <div className="marco onb">
      <div className="marco-tarjeta vm">
        <header className="vm-barra">
          <button className="vm-boton-icono" onClick={onVolver} aria-label="Volver">
            <ChevronLeft size={24} />
          </button>
          <div className="vm-titulo">
            <strong>Dibuja tu finca</strong>
            <span>Hola, {primerNombre}</span>
          </div>
          <span className="vm-avatar" title={sesion.nombre} aria-hidden="true">
            {primerNombre.charAt(0).toUpperCase()}
          </span>
        </header>

        <div className={`vm-mapa ${estado === 'dibujando' ? 'dibujando' : ''}`}>
          <MapContainer center={CENTRO_INICIAL} zoom={13} className="map" zoomControl={false}>
            <LayersControl position="topright">
              <LayersControl.BaseLayer checked name="Satélite">
                <TileLayer url={TILE_SATELITE.url} attribution={TILE_SATELITE.attribution} maxZoom={19} />
              </LayersControl.BaseLayer>
              <LayersControl.BaseLayer name="Calles">
                <TileLayer
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                  maxZoom={19}
                />
              </LayersControl.BaseLayer>
            </LayersControl>
            <CapturaToques activo={estado === 'dibujando'} onPunto={(p) => setPuntos((ps) => [...ps, p])} />
            <Encuadrar puntos={puntos} listo={listo} />
            {puntos.length >= 3 && listo && <Polygon positions={puntos} pathOptions={ESTILO} interactive={false} />}
            {puntos.length >= 2 && !listo && (
              <Polyline positions={puntos.length >= 3 ? [...puntos, puntos[0]] : puntos} pathOptions={{ ...ESTILO, dashArray: '6 6' }} interactive={false} />
            )}
            {!listo &&
              puntos.map((p, i) => (
                <CircleMarker
                  key={i}
                  center={p}
                  radius={i === 0 ? 9 : 7}
                  interactive={false}
                  pathOptions={{ color: '#047857', weight: 3, fillColor: '#fff', fillOpacity: 1 }}
                />
              ))}
          </MapContainer>

          {estado === 'dibujando' && (
            <div className="vm-guia" role="status">
              <Hand size={16} /> Toca cada esquina de tu finca
            </div>
          )}
        </div>

        <section className="vm-panel" aria-live="polite">
          <span className="vm-asa" aria-hidden="true" />
          {estado === 'explorar' && (
            <>
              <h2 className="vm-paso-titulo">Busca tu finca en el mapa</h2>
              <ol className="vm-pasos-lista">
                <li>Mueve el mapa con el dedo y acércalo hasta ver tu terreno.</li>
                <li>Toca <b>Empezar a dibujar</b> y marca cada esquina.</li>
              </ol>
              <button className="onb-btn onb-btn-primario" onClick={empezar}>
                <Pencil size={20} /> Empezar a dibujar
              </button>
            </>
          )}

          {estado === 'dibujando' && (
            <>
              <h2 className="vm-paso-titulo">Marca las esquinas</h2>
              <p className="vm-paso-texto">
                {puntos.length === 0
                  ? 'Toca en el mapa la primera esquina de tu finca.'
                  : puntos.length < 3
                    ? `Llevas ${puntos.length} ${puntos.length === 1 ? 'esquina' : 'esquinas'}. Marca al menos 3.`
                    : `Llevas ${puntos.length} esquinas (unas ${hectareas(area)} ha). Cuando termines, toca Listo.`}
              </p>
              <div className="vm-botones">
                <button className="onb-btn onb-btn-secundario" onClick={() => setPuntos((ps) => ps.slice(0, -1))} disabled={!puntos.length}>
                  <Undo2 size={20} /> Deshacer
                </button>
                <button className="onb-btn onb-btn-primario" onClick={terminar} disabled={puntos.length < 3}>
                  <Check size={20} /> Listo
                </button>
              </div>
              <button className="fg-btn-texto" onClick={() => { setPuntos([]); setEstado('explorar') }}>
                Cancelar
              </button>
            </>
          )}

          {listo && (
            <>
              <h2 className="vm-paso-titulo">
                {muyChica ? 'Tu dibujo es muy pequeño' : `Tu finca mide unas ${hectareas(area)} ha`}
              </h2>
              <p className="vm-paso-texto">
                {muyChica
                  ? 'Acerca más el mapa y vuelve a marcar las esquinas de tu terreno.'
                  : 'Si el contorno no coincide con tu terreno, dibújalo de nuevo.'}
              </p>
              {!muyChica && (
                <button className="onb-btn onb-btn-primario" onClick={guardar} autoFocus>
                  <Check size={20} /> Guardar mi finca
                </button>
              )}
              <button className={muyChica ? 'onb-btn onb-btn-primario' : 'fg-btn-texto'} onClick={empezar}>
                <RotateCcw size={18} /> Dibujar de nuevo
              </button>
            </>
          )}
        </section>
      </div>
    </div>
  )
}
