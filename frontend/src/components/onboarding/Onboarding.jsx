import { useState } from 'react'
import PasoNombre from './PasoNombre.jsx'
import PasoUbicacion from './PasoUbicacion.jsx'
import './onboarding.css'

// Flujo de 2 pasos: nombre → ubicación de la finca.
// `onUseCurrentLocation({ nombre })` y `onSelectManually({ nombre })`
// conectan con la siguiente vista.
export default function Onboarding({ onUseCurrentLocation, onSelectManually, nombreInicial = '', pasoInicial = 1 }) {
  const [paso, setPaso] = useState(pasoInicial)
  const [direccion, setDireccion] = useState(pasoInicial > 1 ? 'atras' : 'adelante')
  const [nombre, setNombre] = useState(nombreInicial)

  const irA = (nuevo) => {
    setDireccion(nuevo > paso ? 'adelante' : 'atras')
    setPaso(nuevo)
  }

  return (
    <div className="marco onb">
      <div className="marco-tarjeta">
        {/* La key fuerza el remontaje para animar la transición entre pasos */}
        <div key={paso} className={`onb-pantalla onb-${direccion}`}>
          {paso === 1 ? (
            <PasoNombre nombre={nombre} onNombreChange={setNombre} onSiguiente={() => irA(2)} />
          ) : (
            <PasoUbicacion
              nombre={nombre}
              onVolver={() => irA(1)}
              onUseCurrentLocation={() => onUseCurrentLocation?.({ nombre })}
              onSelectManually={() => onSelectManually?.({ nombre })}
            />
          )}
        </div>
      </div>
    </div>
  )
}
