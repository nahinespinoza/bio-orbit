import { useState } from 'react'
import { ArrowRight, Sprout } from 'lucide-react'
import Progreso from './Progreso.jsx'

export default function PasoNombre({ nombre, onNombreChange, onSiguiente }) {
  const [error, setError] = useState('')

  const enviar = (e) => {
    e.preventDefault() // Enter también envía el formulario
    if (!nombre.trim()) {
      setError('Escribe tu nombre para continuar.')
      return
    }
    onNombreChange(nombre.trim())
    onSiguiente()
  }

  return (
    <form className="onb-form" onSubmit={enviar} noValidate>
      <div className="onb-top">
        <span className="onb-top-hueco" />
        <Progreso paso={1} />
      </div>

      <div className="onb-cuerpo">
        <div className="onb-avatar" aria-hidden="true">
          <Sprout size={44} strokeWidth={1.75} />
        </div>
        <p className="onb-saludo">¡Te damos la bienvenida a Bio Orbit!</p>
        <label htmlFor="onb-nombre" className="onb-titulo">
          ¿Cómo te llamas?
        </label>
        <input
          id="onb-nombre"
          className="onb-input"
          type="text"
          placeholder="Ej. Juan Pérez"
          autoComplete="name"
          autoFocus
          maxLength={60}
          value={nombre}
          aria-invalid={!!error}
          aria-describedby="onb-nombre-error"
          onChange={(e) => {
            onNombreChange(e.target.value)
            if (error) setError('')
          }}
        />
        <p id="onb-nombre-error" className="onb-error" role="alert">
          {error}
        </p>
      </div>

      <button type="submit" className="onb-btn onb-btn-primario">
        Siguiente <ArrowRight size={20} />
      </button>
    </form>
  )
}
