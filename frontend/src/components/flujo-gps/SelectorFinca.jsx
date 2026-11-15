import { useEffect, useId, useRef, useState } from 'react'
import { Check, ChevronDown, Plus } from 'lucide-react'
import { formatoNumero } from './geo.js'

const resumen = ({ parcelas }) => {
  const ha = parcelas.reduce((s, p) => s + p.area, 0)
  return `${parcelas.length} ${parcelas.length === 1 ? 'parcela' : 'parcelas'} · ${formatoNumero(ha, 1)} ha`
}

// Arriba del inicio: el nombre de la finca que se está viendo. Al tocarlo se abre
// la lista de fincas guardadas para cambiar de una a otra, y el botón para registrar otra.
export default function SelectorFinca({ activa, fincas, onElegir, onNueva }) {
  const [abierto, setAbierto] = useState(false)
  const botonRef = useRef(null)
  const menuRef = useRef(null)
  const idMenu = useId()

  const cerrar = ({ devolverFoco = true } = {}) => {
    setAbierto(false)
    if (devolverFoco) botonRef.current?.focus()
  }

  // Al abrir, el foco va a la finca que se está viendo
  useEffect(() => {
    if (abierto) menuRef.current?.querySelector('[aria-checked="true"]')?.focus()
  }, [abierto])

  // Flechas, Inicio y Fin recorren las opciones; Escape y Tab cierran
  const alTeclear = (e) => {
    if (e.key === 'Escape' || e.key === 'Tab') {
      e.preventDefault()
      cerrar()
      return
    }
    const opciones = [...menuRef.current.querySelectorAll('[role^="menuitem"]')]
    const i = opciones.indexOf(document.activeElement)
    const destino = { ArrowDown: i + 1, ArrowUp: i - 1, Home: 0, End: opciones.length - 1 }[e.key]
    if (destino === undefined) return
    e.preventDefault()
    opciones[(destino + opciones.length) % opciones.length].focus()
  }

  const elegir = (id) => {
    const misma = id === activa.id
    // Al cambiar de finca el inicio se vuelve a montar: no hay botón al que devolver el foco
    cerrar({ devolverFoco: misma })
    if (!misma) onElegir(id)
  }

  return (
    <div className="fg-selector">
      <button
        ref={botonRef}
        type="button"
        className="fg-selector-boton"
        aria-haspopup="menu"
        aria-expanded={abierto}
        aria-controls={abierto ? idMenu : undefined}
        onClick={() => setAbierto((a) => !a)}
      >
        <span className="fg-selector-nombre">{activa.nombre}</span>
        <ChevronDown size={20} aria-hidden="true" />
      </button>

      {abierto && (
        <>
          {/* Tocar fuera del menú solo lo cierra */}
          <div className="fg-selector-fondo" aria-hidden="true" onClick={() => cerrar()} />
          <div
            ref={menuRef}
            id={idMenu}
            role="menu"
            aria-label="Tus fincas"
            className="fg-selector-menu"
            onKeyDown={alTeclear}
          >
            <div className="fg-selector-lista">
              {fincas.map((f) => {
                const actual = f.id === activa.id
                return (
                  <button
                    key={f.id}
                    type="button"
                    role="menuitemradio"
                    aria-checked={actual}
                    tabIndex={-1}
                    className="fg-selector-opcion"
                    onClick={() => elegir(f.id)}
                  >
                    <span className="fg-selector-opcion-texto">
                      <strong>{f.nombre}</strong>
                      <small>{resumen(f)}</small>
                    </span>
                    {actual && <Check size={20} aria-hidden="true" />}
                  </button>
                )
              })}
            </div>
            <div className="fg-selector-separador" role="separator" />
            <button
              type="button"
              role="menuitem"
              tabIndex={-1}
              className="fg-selector-opcion fg-selector-nueva"
              onClick={() => {
                cerrar({ devolverFoco: false })
                onNueva()
              }}
            >
              <span className="fg-selector-nueva-icono" aria-hidden="true">
                <Plus size={18} />
              </span>
              Nueva finca
            </button>
          </div>
        </>
      )}
    </div>
  )
}
