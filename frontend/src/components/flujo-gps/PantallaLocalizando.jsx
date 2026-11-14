import { useCallback, useEffect, useRef, useState } from 'react'
import { Circle, MapContainer, Marker, TileLayer, useMap } from 'react-leaflet'
import { Check, LoaderCircle, MapPinOff, RefreshCw, Satellite, X } from 'lucide-react'
import L from '../../lib/leaflet.js'
import { TILE_SATELITE, formatoCoord } from './geo.js'

// Aunque el GPS responda al instante, la búsqueda dura al menos esto para que
// la animación se perciba.
const DURACION_MINIMA = 2800
const DURACION_MINIMA_ERROR = 1500
const PAUSA_TRAS_VUELO = 1600

const PASOS = ['Activando GPS', 'Buscando señal satelital', 'Calculando tu posición']

const MENSAJES_ERROR = {
  1: 'El celular no nos dio permiso para usar tu ubicación. Actívalo o dibuja tu finca en el mapa.',
  2: 'No encontramos señal GPS. Sal a un lugar abierto e intenta de nuevo, o dibuja tu finca en el mapa.',
  3: 'La búsqueda tardó demasiado. Intenta de nuevo o dibuja tu finca en el mapa.',
}

const ICONO_GPS = L.divIcon({
  className: 'fg-marcador',
  html: '<span class="fg-marcador-pulso"></span><span class="fg-marcador-pulso d2"></span><span class="fg-marcador-punto"></span>',
  iconSize: [26, 26],
  iconAnchor: [13, 13],
})

const coordAleatoria = (rango) => ((Math.random() * 2 - 1) * rango).toFixed(6)

function Vuelo({ ubicacion, onFin }) {
  const map = useMap()
  useEffect(() => {
    if (!ubicacion) return
    map.flyTo([ubicacion.lat, ubicacion.lng], 17, { duration: 3.2, easeLinearity: 0.2 })
    map.once('moveend', onFin)
    return () => map.off('moveend', onFin)
  }, [ubicacion, map, onFin])
  return null
}

function CirculoPrecision({ centro, radioFinal }) {
  const [radio, setRadio] = useState(radioFinal * 5)
  useEffect(() => {
    let raf
    const inicio = performance.now()
    const desde = radioFinal * 5
    const paso = (t) => {
      const k = Math.min(1, (t - inicio) / 1300)
      setRadio(desde + (radioFinal - desde) * (1 - Math.pow(1 - k, 3)))
      if (k < 1) raf = requestAnimationFrame(paso)
    }
    raf = requestAnimationFrame(paso)
    return () => cancelAnimationFrame(raf)
  }, [radioFinal])
  return (
    <Circle
      center={centro}
      radius={radio}
      pathOptions={{ color: '#3b82f6', weight: 1.5, fillColor: '#3b82f6', fillOpacity: 0.15 }}
    />
  )
}

const SIN_GPS = typeof navigator === 'undefined' || !('geolocation' in navigator)
const MENSAJE_SIN_GPS = 'Tu dispositivo no tiene GPS disponible. Dibuja tu finca en el mapa.'

