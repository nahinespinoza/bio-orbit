import { useMemo } from 'react'
import { MapContainer, Polygon, TileLayer } from 'react-leaflet'
import { ChevronRight, Layers, MapPin, Plus, ScanLine, Sprout, Zap } from 'lucide-react'
import L from '../../lib/leaflet.js'
import { TILE_SATELITE, formatoNumero } from './geo.js'
import { MENSAJE_ESTADO } from '../resultados/analisis.js'
import FilaAnalisis from '../ui/FilaAnalisis.jsx'
import SelectorFinca from './SelectorFinca.jsx'

// Inicio: arriba se elige la finca; debajo, sus parcelas y los dos análisis disponibles.
export default function PantallaHome({
  nombre, finca, fincas, onElegirFinca, onNuevaFinca, onProceso, onVerResultados, onAgregarParcela,
}) {
  const { ubicacion, parcelas, analisis } = finca
  const limites = useMemo(() => L.latLngBounds(parcelas.flatMap((p) => p.poligono)), [parcelas])
  const areaTotal = parcelas.reduce((s, p) => s + p.area, 0)
  const varias = parcelas.length > 1
  const primerNombre = nombre.split(' ')[0]
  const porGps = ubicacion.precision != null

  const salud = !analisis
    ? { texto: 'Sin análisis todavía. Toca para analizar.', nota: undefined }
    : analisis.simulado
      ? { texto: 'Mira el ejemplo de cómo se verá', nota: 'Simulado' }
      : { texto: `${MENSAJE_ESTADO[analisis.estado].titulo} · ${analisis.puntaje}/100`, nota: undefined }

  return (
    <div className="fg-pantalla fg-home">
      <header className="fg-home-cabecera">
        <SelectorFinca activa={finca} fincas={fincas} onElegir={onElegirFinca} onNueva={onNuevaFinca} />
        <span className="vm-avatar" title={nombre} aria-hidden="true">
          {primerNombre.charAt(0).toUpperCase()}
        </span>
      </header>

      <div className="fg-home-contenido">
        <article className="fg-tarjeta-finca fg-aparecer">
          <div className="fg-mini-mapa">
            <MapContainer
              // Al agregar una parcela cambian los límites: se vuelve a encuadrar
              key={parcelas.length}
              bounds={limites}
              boundsOptions={{ padding: [20, 20] }}
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
              {parcelas.map((p, i) => (
                <Polygon
                  key={i}
                  positions={p.poligono}
                  pathOptions={{ color: '#fff', weight: 2, fillColor: '#10b981', fillOpacity: 0.4 }}
                />
              ))}
            </MapContainer>
            <span className="fg-insignia">
              <ScanLine size={14} /> {porGps ? 'Contorno aproximado' : 'Dibujada por ti'}
            </span>
          </div>
          <div className="fg-tarjeta-finca-info">
            <div className="fg-tarjeta-finca-texto">
              <h2>{finca.nombre}</h2>
              <p>
                <MapPin size={14} />
                {varias
                  ? `${parcelas.length} parcelas · ${formatoNumero(areaTotal, 1)} ha en total`
                  : porGps
                    ? `Ubicada con el GPS del celular (±${Math.round(ubicacion.precision)} m)`
                    : 'Ubicada dibujándola en el mapa'}
              </p>
            </div>
            <button type="button" className="fg-btn-anadir" onClick={onAgregarParcela}>
              <Plus size={18} /> Añadir parcela
            </button>
          </div>
        </article>

        <section className="fg-aparecer" style={{ '--retraso': '0.1s' }}>
          <h2 className="fg-seccion-titulo">Analiza tu finca</h2>
          <div className="fg-analisis">
            <button className="fg-analisis-btn" onClick={() => onProceso('Rápido')}>
              <span className="fg-analisis-icono"><Zap size={22} /></span>
              <span className="fg-analisis-texto">
                <strong>Rápido</strong>
                <small>Cómo está tu finca y qué lluvia viene</small>
              </span>
              <ChevronRight size={20} />
            </button>
            <button className="fg-analisis-btn azul" onClick={() => onProceso('Profundo')}>
              <span className="fg-analisis-icono"><Layers size={22} /></span>
              <span className="fg-analisis-texto">
                <strong>Profundo</strong>
                <small>Además, qué sembrar en los próximos 4 años</small>
              </span>
              <ChevronRight size={20} />
            </button>
          </div>
        </section>

        <section className="fg-aparecer" style={{ '--retraso': '0.2s' }}>
          <FilaAnalisis
            tono="morado"
            Icono={Sprout}
            titulo="Salud del cultivo"
            texto={salud.texto}
            nota={salud.nota}
            notaTipo="simulado"
            onClick={onVerResultados}
          />
        </section>
      </div>
    </div>
  )
}
