import { useMemo, useState } from 'react'
import PantallaLocalizando from './PantallaLocalizando.jsx'
import PantallaInformativa from './PantallaInformativa.jsx'
import IlustracionUbicar from './IlustracionUbicar.jsx'
import PantallaHectareas from './PantallaHectareas.jsx'
import PantallaUbicarParcela from './PantallaUbicarParcela.jsx'
import PantallaHome from './PantallaHome.jsx'
import PantallaResultados from '../resultados/PantallaResultados.jsx'
import PantallaAnalizando from '../reporte/PantallaAnalizando.jsx'
import CarruselInsights from '../reporte/CarruselInsights.jsx'
import PanelIndicador from '../reporte/PanelIndicador.jsx'
import PanelMapa from '../reporte/PanelMapa.jsx'
import { DefsReporte } from '../reporte/IlustracionesReporte.jsx'
import { detalleDe } from '../../lib/reporte.js'
import { formatoNumero } from './geo.js'
import '../onboarding/onboarding.css'
import '../mapa-movil/mapa-movil.css'
import '../reporte/reporte.css'
import './flujo-gps.css'

// El orden de los números decide hacia dónde se anima el cambio de pantalla
const PANTALLA = {
  LOCALIZANDO: 1, UBICACION_OK: 2, HECTAREAS: 3, HECTAREAS_OK: 4, INFO_UBICAR: 5, UBICAR_PARCELA: 6,
  ANALIZANDO: 7, CARRUSEL: 8, HOME: 9, PANEL: 10, MAPA: 11, RESULTADOS: 12,
}

// Flujo que sigue a "Estoy en mi finca":
// localizar → ✓ ubicación → hectáreas → ✓ superficie → "ahora ubica tu parcela" → mapa →
// analizando → resumen (carrusel) → inicio → panel de un dato / mapa / plan de siembra
// Las pantallas ✓ e informativas avanzan solas.
// Trabaja sobre una finca (`finca`); los cambios se guardan en App con `onCambiar`.
// Una finca con parcelas y sin reporte (recién dibujada a mano) empieza analizando;
// con reporte, en el inicio. Como el flujo se vuelve a montar al cambiar de finca,
// el resumen solo sale la primera vez.
export default function FlujoGps({
  nombre, finca, fincas, onCambiar, onElegirFinca, onNuevaFinca, onCancelar, onManual,
}) {
  const { ubicacion, parcelas, reporte } = finca
  const [pantalla, setPantalla] = useState(
    !parcelas.length ? PANTALLA.LOCALIZANDO : reporte ? PANTALLA.HOME : PANTALLA.ANALIZANDO,
  )
  const [direccion, setDireccion] = useState('adelante')
  const [hectareas, setHectareas] = useState(parcelas[0]?.area ?? null)
  // La finca puede tener varias parcelas; la primera es la que usan los análisis.
  const parcela = parcelas[0] ?? null
  const [agregando, setAgregando] = useState(false)
  const [haNueva, setHaNueva] = useState(null)
  const [modoAnalisis, setModoAnalisis] = useState('Rápido')
  // Dato que muestra el panel especializado (indicador o alerta del mes)
  const [indicadorId, setIndicadorId] = useState(null)
  // A dónde vuelven el mapa grande y el resumen
  const [origenMapa, setOrigenMapa] = useState(PANTALLA.HOME)
  const [resumenDesdeInicio, setResumenDesdeInicio] = useState(false)

  // `dir` fuerza la animación cuando el orden de los números no sirve
  const irA = (destino, dir) => {
    setDireccion(dir ?? (destino > pantalla ? 'adelante' : 'atras'))
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
      irA(reporte ? PANTALLA.HOME : PANTALLA.ANALIZANDO)
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

  const verMapa = (desde) => {
    setOrigenMapa(desde)
    irA(PANTALLA.MAPA)
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
      case PANTALLA.ANALIZANDO:
        return (
          <PantallaAnalizando
            finca={finca}
            onListo={(r) => {
              onCambiar({ reporte: r })
              setResumenDesdeInicio(false)
              irA(PANTALLA.CARRUSEL)
            }}
          />
        )
      case PANTALLA.CARRUSEL:
        if (!reporte) return null
        return (
          <CarruselInsights
            finca={finca}
            reporte={reporte}
            onSalir={() => irA(PANTALLA.HOME, resumenDesdeInicio ? 'atras' : 'adelante')}
          />
        )
      case PANTALLA.PANEL: {
        const detalle = detalleDe(reporte, indicadorId)
        if (!detalle) return null
        return (
          <PanelIndicador
            indicador={detalle}
            reporte={reporte}
            onVolver={() => irA(PANTALLA.HOME)}
            onVerMapa={() => verMapa(PANTALLA.PANEL)}
          />
        )
      }
      case PANTALLA.MAPA:
        if (!reporte) return null
        return (
          <PanelMapa
            finca={finca}
            reporte={reporte}
            capaInicial={origenMapa === PANTALLA.PANEL ? indicadorId : undefined}
            onVolver={() => irA(origenMapa)}
          />
        )
      case PANTALLA.RESULTADOS:
        return (
          <PantallaResultados
            ubicacion={ubicacion}
            parcela={parcela}
            modo={modoAnalisis}
            detalleInicial="siembra"
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
            reporte={reporte}
            onElegirFinca={onElegirFinca}
            onNuevaFinca={onNuevaFinca}
            onAgregarParcela={empezarNuevaParcela}
            onVerResumen={() => {
              setResumenDesdeInicio(true)
              irA(PANTALLA.CARRUSEL, 'adelante')
            }}
            onVerIndicador={(id) => {
              setIndicadorId(id)
              irA(PANTALLA.PANEL)
            }}
            onVerMapa={() => verMapa(PANTALLA.HOME)}
            onPlanSiembra={() => {
              setModoAnalisis('Profundo')
              irA(PANTALLA.RESULTADOS)
            }}
          />
        )
    }
  }

  return (
    <div className="marco onb">
      <div className="marco-tarjeta fg">
        <DefsReporte />
        <div key={pantalla} className={`fg-transicion onb-${direccion}`}>
          {contenido()}
        </div>
      </div>
    </div>
  )
}
