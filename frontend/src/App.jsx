import { useState } from 'react'
import Onboarding from './components/onboarding/Onboarding.jsx'
import VistaMapaMovil from './components/mapa-movil/VistaMapaMovil.jsx'
import FlujoGps from './components/flujo-gps/FlujoGps.jsx'

let ultimoId = 0
const fincaNueva = (nombre = '') => ({
  id: `finca-${++ultimoId}`, nombre, ubicacion: null, parcelas: [], analisis: null,
})

// Las fincas viven solo mientras la app está abierta: al recargar se vuelve al onboarding.
export default function App() {
  const [agricultor, setAgricultor] = useState('')
  // Fincas registradas (con al menos una parcela) y la que se ve en el inicio
  const [fincas, setFincas] = useState([])
  const [activaId, setActivaId] = useState(null)
  // Finca que se está registrando: pasa a `fincas` al guardar su primera parcela.
  // La primera se llama "Mi finca"; las demás piden nombre.
  const [borrador, setBorrador] = useState(() => fincaNueva('Mi finca'))
  // 'datos': nombre y "¿Dónde está tu finca?" · 'mapa': dibujarla a mano ·
  // 'finca': GPS, inicio y análisis
  const [etapa, setEtapa] = useState('datos')
  const [pasoDatos, setPasoDatos] = useState(1)

  const primeraVez = fincas.length === 0
  const finca = borrador ?? fincas.find((f) => f.id === activaId)

  // Aplica `cambios` (objeto o función de la finca) a una finca
  const cambiarFinca = (id, cambios) => {
    const aplicar = (f) => ({ ...f, ...(typeof cambios === 'function' ? cambios(f) : cambios) })
    if (borrador?.id !== id) {
      setFincas((fs) => fs.map((f) => (f.id === id ? aplicar(f) : f)))
      return
    }
    const actualizado = aplicar(borrador)
    if (!actualizado.parcelas.length) {
      setBorrador(actualizado)
      return
    }
    // Ya tiene su primera parcela: queda guardada y es la que se ve en el inicio
    setFincas((fs) => [...fs, actualizado])
    setActivaId(id)
    setBorrador(null)
  }

  // Desde "¿Dónde está tu finca?": con el GPS ('finca') o dibujándola ('mapa')
  const ubicarCon = (destino) => ({ nombre }) => {
    if (primeraVez) setAgricultor(nombre)
    else setBorrador((b) => ({ ...b, nombre }))
    setEtapa(destino)
  }

  // Vuelve a "¿Dónde está tu finca?" conservando el nombre
  const volverAUbicar = () => {
    setPasoDatos(2)
    setEtapa('datos')
  }

  // "Nueva finca" desde el selector del inicio
  const empezarFinca = () => {
    setBorrador(fincaNueva())
    setPasoDatos(1)
    setEtapa('datos')
  }

  // "Volver" desde el nombre de la finca nueva: regresa al inicio de la que se veía
  const cancelarFinca = () => {
    setBorrador(null)
    setEtapa('finca')
  }

  if (etapa === 'datos') {
    return (
      <Onboarding
        modo={primeraVez ? 'agricultor' : 'finca'}
        nombreInicial={primeraVez ? agricultor : borrador.nombre}
        pasoInicial={pasoDatos}
        nombresUsados={fincas.map((f) => f.nombre)}
        onCancelar={cancelarFinca}
        onUseCurrentLocation={ubicarCon('finca')}
        onSelectManually={ubicarCon('mapa')}
      />
    )
  }

  // El modo manual termina cuando el agricultor guarda el dibujo de su finca:
  // desde ahí sigue el mismo camino que el GPS (inicio → resultados).
  if (etapa === 'mapa') {
    return (
      <VistaMapaMovil
        nombre={agricultor}
        onVolver={volverAUbicar}
        onParcelaLista={({ ubicacion, parcela }) => {
          cambiarFinca(borrador.id, { ubicacion, parcelas: [parcela] })
          setEtapa('finca')
        }}
      />
    )
  }

  // Una finca sin parcelas empieza localizando; una registrada, en el inicio.
  // La key vuelve a montar el flujo al cambiar de finca.
  return (
    <FlujoGps
      key={finca.id}
      nombre={agricultor}
      finca={finca}
      fincas={fincas}
      onCambiar={(cambios) => cambiarFinca(finca.id, cambios)}
      onElegirFinca={setActivaId}
      onNuevaFinca={empezarFinca}
      onCancelar={volverAUbicar}
      onManual={() => setEtapa('mapa')}
    />
  )
}
