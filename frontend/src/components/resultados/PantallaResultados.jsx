import { useEffect, useMemo, useRef, useState } from 'react'
import {
  ArrowRight, Check, ChevronLeft, CloudOff, CloudRain, Droplets, FlaskConical, Layers, Leaf, LoaderCircle,
  RefreshCw, Satellite, Sparkles, Sun, Thermometer, WifiOff, Zap,
} from 'lucide-react'
import { PERIODO, obtenerDatosNasa } from '../../lib/nasa.js'
import {
  ESTADOS, MENSAJE_ESTADO, MENSAJE_SIMULADO, MESES_LARGOS, listaTexto, PREFERENCIAS_INICIALES, analizarFinca, compararRotaciones, formato,
} from './analisis.js'
import MapaSalud from './MapaSalud.jsx'
import { ICONO_ESTADO } from './iconos.js'
import GraficoLluvia from './GraficoLluvia.jsx'
import Rotaciones from './Rotaciones.jsx'
import './resultados.css'

const ICONOS_ACCION = { hoja: Leaf, gota: Droplets, lluvia: CloudRain, sol: Sun, rotar: Sparkles, profundo: Layers, nube: CloudOff }

const PASOS = {
  Rápido: ['Descargando 10 años de lluvia (NASA GPM)', 'Leyendo la humedad del suelo', 'Revisando el verdor de tu parcela', 'Preparando tus consejos'],
  Profundo: ['Descargando 10 años de lluvia (NASA GPM)', 'Leyendo la humedad del suelo', 'Revisando el verdor de tu parcela', 'Comparando rotaciones de cultivo', 'Preparando tus consejos'],
}
const DURACION_MIN = { Rápido: 2200, Profundo: 3200 }

const mayuscula = (t) => t.charAt(0).toUpperCase() + t.slice(1)

