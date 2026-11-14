import { useMemo, useState } from 'react'
import PantallaLocalizando from './PantallaLocalizando.jsx'
import PantallaInformativa from './PantallaInformativa.jsx'
import IlustracionUbicar from './IlustracionUbicar.jsx'
import PantallaHectareas from './PantallaHectareas.jsx'
import PantallaUbicarParcela from './PantallaUbicarParcela.jsx'
import PantallaHome from './PantallaHome.jsx'
import PantallaResultados from '../resultados/PantallaResultados.jsx'
import { formatoNumero } from './geo.js'
import '../onboarding/onboarding.css'
import '../mapa-movil/mapa-movil.css'
import './flujo-gps.css'

const PANTALLA = {
  LOCALIZANDO: 1, UBICACION_OK: 2, HECTAREAS: 3, HECTAREAS_OK: 4, INFO_UBICAR: 5, UBICAR_PARCELA: 6, HOME: 7, RESULTADOS: 8,
}

// Flujo que sigue a "Estoy en mi finca":
// localizar → ✓ ubicación → hectáreas → ✓ superficie → "ahora ubica tu parcela" → mapa → home → resultados
// Las pantallas ✓ e informativas avanzan solas.
// Si la finca ya viene dibujada a mano (`parcelaInicial`), empieza en el inicio.
export default function FlujoGps({
  nombre, historial, ubicacionInicial = null, parcelaInicial = null, onEvento, onProceso, onCancelar, onManual,
}) {
  const [pantalla, setPantalla] = useState(parcelaInicial ? PANTALLA.HOME : PANTALLA.LOCALIZANDO)
  const [direccion, setDireccion] = useState('adelante')
  const [ubicacion, setUbicacion] = useState(ubicacionInicial)
  const [hectareas, setHectareas] = useState(parcelaInicial?.area ?? null)
  // La finca puede tener varias parcelas; la primera es la que usan los análisis.
  const [parcelas, setParcelas] = useState(parcelaInicial ? [parcelaInicial] : [])
  const parcela = parcelas[0] ?? null
  const [agregando, setAgregando] = useState(false)
  const [haNueva, setHaNueva] = useState(null)
  const [modoAnalisis, setModoAnalisis] = useState('Rápido')
  const [analisis, setAnalisis] = useState(null)

  const irA = (destino) => {
    setDireccion(destino > pantalla ? 'adelante' : 'atras')
    setPantalla(destino)
  }

  const alUbicar = (u) => {
    setUbicacion(u)
    onEvento('Ubicación', `Encontrada con GPS (±${Math.round(u.precision)} m)`)
    irA(PANTALLA.UBICACION_OK)
  }

  const alGuardarHectareas = (ha) => {
    setHectareas(ha)
    onEvento('Superficie', `${formatoNumero(ha)} ha declaradas`)
    irA(PANTALLA.HECTAREAS_OK)
  }

  // `otra`: el usuario eligió "Guardar y agregar otra parcela"
  const alAceptarParcela = ({ automatico, ...resultado }, { otra = false } = {}) => {
    const tamano = `${formatoNumero(resultado.area, 1)} ha`
    if (agregando) {
      setParcelas((prev) => [...prev, resultado])
      onEvento('Parcela', `Nueva parcela agregada: ${tamano}`)
    } else {
      setParcelas([resultado])
      onEvento('Parcela', automatico ? `Contorno ajustado al mapa: ${tamano}` : `Ubicada en el mapa: ${tamano}`)
    }
    if (otra) {
      setAgregando(true)
      setHaNueva(null)
      irA(PANTALLA.HECTAREAS)
    } else {
      setAgregando(false)
      irA(PANTALLA.HOME)
    }
  }

  // "Añadir parcela" desde el inicio: hectáreas → cuadro con ajuste automático
  const empezarNuevaParcela = () => {
    setAgregando(true)
    setHaNueva(null)
    irA(PANTALLA.HECTAREAS)
  }

  const cancelarNuevaParcela = () => {
    setAgregando(false)
    irA(PANTALLA.HOME)
  }

  const analizar = (modo) => {
    setModoAnalisis(modo)
    onProceso(modo, modo === 'Profundo' ? 'Plan de siembra para 4 años' : 'Revisión de tu finca y la lluvia')
    irA(PANTALLA.RESULTADOS)
  }

  const poligonosGuardados = useMemo(() => parcelas.map((p) => p.poligono), [parcelas])

  const contenido = () => {
    switch (pantalla) {
      case PANTALLA.LOCALIZANDO:
        return <PantallaLocalizando onUbicada={alUbicar} onCancelar={onCancelar} onManual={onManual} />
      case PANTALLA.UBICACION_OK:
        return (
          <PantallaInformativa
            titulo="¡Ubicación obtenida!"
            mensaje="Ya sabemos dónde está tu finca."
            onFin={() => irA(PANTALLA.HECTAREAS)}
          />
        )
      case PANTALLA.HECTAREAS:
        if (agregando) {
          return (
            <PantallaHectareas
              valorInicial={haNueva}
              titulo="¿Cuántas hectáreas tiene tu nueva parcela?"
              subtitulo="Después la pondrás en el mapa, al lado de las que ya tienes."
              onGuardar={(ha) => {
                setHaNueva(ha)
                irA(PANTALLA.UBICAR_PARCELA)
              }}
              onVolver={cancelarNuevaParcela}
            />
          )
        }
        return (
          <PantallaHectareas
            valorInicial={hectareas}
            onGuardar={alGuardarHectareas}
            onVolver={onCancelar}
          />
        )
      case PANTALLA.HECTAREAS_OK:
        return (
          <PantallaInformativa
            titulo="¡Superficie guardada!"
            mensaje={`Tu finca tiene ${formatoNumero(hectareas)} hectáreas.`}
            onFin={() => irA(PANTALLA.INFO_UBICAR)}
          />
        )
      case PANTALLA.INFO_UBICAR:
        return (
          <PantallaInformativa
            ilustracion={<IlustracionUbicar />}
            titulo="Ahora ubica tu parcela"
            mensaje="Mueve el cuadro hasta que quede encima de tu terreno."
            duracion={3400}
            onFin={() => irA(PANTALLA.UBICAR_PARCELA)}
          />
        )
      case PANTALLA.UBICAR_PARCELA:
        return (
          <PantallaUbicarParcela
            ubicacion={ubicacion}
            hectareas={agregando ? haNueva : hectareas}
            otrasParcelas={agregando ? poligonosGuardados : undefined}
            onAceptar={alAceptarParcela}
            onVolver={() => irA(PANTALLA.HECTAREAS)}
          />
        )
      case PANTALLA.RESULTADOS:
        return (
          <PantallaResultados
            ubicacion={ubicacion}
            parcela={parcela}
            modo={modoAnalisis}
            onVolver={() => irA(PANTALLA.HOME)}
            onProfundo={() => {
              setModoAnalisis('Profundo')
              onProceso('Profundo', 'Plan de siembra para 4 años')
            }}
            onAnalisis={setAnalisis}
          />
        )
      default:
        return (
          <PantallaHome
            nombre={nombre}
            ubicacion={ubicacion}
            parcelas={parcelas}
            historial={historial}
            analisis={analisis}
            onProceso={analizar}
            onAgregarParcela={empezarNuevaParcela}
            onVerResultados={() => (analisis ? irA(PANTALLA.RESULTADOS) : analizar('Rápido'))}
          />
        )
    }
  }

  return (
    <div className="marco onb">
      <div className="marco-tarjeta fg">
        <div key={pantalla} className={`fg-transicion onb-${direccion}`}>
          {contenido()}
        </div>
      </div>
    </div>
  )
}
