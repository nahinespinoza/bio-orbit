import { useMemo } from 'react'
import { MapContainer, Marker, Polygon, Rectangle, TileLayer } from 'react-leaflet'
import L from '../../lib/leaflet.js'
import { TILE_SATELITE } from '../flujo-gps/geo.js'
import { ESTADOS, ORDEN_ESTADOS, formato, textoZona } from './analisis.js'
import { ICONO_ESTADO } from './iconos.js'

const ICONO_FOCO = L.divIcon({
  className: 'rs-foco',
  html: '<span></span><span></span>',
  iconSize: [56, 56],
  iconAnchor: [28, 28],
})

const CAPAS = {
  verdor: {
    nombre: 'Verdor',
    pregunta: '¿Qué tan sanas y verdes están tus plantas?',
    etiquetas: { bien: 'Sano', atencion: 'Algo débil', problema: 'Débil', grave: 'Muy débil' },
  },
  humedad: {
    nombre: 'Agua en el suelo',
    pregunta: '¿Cuánta agua tiene el suelo en cada zona?',
    etiquetas: { bien: 'Húmedo', atencion: 'Algo seco', problema: 'Seco', grave: 'Muy seco' },
  },
}

export default function MapaSalud({ parcela, zonas, capa, onCapa, resaltar }) {
  const sim = zonas.simulado
  const limites = useMemo(() => L.latLngBounds(parcela.poligono), [parcela])
  const lienzo = useMemo(() => L.canvas({ padding: 0.5 }), [])
  const resumen = zonas[capa]
  const { etiquetas } = CAPAS[capa]

  return (
    <div className="rs-tarjeta rs-mapa-tarjeta">
      <div className="rs-segmentos" role="tablist" aria-label="Capa del mapa">
        {Object.entries(CAPAS).map(([id, c]) => (
          <button key={id} role="tab" aria-selected={capa === id} className={capa === id ? 'activo' : ''} onClick={() => onCapa(id)}>
            {c.nombre}
          </button>
        ))}
      </div>
      <p className="rs-pregunta">{CAPAS[capa].pregunta}</p>

      <div className="rs-mapa">
        <MapContainer
          bounds={limites}
          boundsOptions={{ padding: [18, 18] }}
          className="map"
          zoomControl={false}
          scrollWheelZoom={false}
          doubleClickZoom={false}
          attributionControl={false}
        >
          <TileLayer url={TILE_SATELITE.url} maxZoom={19} />
          {zonas.celdas.map((c, i) => (
            <Rectangle
              key={i}
              bounds={c.limites}
              pathOptions={{ renderer: lienzo, stroke: false, fillColor: ESTADOS[c.estado[capa]].color, fillOpacity: 0.62 }}
              interactive={false}
            />
          ))}
          <Polygon positions={parcela.poligono} interactive={false} pathOptions={{ color: '#fff', weight: 2.5, fill: false }} />
          {resaltar && resumen.afectadas && <Marker position={resumen.afectadas.centro} icon={ICONO_FOCO} interactive={false} />}
        </MapContainer>
        {sim && <span className="rs-insignia-demo">Simulación · no es tu parcela real</span>}
      </div>

      {/* Barra apilada + leyenda con ícono y texto: el color nunca va solo */}
      <div className="rs-barra-apilada" aria-hidden="true">
        {resumen.distribucion
          .filter((d) => d.porcentaje > 0)
          .map((d) => (
            <span key={d.estado} style={{ flexGrow: d.porcentaje, background: ESTADOS[d.estado].color }} />
          ))}
      </div>
      <ul className="rs-leyenda">
        {ORDEN_ESTADOS.map((k) => {
          const d = resumen.distribucion.find((x) => x.estado === k)
          const Icono = ICONO_ESTADO[k]
          return (
            <li key={k} className={d.porcentaje === 0 ? 'vacio' : ''}>
              <Icono size={16} style={{ color: ESTADOS[k].color }} aria-hidden="true" />
              <span className="rs-leyenda-nombre">{etiquetas[k]}</span>
              <span className="rs-leyenda-ha">{formato(d.hectareas, 2)} ha</span>
              <strong>{Math.round(d.porcentaje)}%</strong>
            </li>
          )
        })}
      </ul>
      {sim ? (
        <p className="rs-nota rs-nota-sim">
          Estos colores son un ejemplo inventado para mostrar cómo funcionará el mapa. No describen lo que pasa en tu terreno
          y no sirven para decidir dónde revisar o regar.
        </p>
      ) : resumen.afectadas ? (
        <p className="rs-nota">
          Las zonas a revisar están en <strong>{textoZona(resumen.afectadas.zona)}</strong> de tu parcela.
        </p>
      ) : (
        <p className="rs-nota">Toda la parcela se ve pareja. ¡Bien!</p>
      )}
    </div>
  )
}
