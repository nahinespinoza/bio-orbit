import { useEffect, useMemo, useRef, useState } from 'react'
import {
  Check, ChevronLeft, CloudRain, Droplets, Layers, LoaderCircle, RefreshCw, Satellite, Sprout, Wheat, WifiOff, Zap,
} from 'lucide-react'
import { PERIODO, obtenerDatosNasa } from '../../lib/nasa.js'
import { MESES_LARGOS, PREFERENCIAS_INICIALES, analizarFinca, compararRotaciones, formato } from './analisis.js'
import MapaSalud from './MapaSalud.jsx'
import GraficoLluvia from './GraficoLluvia.jsx'
import Rotaciones from './Rotaciones.jsx'
import Widget from '../ui/Widget.jsx'
import FilaAnalisis from '../ui/FilaAnalisis.jsx'
import { IlustracionClima } from '../ui/Ilustraciones.jsx'
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
  siembra: 'Plan de siembra',
}

const mayuscula = (t) => t.charAt(0).toUpperCase() + t.slice(1)

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

// `detalleInicial` (opcional): abre directo en un detalle; volver desde ahí regresa a `onVolver`.
export default function PantallaResultados({ ubicacion, parcela, modo, detalleInicial = null, onVolver, onProfundo, onAnalisis }) {
  const [datos, setDatos] = useState(null)
  const [intento, setIntento] = useState(0)
  const [paso, setPaso] = useState(0)
  const [detalle, setDetalle] = useState(detalleInicial) // null = lista | verdor | humedad | lluvia | siembra
  const [prefs, setPrefs] = useState(PREFERENCIAS_INICIALES)
  const contenidoRef = useRef(null)
  const profundo = modo === 'Profundo'

  // Descarga de datos NASA con una duración mínima para que el usuario vea el progreso.
  useEffect(() => {
    const control = new AbortController()
    const minimo = DURACION_MIN[modo]
    const inicio = performance.now()
    obtenerDatosNasa(ubicacion, control.signal)
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
    () => (datos ? analizarFinca({ datos, parcela, ubicacion }) : null),
    [datos, parcela, ubicacion],
  )
  const comparacion = useMemo(
    () => (analisis ? compararRotaciones(analisis.lluvia, prefs) : null),
    [analisis, prefs],
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

  // Desde el detalle con que se abrió, volver regresa a quien abrió la pantalla
  const aLista = detalle !== null && detalle !== detalleInicial
  const cabecera = (
    <header className="rs-cabecera">
      <button
        className="rs-volver"
        onClick={aLista ? () => setDetalle(null) : onVolver}
        aria-label={aLista ? 'Volver a resultados' : 'Volver al inicio'}
      >
        <ChevronLeft size={24} />
      </button>
      <h1>{detalle ? TITULOS[detalle] : 'Resultados'}</h1>
      {!detalle && (
        <span className={`rs-modo ${profundo ? 'profundo' : ''}`}>
          {profundo ? <Layers size={14} /> : <Zap size={14} />} {modo}
        </span>
      )}
    </header>
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
  const recomendado = comparacion.planes.find((p) => p.id === comparacion.recomendado)

  const textoSiembra = !profundo
    ? 'Descubre qué sembrar en los próximos 4 años'
    : comparacion.ejemplo
      ? 'Calculado con lluvia de ejemplo: reintenta con conexión'
      : `Te recomendamos: ${recomendado.nombre.toLowerCase()}`

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
          <li>
            <FilaAnalisis
              tono="verde"
              Icono={Wheat}
              titulo="Plan de siembra"
              texto={textoSiembra}
              nota={profundo ? 'Próximos 4 años' : 'Análisis profundo'}
              onClick={() => {
                if (!profundo) onProfundo()
                setDetalle('siembra')
              }}
            />
          </li>
        </ul>
      </section>

      <p className="rs-fuentes-linea">
        <Satellite size={14} /> Datos de la NASA: GPM IMERG y POWER
      </p>
    </>
  )

  const vistaLluvia = (
    <>
      {consejoLluvia && consejoLluvia.id !== 'sin-datos' && (
        <div className={`rs-consejo nivel-${consejoLluvia.nivel}`}>
          <CloudRain size={20} />
          <div>
            <strong>{consejoLluvia.titulo}</strong>
            <span>{consejoLluvia.texto}</span>
          </div>
        </div>
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
          {detalle === null && lista}
          {(detalle === 'verdor' || detalle === 'humedad') && (
            <MapaSalud parcela={parcela} zonas={zonas} capa={detalle} />
          )}
          {detalle === 'lluvia' && vistaLluvia}
          {detalle === 'siembra' && profundo && (
            <div className="rs-rotacion">
              <Rotaciones comparacion={comparacion} prefs={prefs} onPrefs={setPrefs} />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
