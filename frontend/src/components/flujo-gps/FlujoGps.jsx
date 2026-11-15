import { useMemo, useState } from 'react'
import PantallaLocalizando from './PantallaLocalizando.jsx'
import PantallaInformativa from './PantallaInformativa.jsx'
import IlustracionUbicar from './IlustracionUbicar.jsx'
import PantallaHectareas from './PantallaHectareas.jsx'
import PantallaUbicarParcela from './PantallaUbicarParcela.jsx'
import PantallaHome from './PantallaHome.jsx'
import PantallaNombreParcela from './PantallaNombreParcela.jsx'
import PantallaResultados from '../resultados/PantallaResultados.jsx'
import PantallaAnalizando from '../reporte/PantallaAnalizando.jsx'
import CarruselInsights from '../reporte/CarruselInsights.jsx'
import { DefsReporte } from '../reporte/IlustracionesReporte.jsx'
import { reporteEjemplo, reporteToacaso } from '../../lib/reporteFincas.js'
import { UBICACION_DEMO } from '../../lib/ubicacionDemo.js'
import { centroide, formatoNumero } from './geo.js'
import '../onboarding/onboarding.css'
import '../mapa-movil/mapa-movil.css'
import './flujo-gps.css'
import '../reporte/reporte.css'

const PANTALLA = {
  LOCALIZANDO: 1, UBICACION_OK: 2, HECTAREAS: 3, HECTAREAS_OK: 4, INFO_UBICAR: 5, UBICAR_PARCELA: 6, HOME: 7, RESULTADOS: 8,
  // Editar una finca: por cada parcela, animación → cuadro sobre la parcela; al final, ✓
  EDITAR_INFO: 9, EDITAR_PARCELA: 10, EDITAR_OK: 11,
  // Ruta "/": al registrar la primera parcela, "Analizando…" → resumen de la semana → inicio
  ANALIZANDO: 12, RESUMEN_INICIAL: 13,
  // "Añadir parcela": nombre de la tarjeta → hectáreas → ubicar
  NOMBRE_PARCELA: 14,
}

