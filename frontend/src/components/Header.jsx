import { Orbit, UserRound } from 'lucide-react'

export default function Header({ nombre }) {
  return (
    <header className="header">
      <div className="brand">
        <Orbit size={26} />
        <div>
          <span className="brand-name">Bio Orbit</span>
          <span className="brand-sub">Monitoreo satelital</span>
        </div>
      </div>
      <h1 className="header-title">Monitoreo de Cultivos</h1>
      <div className="header-usuario">
        {nombre && (
          <>
            <span className="usuario-nombre">{nombre}</span>
            <span className="usuario-avatar">
              <UserRound size={18} />
            </span>
          </>
        )}
      </div>
    </header>
  )
}
