import { useEffect, useMemo, useRef, useState } from 'react'
import {
  Check, ChevronLeft, CloudRain, Droplets, Layers, LoaderCircle, RefreshCw, Satellite, Sprout, WifiOff, Zap,
} from 'lucide-react'
import { PERIODO, obtenerDatosNasa } from '../../lib/nasa.js'
import {
  MESES_LARGOS, analizarFinca, formato, zonasRemoteSensing,
} from './analisis.js'
import MapaSalud from './MapaSalud.jsx'
import GraficoLluvia from './GraficoLluvia.jsx'
import RecomendacionesIA, { AccesoPitagoras } from './RecomendacionesIA.jsx'
import Widget from '../ui/Widget.jsx'
import FilaAnalisis from '../ui/FilaAnalisis.jsx'
import { IlustracionClima } from '../ui/Ilustraciones.jsx'
import AlertaPrincipal from './AlertaPrincipal.jsx'
import AnalisisCard from './AnalisisCard.jsx'
import EstadoParcelaCard from './EstadoParcelaCard.jsx'
import TarjetaResumenSemana from './TarjetaResumenSemana.jsx'
import SelectorFinca from '../flujo-gps/SelectorFinca.jsx'
import CarruselInsights from '../reporte/CarruselInsights.jsx'
import ResumenSemanaCompacto from '../reporte/ResumenSemanaCompacto.jsx'
import './resultados.css'

const PASOS = {
  Rápido: ['Descargando 10 años de lluvia (NASA GPM)', 'Leyendo la humedad del suelo', 'Revisando el verdor de tu parcela', 'Preparando tus consejos'],
  Profundo: ['Descargando 10 años de lluvia (NASA GPM)', 'Leyendo la humedad del suelo', 'Revisando el verdor de tu parcela', 'Comparando rotaciones de cultivo', 'Preparando tus consejos'],
}
const DURACION_MIN = { Rápido: 2200, Profundo: 3200 }

const TITULOS = {
  verdor: 'Salud del cultivo',
  humedad: 'Agua en el suelo',
  lluvia: 'Lluvia en tu zona',
  siembra: 'Recomendaciones',
}

const mayuscula = (t) => t.charAt(0).toUpperCase() + t.slice(1)

// --- Remote-sensing (datos quemados, Parcela 1) ------------------------------------------------
// Lo que se presenta sale de `rs.resumen` (resumen-parcela1.json). La serie mensual de NASA POWER de la
// parcela cubre 5 años (2021–2026): cada mes tiene 4 o 5 años con dato.
const RS_MIN_AÑOS = 4
const fechaCorta = (iso) => iso.split('-').reverse().join('/')
const pct = (v) => `${Math.round(v)}%`

// Nombre corto de cada alerta para las etiquetas de riesgo de las tarjetas
const CORTO = { NUTRICION_PROBABLE: 'Nitrógeno', NUTRIENTES: 'Nutrientes', PLAGAS_LANCHA: 'Lancha', HELADAS: 'Heladas' }

function alertasRS(rs) {
  return rs.resumen.alertas.map((a) => ({
    id: a.codigo,
    nivel: a.nivel,
    confirmada: Boolean(a.confirmada),
    titulo: rs.alertas_textos[a.codigo]?.titulo ?? CORTO[a.codigo] ?? a.codigo,
    texto: rs.alertas_textos[a.codigo]?.mensaje ?? '',
  }))
}

// "Lancha · alto (preventivo)" a partir de la alerta con ese código (null si no hay)
function riesgoDe(alertas, codigo) {
  const a = alertas.find((x) => x.id === codigo)
  if (!a) return null
  const nivel = a.nivel.toLowerCase()
  return { nivel, texto: `${CORTO[codigo] ?? a.titulo} · ${nivel}${a.confirmada ? '' : ' (preventivo)'}` }
}

