import { AlertTriangle, ChevronRight, MapPin, Plus, Satellite, ScanLine, Wheat } from 'lucide-react'
import { formatoNumero } from './geo.js'
import { NIVELES, peorNivel } from '../../lib/reporte.js'
import FilaAnalisis from '../ui/FilaAnalisis.jsx'
import Widget from '../ui/Widget.jsx'
import { IlustracionReporte } from '../reporte/IlustracionesReporte.jsx'
import MapaParcelas from '../reporte/MapaParcelas.jsx'
import SelectorFinca from './SelectorFinca.jsx'

// Un widget por dato del reporte semanal. Si son datos de ejemplo, el primero lo dice.
function Widgets({ lista, ejemplo, onVerDetalle }) {
  return lista.map((i, n) => (
    <Widget
      key={i.id}
      tono={i.tono}
      ilustracion={<IlustracionReporte tipo={i.ilustracion} />}
      valor={i.valor}
      unidad={i.unidad}
      detalle={[i.etiqueta]}
      estado={i.estado}
      etiqueta={i.titulo}
      insignia={ejemplo && n === 0 ? 'Datos de ejemplo' : undefined}
      accion={{ texto: 'Ver detalle', onClick: () => onVerDetalle(i.id) }}
    />
  ))
}

function TituloSeccion({ titulo, fecha }) {
  return (
    <div className="fg-seccion-cabeza">
      <h2 className="fg-seccion-titulo">{titulo}</h2>
      {fecha && <span>{fecha}</span>}
    </div>
  )
}

// Inicio: arriba se elige la finca; debajo, sus parcelas y el reporte de la semana
// (un widget por dato, cada uno abre su panel).
export default function PantallaHome({
  nombre, finca, fincas, reporte, onElegirFinca, onNuevaFinca, onAgregarParcela,
  onVerResumen, onVerIndicador, onVerMapa, onPlanSiembra,
}) {
  const { ubicacion, parcelas } = finca
  const areaTotal = parcelas.reduce((s, p) => s + p.area, 0)
  const varias = parcelas.length > 1
  const primerNombre = nombre.split(' ')[0]
  const porGps = ubicacion?.precision != null
  const colorFinca = reporte ? NIVELES[peorNivel(reporte)].color : '#10b981'

  const insignia = finca.preanalizada ? 'Parcela analizada' : porGps ? 'Contorno aproximado' : 'Dibujada por ti'
  const lineaFinca = varias
    ? `${parcelas.length} parcelas · ${formatoNumero(areaTotal, 1)} ha en total`
    : finca.preanalizada
      ? `1 parcela · ${formatoNumero(areaTotal)} ha`
      : porGps
      ? `Ubicada con el GPS del celular (±${Math.round(ubicacion.precision)} m)`
      : 'Ubicada dibujándola en el mapa'

  const deParcela = reporte?.indicadores.filter((i) => i.grupo === 'parcela') ?? []
  const deClima = reporte?.indicadores.filter((i) => i.grupo === 'clima') ?? []
  const alertas = reporte?.alertas ?? []
  const principal = reporte?.alertaPrincipal

  const contenidoAlerta = principal && (
    <>
      <AlertTriangle size={22} aria-hidden="true" />
      <span className="fg-alerta-texto">
        <strong>{principal.texto}</strong>
        {principal.confirmada && <small>Confirmado por satélite</small>}
      </span>
      {principal.indicadorId && <ChevronRight size={20} aria-hidden="true" />}
    </>
  )

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
            <MapaParcelas parcelas={parcelas} color={colorFinca} />
            <span className="fg-insignia">
              <ScanLine size={14} /> {insignia}
            </span>
            {/* Encima del mapa: todo el mapa abre el panel con el mapa grande */}
            <button type="button" className="fg-mini-mapa-boton" onClick={onVerMapa} aria-label="Ver mi finca en el mapa">
              <span className="fg-ver-mapa">
                Ver mapa <ChevronRight size={14} />
              </span>
            </button>
          </div>
          <div className="fg-tarjeta-finca-info">
            <div className="fg-tarjeta-finca-texto">
              <h2>{finca.nombre}</h2>
              <p>
                <MapPin size={14} />
                {lineaFinca}
              </p>
            </div>
            <button type="button" className="fg-btn-anadir" onClick={onAgregarParcela}>
              <Plus size={18} /> Añadir parcela
            </button>
          </div>
        </article>

        {reporte && (
          <>
            {principal && (
              <div className="fg-aparecer" style={{ '--retraso': '0.05s' }}>
                {principal.indicadorId ? (
                  <button type="button" className="fg-alerta" onClick={() => onVerIndicador(principal.indicadorId)}>
                    {contenidoAlerta}
                  </button>
                ) : (
                  <div className="fg-alerta">{contenidoAlerta}</div>
                )}
              </div>
            )}

            <button type="button" className="fg-fila-resumen fg-aparecer" style={{ '--retraso': '0.1s' }} onClick={onVerResumen}>
              <span className="fg-fila-resumen-texto">
                <strong>Resumen de la semana</strong>
                {reporte.periodoClima && <span>{reporte.periodoClima}</span>}
              </span>
              <ChevronRight size={20} aria-hidden="true" />
            </button>

            {deParcela.length > 0 && (
              <section className="fg-seccion fg-aparecer" style={{ '--retraso': '0.15s' }}>
                <TituloSeccion titulo="Tu parcela" fecha={reporte.fotoFecha} />
                <Widgets lista={deParcela} ejemplo={reporte.ejemplo} onVerDetalle={onVerIndicador} />
              </section>
            )}

            {deClima.length > 0 && (
              <section className="fg-seccion fg-aparecer" style={{ '--retraso': '0.2s' }}>
                <TituloSeccion titulo="Clima de la semana" fecha={reporte.periodoClima} />
                <Widgets lista={deClima} ejemplo={reporte.ejemplo} onVerDetalle={onVerIndicador} />
              </section>
            )}

            {alertas.length > 0 && (
              <section className="fg-seccion fg-alertas-mes">
                <TituloSeccion titulo={reporte.mesAlertas ? `Para ${reporte.mesAlertas}` : 'Próximo mes'} />
                {alertas.map((a) => (
                  <Widget
                    key={a.id}
                    tono="ocre"
                    ilustracion={<IlustracionReporte tipo={a.ilustracion} />}
                    valor={a.titulo}
                    detalle={a.subtitulo ? [a.subtitulo] : []}
                    estado={a.riesgo ? { nivel: a.nivel, texto: a.riesgo } : undefined}
                    accion={{ texto: 'Ver detalle', onClick: () => onVerIndicador(a.id) }}
                  />
                ))}
              </section>
            )}
          </>
        )}

        <FilaAnalisis
          tono="verde"
          Icono={Wheat}
          titulo="Plan de siembra"
          texto="Qué sembrar en los próximos 4 años"
          onClick={onPlanSiembra}
        />

        {reporte && (
          <p className="fg-fuente">
            <Satellite size={14} aria-hidden="true" />
            {['Fuente: NASA POWER y Sentinel-2', reporte.zona].filter(Boolean).join(' · ')}
          </p>
        )}
      </div>
    </div>
  )
}
