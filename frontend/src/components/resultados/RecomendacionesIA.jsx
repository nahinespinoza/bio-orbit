import { useEffect, useId, useRef, useState } from 'react'
import {
  ArrowRight, Bean, BookOpen, Bug, Check, ChevronDown, ChevronRight, Coins, Hand,
  Info, Leaf, LoaderCircle, MapPin, RefreshCw, SlidersHorizontal, Sparkles, Sprout,
  Timer, TriangleAlert, Wheat,
} from 'lucide-react'
import {
  CONFIANZA, ENCHARCAMIENTOS, PRIORIDADES, RIEGOS, agruparDescartes, alertasDeParcela,
  obtenerCultivos, recomendarCultivos, referenciasDe,
} from '../../lib/pitagoras.js'
import './recomendaciones-ia.css'

const ICONOS_PRIORIDAD = { market_value: Coins, speed: Timer, fewer_pests: Bug, low_labor: Hand }
const ICONOS_CRITERIO = { risk: MapPin, aptitude: Sprout }
const PESTAÑAS = [['rotacion', 'Rotación'], ['motivos', 'Por qué'], ['alternativas', 'Alternativas']]
const TITULOS_ALERTA = { ALTO: 'Riesgo alto en tu parcela', MEDIO: 'Riesgo medio en tu parcela' }
const CLASE_CONFIANZA = { alta: 'high', media: 'medium', baja: 'low' }
const PORCENTAJE = (n) => Math.round(n * 100)

function IconoCultivo({ cultivo, size = 28 }) {
  const Icono = ['haba', 'chocho', 'arveja', 'lenteja'].includes(cultivo) ? Bean
    : ['cebada', 'trigo', 'avena', 'maiz', 'quinua', 'qaniwa'].includes(cultivo) ? Wheat
      : ['pasto', 'barbecho', 'abono'].includes(cultivo) ? Leaf : Sprout
  return <Icono size={size} strokeWidth={1.5} aria-hidden="true" />
}

export function AccesoPitagoras({ onClick }) {
  return (
    <button className="pg-acceso" type="button" onClick={onClick}>
      <span className="pg-acceso-icono"><Sprout size={25} strokeWidth={1.7} aria-hidden="true" /></span>
      <span className="pg-acceso-texto">
        <strong>Próximos sembríos</strong>
        <small>Elige qué sembrar en tu próximo ciclo.</small>
      </span>
      <ChevronRight size={21} aria-hidden="true" />
    </button>
  )
}

function Aviso({ children, error = false }) {
  return (
    <div className={`pg-aviso ${error ? 'pg-error' : ''}`} role={error ? 'alert' : undefined}>
      {error ? <TriangleAlert size={18} aria-hidden="true" /> : <Info size={18} aria-hidden="true" />}
      <div>{children}</div>
    </div>
  )
}

function Explicacion({ titulo, Icono = Info, children, aviso = false }) {
  return (
    <details className={`pg-explicacion ${aviso ? 'pg-explicacion-aviso' : ''}`}>
      <summary>
        <span className="pg-motivo-icono"><Icono size={20} aria-hidden="true" /></span>
        <span className="pg-explicacion-titulo">{titulo}</span>
        <ChevronDown size={17} aria-hidden="true" />
      </summary>
      <div className="pg-explicacion-contenido">{children}</div>
    </details>
  )
}

function Motivos({ cultivo, resultado }) {
  return (
    <div className="pg-motivos">
      {cultivo.priority_missing && <Aviso>Faltan datos de tu prioridad para este cultivo. Se usó un valor bajo en la comparación.</Aviso>}
      {(cultivo.why ?? []).map((motivo) => {
        const Icono = motivo.criterion === 'priority' ? ICONOS_PRIORIDAD[resultado.priority?.id] ?? Leaf : ICONOS_CRITERIO[motivo.criterion] ?? Leaf
        const referencias = referenciasDe(resultado, motivo.references)
        return (
          <Explicacion key={motivo.criterion} Icono={Icono} titulo={`${motivo.title} · ${motivo.score}/100`}>
            <p>{motivo.detail}</p>
            {motivo.data && motivo.data !== motivo.detail && <small>Dato de la ficha: {motivo.data}</small>}
            {referencias.length > 0 && <small>Fuentes: {referencias.map((r, i) => (
              <span key={r.id}>{i > 0 && ', '}{r.url ? <a href={r.url} target="_blank" rel="noreferrer">{r.title}</a> : r.title}</span>
            ))}</small>}
          </Explicacion>
        )
      })}
    </div>
  )
}

