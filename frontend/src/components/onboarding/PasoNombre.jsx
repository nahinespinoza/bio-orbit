import { useState } from 'react'
import { ArrowRight, ChevronLeft, Sprout, Tractor } from 'lucide-react'
import Progreso from './Progreso.jsx'

// El mismo paso sirve para el nombre del agricultor (primera vez) y para el de una finca más
const TEXTOS = {
  agricultor: {
    Icono: Sprout,
    saludo: '¡Te damos la bienvenida a Bio Orbit!',
    titulo: '¿Cómo te llamas?',
    placeholder: 'Ej. Juan Pérez',
    autoComplete: 'name',
    vacio: 'Escribe tu nombre para continuar.',
  },
  finca: {
    Icono: Tractor,
    saludo: 'Vamos a agregar otra finca',
    titulo: '¿Cómo se llama tu finca?',
    placeholder: 'Ej. Finca El Rosal',
    autoComplete: 'off',
    vacio: 'Escribe un nombre para tu finca.',
  },
}

// `validar(nombre)` devuelve un mensaje de error o '' si el nombre sirve.
// `onVolver` muestra el botón "Volver" (al registrar otra finca se puede cancelar).
export default function PasoNombre({ modo = 'agricultor', nombre, onNombreChange, onSiguiente, onVolver, validar }) {
  const [error, setError] = useState('')
  const { Icono, ...textos } = TEXTOS[modo]

  const enviar = (e) => {
    e.preventDefault() // Enter también envía el formulario
    const mensaje = !nombre.trim() ? textos.vacio : (validar?.(nombre.trim()) ?? '')
    if (mensaje) {
      setError(mensaje)
      return
    }
    onNombreChange(nombre.trim())
    onSiguiente()
  }

  return (
    <form className="onb-form" onSubmit={enviar} noValidate>
      <div className="onb-top">
        {onVolver ? (
          <button type="button" className="onb-volver" onClick={onVolver}>
            <ChevronLeft size={20} /> Volver
          </button>
        ) : (
          <span className="onb-top-hueco" />
        )}
        <Progreso paso={1} />
      </div>

      <div className="onb-cuerpo">
        <div className="onb-avatar" aria-hidden="true">
          <Icono size={44} strokeWidth={1.75} />
        </div>
        <p className="onb-saludo">{textos.saludo}</p>
        <label htmlFor="onb-nombre" className="onb-titulo">
          {textos.titulo}
        </label>
        <input
          id="onb-nombre"
          className="onb-input"
          type="text"
          placeholder={textos.placeholder}
          autoComplete={textos.autoComplete}
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
