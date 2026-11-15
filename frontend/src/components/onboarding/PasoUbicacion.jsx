import { ChevronLeft, LocateFixed, Map as MapIcon } from 'lucide-react'
import Progreso from './Progreso.jsx'

// Solo GPS: la opción de dibujar la finca en el mapa se quitó de este paso.
export default function PasoUbicacion({ nombre, onVolver, onUseCurrentLocation }) {
  return (
    <div className="onb-form">
      <div className="onb-top">
        <button type="button" className="onb-volver" onClick={onVolver}>
          <ChevronLeft size={20} /> Volver
        </button>
        <Progreso paso={2} />
      </div>

      <div className="onb-cuerpo">
        <div className="onb-avatar" aria-hidden="true">
          <MapIcon size={44} strokeWidth={1.75} />
        </div>
        <p className="onb-saludo">Hola, {nombre.split(' ')[0]}</p>
        <h1 className="onb-titulo">¿Dónde está tu finca?</h1>
        <p className="onb-subtitulo">Si estás ahora en tu finca, usa el GPS del celular para encontrarla.</p>
      </div>

      <div className="onb-acciones">
        <button type="button" className="onb-btn onb-btn-primario" onClick={onUseCurrentLocation}>
          <LocateFixed size={20} /> Estoy en mi finca (usar GPS)
        </button>
      </div>
    </div>
  )
}