function Rotacion({ cultivo }) {
  const secuencia = cultivo.rotation ?? []
  if (!secuencia.length) return <Aviso>No hay una secuencia de rotación disponible para este cultivo.</Aviso>
  return (
    <div className="pg-rotacion">
      <h3>{secuencia.length} {secuencia.length === 1 ? 'ciclo disponible' : 'ciclos disponibles'}</h3>
      <ol className="pg-linea-tiempo">
        {secuencia.map((paso) => (
          <li key={paso.cycle}>
            <span className="pg-paso-numero">{paso.cycle}</span>
            <div><small>{paso.cycle === 1 ? 'Tu próxima siembra' : `Después · Ciclo ${paso.cycle}`}</small><strong>{paso.name}</strong>
              <span>Confianza {CONFIANZA[paso.confidence]?.toLowerCase() ?? 'sin evaluar'}</span>
            </div>
            <IconoCultivo cultivo={paso.crop} size={26} />
          </li>
        ))}
      </ol>
      <Explicacion titulo="Cómo leer esta rotación">
        <p>Cada paso es un ciclo de cultivo, no un año calendario. Sigue la secuencia para ver qué sembrar después.</p>
      </Explicacion>
    </div>
  )
}

function Alternativas({ resultado, elegido, onElegir }) {
  const opciones = [resultado.recommendation, ...(resultado.alternatives ?? [])]
  return (
    <div className="pg-alternativas">
      <h3>Compara antes de decidir</h3>
      {opciones.map((cultivo, i) => (
        <button type="button" className={`pg-alternativa ${elegido === cultivo.crop ? 'elegida' : ''}`} key={cultivo.crop} onClick={() => onElegir(cultivo.crop)} aria-pressed={elegido === cultivo.crop}>
          <span className="pg-cultivo-mini"><IconoCultivo cultivo={cultivo.crop} /></span>
          <span className="pg-alternativa-nombre"><strong>{cultivo.name}</strong><small>{i === 0 ? 'Primera opción' : 'Alternativa'} · Confianza {CONFIANZA[cultivo.confidence]?.toLowerCase()}</small></span>
          <span className="pg-alternativa-puntaje">{cultivo.affinity}<small>/100</small></span>
          {elegido === cultivo.crop ? <Check size={18} aria-hidden="true" /> : <ChevronRight size={18} aria-hidden="true" />}
        </button>
      ))}
      <Explicacion titulo="Cómo comparar las opciones">
        <p>Toca un cultivo para abrir su rotación.</p>
        <p>{resultado.how_to_compare || 'El puntaje compara las opciones según tus datos.'} No representa la probabilidad de una buena cosecha.</p>
      </Explicacion>
    </div>
  )
}

function Descartados({ descartados, cultivos }) {
  const grupos = agruparDescartes(descartados, cultivos)
  return <ul>{grupos.map(({ motivo, nombres }) => <li key={motivo}><strong>{nombres.join(', ')}:</strong> {motivo}</li>)}</ul>
}