// El agua: el suelo (NASA, regional) y las hojas (Sentinel-2) pueden no coincidir.
// La fila usa lenguaje de finca; el detalle explica las cifras (NDMI incluido).
function aguaRS({ agua }) {
  if (!agua) return { fila: 'Sin datos de agua para esta fecha.', titulo: null, texto: null }
  if (agua.estado === 'FUENTES_DIFIEREN') {
    return {
      fila: 'Las fuentes difieren: suelo húmedo, hojas con poca agua',
      titulo: 'El suelo y las hojas no coinciden',
      texto:
        `La humedad del suelo de la zona es ${pct(agua.regionalPct)} (NASA POWER), pero el satélite ve poca agua ` +
        `en las hojas (NDMI ${formato(agua.ndmi, 2)}). Revisa el lote en campo: puede ser estrés local, ` +
        'drenaje o poca cobertura del cultivo.',
    }
  }
  return { fila: `Suelo de la zona con ${pct(agua.regionalPct)} de humedad`, titulo: null, texto: null }
}

function Cargando({ modo, paso }) {
  const pasos = PASOS[modo]
  const progreso = Math.round((paso / pasos.length) * 100)
  return (
    <div className="rs-cargando">
      <div className="rs-cargando-icono">
        <span className="rs-orbita" />
        <Satellite size={34} />
      </div>
      <h2>Analizando tu finca…</h2>
      <p>Estamos juntando datos de satélites de la NASA. No tienes que hacer nada.</p>
      <div className="fg-progreso" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={progreso}>
        <span style={{ width: `${progreso}%` }} />
      </div>
      <ul className="fg-pasos">
        {pasos.map((texto, i) => (
          <li key={texto} className={i < paso ? 'hecho' : i === paso ? 'activo' : ''}>
            <span className="fg-paso-icono">
              {i < paso ? <Check size={14} /> : i === paso ? <LoaderCircle size={14} className="onb-girando" /> : null}
            </span>
            {texto}
          </li>
        ))}
      </ul>
    </div>
  )
}

// Cómo es el mes actual comparado con el resto del año (define ilustración y texto).
function estacionDelMes(mediana, promedio) {
  if (mediana == null || promedio == null) return { tipo: 'nubes', texto: 'Sin datos de lluvia' }
  if (mediana >= promedio) return { tipo: 'lluvia', texto: 'Temporada de lluvias' }
  if (mediana < promedio * 0.6) return { tipo: 'sol', texto: 'Época seca' }
  return { tipo: 'nubes', texto: 'Lluvia moderada' }
}

