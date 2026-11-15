import { X } from 'lucide-react'
import './resumen-compacto.css'

// Versión resumida del resumen de la semana: todo en una sola pantalla, sin deslizar.
// Usa el mismo modelo (`reporte`, de lib/reporte.js) y los estilos del carrusel.
export default function ResumenSemanaCompacto({ finca, reporte, onSalir }) {
  const { indicadores, alertas, alertaPrincipal, ejemplo } = reporte
  const conEstado = indicadores.filter((i) => i.estado && i.id !== alertaPrincipal?.indicadorId)
  const sinEstado = indicadores.filter((i) => !i.estado)

  return (
    <div className="fg-pantalla rp-carrusel ui-sobre-oscuro">
      <div className="rp-compacto">
        <section className="rp-diapositiva rp-resumen rp-compacto-hoja">
          <p className="rp-antetitulo">
            <span>{[finca.nombre, reporte.periodoClima].filter(Boolean).join(' · ')}</span>
            {ejemplo && <span className="rp-ejemplo">Datos de ejemplo</span>}
          </p>
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

          {sinEstado.length > 0 && (
            <dl className="rp-compacto-datos">
              {sinEstado.map((i) => (
                <div key={i.id}>
                  <dt>{i.titulo}</dt>
                  <dd>
                    {i.valor} {i.unidad} <small>{i.etiqueta}</small>
                  </dd>
                </div>
              ))}
            </dl>
          )}

          {alertas.length > 0 && (
            <>
              <h2 className="rp-compacto-subtitulo">
                {reporte.mesAlertas ? `Para ${reporte.mesAlertas}` : 'Próximo mes'}
              </h2>
              <ul className="rp-resumen-lista">
                {alertas.map((a) => (
                  <li key={a.id} className="rp-resumen-fila">
                    <span className={`ui-punto ui-nivel-${a.nivel}`} aria-hidden="true" />
                    <span className="rp-resumen-texto">
                      {a.titulo}
                      {a.subtitulo && <> ({a.subtitulo})</>}
                    </span>
                    {a.riesgo && <small>{a.riesgo}</small>}
                  </li>
                ))}
              </ul>
            </>
          )}

          <button type="button" className="rp-boton-principal" onClick={onSalir}>
            Volver a los resultados
          </button>
        </section>
      </div>

      <button type="button" className="rp-cerrar" onClick={onSalir} aria-label="Cerrar resumen">
        <X size={24} />
      </button>
    </div>
  )
}