function Fuentes({ resultado, cultivos, monitoreada }) {
  const pesos = resultado.weights
  return (
    <details className="pg-fuentes">
      <summary><BookOpen size={17} aria-hidden="true" /> Fuentes y datos por completar <ChevronDown size={17} aria-hidden="true" /></summary>
      <div className="pg-fuentes-contenido">
        {pesos && <p>Comparación: {PORCENTAJE(pesos.priority)} % tu prioridad, {PORCENTAJE(pesos.risk)} % condiciones de tu parcela y {PORCENTAJE(pesos.aptitude)} % tu rotación.</p>}
        <p>Orientación para tu técnico; sin garantía de rendimiento ni ingresos.</p>
        {monitoreada && resultado.data_date && <p>Datos de monitoreo: {resultado.data_date}. Verifica las condiciones actuales.</p>}
        {(resultado.missing_data ?? []).length > 0 && <p>Faltan datos de la ficha para: {resultado.missing_data.join('; ')}.</p>}
        {resultado.flags?.evidence_trimmed && <p>Se resumió parte de la evidencia para esta consulta.</p>}
        {(resultado.sources ?? []).length > 0 && <><h4>Fuentes consultadas</h4>
          <ul>{resultado.sources.map((f) => <li key={f.id}>{f.url ? <a href={f.url} target="_blank" rel="noreferrer">{f.title}</a> : f.title}</li>)}</ul></>}
        {(resultado.discarded ?? []).length > 0 && <><h4>Opciones descartadas</h4><Descartados descartados={resultado.discarded} cultivos={cultivos} /></>}
      </div>
    </details>
  )
}

