import { useState } from 'react'
import { ArrowRight, ChevronLeft, Sprout } from 'lucide-react'

// Cultivos frecuentes: un toque y listo (también se puede escribir otro).
const CULTIVOS = ['Papa', 'Maíz', 'Arroz', 'Cacao', 'Banano']

const conMayuscula = (t) => t.charAt(0).toLocaleUpperCase('es') + t.slice(1)

// Primer paso de "Añadir parcela": qué se siembra. La tarjeta se llamará "Parcela N <cultivo>".
export default function PantallaNombreParcela({ numero, onGuardar, onVolver }) {
  const [cultivo, setCultivo] = useState('')
  const [error, setError] = useState('')

  const cambiar = (valor) => {
    setCultivo(valor)
    if (error) setError('')
  }

  const enviar = (e) => {
    e.preventDefault() // Enter también envía
    const limpio = cultivo.trim().replace(/\s+/g, ' ')
    if (!limpio) {
      setError('Escribe o elige qué tienes sembrado.')
      return
    }
    onGuardar(conMayuscula(limpio))
  }

  const elegido = cultivo.trim().toLocaleLowerCase('es')

  return (
    <form className="fg-pantalla fg-pantalla-padding" onSubmit={enviar} noValidate>
      <div className="onb-top">
        <button type="button" className="onb-volver" onClick={onVolver}>
          <ChevronLeft size={20} /> Volver
        </button>
      </div>

      <div className="fg-cuerpo">
        <div className="onb-avatar" aria-hidden="true">
          <Sprout size={44} strokeWidth={1.75} />
        </div>
        <label htmlFor="fg-cultivo" className="onb-titulo fg-titulo-largo">
          ¿Qué tipo de plantación tienes?
        </label>
        <p className="onb-subtitulo">
          Tu tarjeta se llamará «Parcela {numero} {cultivo.trim() ? conMayuscula(cultivo.trim()) : '…'}».
        </p>

        <div className="fg-sugerencias" role="group" aria-label="Cultivos frecuentes">
          {CULTIVOS.map((c) => (
            <button
              key={c}
              type="button"
              className={`fg-chip ${elegido === c.toLocaleLowerCase('es') ? 'activo' : ''}`}
              aria-pressed={elegido === c.toLocaleLowerCase('es')}
              onClick={() => cambiar(c)}
            >
              {c}
            </button>
          ))}
        </div>

        <input
          id="fg-cultivo"
          className="onb-input"
          type="text"
          autoComplete="off"
          maxLength={30}
          placeholder="Otro cultivo, ej. Quinua"
          value={cultivo}
          aria-invalid={!!error}
          aria-describedby="fg-cultivo-error"
          onChange={(e) => cambiar(e.target.value)}
        />
        <p id="fg-cultivo-error" className="onb-error" role="alert">
          {error}
        </p>
      </div>

      <button type="submit" className="onb-btn onb-btn-primario">
        Siguiente <ArrowRight size={20} />
      </button>
    </form>
  )
}
