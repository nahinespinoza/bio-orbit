import { useCallback, useState } from 'react'
import Onboarding from './components/onboarding/Onboarding.jsx'
import VistaMapaMovil from './components/mapa-movil/VistaMapaMovil.jsx'
import FlujoGps from './components/flujo-gps/FlujoGps.jsx'

export default function App() {
  // null mientras el usuario está en el onboarding
  const [sesion, setSesion] = useState(null)
  const [ultimoNombre, setUltimoNombre] = useState('')
  const [historial, setHistorial] = useState([])

  const registrar = useCallback((tipo, detalle) => {
    setHistorial((prev) => [
      { id: crypto.randomUUID(), tipo, detalle, fecha: new Date() },
      ...prev,
    ])
  }, [])

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

  if (!sesion) {
    return (
      <Onboarding
        nombreInicial={ultimoNombre}
        pasoInicial={ultimoNombre ? 2 : 1}
        onUseCurrentLocation={onUseCurrentLocation}
        onSelectManually={onSelectManually}
      />
    )
  }

  if (sesion.modo === 'manual') {
    return (
      <VistaMapaMovil
        sesion={sesion}
        onVolver={volverAlOnboarding}
        onEvento={registrar}
        onParcelaLista={onParcelaLista}
      />
    )
  }

  // 'gps' empieza localizando; 'finca' (dibujada a mano) empieza en el inicio.
  return (
    <FlujoGps
      nombre={sesion.nombre}
      historial={historial}
      ubicacionInicial={sesion.ubicacion}
      parcelaInicial={sesion.parcela}
      onEvento={registrar}
      onProceso={registrar}
      onCancelar={volverAlOnboarding}
      onManual={() => onSelectManually({ nombre: sesion.nombre })}
    />
  )
}
