import { AlertTriangle, Check, ChevronLeft, Map as IconoMapa, Satellite } from 'lucide-react'
import { NIVELES } from '../../lib/reporte.js'
import { IlustracionReporte } from './IlustracionesReporte.jsx'
import '../resultados/resultados.css'

const ICONO_NIVEL = { bien: Check, atencion: AlertTriangle, problema: AlertTriangle, exceso: AlertTriangle, sin_dato: AlertTriangle }

// Panel especializado de un dato: el número en grande, su estado y qué hacer
// (el mensaje literal del JSON). Sin gráficos.
// `indicador` también puede ser una alerta del mes adaptada a la misma forma.
export default function PanelIndicador({ indicador, reporte, onVolver, onVerMapa }) {
  const { titulo, tono, ilustracion, valor, unidad, etiqueta, estado, mensaje, partes = [], historial = [] } = indicador
  const numero = Boolean(unidad)
  const conMapa = indicador.id === 'salud' || indicador.id === 'agua'
  const fecha = {
    parcela: reporte.fotoFecha,
    clima: reporte.periodoClima,
    alerta: reporte.mesAlertas && `Para ${reporte.mesAlertas}`,
  }[indicador.grupo]
  // Lo de la parcela cruza el clima de la zona con la foto satelital
  const fuente = indicador.grupo === 'parcela' ? 'NASA POWER y Sentinel-2' : 'NASA POWER'
  const nivelMensaje = estado?.nivel ?? 'sin_dato'
  const IconoMensaje = ICONO_NIVEL[nivelMensaje]

  return (
    <div className="fg-pantalla rs rp-panel">
      <header className="rs-cabecera">
        <button type="button" className="rs-volver" onClick={onVolver} aria-label="Volver al inicio">
          <ChevronLeft size={24} />
        </button>
        <h1>{titulo}</h1>
      </header>

      <div className="rs-contenido">
        <section className={`rp-dato tono-${tono} ui-sobre-oscuro`}>
          {reporte.ejemplo && <span className="rp-ejemplo">Datos de ejemplo</span>}
          <div className="rp-dato-dibujo"><IlustracionReporte tipo={ilustracion} /></div>
          <p className={`rp-dato-valor${numero ? '' : ' texto'}`}>
            <strong>{valor}</strong>
            {unidad && <span>{unidad}</span>}
          </p>
          {etiqueta && <p className="rp-dato-etiqueta">{etiqueta}</p>}
          {estado && (
            <span className="rp-pildora">
              <span className={`ui-punto ui-nivel-${estado.nivel}`} aria-hidden="true" />
              {estado.texto}
            </span>
          )}
        </section>

        {mensaje && (
          <section className={`rp-que-hacer nivel-${nivelMensaje}`}>
            <IconoMensaje size={24} aria-hidden="true" />
            <div>
              <h2>Qué hacer</h2>
              <p>{mensaje}</p>
            </div>
          </section>
        )}

        {partes.length > 0 && (
          <ul className="rp-partes">
            {partes.map((p) => (
              <li key={p.etiqueta}>
                {p.nivel && <span className={`ui-punto ui-nivel-${p.nivel}`} aria-hidden="true" />}
                <span>{p.etiqueta}</span>
                <strong>{p.texto}</strong>
              </li>
            ))}
          </ul>
        )}

        {historial.length > 0 && (
          <section className="rp-historial">
            <h2 id="rp-historial-titulo">Foto por foto</h2>
            {/* Se desplaza de lado: con foco también se mueve con las flechas */}
            <ol tabIndex={0} aria-labelledby="rp-historial-titulo">
              {historial.map((h) => (
                <li key={h.dia}>
                  <span>{h.dia}</span>
                  <span className={`rp-historial-punto ui-punto ui-nivel-${h.nivel}`} aria-hidden="true" />
                  <small>{NIVELES[h.nivel].nombre}</small>
                </li>
              ))}
            </ol>
          </section>
        )}

        {conMapa && (
          <button type="button" className="rp-boton-mapa" onClick={onVerMapa}>
            <IconoMapa size={20} /> Ver en el mapa
          </button>
        )}

        <p className="rs-fuentes-linea">
          <Satellite size={14} />
          {[`Fuente: ${fuente}`, fecha].filter(Boolean).join(' · ')}
        </p>
      </div>
    </div>
  )
}
