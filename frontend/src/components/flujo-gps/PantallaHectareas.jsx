import { useState } from 'react'
import { ChevronLeft, LandPlot, Minus, Plus, Save } from 'lucide-react'

const SUGERENCIAS = [1, 5, 10, 25, 50]
const MAXIMO = 100000

const leer = (texto) => parseFloat(String(texto).replace(',', '.'))

export default function PantallaHectareas({
  valorInicial,
  onGuardar,
  onVolver,
  titulo = '¿Cuántas hectáreas tiene tu finca?',
  subtitulo = 'Usaremos este dato para delimitar tu parcela en el mapa.',
}) {
  const [texto, setTexto] = useState(valorInicial ? String(valorInicial) : '')
  const [error, setError] = useState('')
  const valor = leer(texto)

  const cambiar = (nuevo) => {
    setTexto(nuevo)
    if (error) setError('')
  }

  const ajustar = (delta) => {
    const base = Number.isFinite(valor) ? valor : 0
    cambiar(String(Math.max(0, Math.round((base + delta) * 100) / 100)))
  }

  const enviar = (e) => {
    e.preventDefault()
    if (!Number.isFinite(valor) || valor <= 0) {
      setError('Ingresa una superficie mayor a 0.')
      return
    }
    if (valor > MAXIMO) {
      setError('El valor parece demasiado grande. Revisa la cantidad.')
      return
    }
    onGuardar(Math.round(valor * 100) / 100)
  }

  return (
    <form className="fg-pantalla fg-pantalla-padding" onSubmit={enviar} noValidate>
      <div className="onb-top">
        <button type="button" className="onb-volver" onClick={onVolver}>
          <ChevronLeft size={20} /> Volver
        </button>
      </div>

      <div className="fg-cuerpo">
        <div className="onb-avatar" aria-hidden="true">
          <LandPlot size={44} strokeWidth={1.75} />
        </div>
        <label htmlFor="fg-hectareas" className="onb-titulo fg-titulo-largo">
          {titulo}
        </label>
        <p className="onb-subtitulo">{subtitulo}</p>

        <div className={`fg-campo-ha ${error ? 'invalido' : ''}`}>
          <button type="button" className="fg-paso-btn" onClick={() => ajustar(-1)} aria-label="Restar una hectárea">
            <Minus size={20} />
          </button>
          <div className="fg-campo-ha-centro">
            <input
              id="fg-hectareas"
              className="fg-input-ha"
              type="text"
              inputMode="decimal"
              placeholder="0"
              autoFocus
              autoComplete="off"
              value={texto}
              aria-invalid={!!error}
              aria-describedby="fg-ha-error fg-ha-ayuda"
              onChange={(e) => cambiar(e.target.value.replace(/[^\d.,]/g, ''))}
            />
            <span className="fg-unidad">ha</span>
          </div>
          <button type="button" className="fg-paso-btn" onClick={() => ajustar(1)} aria-label="Sumar una hectárea">
            <Plus size={20} />
          </button>
        </div>

        <div className="fg-sugerencias" role="group" aria-label="Valores frecuentes">
          {SUGERENCIAS.map((n) => (
            <button
              key={n}
              type="button"
              className={`fg-chip ${valor === n ? 'activo' : ''}`}
              onClick={() => cambiar(String(n))}
            >
              {n} ha
            </button>
          ))}
        </div>

        <p id="fg-ha-ayuda" className="fg-ayuda">
          1 hectárea = 10.000 m² (aprox. una cancha y media de fútbol)
        </p>
        <p id="fg-ha-error" className="onb-error" role="alert">
          {error}
        </p>
      </div>

      <button type="submit" className="onb-btn onb-btn-primario">
        <Save size={20} /> Guardar
      </button>
    </form>
  )
}