// Flujo que sigue a "Estoy en mi finca":
// localizar → ✓ ubicación → hectáreas → ✓ superficie → "ahora ubica tu parcela" → mapa → home → resultados
// Las pantallas ✓ e informativas avanzan solas.
// Si la finca ya viene dibujada a mano (`parcelaInicial`), empieza en el inicio
// (en "/" pasa antes por "Analizando…" y el resumen de la semana).
export default function FlujoGps({
  nombre, ubicacionInicial = null, parcelaInicial = null, fincasExtra, remoteSensingPrincipal, onCancelar, onManual,
}) {
  // En "/" (sin `fincasExtra`) el resumen de la semana se muestra una vez, antes del primer inicio
  const conResumenInicial = !fincasExtra
  const [pantalla, setPantalla] = useState(
    parcelaInicial ? (conResumenInicial ? PANTALLA.ANALIZANDO : PANTALLA.HOME) : PANTALLA.LOCALIZANDO,
  )
  const [resumenVisto, setResumenVisto] = useState(Boolean(parcelaInicial) || !conResumenInicial)
  const [reporteInicial, setReporteInicial] = useState(null)
  const [direccion, setDireccion] = useState('adelante')
  const [ubicacion, setUbicacion] = useState(ubicacionInicial)
  const [hectareas, setHectareas] = useState(parcelaInicial?.area ?? null)
  // La finca puede tener varias parcelas; la primera es la que usan los análisis.
  const [parcelas, setParcelas] = useState(parcelaInicial ? [parcelaInicial] : [])
  const parcela = parcelas[0] ?? null
  const [agregando, setAgregando] = useState(false)
  const [haNueva, setHaNueva] = useState(null)
  // Tarjeta nueva: su número ("Parcela N") y el nombre final ("Parcela N <cultivo>")
  const [numeroNueva, setNumeroNueva] = useState(2)
  const [nombreNueva, setNombreNueva] = useState('')
  const [cultivoNueva, setCultivoNueva] = useState('')
  // Otras fincas (ruta /prueba) y la edición en curso:
  // { finca: 'principal' | índice en `fincas`, indice: parcela actual, nuevas: parcelas ya re-ubicadas }
  const [fincas, setFincas] = useState(fincasExtra ?? [])
  const [edicion, setEdicion] = useState(null)

  const irA = (destino, sentido) => {
    setDireccion(sentido ?? (destino > pantalla ? 'adelante' : 'atras'))
    setPantalla(destino)
  }

  const parcelasDe = (finca) => (finca === 'principal' ? parcelas : fincas[finca].parcelas)
  // En /prueba la principal es la "Parcela 1 Papa" de Toacaso; en "/" es la finca del usuario
  // (en "/", con el cultivo que eligió al registrarla: "Parcela 1 <cultivo>")
  const [cultivoPrincipal, setCultivoPrincipal] = useState('')
  const nombrePrincipal = fincasExtra ? 'Parcela 1 Papa' : cultivoPrincipal ? `Parcela 1 ${cultivoPrincipal}` : 'Mi finca'
  const nombreDe = (finca) => (finca === 'principal' ? nombrePrincipal : fincas[finca].nombre)

  const editarFinca = (finca) => {
    setEdicion({ finca, indice: 0, nuevas: parcelasDe(finca) })
    irA(PANTALLA.EDITAR_INFO)
  }

  const alAceptarEdicion = ({ automatico: _automatico, ...resultado }) => {
    const nuevas = edicion.nuevas.map((p, i) => (i === edicion.indice ? resultado : p))
    if (edicion.indice + 1 < nuevas.length) {
      setEdicion({ ...edicion, indice: edicion.indice + 1, nuevas })
      irA(PANTALLA.EDITAR_INFO, 'adelante')
      return
    }
    if (edicion.finca === 'principal') {
      setParcelas(nuevas)
    } else {
      setFincas((prev) => prev.map((f, i) => (i === edicion.finca ? { ...f, parcelas: nuevas } : f)))
    }
    setEdicion({ ...edicion, nuevas })
    irA(PANTALLA.EDITAR_OK)
  }

  // Tocar una tarjeta abre el análisis de esa finca (su primera parcela).
  // En resultados, el selector de la cabecera cambia de finca sin volver al inicio.
  const [seleccion, setSeleccion] = useState(null) // null = finca principal
  const verFinca = (finca) => {
    if (finca === 'principal') {
      setSeleccion(null)
    } else {
      const parcelaFinca = fincas[finca].parcelas[0]
      const [lat, lng] = centroide(parcelaFinca.poligono)
      setSeleccion({ finca, ubicacion: { lat, lng, precision: null }, parcela: parcelaFinca })
    }
    irA(PANTALLA.RESULTADOS)
  }

  const fincaActiva = seleccion ? seleccion.finca : 'principal'
  const opcionesFinca = [
    { id: 'principal', nombre: nombreDe('principal'), parcelas },
    ...fincas.map((f, i) => ({ id: String(i), nombre: f.nombre, parcelas: f.parcelas })),
  ]
  // Toacaso (Parcela 1 en /prueba) tiene datos reales; el resto, los mismos marcados "Datos de ejemplo"
  const reporteDe = (finca) => (finca === 'principal' && remoteSensingPrincipal ? reporteToacaso() : reporteEjemplo())

  // Va al inicio; en "/" la primera vez pasa antes por "Analizando…" y el resumen de la semana
  const irAlInicio = () => {
    if (resumenVisto) {
      irA(PANTALLA.HOME)
    } else {
      setResumenVisto(true)
      irA(PANTALLA.ANALIZANDO)
    }
  }

  const cancelarEdicion = () => {
    setEdicion(null)
    irA(PANTALLA.HOME)
  }

  const alUbicar = (u) => {
    setUbicacion(u)
    irA(PANTALLA.UBICACION_OK)
  }

  // Primera finca: hectáreas → qué cultivo tiene → ✓ superficie
  const alGuardarHectareas = (ha) => {
    setHectareas(ha)
    irA(PANTALLA.NOMBRE_PARCELA, 'adelante')
  }

  // `otra`: el usuario eligió "Guardar y agregar otra parcela"
  // (`automatico` solo indica si se ajustó a los bordes; no se guarda en la parcela)
  // Cada parcela añadida es otra tarjeta: "Parcela N <cultivo>".
  const alAceptarParcela = ({ automatico, ...resultado }, { otra = false } = {}) => {
    if (agregando) {
      setFincas((prev) => [
        ...prev,
        {
          id: `nueva-${Date.now()}`,
          nombre: nombreNueva,
          cultivo: cultivoNueva,
          zona: ubicacion?.zona ?? '',
          insignia: automatico ? 'Contorno aproximado' : 'Ubicada por ti',
          parcelas: [resultado],
        },
      ])
    } else {
      setParcelas([resultado])
    }
    if (otra) {
      empezarNuevaParcela(agregando ? 1 : 0)
    } else {
      setAgregando(false)
      irAlInicio()
    }
  }

  // "Añadir parcela": nombre → hectáreas → cuadro con ajuste automático → tarjeta nueva
  function empezarNuevaParcela(extra = 0) {
    setAgregando(true)
    setHaNueva(null)
    // `extra`: tarjetas recién creadas que todavía no están en `fincas` (al encadenar "agregar otra")
    setNumeroNueva(fincas.length + 2 + extra)
    setNombreNueva('')
    setCultivoNueva('')
    irA(PANTALLA.NOMBRE_PARCELA)
  }

  const cancelarNuevaParcela = () => {
    setAgregando(false)
    irA(PANTALLA.HOME)
  }

  // Todas las parcelas ya guardadas (de todas las tarjetas): el cuadro nuevo aparece a su lado
  const poligonosGuardados = useMemo(
    () => [...parcelas, ...fincas.flatMap((f) => f.parcelas)].map((p) => p.poligono),
    [parcelas, fincas],
  )

  const contenido = () => {
    switch (pantalla) {
      case PANTALLA.LOCALIZANDO:
        // No se usa el GPS del celular: se "detecta" la ubicación por defecto de lib/ubicacionDemo.js
        return (
          <PantallaLocalizando
            ubicacionFija={UBICACION_DEMO}
            onUbicada={alUbicar}
            onCancelar={onCancelar}
            onManual={onManual}
          />
        )
      case PANTALLA.UBICACION_OK:
        return (
          <PantallaInformativa
            titulo="¡Ubicación obtenida!"
            mensaje="Ya sabemos dónde está tu finca."
            onFin={() => irA(PANTALLA.HECTAREAS)}
          />
        )
      case PANTALLA.NOMBRE_PARCELA:
        // Al añadir una tarjeta es el primer paso; al registrar la primera finca, va después de las hectáreas
        if (!agregando) {
          return (
            <PantallaNombreParcela
              numero={1}
              onGuardar={(cultivo) => {
                setCultivoPrincipal(cultivo)
                irA(PANTALLA.HECTAREAS_OK, 'adelante')
              }}
              onVolver={() => irA(PANTALLA.HECTAREAS, 'atras')}
            />
          )
        }
        return (
          <PantallaNombreParcela
            numero={numeroNueva}
            onGuardar={(cultivo) => {
              setCultivoNueva(cultivo)
              setNombreNueva(`Parcela ${numeroNueva} ${cultivo}`)
              irA(PANTALLA.HECTAREAS, 'adelante')
            }}
            onVolver={cancelarNuevaParcela}
          />
        )
      case PANTALLA.HECTAREAS:
        if (agregando) {
          return (
            <PantallaHectareas
              valorInicial={haNueva}
              titulo={`¿Cuántas hectáreas tiene «${nombreNueva}»?`}
              subtitulo="Después la pondrás en el mapa, al lado de las que ya tienes."
              onGuardar={(ha) => {
                setHaNueva(ha)
                irA(PANTALLA.UBICAR_PARCELA)
              }}
              onVolver={() => irA(PANTALLA.NOMBRE_PARCELA, 'atras')}
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
      case PANTALLA.EDITAR_INFO: {
        const total = edicion.nuevas.length
        return (
          <PantallaInformativa
            ilustracion={<IlustracionUbicar />}
            titulo={total > 1 ? `Ubica la parcela ${edicion.indice + 1} de ${total}` : 'Ahora ubica tu parcela'}
            mensaje={`${nombreDe(edicion.finca)}: mueve el cuadro hasta que quede encima del terreno.`}
            duracion={3400}
            onFin={() => irA(PANTALLA.EDITAR_PARCELA)}
          />
        )
      }
      case PANTALLA.EDITAR_PARCELA: {
        const actual = edicion.nuevas[edicion.indice]
        const [lat, lng] = centroide(actual.poligono)
        const total = edicion.nuevas.length
        return (
          <PantallaUbicarParcela
            ubicacion={{ lat, lng }}
            centroInicial={{ lat, lng }}
            hectareas={Math.round(actual.area * 100) / 100}
            otrasParcelas={edicion.nuevas.filter((_, i) => i !== edicion.indice).map((p) => p.poligono)}
            titulo={total > 1 ? `Parcela ${edicion.indice + 1} de ${total}: pon el cuadro encima` : undefined}
            edicion
            onAceptar={alAceptarEdicion}
            onVolver={cancelarEdicion}
          />
        )
      }
      case PANTALLA.EDITAR_OK: {
        const area = edicion.nuevas.reduce((s, p) => s + p.area, 0)
        const n = edicion.nuevas.length
        return (
          <PantallaInformativa
            titulo="¡Finca actualizada!"
            mensaje={`${nombreDe(edicion.finca)}: ${n} ${n > 1 ? 'parcelas' : 'parcela'} · ${formatoNumero(area, 1)} ha.`}
            onFin={() => {
              setEdicion(null)
              irA(PANTALLA.HOME)
            }}
          />
        )
      }
      case PANTALLA.ANALIZANDO:
        return (
          <PantallaAnalizando
            finca={{ nombre: nombreDe('principal'), parcelas }}
            onListo={(r) => {
              setReporteInicial(r)
              irA(PANTALLA.RESUMEN_INICIAL)
            }}
          />
        )
      case PANTALLA.RESUMEN_INICIAL:
        return (
          <CarruselInsights
            finca={{ nombre: nombreDe('principal'), parcelas }}
            reporte={reporteInicial}
            onSalir={() => irA(PANTALLA.HOME, 'adelante')}
          />
        )
      case PANTALLA.RESULTADOS:
        return (
          <PantallaResultados
            // Al cambiar de finca con el selector, la pantalla se vuelve a montar con sus datos
            key={fincaActiva}
            ubicacion={seleccion?.ubicacion ?? ubicacion}
            parcela={seleccion?.parcela ?? parcela}
            // Ruta /prueba: la finca principal (Parcela 1) usa los datos quemados del remote-sensing
            remoteSensing={seleccion ? undefined : remoteSensingPrincipal}
            // Ruta /prueba: todo ya está procesado (sin "Analizando…"). Las parcelas de ejemplo están a
            // menos de 2 km de Toacaso, en la misma celda de NASA POWER: comparten su serie mensual.
            datosPrecargados={fincasExtra && remoteSensingPrincipal ? remoteSensingPrincipal.mensual : undefined}
            onVolver={() => {
              setSeleccion(null)
              irA(PANTALLA.HOME)
            }}
            finca={{ nombre: nombreDe(fincaActiva), parcelas: parcelasDe(fincaActiva) }}
            reporte={reporteDe(fincaActiva)}
            selector={{
              fincas: opcionesFinca,
              activaId: String(fincaActiva),
              onElegir: (id) => verFinca(id === 'principal' ? 'principal' : Number(id)),
              onNueva: () => {
                setSeleccion(null)
                empezarNuevaParcela()
              },
            }}
          />
        )
      default:
        return (
          <PantallaHome
            nombre={nombre}
            ubicacion={ubicacion}
            parcelas={parcelas}
            nombrePrincipal={nombrePrincipal}
            fincasExtra={fincas}
            onEditarFinca={editarFinca}
            onVerFinca={verFinca}
            onAgregarParcela={() => empezarNuevaParcela()}
          />
        )
    }
  }

  return (
    <div className="marco onb">
      <div className="marco-tarjeta fg">
        {/* Degradados de las ilustraciones del resumen de la semana (se definen una vez) */}
        <DefsReporte />
        <div key={pantalla} className={`fg-transicion onb-${direccion}`}>
          {contenido()}
        </div>
      </div>
    </div>
  )
}
