import { useCallback, useEffect, useRef } from 'react'
import CheckAnimado from './CheckAnimado.jsx'

// Pantalla solo informativa: confirma que algo salió bien y avanza sola
// después de `duracion` ms, como si el usuario hubiera tocado "Continuar".
// Tocar en cualquier parte adelanta el paso.
export default function PantallaInformativa({ ilustracion = <CheckAnimado />, titulo, mensaje, duracion = 2600, onFin }) {
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
    const id = setTimeout(terminar, duracion)
    return () => clearTimeout(id)
  }, [duracion, terminar])

  return (
    <div className="fg-pantalla fg-pantalla-padding fg-informativa" onPointerUp={terminar}>
      <div className="fg-cuerpo" role="status" aria-live="polite">
        {ilustracion}
        <h1 className="fg-titulo fg-aparecer" style={{ '--retraso': '0.5s' }}>
          {titulo}
        </h1>
        {mensaje && (
          <p className="fg-texto fg-aparecer" style={{ '--retraso': '0.6s' }}>
            {mensaje}
          </p>
        )}
      </div>
      <div className="fg-temporizador" aria-hidden="true">
        <span style={{ animationDuration: `${duracion}ms` }} />
      </div>
    </div>
  )
}
