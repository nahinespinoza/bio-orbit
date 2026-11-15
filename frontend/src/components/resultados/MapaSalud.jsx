import { useMemo } from 'react'
import { MapContainer, Marker, Polygon, Rectangle, TileLayer } from 'react-leaflet'
import L from '../../lib/leaflet.js'
import { TILE_SATELITE } from '../flujo-gps/geo.js'
import { ESTADOS, ORDEN_ESTADOS, formato, textoZona } from './analisis.js'
import { ICONO_ESTADO } from './iconos.js'
import BarraSalud from './BarraSalud.jsx'
import { ETIQUETAS_SALUD } from './salud.js'

const ICONO_FOCO = L.divIcon({
  className: 'rs-foco',
  html: '<span></span><span></span>',
  iconSize: [56, 56],
  iconAnchor: [28, 28],
})

const ETIQUETAS_CAPA = {
  verdor: ETIQUETAS_SALUD, // Sana / En alerta / Débil / Crítica: el mismo vocabulario en toda la app
  humedad: { bien: 'Húmedo', atencion: 'Algo seco', problema: 'Seco', grave: 'Muy seco' },
}

// Detalle de una capa (verdor o humedad): mapa grande por zonas y su reparto.
export default function MapaSalud({ parcela, zonas, capa, resaltar }) {
  const sim = zonas.simulado
  const limites = useMemo(() => L.latLngBounds(parcela.poligono), [parcela])
  const lienzo = useMemo(() => L.canvas({ padding: 0.5 }), [])
  const resumen = zonas[capa]
  const etiquetas = ETIQUETAS_CAPA[capa]

  return (
    <div className="rs-tarjeta rs-mapa-tarjeta">
      <div className="rs-mapa">
        <MapContainer
          bounds={limites}
          boundsOptions={{ padding: [22, 22] }}
          className="map"
          zoomControl={false}
          scrollWheelZoom={false}
          doubleClickZoom={false}
          attributionControl={false}
        >
          <TileLayer url={TILE_SATELITE.url} maxZoom={19} />
          {zonas.celdas.map((c, i) => c.estado[capa] && (
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
        {!sim && zonas.fuente && <span className="rs-insignia-demo">{zonas.fuente}</span>}
      </div>

      <BarraSalud segmentos={resumen.distribucion} etiquetas={etiquetas} leyenda={false} />
      <ul className="rs-leyenda">
        {/* Con datos reales solo se listan los estados presentes (Sana / En alerta / Crítica) */}
        {ORDEN_ESTADOS.filter((k) => sim || resumen.distribucion.find((x) => x.estado === k).porcentaje > 0).map((k) => {
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
      {/* Con datos reales se indica dónde revisar; con la simulación no se afirma nada. */}
      {!sim && resumen.afectadas && (
        <p className="rs-nota">
          Revisa <strong>{textoZona(resumen.afectadas.zona)}</strong> de tu parcela.
        </p>
      )}
    </div>
  )
}
