import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { CircleMarker, MapContainer, Marker, Polygon, TileLayer, useMap } from 'react-leaflet'
import { Check, ChevronLeft, LoaderCircle, Move, Plus, TriangleAlert } from 'lucide-react'
import L from '../../lib/leaflet.js'
import { TILE_SATELITE, areaHa, centroAlLado, centroide, cuadradoPorArea, formatoNumero, perimetroM } from './geo.js'
import { detectarParcela } from './deteccion.js'

const ESPERA_TRAS_SOLTAR = 450 // ms antes de ajustar automáticamente al soltar
const DURACION_MINIMA_AJUSTE = 1200 // para que se vea el escaneo

const esperar = (ms) => new Promise((r) => setTimeout(r, ms))

const ICONO_GPS = L.divIcon({
  className: 'fg-marcador',
  html: '<span class="fg-marcador-punto"></span>',
  iconSize: [20, 20],
  iconAnchor: [10, 10],
})

const ICONO_ASA = L.divIcon({
  className: 'fg-asa',
  html:
    '<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">' +
    '<path d="M12 2v20M2 12h20M9 5l3-3 3 3M9 19l3 3 3-3M5 9l-3 3 3 3M19 9l3 3-3 3"/></svg>',
  iconSize: [48, 48],
  iconAnchor: [24, 24],
})

const marcarTrazo = (e) => e.target.getElement()?.setAttribute('pathLength', '1')

// Cuadro que se arrastra con el dedo o el mouse (pointer events) y, como
// alternativa más fácil de tocar, con la manija del centro.
function CuadroArrastrable({ puntos, apagado, onEmpezar, onMover, onSoltar }) {
  const map = useMap()
  const capaRef = useRef(null)
  const callbacks = useRef({ onEmpezar, onMover, onSoltar })
  useEffect(() => {
    callbacks.current = { onEmpezar, onMover, onSoltar }
  })

  useEffect(() => {
    const el = capaRef.current?.getElement()
    if (!el) return
    let ultimo = null

    const abajo = (e) => {
      e.stopPropagation()
      e.preventDefault()
      el.setPointerCapture?.(e.pointerId)
      map.dragging.disable()
      ultimo = map.mouseEventToLatLng(e)
      callbacks.current.onEmpezar()
    }
    const mover = (e) => {
      if (!ultimo) return
      const actual = map.mouseEventToLatLng(e)
      callbacks.current.onMover([actual.lat - ultimo.lat, actual.lng - ultimo.lng])
      ultimo = actual
    }
    const arriba = (e) => {
      if (!ultimo) return
      ultimo = null
      el.releasePointerCapture?.(e.pointerId)
      map.dragging.enable()
      callbacks.current.onSoltar()
    }

    el.addEventListener('pointerdown', abajo)
    el.addEventListener('pointermove', mover)
    el.addEventListener('pointerup', arriba)
    el.addEventListener('pointercancel', arriba)
    return () => {
      el.removeEventListener('pointerdown', abajo)
      el.removeEventListener('pointermove', mover)
      el.removeEventListener('pointerup', arriba)
      el.removeEventListener('pointercancel', arriba)
    }
  }, [map])

  const ultimoAsa = useRef(null)
  const eventosAsa = useMemo(
    () => ({
      dragstart: (e) => {
        ultimoAsa.current = e.target.getLatLng()
        callbacks.current.onEmpezar()
      },
      drag: (e) => {
        const actual = e.target.getLatLng()
        callbacks.current.onMover([actual.lat - ultimoAsa.current.lat, actual.lng - ultimoAsa.current.lng])
        ultimoAsa.current = actual
      },
      dragend: () => callbacks.current.onSoltar(),
    }),
    [],
  )

  return (
    <>
      <Polygon
        ref={capaRef}
        positions={puntos}
        bubblingMouseEvents={false}
        className="fg-cuadro"
        pathOptions={{
          color: '#ffffff',
          weight: apagado ? 2 : 3,
          dashArray: apagado ? '6 6' : null,
          fillColor: '#10b981',
          fillOpacity: apagado ? 0.05 : 0.28,
        }}
      />
      <Marker position={centroide(puntos)} icon={ICONO_ASA} draggable eventHandlers={eventosAsa} />
    </>
  )
}

