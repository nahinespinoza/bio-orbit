import { useState } from 'react'
import PasoNombre from './PasoNombre.jsx'
import PasoUbicacion from './PasoUbicacion.jsx'
import './onboarding.css'

// Flujo de 2 pasos: nombre → ubicación de la finca.
// `modo`: 'agricultor' (primera vez, pide el nombre de la persona) o 'finca'
// (otra finca desde el inicio: pide el nombre de la finca y se puede cancelar con `onCancelar`).
// `onUseCurrentLocation({ nombre })` y `onSelectManually({ nombre })`
// conectan con la siguiente vista.
export default function Onboarding({
  modo = 'agricultor', onUseCurrentLocation, onSelectManually, onCancelar,
  nombresUsados = [], nombreInicial = '', pasoInicial = 1,
}) {
  const [paso, setPaso] = useState(pasoInicial)
  const [direccion, setDireccion] = useState(pasoInicial > 1 ? 'atras' : 'adelante')
  const [nombre, setNombre] = useState(nombreInicial)

  const esFinca = modo === 'finca'

  const nombreRepetido = (n) =>
    nombresUsados.some((u) => u.toLocaleLowerCase('es') === n.toLocaleLowerCase('es'))
      ? 'Ya tienes una finca con ese nombre.'
      : ''

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
            <PasoNombre
              modo={modo}
              nombre={nombre}
              onNombreChange={setNombre}
              onSiguiente={() => irA(2)}
              onVolver={esFinca ? onCancelar : undefined}
              validar={esFinca ? nombreRepetido : undefined}
            />
          ) : (
            <PasoUbicacion
              saludo={esFinca ? nombre : `Hola, ${nombre.split(' ')[0]}`}
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
