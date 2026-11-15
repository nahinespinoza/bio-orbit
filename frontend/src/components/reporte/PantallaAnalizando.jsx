import { useEffect, useRef } from 'react'
import { Satellite } from 'lucide-react'
import { obtenerReporte } from '../../lib/reporte.js'
import '../resultados/resultados.css'

// Espera mientras se arma el reporte de una finca recién registrada.
// Al terminar avisa con `onListo(reporte)`; si la pantalla se cierra, se cancela.
export default function PantallaAnalizando({ finca, onListo }) {
  const onListoRef = useRef(onListo)
  useEffect(() => {
    onListoRef.current = onListo
  })

  // Solo al entrar: la finca no cambia mientras esta pantalla está abierta
  const fincaRef = useRef(finca)
  useEffect(() => {
    const control = new AbortController()
    obtenerReporte(fincaRef.current, control.signal)
      .then((reporte) => !control.signal.aborted && onListoRef.current(reporte))
      .catch(() => {})
    return () => control.abort()
  }, [])

  return (
    <div className="fg-pantalla rs">
      <div className="rs-cargando" role="status">
        <div className="rs-cargando-icono">
          <span className="rs-orbita" />
          <Satellite size={34} />
        </div>
        <h2>Analizando tu finca…</h2>
      </div>
    </div>
  )
}