const SIN_PARCELAS = []

// `otrasParcelas`: polígonos ya guardados de la finca. Se muestran como
// referencia y el cuadro nuevo aparece a su lado.
export default function PantallaUbicarParcela({ ubicacion, hectareas, otrasParcelas = SIN_PARCELAS, onAceptar, onVolver }) {
  const inicial = useMemo(
    () => cuadradoPorArea(otrasParcelas.length ? centroAlLado(otrasParcelas, hectareas) : ubicacion, hectareas),
    [ubicacion, hectareas, otrasParcelas],
  )
  const limites = useMemo(
    () => L.latLngBounds([...inicial, ...otrasParcelas.flat()]).pad(otrasParcelas.length ? 0.12 : 0.9),
    [inicial, otrasParcelas],
  )
  const [cuadro, setCuadro] = useState(inicial)
  const [estado, setEstado] = useState('ubicando') // ubicando | ajustando | listo
  const [deteccion, setDeteccion] = useState(null)
  const corrida = useRef(0)
  const temporizador = useRef(null)
  const cuadroRef = useRef(cuadro)
  useEffect(() => {
    cuadroRef.current = cuadro
  }, [cuadro])
  useEffect(() => () => clearTimeout(temporizador.current), [])

  const ajustar = useCallback(
    async (puntos) => {
      const id = ++corrida.current
      setDeteccion(null)
      setEstado('ajustando')
      const [resultado] = await Promise.all([detectarParcela(puntos, hectareas), esperar(DURACION_MINIMA_AJUSTE)])
      if (id !== corrida.current) return // el usuario volvió a mover el cuadro
      setDeteccion({ ...resultado, id })
      setEstado('listo')
    },
    [hectareas],
  )

  const alEmpezar = useCallback(() => {
    corrida.current++
    clearTimeout(temporizador.current)
    setDeteccion(null)
    setEstado('ubicando')
  }, [])

  const alMover = useCallback(([dLat, dLng]) => {
    setCuadro((c) => c.map(([lat, lng]) => [lat + dLat, lng + dLng]))
  }, [])

  const alSoltar = useCallback(() => {
    clearTimeout(temporizador.current)
    temporizador.current = setTimeout(() => ajustar(cuadroRef.current), ESPERA_TRAS_SOLTAR)
  }, [ajustar])

  const moverOtraVez = () => {
    corrida.current++
    setDeteccion(null)
    setEstado('ubicando')
  }

  const aceptar = (opciones) => {
    const automatico = !!deteccion?.ok
    const poligono = automatico ? deteccion.poligono : cuadro
    onAceptar({ poligono, area: areaHa(poligono), perimetro: perimetroM(poligono), automatico }, opciones)
  }

  const detectado = estado === 'listo' && deteccion?.ok
  // Si lo detectado difiere mucho de lo declarado, se lo decimos en palabras simples
  const razon = detectado ? deteccion.area / hectareas : 1
  const avisoTamano =
    razon > 1.3
      ? ` Es más grande que las ${formatoNumero(hectareas)} ha que nos dijiste.`
      : razon < 0.7
        ? ` Es más chica que las ${formatoNumero(hectareas)} ha que nos dijiste.`
        : ''

  return (
    <div className="fg-pantalla">
      <div className={`fg-mapa fg-ubicar ${estado}`}>
        <MapContainer bounds={limites} className="map" zoomControl={false} doubleClickZoom={false}>
          <TileLayer url={TILE_SATELITE.url} attribution={TILE_SATELITE.attribution} maxZoom={19} />
          <Marker position={[ubicacion.lat, ubicacion.lng]} icon={ICONO_GPS} interactive={false} />
          {otrasParcelas.map((poligono, i) => (
            <Polygon
              key={`otra-${i}`}
              positions={poligono}
              interactive={false}
              pathOptions={{ color: '#ffffff', weight: 2, fillColor: '#047857', fillOpacity: 0.45 }}
            />
          ))}
          <CuadroArrastrable
            puntos={cuadro}
            apagado={detectado}
            onEmpezar={alEmpezar}
            onMover={alMover}
            onSoltar={alSoltar}
          />
          {detectado && (
            <>
              <Polygon
                key={deteccion.id}
                positions={deteccion.poligono}
                interactive={false}
                eventHandlers={{ add: marcarTrazo }}
                className="fg-trazo"
                pathOptions={{ color: '#fbbf24', weight: 3, fillColor: '#fbbf24', fillOpacity: 0.3 }}
              />
              {deteccion.poligono.map((p, i) => (
                <CircleMarker
                  key={`${deteccion.id}-${i}`}
                  center={p}
                  radius={5}
                  interactive={false}
                  pathOptions={{ color: '#b45309', weight: 2, fillColor: '#fff', fillOpacity: 1 }}
                />
              ))}
            </>
          )}
        </MapContainer>

        {estado === 'ajustando' && <div className="fg-escaneo" aria-hidden="true" />}

        <button className="fg-cerrar" onClick={onVolver} aria-label="Volver">
          <ChevronLeft size={22} />
        </button>
        <div className={`fg-chip-gps ${estado === 'listo' ? 'fijada' : 'buscando'}`}>
          <span className="fg-chip-punto" />
          {estado === 'ubicando' && 'Arrastra el cuadro'}
          {estado === 'ajustando' && 'Buscando los bordes…'}
          {estado === 'listo' && (detectado ? 'Contorno ajustado' : 'Cuadro en su lugar')}
        </div>
      </div>

      <section className="fg-hoja" aria-live="polite">
        {estado === 'ubicando' && (
          <>
            <div className="fg-hoja-cabecera">
              <span className="fg-hoja-icono buscando">
                <Move size={22} />
              </span>
              <div>
                <h1 className="fg-hoja-titulo">Pon el cuadro sobre tu parcela</h1>
                <p className="fg-hoja-texto">
                  Arrástralo con el dedo. Mide {formatoNumero(hectareas)} ha, como tu {otrasParcelas.length ? 'parcela' : 'finca'}.
                </p>
              </div>
            </div>
            <button className="onb-btn onb-btn-primario" onClick={() => ajustar(cuadro)}>
              <Check size={20} /> Listo, ajustar a mi parcela
            </button>
          </>
        )}

        {estado === 'ajustando' && (
          <div className="fg-hoja-cabecera">
            <span className="fg-hoja-icono buscando">
              <LoaderCircle size={22} className="onb-girando" />
            </span>
            <div>
              <h1 className="fg-hoja-titulo">Ajustando a tu parcela…</h1>
              <p className="fg-hoja-texto">Estamos buscando los bordes de tu terreno.</p>
            </div>
          </div>
        )}

        {estado === 'listo' && (
          <>
            <div className="fg-hoja-cabecera">
              <span className={`fg-hoja-icono ${detectado ? 'fijada' : 'buscando'}`}>
                {detectado ? <Check size={22} /> : <TriangleAlert size={22} />}
              </span>
              <div>
                <h1 className="fg-hoja-titulo">{detectado ? '¿Así está bien?' : 'No vimos bien los bordes'}</h1>
                <p className="fg-hoja-texto">
                  {detectado
                    ? `La línea amarilla sigue lo que se ve en el mapa: unas ${formatoNumero(deteccion.area, 1)} ha.${avisoTamano}`
                    : 'Guardaremos el cuadro donde lo pusiste. También puedes moverlo otra vez.'}
                </p>
              </div>
            </div>
            <div className="onb-acciones">
              <button className="onb-btn onb-btn-primario" onClick={() => aceptar()} autoFocus>
                <Check size={20} /> {detectado ? 'Sí, guardar mi parcela' : 'Guardar así'}
              </button>
              <button className="onb-btn onb-btn-secundario" onClick={() => aceptar({ otra: true })}>
                <Plus size={20} /> Guardar y agregar otra parcela
              </button>
              <button className="fg-btn-texto" onClick={moverOtraVez}>
                Moverlo otra vez
              </button>
            </div>
          </>
        )}
      </section>
    </div>
  )
}