function Anillo({ valor, color, tam = 96, grosor = 10, children }) {
  const r = (tam - grosor) / 2
  const c = 2 * Math.PI * r
  return (
    <div className="rs-anillo" style={{ width: tam, height: tam }}>
      <svg viewBox={`0 0 ${tam} ${tam}`} aria-hidden="true">
        <circle cx={tam / 2} cy={tam / 2} r={r} fill="none" stroke="#e8ece9" strokeWidth={grosor} />
        <circle
          className="rs-anillo-valor"
          cx={tam / 2}
          cy={tam / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={grosor}
          strokeLinecap="round"
          strokeDasharray={c}
          style={{ '--vacio': c, strokeDashoffset: c * (1 - valor / 100) }}
          transform={`rotate(-90 ${tam / 2} ${tam / 2})`}
        />
      </svg>
      <div className="rs-anillo-centro">{children}</div>
    </div>
  )
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

export default function PantallaResultados({ ubicacion, parcela, modo, onVolver, onProfundo, onAnalisis }) {
  const [datos, setDatos] = useState(null)
  const [intento, setIntento] = useState(0)
  const [paso, setPaso] = useState(0)
  const [capa, setCapa] = useState('verdor')
  const [resaltar, setResaltar] = useState(false)
  const [prefs, setPrefs] = useState(PREFERENCIAS_INICIALES)
  const refs = { mapa: useRef(null), lluvia: useRef(null), rotacion: useRef(null) }
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

  // Al pasar de Rápido a Profundo, llevar al usuario a la nueva sección.
  const modoPrevio = useRef(modo)
  useEffect(() => {
    if (modoPrevio.current !== modo && profundo) {
      requestAnimationFrame(() => refs.rotacion.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
    }
    modoPrevio.current = modo
  })

  const reintentar = () => {
    setDatos(null)
    setPaso(0)
    setIntento((n) => n + 1)
  }

  const ir = (seccion) => refs[seccion].current?.scrollIntoView({ behavior: 'smooth', block: 'start' })

  const ejecutarAccion = (accion) => {
    if (accion.tipo === 'mapa') {
      setCapa(accion.capa)
      setResaltar(true)
      ir('mapa')
    } else if (accion.tipo === 'lluvia') ir('lluvia')
    else if (accion.tipo === 'rotacion') ir('rotacion')
    else if (accion.tipo === 'profundo') onProfundo()
    else if (accion.tipo === 'reintentar') reintentar()
  }

  const cabecera = (
    <header className="rs-cabecera">
      <button className="rs-volver" onClick={onVolver} aria-label="Volver al inicio">
        <ChevronLeft size={24} />
      </button>
      <div>
        <h1>Resultados</h1>
        <p>{datos ? `Analizado hoy, ${new Date().toLocaleDateString('es', { day: 'numeric', month: 'long' })}` : 'Procesando…'}</p>
      </div>
      <span className={`rs-modo ${profundo ? 'profundo' : ''}`}>
        {profundo ? <Layers size={14} /> : <Zap size={14} />} {modo}
      </span>
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

  const { estado, puntaje, zonas, lluvia, acciones, diagnosticoSimulado } = analisis
  const mensaje = diagnosticoSimulado ? MENSAJE_SIMULADO : MENSAJE_ESTADO[estado]
  const IconoEstado = diagnosticoSimulado ? FlaskConical : ICONO_ESTADO[estado]
  const mesAhora = lluvia.meses[analisis.mesActual]
  const { promedioMes } = lluvia
  const conDatos = (v, sufijo = '') => (v == null ? 'Sin datos' : `${v}${sufijo}`)
  const recomendado = comparacion.planes.find((p) => p.id === comparacion.recomendado)

  const todasAcciones = [
    ...acciones,
    profundo
      ? // Sin lluvia real no se da un consejo de siembra: la comparación queda abajo con su aviso.
        recomendado && !comparacion.ejemplo && {
          id: 'rotar',
          nivel: 'bien',
          icono: 'rotar',
          titulo: `Para la próxima siembra: ${recomendado.nombre.toLowerCase()}`,
          texto: 'Es la rotación que mejor se ajusta a tus respuestas y a la lluvia de tu zona.',
          accion: { tipo: 'rotacion', texto: 'Ver por qué' },
        }
      : {
          id: 'profundo',
          nivel: 'info',
          icono: 'profundo',
          titulo: '¿Qué sembrar después?',
          texto: 'El análisis profundo compara rotaciones de cultivo con la lluvia de tu zona.',
          accion: { tipo: 'profundo', texto: 'Hacer análisis profundo' },
        },
  ].filter(Boolean)

  return (
    <div className="fg-pantalla rs">
      {cabecera}
      <div className="rs-contenido" ref={contenidoRef}>
        {analisis.simulado && (
          <div className="rs-aviso">
            <WifiOff size={18} />
            <span>No pudimos conectar con la NASA. Mostramos datos de ejemplo.</span>
            <button onClick={reintentar}>
              <RefreshCw size={14} /> Reintentar
            </button>
          </div>
        )}

        {/* 1. Respuesta principal en una frase */}
        <section className={`rs-tarjeta rs-heroe fg-aparecer ${diagnosticoSimulado ? 'simulado' : ''}`}>
          <Anillo valor={puntaje} color={diagnosticoSimulado ? '#9ca3af' : ESTADOS[estado].color}>
            <strong>{puntaje}</strong>
            <small>{diagnosticoSimulado ? 'ejemplo' : 'de 100'}</small>
          </Anillo>
          <div className="rs-heroe-texto">
            {diagnosticoSimulado ? (
              <span className="rs-etiqueta-sim">
                <IconoEstado size={13} /> Simulación
              </span>
            ) : (
              <span className="rs-estado" style={{ '--c': ESTADOS[estado].color }}>
                <IconoEstado size={14} /> {ESTADOS[estado].nombre}
              </span>
            )}
            <h2>{mensaje.titulo}</h2>
            <p>{mensaje.texto}</p>
          </div>
          <div className="rs-heroe-datos">
            <button onClick={() => { setCapa('verdor'); ir('mapa') }}>
              <Leaf size={16} />
              <strong>{Math.round(zonas.verdor.normal)}%</strong>
              <span>plantas sanas</span>
              {zonas.simulado && <em className="rs-mini-sim">simulado</em>}
            </button>
            <button onClick={() => { setCapa('humedad'); ir('mapa') }}>
              <Droplets size={16} />
              <strong>{Math.round(zonas.humedad.normal)}%</strong>
              <span>suelo húmedo</span>
              {zonas.simulado && <em className="rs-mini-sim">simulado</em>}
            </button>
            <button onClick={() => ir('lluvia')}>
              <CloudRain size={16} />
              <strong>{conDatos(mesAhora.mediana, ' mm')}</strong>
              <span>lluvia normal en {MESES_LARGOS[analisis.mesActual].slice(0, 3)}</span>
              {analisis.simulado && <em className="rs-mini-sim">ejemplo</em>}
            </button>
          </div>
        </section>

        {/* 2. Qué hacer ahora */}
        <section className="fg-aparecer" style={{ '--retraso': '0.08s' }}>
          <h2 className="rs-titulo">Qué hacer ahora</h2>
          <ul className="rs-acciones">
            {todasAcciones.map((a) => {
              const Icono = ICONOS_ACCION[a.icono] ?? Leaf
              return (
                <li key={a.id} className={`rs-accion nivel-${a.nivel}`}>
                  <span className="rs-accion-icono"><Icono size={20} /></span>
                  <div>
                    <strong>{a.titulo}</strong>
                    <p>{a.texto}</p>
                    <button onClick={() => ejecutarAccion(a.accion)}>
                      {a.accion.texto} <ArrowRight size={15} />
                    </button>
                  </div>
                </li>
              )
            })}
          </ul>
        </section>

        {/* 3. Mapa de salud por zonas */}
        <section ref={refs.mapa} className="rs-seccion fg-aparecer" style={{ '--retraso': '0.16s' }}>
          <h2 className="rs-titulo">Tu parcela por zonas</h2>
          <MapaSalud
            parcela={parcela}
            zonas={zonas}
            capa={capa}
            onCapa={(c) => { setCapa(c); setResaltar(false) }}
            resaltar={resaltar}
          />
        </section>

        {/* 4. Lluvia de la zona (NASA GPM IMERG) */}
        <section ref={refs.lluvia} className="rs-seccion fg-aparecer" style={{ '--retraso': '0.24s' }}>
          <h2 className="rs-titulo">Lluvia en tu zona</h2>
          <div className="rs-tarjeta">
            <div className="rs-cifras">
              <div><span>Al año</span><strong>{lluvia.anual == null ? 'Sin datos' : `${formato(lluvia.anual, 0)} mm`}</strong></div>
              <div><span>Más lluvioso</span><strong>{lluvia.masLluvioso ? mayuscula(MESES_LARGOS[lluvia.masLluvioso.mes]) : 'Sin datos'}</strong></div>
              <div><span>Más seco</span><strong>{lluvia.masSeco ? mayuscula(MESES_LARGOS[lluvia.masSeco.mes]) : 'Sin datos'}</strong></div>
            </div>
            <GraficoLluvia lluvia={lluvia} mesActual={analisis.mesActual} />
            <p className="rs-nota">
              {analisis.simulado && <><strong>Datos de ejemplo, no de tu zona.</strong> </>}
              {mesAhora.mediana != null && promedioMes != null &&
                (mesAhora.mediana >= promedioMes
                  ? 'Estás en temporada de lluvias. '
                  : mesAhora.mediana < promedioMes * 0.6
                    ? 'Estás en meses de poca lluvia. '
                    : 'Este mes suele llover de forma moderada. ')}
              {lluvia.temporadaSeca && <>La época seca suele ir de <strong>{lluvia.temporadaSeca}</strong>. </>}
              {lluvia.mesesSinDatos.length > 0 && (
                <>Sin datos suficientes para {listaTexto(lluvia.mesesSinDatos.map((m) => MESES_LARGOS[m]))}. </>
              )}
              {analisis.temperatura != null && (
                <><Thermometer size={13} className="rs-en-linea" /> Temperatura media este mes: {formato(analisis.temperatura)} °C.</>
              )}
            </p>
          </div>
        </section>

        {/* 5. Rotaciones (análisis profundo) */}
        <section ref={refs.rotacion} className="rs-seccion">
          <h2 className="rs-titulo">¿Qué sembrar en los próximos 4 años?</h2>
          {profundo ? (
            <div className="rs-rotacion fg-aparecer">
              <Rotaciones comparacion={comparacion} prefs={prefs} onPrefs={setPrefs} />
            </div>
          ) : (
            <div className="rs-tarjeta rs-bloqueado">
              <Layers size={26} />
              <p>Comparamos 3 formas de rotar cultivos con la lluvia de tus últimos 10 años y te decimos cuál cuida mejor tu suelo.</p>
              <button className="onb-btn onb-btn-primario" onClick={onProfundo}>
                Hacer análisis profundo <ArrowRight size={18} />
              </button>
            </div>
          )}
        </section>

        {/* 6. De dónde salen los datos */}
        <section className="rs-seccion">
          <h2 className="rs-titulo">¿De dónde salen estos datos?</h2>
          <ul className="rs-tarjeta rs-fuentes">
            <li>
              <CloudRain size={18} />
              <div>
                <strong>Lluvia · NASA GPM IMERG</strong>
                <span>Satélites miden la lluvia diaria, {PERIODO.inicio}–{PERIODO.fin}. Cada dato cubre un cuadro de unos 10 km.</span>
              </div>
              <em className={analisis.simulado ? 'demo' : 'real'}>{analisis.simulado ? 'Ejemplo' : 'Dato real'}</em>
            </li>
            <li>
              <Thermometer size={18} />
              <div>
                <strong>Temperatura · NASA POWER</strong>
                <span>Modelo MERRA-2 de la NASA, cuadros de unos 50 km. Sirve para ver la tendencia de la zona.</span>
              </div>
              <em className={analisis.simulado ? 'demo' : 'real'}>{analisis.simulado ? 'Ejemplo' : 'Dato real'}</em>
            </li>
            <li>
              <Leaf size={18} />
              <div>
                <strong>Verdor y humedad por zonas</strong>
                <span>
                  Simulado: un patrón inventado en cuadros de {zonas.tamCelda} m para mostrar cómo se verá. El puntaje general sale
                  de aquí. Cuando conectemos imágenes Landsat / Sentinel-2 será un dato real.
                </span>
              </div>
              <em className="demo">Simulado</em>
            </li>
          </ul>
          <p className="rs-nota">
            El satélite ve un área grande alrededor de tu finca. En montaña puede marcar más o menos lluvia de la que cae en tu
            terreno: si tienes un pluviómetro, compara.
          </p>
        </section>
      </div>
    </div>
  )
}