export default function RecomendacionesIA({ finca, monitoreada = false }) {
  const [formulario, setFormulario] = useState(() => ({
    cultivo: /papa/i.test(finca?.nombre ?? '') ? 'papa' : '',
    prioridad: 'market_value', riego: '', drenaje: '',
  }))
  const [catalogo, setCatalogo] = useState({ estado: 'cargando', cultivos: [], error: '' })
  const [intento, setIntento] = useState(0)
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState('')
  const [resultado, setResultado] = useState(null)
  const [editando, setEditando] = useState(true)
  const [elegido, setElegido] = useState(null)
  const [pestaña, setPestaña] = useState('rotacion')
  const peticion = useRef(null)
  const raiz = useRef(null)
  const focoPrincipal = useRef(null)
  const id = useId()

  useEffect(() => {
    const control = new AbortController()
    obtenerCultivos(control.signal)
      .then((cultivos) => { if (!control.signal.aborted) setCatalogo({ estado: 'listo', cultivos, error: '' }) })
      .catch((e) => { if (!control.signal.aborted) setCatalogo({ estado: 'error', cultivos: [], error: e.message }) })
    return () => control.abort()
  }, [intento])

  useEffect(() => () => peticion.current?.abort(), [])

  useEffect(() => {
    if (resultado || !editando) {
      raiz.current?.closest('.rs-contenido')?.scrollTo({ top: 0, behavior: 'instant' })
      focoPrincipal.current?.focus({ preventScroll: true })
    }
  }, [resultado, editando])

  const cambiar = (campo, valor) => setFormulario((anterior) => ({ ...anterior, [campo]: valor }))
  const elegirAlternativa = (cultivo) => {
    setElegido(cultivo)
    setPestaña('rotacion')
    document.getElementById(`${id}-rotacion`)?.focus()
  }
  const generar = async (event) => {
    event.preventDefault()
    peticion.current?.abort()
    const control = new AbortController()
    peticion.current = control
    setCargando(true)
    setError('')
    setResultado(null)
    try {
      const nuevo = await recomendarCultivos(formulario, control.signal)
      if (control.signal.aborted) return
      setResultado(nuevo)
      setElegido(nuevo.recommendation?.crop ?? null)
      setPestaña('rotacion')
      setEditando(false)
    } catch (e) {
      if (!control.signal.aborted) setError(e.message)
    } finally {
      if (!control.signal.aborted) setCargando(false)
    }
  }

  const cultivo = resultado?.status === 'ok'
    ? [resultado.recommendation, ...(resultado.alternatives ?? [])].find((c) => c.crop === elegido) ?? resultado.recommendation
    : null
  const alertas = cultivo ? alertasDeParcela(cultivo, monitoreada) : []

  return (
    <section className="pg" ref={raiz} aria-label="Recomendaciones de Pitágoras">
      {editando ? (
        <>
          <form onSubmit={generar} className="pg-formulario" aria-busy={cargando}>
            <fieldset disabled={cargando} className="pg-campos">
              <legend className="pg-solo-lectores">Datos para tu recomendación</legend>
              <label className="pg-campo" htmlFor={`${id}-cultivo`}>¿Qué cultivaste por última vez?
                <select ref={focoPrincipal} name="cultivo" id={`${id}-cultivo`} value={formulario.cultivo} onChange={(e) => cambiar('cultivo', e.target.value)} required disabled={catalogo.estado !== 'listo'}>
                  <option value="">{catalogo.estado === 'cargando' ? 'Cargando cultivos…' : 'Elige un cultivo'}</option>
                  {catalogo.cultivos.map((c) => <option value={c.crop_id} key={c.crop_id}>{c.name}</option>)}
                  <option value="new_land">Es tierra nueva, aún no he sembrado</option>
                </select>
              </label>
              {catalogo.estado === 'error' && <Aviso error><p>{catalogo.error}</p><button className="pg-enlace" type="button" onClick={() => { setCatalogo({ estado: 'cargando', cultivos: [], error: '' }); setIntento((n) => n + 1) }}><RefreshCw size={15} /> Volver a cargar cultivos</button></Aviso>}

              <fieldset className="pg-prioridades"><legend>¿Qué quieres priorizar?</legend><div className="pg-prioridades-grid">
                {PRIORIDADES.map((p) => { const Icono = ICONOS_PRIORIDAD[p.id]; return (
                  <label className={`pg-prioridad ${formulario.prioridad === p.id ? 'activa' : ''}`} key={p.id}>
                    <input type="radio" name={`${id}-prioridad`} value={p.id} checked={formulario.prioridad === p.id} onChange={() => cambiar('prioridad', p.id)} />
                    <Icono size={22} aria-hidden="true" /><strong>{p.nombre}</strong><span>{p.detalle}</span>
                  </label>
                ) })}
              </div></fieldset>

              <div className="pg-dos-campos">
                <label className="pg-campo" htmlFor={`${id}-riego`}>¿Cómo riegas?<select name="riego" id={`${id}-riego`} value={formulario.riego} onChange={(e) => cambiar('riego', e.target.value)} required>
                  <option value="">Elige una opción</option>
                  {RIEGOS.map((r) => <option value={r.id} key={r.id}>{r.nombre}</option>)}
                </select></label>
                <label className="pg-campo" htmlFor={`${id}-drenaje`}>¿Se empoza el agua?<select name="drenaje" id={`${id}-drenaje`} value={formulario.drenaje} onChange={(e) => cambiar('drenaje', e.target.value)} required>
                  <option value="">Elige una opción</option>
                  {ENCHARCAMIENTOS.map((r) => <option value={r.id} key={r.id}>{r.nombre}</option>)}
                </select></label>
              </div>
            </fieldset>
            {error && <Aviso error><p>{error}</p></Aviso>}
            <button className="pg-boton-principal" type="submit" disabled={cargando || catalogo.estado !== 'listo'}>{cargando ? <><LoaderCircle size={20} className="pg-girando" /> Comparando cultivos…</> : <><Sparkles size={19} /> Ver mi recomendación <ArrowRight size={19} /></>}</button>
            <p className="pg-nota pg-centrado" role="status">{cargando ? 'Revisando tus prioridades y las reglas de rotación.' : 'Tus respuestas hacen la recomendación más útil.'}</p>
            {resultado && <button className="pg-enlace pg-cancelar" type="button" onClick={() => setEditando(false)}>Volver al resultado anterior</button>}
          </form>
        </>
      ) : resultado?.status === 'no_candidates' ? (
        <div className="pg-vacio"><span className="pg-vacio-icono"><Sprout size={40} /></span><h2 ref={focoPrincipal} tabIndex={-1}>Revisemos tus opciones</h2><p>Ningún cultivo cumple todas las condiciones que indicaste. Revisa tus datos antes de elegir qué sembrar.</p>
          <details className="pg-fuentes"><summary>Ver por qué se descartaron <ChevronDown size={17} aria-hidden="true" /></summary><Descartados descartados={resultado.discarded} cultivos={catalogo.cultivos} /></details>
          <button type="button" className="pg-boton-principal" onClick={() => setEditando(true)}><SlidersHorizontal size={18} /> Revisar mis datos</button>
        </div>
      ) : cultivo ? (
        <>
          <div className="pg-resultado-acciones"><button type="button" className="pg-ajustar" onClick={() => setEditando(true)}><SlidersHorizontal size={16} /> Ajustar datos</button></div>

          <article className="pg-recomendacion">
            <div className="pg-recomendacion-etiqueta"><Sparkles size={15} /> {cultivo.crop === resultado.recommendation.crop ? 'Primera opción para ti' : 'Explorando una alternativa'}</div>
            <div className="pg-cultivo-principal"><div><h2 ref={focoPrincipal} tabIndex={-1}>{cultivo.name}</h2><p>Para tu próximo ciclo de cultivo</p></div><span className="pg-cultivo-ilustracion"><IconoCultivo cultivo={cultivo.crop} size={54} /></span></div>
            {cultivo.summary && <p className="pg-resumen">{cultivo.summary}</p>}
            <div className="pg-puntaje"><span>Afinidad con tus prioridades</span><strong>{cultivo.affinity}<small> / 100</small></strong></div>
            <div className="pg-puntaje-barra" aria-hidden="true"><span style={{ width: `${Math.min(100, Math.max(0, cultivo.affinity))}%` }} /></div>
            <div className="pg-confianza"><span><span className={`pg-confianza-punto ${CLASE_CONFIANZA[cultivo.confidence] ?? ''}`} /> Confianza {CONFIANZA[cultivo.confidence]?.toLowerCase()}</span><span>Según los datos disponibles</span></div>
          </article>

          <div className="pg-detalle">
            <div className="pg-pestañas" role="tablist" aria-label="Explora la recomendación">
              {PESTAÑAS.map(([valor, etiqueta], indice) => <button type="button" role="tab" id={`${id}-${valor}`} aria-controls={`${id}-panel`} aria-selected={pestaña === valor} tabIndex={pestaña === valor ? 0 : -1} key={valor} onClick={() => setPestaña(valor)} onKeyDown={(e) => {
                const siguiente = e.key === 'ArrowRight' ? (indice + 1) % PESTAÑAS.length : e.key === 'ArrowLeft' ? (indice + PESTAÑAS.length - 1) % PESTAÑAS.length : e.key === 'Home' ? 0 : e.key === 'End' ? PESTAÑAS.length - 1 : null
                if (siguiente !== null) { e.preventDefault(); setPestaña(PESTAÑAS[siguiente][0]); document.getElementById(`${id}-${PESTAÑAS[siguiente][0]}`)?.focus() }
              }}>{etiqueta}</button>)}
            </div>
            <div className="pg-panel" role="tabpanel" id={`${id}-panel`} aria-labelledby={`${id}-${pestaña}`} tabIndex={0}>
              {pestaña === 'rotacion' && <Rotacion key={cultivo.crop} cultivo={cultivo} />}
              {pestaña === 'motivos' && <Motivos key={cultivo.crop} cultivo={cultivo} resultado={resultado} />}
              {pestaña === 'alternativas' && <Alternativas resultado={resultado} elegido={cultivo.crop} onElegir={elegirAlternativa} />}
            </div>
          </div>

          {alertas.map((alerta) => (
            <Explicacion key={`${cultivo.crop}-${alerta.message}`} titulo={TITULOS_ALERTA[alerta.level] ?? 'Antes de sembrar'} Icono={TriangleAlert} aviso>
              <p>{alerta.message}</p>
            </Explicacion>
          ))}
          <Fuentes resultado={resultado} cultivos={catalogo.cultivos} monitoreada={monitoreada} />
        </>
      ) : null}
    </section>
  )
}
