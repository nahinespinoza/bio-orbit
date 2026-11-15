import { Move } from 'lucide-react'

// Un cuadro que se desliza sobre unas parcelas: anticipa lo que hará el usuario.
export default function IlustracionUbicar() {
  return (
    <div className="fg-ilustra-ubicar" aria-hidden="true">
      <span className="fg-ilustra-parcela a" />
      <span className="fg-ilustra-parcela b" />
      <span className="fg-ilustra-parcela c" />
      <span className="fg-ilustra-parcela d" />
      <span className="fg-ilustra-cuadro">
        <Move size={22} />
      </span>
    </div>
  )
}
