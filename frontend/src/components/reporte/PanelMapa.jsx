import { useState } from 'react'
import { ChevronLeft } from 'lucide-react'
import { NIVELES } from '../../lib/reporte.js'
import MapaParcelas from './MapaParcelas.jsx'

// Capas que se pueden ver en el mapa: una por dato con estado
const CAPAS = [
  { id: 'salud', nombre: 'Salud', imagen: 'vigor' },
  { id: 'agua', nombre: 'Agua', imagen: 'humedad' },
  { id: 'helada', nombre: 'Heladas', imagen: null },
  { id: 'calor', nombre: 'Calor', imagen: null },
]

// Colores con que el equipo de datos pinta las imágenes de zonas (precision_s2.py)
const COLOR_ZONAS = { bien: '#1a9850', atencion: '#fac81e', problema: '#d73027', exceso: '#2c7bb6', sin_dato: '#a0a0a0' }

const LEYENDAS = {
  salud: [['bien', 'Verde: sana'], ['atencion', 'Amarillo: en alerta'], ['problema', 'Rojo: crítica'], ['sin_dato', 'Gris: sin cultivo']],
  agua: [['problema', 'Rojo: seca'], ['atencion', 'Amarillo: algo seca'], ['bien', 'Verde: bien'], ['exceso', 'Azul: mucha agua']],
  helada: [['bien', 'Verde: bien'], ['atencion', 'Amarillo: atención'], ['problema', 'Rojo: problema']],
  calor: [['bien', 'Verde: bien'], ['atencion', 'Amarillo: atención'], ['problema', 'Rojo: problema']],
}

// Nivel de una parcela en una capa. Hoy los datos son de toda la finca, así que
// todas las parcelas tienen el mismo; cuando haya datos por parcela, va aquí.
const nivelDeParcela = (_indice, indicador) => indicador?.estado?.nivel ?? 'sin_dato'

// Mapa grande de la finca con sus parcelas pintadas por estado, y una hoja abajo
// para elegir qué dato se pinta.
export default function PanelMapa({ finca, reporte, capaInicial = 'salud', onVolver }) {
  const capas = CAPAS.filter((c) => reporte.indicadores.some((i) => i.id === c.id && i.estado))
  const [capaId, setCapaId] = useState(capas.some((c) => c.id === capaInicial) ? capaInicial : capas[0]?.id)
  const [elegida, setElegida] = useState(null)

  const { parcelas } = finca
  const capa = capas.find((c) => c.id === capaId)
  const indicador = reporte.indicadores.find((i) => i.id === capaId)
  const imagen = capa?.imagen && reporte.capas?.[capa.imagen]
  const nivel = nivelDeParcela(elegida, indicador)
  const cuantas = `${parcelas.length} ${parcelas.length === 1 ? 'parcela' : 'parcelas'}`
  const nombre = elegida != null ? `Parcela ${elegida + 1}` : parcelas.length === 1 ? 'Parcela 1' : cuantas
  const colores = imagen ? COLOR_ZONAS : Object.fromEntries(Object.entries(NIVELES).map(([k, v]) => [k, v.color]))

  return (
    <div className="fg-pantalla rp-mapa">
      <div className="rp-mapa-grande">
        <MapaParcelas
          parcelas={parcelas}
          color={(i) => NIVELES[nivelDeParcela(i, indicador)].color}
          capa={imagen ? { url: imagen, limites: reporte.capas.limites } : null}
          interactivo
          seleccionada={elegida}
          onElegir={setElegida}
        />
        <button type="button" className="rp-flotante rp-mapa-volver" onClick={onVolver} aria-label="Volver">
          <ChevronLeft size={24} />
        </button>
        <span className="rp-flotante rp-mapa-nombre">{finca.nombre} · {cuantas}</span>
      </div>

      <section className="rp-hoja">
        {capas.length > 0 && (
          <div className="rp-capas" role="group" aria-label="Qué ver en el mapa">
            {capas.map((c) => (
              <button
                key={c.id}
                type="button"
                aria-pressed={c.id === capaId}
                onClick={() => setCapaId(c.id)}
              >
                {c.nombre}
              </button>
            ))}
          </div>
        )}

        {indicador && (
          <div className={`rp-estado nivel-${nivel}`} aria-live="polite">
            <span className={`rp-estado-punto ui-punto ui-nivel-${nivel}`} aria-hidden="true" />
            <strong className="rp-estado-texto">
              {nombre} · {indicador.estado.texto}
            </strong>
            <strong className="rp-estado-valor">
              {indicador.valor}
              {indicador.unidad && ` ${indicador.unidad}`}
            </strong>
          </div>
        )}

        {capaId && (
          <ul className="rp-leyenda">
            {LEYENDAS[capaId].map(([n, texto]) => (
              <li key={n}>
                <span style={{ background: colores[n] }} aria-hidden="true" />
                {texto}
              </li>
            ))}
          </ul>
        )}
        {reporte.ejemplo && <p className="rp-mapa-nota">Datos de ejemplo</p>}
      </section>
    </div>
  )
}
