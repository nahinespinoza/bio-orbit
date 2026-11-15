import { useState } from 'react'
import { ChevronUp, X } from 'lucide-react'
import { NIVELES, peorNivel } from '../../lib/reporte.js'
import { IlustracionReporte } from './IlustracionesReporte.jsx'
import MapaParcelas from './MapaParcelas.jsx'

function Pildora({ nivel, texto, alerta = false }) {
  return (
    <span className={`rp-pildora${alerta ? ' alerta' : ''}`}>
      <span className={`ui-punto ui-nivel-${nivel}`} aria-hidden="true" />
      {texto}
    </span>
  )
}

function Antetitulo({ texto, ejemplo }) {
  return (
    <p className="rp-antetitulo">
      <span>{texto}</span>
      {ejemplo && <span className="rp-ejemplo">Datos de ejemplo</span>}
    </p>
  )
}

// Resumen a pantalla completa que sale al terminar el análisis de una finca:
// una pantalla por dato, se desliza hacia arriba. Termina en el mapa.
export default function CarruselInsights({ finca, reporte, onSalir }) {
  const [actual, setActual] = useState(0)
  const { indicadores, alertas, alertaPrincipal, ejemplo } = reporte
  const conEstado = indicadores.filter((i) => i.estado && i.id !== alertaPrincipal?.indicadorId)
  const total = 1 + indicadores.length + alertas.length + 1

  const alDeslizar = (e) => {
    const { scrollTop, clientHeight } = e.currentTarget
    const i = Math.round(scrollTop / clientHeight)
    if (i !== actual) setActual(i)
  }

  return (
    <div className="fg-pantalla rp-carrusel ui-sobre-oscuro">
      <div className="rp-carrusel-pistas" onScroll={alDeslizar} tabIndex={0} aria-label="Resumen de la semana">
        {/* 1 · Resumen */}
        <section className="rp-diapositiva rp-resumen">
          <Antetitulo texto={[finca.nombre, reporte.periodoClima].filter(Boolean).join(' · ')} ejemplo={ejemplo} />
          <h1 className="rp-resumen-titulo">Tu semana</h1>
          <ul className="rp-resumen-lista">
            {alertaPrincipal && (
              <li className="rp-resumen-fila destacada">
                <span className="rp-cuadro" aria-hidden="true" />
                <span className="rp-resumen-texto">{alertaPrincipal.texto}</span>
              </li>
            )}
            {conEstado.map((i) => (
              <li key={i.id} className="rp-resumen-fila">
                <span className={`ui-punto ui-nivel-${i.estado.nivel}`} aria-hidden="true" />
                <span className="rp-resumen-texto">{i.estado.texto}</span>
                <small>{i.titulo}</small>
              </li>
            ))}
          </ul>
          <span className="rp-deslizar">
            <ChevronUp size={24} aria-hidden="true" />
            Desliza hacia arriba
          </span>
        </section>

        {/* 2 · Un dato por pantalla */}
        {indicadores.map((i) => (
          <section key={i.id} className={`rp-diapositiva tono-${i.tono}`} aria-label={i.titulo}>
            <Antetitulo texto={i.titulo} ejemplo={ejemplo} />
            <div className="rp-diapositiva-dibujo"><IlustracionReporte tipo={i.ilustracion} /></div>
            {i.estado && <Pildora nivel={i.estado.nivel} texto={i.estado.texto} />}
            <p className={`rp-valor-grande${i.valor.length > 4 ? ' largo' : ''}`}>
              <strong>{i.valor}</strong>
              {i.unidad && <span>{i.unidad}</span>}
            </p>
            <p className="rp-diapositiva-etiqueta">{i.etiqueta}</p>
            {i.grupo === 'parcela' && reporte.fotoFecha && <p className="rp-diapositiva-fecha">{reporte.fotoFecha}</p>}
          </section>
        ))}

        {/* 3 · Alertas del mes que viene */}
        {alertas.map((a) => (
          <section key={a.id} className="rp-diapositiva tono-ocre" aria-label={a.titulo}>
            <Antetitulo texto={reporte.mesAlertas ? `Para ${reporte.mesAlertas}` : 'Próximo mes'} ejemplo={ejemplo} />
            <div className="rp-diapositiva-dibujo"><IlustracionReporte tipo={a.ilustracion} /></div>
            {a.riesgo && <Pildora nivel={a.nivel} texto={a.riesgo} alerta />}
            <p className="rp-titulo-alerta">{a.titulo}</p>
            {a.subtitulo && <p className="rp-diapositiva-etiqueta">{a.subtitulo}</p>}
          </section>
        ))}

        {/* 4 · Mapa y salida */}
        <section className="rp-diapositiva rp-diapositiva-mapa" aria-label="Mapa de tu finca">
          <div className="rp-mapa-fondo">
            <MapaParcelas
              parcelas={finca.parcelas}
              color={NIVELES[peorNivel(reporte)].color}
              capa={reporte.capas ? { url: reporte.capas.vigor, limites: reporte.capas.limites } : null}
            />
          </div>
          <div className="rp-mapa-pie">
            <h2>{finca.nombre}</h2>
            <button type="button" className="rp-boton-principal" onClick={onSalir}>Ir a mi finca</button>
          </div>
        </section>
      </div>

      <button type="button" className="rp-cerrar" onClick={onSalir} aria-label="Cerrar resumen">
        <X size={24} />
      </button>

      <div className="rp-puntos" aria-hidden="true">
        {Array.from({ length: total }, (_, i) => (
          <span key={i} className={i === actual ? 'activo' : ''} />
        ))}
      </div>
    </div>
  )
}
