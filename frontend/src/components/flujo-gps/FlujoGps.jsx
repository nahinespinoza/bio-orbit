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
// Trabaja sobre una finca (`finca`); los cambios se guardan en App con `onCambiar`.
// Si la finca ya tiene parcelas (registrada antes o dibujada a mano), empieza en el inicio.
export default function FlujoGps({
  nombre, finca, fincas, onCambiar, onElegirFinca, onNuevaFinca, onCancelar, onManual,
}) {
  const { ubicacion, parcelas, analisis } = finca
  const [pantalla, setPantalla] = useState(parcelas.length ? PANTALLA.HOME : PANTALLA.LOCALIZANDO)
  const [direccion, setDireccion] = useState('adelante')
  const [hectareas, setHectareas] = useState(parcelas[0]?.area ?? null)
  // La finca puede tener varias parcelas; la primera es la que usan los análisis.
  const parcela = parcelas[0] ?? null
  const [agregando, setAgregando] = useState(false)
  const [haNueva, setHaNueva] = useState(null)
  const [modoAnalisis, setModoAnalisis] = useState('Rápido')

  const irA = (destino) => {
    setDireccion(destino > pantalla ? 'adelante' : 'atras')
    setPantalla(destino)
  }

  const alUbicar = (u) => {
    onCambiar({ ubicacion: u })
    irA(PANTALLA.UBICACION_OK)
  }

  const alGuardarHectareas = (ha) => {
    setHectareas(ha)
    irA(PANTALLA.HECTAREAS_OK)
  }

  // `otra`: el usuario eligió "Guardar y agregar otra parcela"
  // (`automatico` solo indica si se ajustó a los bordes; no se guarda en la parcela)
  const alAceptarParcela = ({ automatico: _automatico, ...resultado }, { otra = false } = {}) => {
    onCambiar((f) => ({ parcelas: agregando ? [...f.parcelas, resultado] : [resultado] }))
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
            onProfundo={() => setModoAnalisis('Profundo')}
            onAnalisis={(a) => onCambiar({ analisis: a })}
          />
        )
      default:
        return (
          <PantallaHome
            nombre={nombre}
            finca={finca}
            fincas={fincas}
            onElegirFinca={onElegirFinca}
            onNuevaFinca={onNuevaFinca}
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