export default function PantallaLocalizando({ onUbicada, onCancelar, onManual }) {
  const [estado, setEstado] = useState(SIN_GPS ? 'error' : 'buscando') // buscando | fijada | error
  const [ubicacion, setUbicacion] = useState(null)
  const [error, setError] = useState(SIN_GPS ? MENSAJE_SIN_GPS : '')
  const [paso, setPaso] = useState(0)
  const [intento, setIntento] = useState(0)
  const [vueloListo, setVueloListo] = useState(false)
  const [coordFalsa, setCoordFalsa] = useState(['0.000000', '0.000000'])

  const onUbicadaRef = useRef(onUbicada)
  useEffect(() => {
    onUbicadaRef.current = onUbicada
  })

  // Pasos y coordenadas que "giran" mientras se busca la señal
  useEffect(() => {
    if (estado !== 'buscando') return
    const pasos = setInterval(() => setPaso((p) => Math.min(p + 1, PASOS.length - 1)), 950)
    const coords = setInterval(() => setCoordFalsa([coordAleatoria(90), coordAleatoria(180)]), 70)
    return () => {
      clearInterval(pasos)
      clearInterval(coords)
    }
  }, [estado])

  useEffect(() => {
    let activo = true
    let espera
    const inicio = performance.now()
    if (SIN_GPS) return
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        espera = setTimeout(() => {
          if (!activo) return
          setUbicacion({ lat: coords.latitude, lng: coords.longitude, precision: coords.accuracy })
          setEstado('fijada')
        }, Math.max(0, DURACION_MINIMA - (performance.now() - inicio)))
      },
      (err) => {
        // Un permiso denegado responde al instante: mostramos la búsqueda un momento
        espera = setTimeout(() => {
          if (!activo) return
          setError(MENSAJES_ERROR[err.code] ?? MENSAJES_ERROR[2])
          setEstado('error')
        }, Math.max(0, DURACION_MINIMA_ERROR - (performance.now() - inicio)))
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 },
    )
    return () => {
      activo = false
      clearTimeout(espera)
    }
  }, [intento])

  const alTerminarVuelo = useCallback(() => setVueloListo(true), [])

  useEffect(() => {
    if (!vueloListo || !ubicacion) return
    const id = setTimeout(() => onUbicadaRef.current(ubicacion), PAUSA_TRAS_VUELO)
    return () => clearTimeout(id)
  }, [vueloListo, ubicacion])

  const reintentar = () => {
    if (SIN_GPS) return
    setError('')
    setPaso(0)
    setEstado('buscando')
    setIntento((n) => n + 1)
  }

  const centro = ubicacion ? [ubicacion.lat, ubicacion.lng] : null
  const precisionTexto = ubicacion ? `±${Math.round(ubicacion.precision)} m` : '—'

  return (
    <div className="fg-pantalla">
      <div className={`fg-mapa fg-estado-${estado} ${vueloListo ? 'fg-vuelo-listo' : ''}`}>
        <MapContainer
          center={[8, -40]}
          zoom={2}
          className="map"
          zoomControl={false}
          dragging={false}
          scrollWheelZoom={false}
          doubleClickZoom={false}
          touchZoom={false}
          boxZoom={false}
          keyboard={false}
        >
          <TileLayer url={TILE_SATELITE.url} attribution={TILE_SATELITE.attribution} maxZoom={19} />
          <Vuelo ubicacion={ubicacion} onFin={alTerminarVuelo} />
          {vueloListo && centro && (
            <>
              <CirculoPrecision centro={centro} radioFinal={Math.min(Math.max(ubicacion.precision, 12), 250)} />
              <Marker position={centro} icon={ICONO_GPS} />
            </>
          )}
        </MapContainer>

        <div className="fg-velo" />
        <div className="fg-cuadricula" />
        <div className="fg-hud" aria-hidden="true">
          <span /> <span /> <span /> <span />
        </div>
        {estado === 'buscando' && (
          <div className="fg-radar" aria-hidden="true">
            <span className="fg-radar-barrido" />
            <span className="fg-radar-anillo" />
            <span className="fg-radar-anillo d2" />
            <span className="fg-radar-anillo d3" />
            <span className="fg-radar-centro" />
          </div>
        )}

        <button className="fg-cerrar" onClick={onCancelar} aria-label="Cancelar">
          <X size={20} />
        </button>
        <div className={`fg-chip-gps ${estado}`}>
          <span className="fg-chip-punto" />
          {estado === 'buscando' && 'Buscando señal…'}
          {estado === 'fijada' && 'Señal GPS fijada'}
          {estado === 'error' && 'Sin señal'}
        </div>
      </div>

      <section className="fg-hoja" aria-live="polite">
        {estado === 'error' ? (
          <>
            <div className="fg-hoja-cabecera">
              <span className="fg-hoja-icono error">
                <MapPinOff size={22} />
              </span>
              <div>
                <h1 className="fg-hoja-titulo">No pudimos ubicarte</h1>
                <p className="fg-hoja-texto">{error}</p>
              </div>
            </div>
            <div className="onb-acciones">
              <button className="onb-btn onb-btn-primario" onClick={reintentar}>
                <RefreshCw size={18} /> Reintentar
              </button>
              <button className="onb-btn onb-btn-secundario" onClick={onManual}>
                Dibujar en el mapa
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="fg-hoja-cabecera">
              <span className={`fg-hoja-icono ${estado}`}>
                {estado === 'buscando' ? <Satellite size={22} /> : <Check size={22} />}
              </span>
              <div>
                <h1 className="fg-hoja-titulo">
                  {estado === 'buscando' ? 'Detectando tu ubicación…' : 'Ubicación detectada'}
                </h1>
                <p className="fg-hoja-texto">
                  {estado === 'buscando' ? 'Quédate quieto un momento, mejor al aire libre.' : 'Acercando el mapa a tu finca…'}
                </p>
              </div>
            </div>

            <ul className="fg-pasos">
              {PASOS.map((texto, i) => {
                const hecho = estado === 'fijada' || i < paso
                const activo = estado === 'buscando' && i === paso
                return (
                  <li key={texto} className={hecho ? 'hecho' : activo ? 'activo' : ''}>
                    <span className="fg-paso-icono">
                      {hecho ? <Check size={14} /> : activo ? <LoaderCircle size={14} className="onb-girando" /> : null}
                    </span>
                    {texto}
                  </li>
                )
              })}
            </ul>

            <div className="fg-lectura">
              <div>
                <span>Latitud</span>
                <strong>{ubicacion ? formatoCoord(ubicacion.lat) : coordFalsa[0]}</strong>
              </div>
              <div>
                <span>Longitud</span>
                <strong>{ubicacion ? formatoCoord(ubicacion.lng) : coordFalsa[1]}</strong>
              </div>
              <div>
                <span>Precisión</span>
                <strong>{precisionTexto}</strong>
              </div>
            </div>
          </>
        )}
      </section>
    </div>
  )
}
