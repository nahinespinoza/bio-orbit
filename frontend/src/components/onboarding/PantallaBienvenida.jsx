import { useCallback, useEffect, useRef } from 'react'
import { Sprout } from 'lucide-react'
import './bienvenida.css'

const DURACION = 3200 // ms; tocar en cualquier parte adelanta

// Ruta /prueba: en lugar de pedir el nombre, saluda al agricultor y entra solo al inicio.
export default function PantallaBienvenida({ nombre, onFin }) {
  const onFinRef = useRef(onFin)
  useEffect(() => {
    onFinRef.current = onFin
  })
  const terminado = useRef(false)
  const terminar = useCallback(() => {
    if (terminado.current) return
    terminado.current = true
    onFinRef.current()
  }, [])

  useEffect(() => {
    const id = setTimeout(terminar, DURACION)
    return () => clearTimeout(id)
  }, [terminar])

  return (
    <div className="marco onb">
      <div className="marco-tarjeta bv" onPointerUp={terminar}>
        <div className="bv-cuerpo" role="status" aria-live="polite">
          <div className="bv-logo" aria-hidden="true">
            <span className="bv-onda" />
            <span className="bv-onda d2" />
            <span className="bv-onda d3" />
            <span className="bv-circulo">
              <Sprout size={52} strokeWidth={1.75} />
            </span>
          </div>
          <p className="bv-saludo">Bienvenido</p>
          <h1 className="bv-nombre">{nombre}</h1>
          <p className="bv-texto">Preparando tus parcelas…</p>
        </div>
        <div className="bv-progreso" aria-hidden="true">
          <span style={{ animationDuration: `${DURACION}ms` }} />
        </div>
      </div>
    </div>
  )
}
