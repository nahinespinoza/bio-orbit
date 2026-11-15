import { useState } from 'react'
import Onboarding from './components/onboarding/Onboarding.jsx'
import PantallaBienvenida from './components/onboarding/PantallaBienvenida.jsx'
import VistaMapaMovil from './components/mapa-movil/VistaMapaMovil.jsx'
import FlujoGps from './components/flujo-gps/FlujoGps.jsx'
import { FINCAS_EJEMPLO, PARCELA, UBICACION } from './lib/parcelaMonitoreada.js'
import { RS_PARCELA1 } from './lib/remoteSensingParcela1.js'

// En /prueba no se pide la ubicación: tras el nombre se entra al inicio con la
// parcela monitoreada por el remote-sensing (Toacaso / Sigchos).
const ES_PRUEBA = window.location.pathname.replace(/\/+$/, '') === '/prueba'
// En /prueba no se pide el nombre: una pantalla de bienvenida saluda a este agricultor
const NOMBRE_PRUEBA = 'Maximiliano'

export default function App() {
  // null mientras el usuario está en el onboarding
  const [sesion, setSesion] = useState(null)
  const [ultimoNombre, setUltimoNombre] = useState('')

  // La ubicación se obtiene dentro del flujo GPS (pantalla "Detectando tu ubicación")
  const onUseCurrentLocation = ({ nombre }) => {
    setSesion({ nombre, ubicacion: null, modo: 'gps' })
  }

  const onSelectManually = ({ nombre }) => {
    setSesion({ nombre, ubicacion: null, modo: 'manual' })
  }

  // El modo manual termina cuando el agricultor guarda el dibujo de su finca:
  // desde ahí sigue el mismo camino que el GPS (inicio → resultados).
  const onParcelaLista = ({ ubicacion, parcela }) => {
    setSesion((s) => ({ ...s, modo: 'finca', ubicacion, parcela }))
  }

  // Vuelve al paso "Ubica tu finca" conservando el nombre
  const volverAlOnboarding = () => {
    setUltimoNombre(sesion.nombre)
    setSesion(null)
  }

  const onNombreListo = ({ nombre }) => {
    setSesion({ nombre, modo: 'finca', ubicacion: UBICACION, parcela: PARCELA })
  }

  if (!sesion && ES_PRUEBA) {
    return <PantallaBienvenida nombre={NOMBRE_PRUEBA} onFin={() => onNombreListo({ nombre: NOMBRE_PRUEBA })} />
  }

  if (!sesion) {
    return (
      <Onboarding
        nombreInicial={ultimoNombre}
        pasoInicial={ultimoNombre && !ES_PRUEBA ? 2 : 1}
        onNombreListo={ES_PRUEBA ? onNombreListo : undefined}
        onUseCurrentLocation={onUseCurrentLocation}
      />
    )
  }

  if (sesion.modo === 'manual') {
    return (
      <VistaMapaMovil
        sesion={sesion}
        onVolver={volverAlOnboarding}
        onParcelaLista={onParcelaLista}
      />
    )
  }

  // 'gps' empieza localizando; 'finca' (dibujada a mano) empieza en el inicio.
  return (
    <FlujoGps
      nombre={sesion.nombre}
      ubicacionInicial={sesion.ubicacion}
      parcelaInicial={sesion.parcela}
      fincasExtra={ES_PRUEBA ? FINCAS_EJEMPLO : undefined}
      remoteSensingPrincipal={ES_PRUEBA ? RS_PARCELA1 : undefined}
      onCancelar={volverAlOnboarding}
      onManual={() => onSelectManually({ nombre: sesion.nombre })}
    />
  )
}