// Con `remoteSensing` (datos quemados de remote-sensing/, ver frontend/scripts/generar_remote_sensing.py)
// no se descarga nada: el clima sale de NASA POWER de la parcela y el mapa de salud de Sentinel-2.
// `finca` ({ nombre, parcelas }) + `reporte` (lib/reporte.js): tarjeta "Resumen de la semana".
// `selector` ({ fincas, activaId, onElegir, onNueva }): con varias fincas, la cabecera cambia de finca sin volver.
export default function PantallaResultados({
  ubicacion, parcela, modo, remoteSensing: rs, finca, reporte, selector, onVolver, onAnalisis,
}) {
  const [datos, setDatos] = useState(null)
  const [intento, setIntento] = useState(0)
  const [paso, setPaso] = useState(0)
  const [detalle, setDetalle] = useState(null) // null = lista | verdor | humedad | lluvia | siembra
  const [presentacion, setPresentacion] = useState(null) // null | 'interactivo' | 'resumido'
  const contenidoRef = useRef(null)
  const profundo = modo === 'Profundo'

  // Descarga de datos NASA con una duración mínima para que el usuario vea el progreso.
  useEffect(() => {
    const control = new AbortController()
    const minimo = DURACION_MIN[modo]
    const inicio = performance.now()
    const fuente = rs
      ? Promise.resolve({ lluvia: rs.mensual.lluvia, humedad: rs.mensual.humedad, temperatura: rs.mensual.temperatura, simulado: false })
      : obtenerDatosNasa(ubicacion, control.signal)
    fuente
      .then((d) => new Promise((ok) => setTimeout(() => ok(d), Math.max(0, minimo - (performance.now() - inicio)))))
      .then((d) => !control.signal.aborted && setDatos(d))
      .catch(() => {})
    return () => control.abort()
    // El modo solo afecta a la primera carga; pasar a "Profundo" no vuelve a descargar.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ubicacion, intento])

  useEffect(() => {
    if (datos) return
    const total = PASOS[modo].length
    const id = setInterval(() => setPaso((p) => Math.min(total - 1, p + 1)), DURACION_MIN[modo] / total)
    return () => clearInterval(id)
  }, [datos, modo])

  const analisis = useMemo(
    () =>
      datos
        ? analizarFinca({
            datos,
            parcela,
            ubicacion,
            zonas: rs ? zonasRemoteSensing(rs, parcela) : undefined,
            minAños: rs ? RS_MIN_AÑOS : undefined,
          })
        : null,
    [datos, parcela, ubicacion, rs],
  )

  const onAnalisisRef = useRef(onAnalisis)
  useEffect(() => {
    onAnalisisRef.current = onAnalisis
  })
  useEffect(() => {
    if (analisis) {
      onAnalisisRef.current?.({ puntaje: analisis.puntaje, estado: analisis.estado, simulado: analisis.diagnosticoSimulado })
    }
  }, [analisis])

  // Cada vista (lista o detalle) empieza desde arriba.
  useEffect(() => {
    if (contenidoRef.current) contenidoRef.current.scrollTop = 0
  }, [detalle])

  const reintentar = () => {
    setDatos(null)
    setPaso(0)
    setIntento((n) => n + 1)
  }

  const cabecera = (
    <header className="rs-cabecera">
      <button
        className="rs-volver"
        onClick={detalle ? () => setDetalle(null) : onVolver}
        aria-label={detalle ? 'Volver a resultados' : 'Volver al inicio'}
      >
        <ChevronLeft size={24} />
      </button>
      {!detalle && selector?.fincas.length > 1 ? (
        <SelectorFinca
          activa={selector.fincas.find((f) => f.id === selector.activaId) ?? selector.fincas[0]}
          fincas={selector.fincas}
          onElegir={selector.onElegir}
          onNueva={selector.onNueva}
        />
      ) : (
        <h1>{detalle ? TITULOS[detalle] : 'Resultados'}</h1>
      )}
      {!detalle && (
        <span className={`rs-modo ${profundo ? 'profundo' : ''}`}>
          {profundo ? <Layers size={14} /> : <Zap size={14} />} {modo}
        </span>
      )}
    </header>
  )

  if (presentacion && reporte && finca) {
    const salir = () => setPresentacion(null)
    return presentacion === 'interactivo'
      ? <CarruselInsights finca={finca} reporte={reporte} onSalir={salir} />
      : <ResumenSemanaCompacto finca={finca} reporte={reporte} onSalir={salir} />
  }

  const tarjetaResumen = reporte && finca && (
    <TarjetaResumenSemana
      periodo={reporte.periodoClima}
      ejemplo={reporte.ejemplo}
      onInteractivo={() => setPresentacion('interactivo')}
      onResumido={() => setPresentacion('resumido')}
    />
  )

  if (!analisis) {
    return (
      <div className="fg-pantalla rs">
        {cabecera}
        <Cargando modo={modo} paso={paso} />
      </div>
    )
  }

  const { zonas, lluvia, acciones } = analisis
  const ejemplo = analisis.simulado
  const mesAhora = lluvia.meses[analisis.mesActual]
  const nombreMes = MESES_LARGOS[analisis.mesActual]
  const estacion = estacionDelMes(mesAhora.mediana, lluvia.promedioMes)
  const consejoLluvia = acciones.find((a) => a.id === 'lluvia' || a.id === 'sin-datos')

  // Remote-sensing (Parcela 1): lo que se presenta sale del resumen
  const r = rs?.resumen
  const agua = r ? aguaRS(r) : null
  const consejoRS = r && {
    verdor: r.salud && {
      titulo: r.salud.mensaje,
      texto: `Foto Sentinel-2 del ${fechaCorta(r.salud.fecha)}. ${rs.alertas_textos.NUTRICION_PROBABLE?.mensaje ?? ''}`,
    },
    humedad: agua.titulo && { titulo: agua.titulo, texto: agua.texto },
  }

  const lista = (
    <>
      {ejemplo && (
        <div className="rs-aviso">
          <WifiOff size={18} />
          <span>Sin conexión con la NASA. Datos de ejemplo.</span>
          <button onClick={reintentar}>
            <RefreshCw size={14} /> Reintentar
          </button>
        </div>
      )}

      <Widget
        tono="azul"
        ilustracion={<IlustracionClima tipo={estacion.tipo} />}
        valor={analisis.temperatura == null ? '—' : formato(analisis.temperatura)}
        unidad="°C"
        insignia={ejemplo ? 'Datos de ejemplo' : undefined}
        detalle={[
          `Lo normal en ${nombreMes}`,
          mesAhora.mediana == null ? 'Lluvia: sin datos' : `Lluvia: ${mesAhora.mediana} mm al mes`,
        ]}
        etiqueta={estacion.texto}
        accion={{ texto: 'Ver lluvia', onClick: () => setDetalle('lluvia') }}
      />

      {tarjetaResumen}

      <section>
        <h2 className="rs-titulo">Análisis de tu parcela</h2>
        <ul className="ui-lista">
          <li>
            <FilaAnalisis
              tono="morado"
              Icono={Sprout}
              titulo="Salud del cultivo"
              texto={`${Math.round(zonas.verdor.normal)}% de tu parcela se ve sana`}
              nota={zonas.simulado ? 'Simulado' : undefined}
              notaTipo="simulado"
              onClick={() => setDetalle('verdor')}
            />
          </li>
          <li>
            <FilaAnalisis
              tono="azul"
              Icono={Droplets}
              titulo="Agua en el suelo"
              texto={`${Math.round(zonas.humedad.normal)}% del suelo tiene buena humedad`}
              nota={zonas.simulado ? 'Simulado' : undefined}
              notaTipo="simulado"
              onClick={() => setDetalle('humedad')}
            />
          </li>
          <li>
            <FilaAnalisis
              tono="turquesa"
              Icono={CloudRain}
              titulo="Lluvia"
              texto={consejoLluvia?.titulo ?? 'Lluvia de los últimos 10 años'}
              nota={ejemplo ? 'Datos de ejemplo' : `NASA GPM · ${PERIODO.inicio}–${PERIODO.fin}`}
              notaTipo={ejemplo ? 'simulado' : undefined}
              onClick={() => setDetalle('lluvia')}
            />
          </li>
        </ul>
      </section>

      <AccesoPitagoras onClick={() => setDetalle('siembra')} />

      <p className="rs-fuentes-linea">
        <Satellite size={14} /> Datos de la NASA: GPM IMERG y POWER
      </p>
    </>
  )

  // Parcela 1 (remote-sensing): clima → estado de la parcela → alertas → análisis
  const listaRS = r && (() => {
    const alertas = alertasRS(rs)
    return (
      <>
        <Widget
          tono="azul"
          ilustracion={<IlustracionClima tipo={r.clima.lluvia7dMm >= 40 ? 'lluvia' : 'nubes'} />}
          valor={formato(r.clima.tempMediaC)}
          unidad="°C"
          insignia="Últimos 7 días"
          detalle={[
            `Mín ${formato(r.clima.tempMinC)} °C · Máx ${formato(r.clima.tempMaxC)} °C`,
            `Lluvia: ${formato(r.clima.lluvia7dMm)} mm en 7 días`,
          ]}
          etiqueta="Clima en tu parcela"
          accion={{ texto: 'Ver lluvia', onClick: () => setDetalle('lluvia') }}
        />

        <EstadoParcelaCard parcela={parcela} zonas={zonas} salud={r.salud} onAbrir={() => setDetalle('verdor')} />

        <AlertaPrincipal alertas={alertas} />

        {tarjetaResumen}

        <section>
          <h2 className="rs-titulo">Análisis de tu parcela</h2>
          <ul className="ui-lista">
            {/* La salud del cultivo se abre desde "Estado de tu parcela" (arriba) */}
            <li>
              <AnalisisCard
                tono="azul"
                Icono={Droplets}
                titulo="Agua"
                nota="NASA POWER + Sentinel-2"
                onClick={() => setDetalle('humedad')}
              >
                {agua.fila}
              </AnalisisCard>
            </li>
            <li>
              <AnalisisCard
                tono="turquesa"
                Icono={CloudRain}
                titulo="Lluvia"
                riesgo={riesgoDe(alertas, 'PLAGAS_LANCHA')}
                nota={r.lluvia?.fuente}
                onClick={() => setDetalle('lluvia')}
              >
                {r.lluvia?.diciembreMm != null
                  ? `Diciembre: unos ${formato(r.lluvia.diciembreMm, 0)} mm (promedio histórico)`
                  : 'Sin datos de lluvia para el próximo mes.'}
              </AnalisisCard>
            </li>
          </ul>
        </section>

        <AccesoPitagoras onClick={() => setDetalle('siembra')} />

        {r.confianza && (
          <p className="rs-fuentes-linea">
            <Satellite size={14} /> {r.confianza.capturasUsadas} de {r.confianza.capturasTotales} fotos Sentinel-2
            usadas · {formato(r.confianza.areaHa, 2)} ha
          </p>
        )}
      </>
    )
  })()

  const vistaLluvia = (
    <>
      {r ? (
        <div className="rs-consejo nivel-info">
          <CloudRain size={20} />
          <div>
            <strong>Diciembre: unos {formato(r.lluvia.diciembreMm, 0)} mm</strong>
            <span>Promedio histórico de {r.lluvia.fuente}. En los últimos 7 días cayeron {formato(r.clima.lluvia7dMm)} mm.</span>
          </div>
        </div>
      ) : (
        consejoLluvia && consejoLluvia.id !== 'sin-datos' && (
          <div className={`rs-consejo nivel-${consejoLluvia.nivel}`}>
            <CloudRain size={20} />
            <div>
              <strong>{consejoLluvia.titulo}</strong>
              <span>{consejoLluvia.texto}</span>
            </div>
          </div>
        )
      )}
      <div className="rs-tarjeta">
        {ejemplo && <span className="rs-etiqueta-ejemplo">Datos de ejemplo</span>}
        <div className="rs-cifras">
          <div><span>Al año</span><strong>{lluvia.anual == null ? 'Sin datos' : `${formato(lluvia.anual, 0)} mm`}</strong></div>
          <div><span>Más lluvioso</span><strong>{lluvia.masLluvioso ? mayuscula(MESES_LARGOS[lluvia.masLluvioso.mes]) : 'Sin datos'}</strong></div>
          <div><span>Más seco</span><strong>{lluvia.masSeco ? mayuscula(MESES_LARGOS[lluvia.masSeco.mes]) : 'Sin datos'}</strong></div>
        </div>
        <GraficoLluvia lluvia={lluvia} mesActual={analisis.mesActual} />
      </div>
    </>
  )

  return (
    <div className="fg-pantalla rs">
      {cabecera}
      <div className="rs-contenido" ref={contenidoRef}>
        <div key={detalle ?? 'lista'} className="rs-vista">
          {detalle === null && (listaRS || lista)}
          {(detalle === 'verdor' || detalle === 'humedad') && (
            <>
              {consejoRS?.[detalle] && (
                <div className={`rs-consejo nivel-${detalle === 'verdor' ? 'atencion' : 'info'}`}>
                  {detalle === 'verdor' ? <Sprout size={20} /> : <Droplets size={20} />}
                  <div>
                    <strong>{consejoRS[detalle].titulo}</strong>
                    <span>{consejoRS[detalle].texto}</span>
                  </div>
                </div>
              )}
              <MapaSalud parcela={parcela} zonas={zonas} capa={detalle} />
            </>
          )}
          {detalle === 'lluvia' && vistaLluvia}
          {detalle === 'siembra' && (
            <RecomendacionesIA finca={finca} ubicacion={ubicacion} monitoreada={Boolean(rs)} />
          )}
        </div>
      </div>
    </div>
  )
}
