// Dibujos del reporte semanal, copiados de las maquetas del flujo de resultados.
// Los degradados se definen una sola vez en <DefsReporte />, que se monta en FlujoGps.

const NUBE = 'M22 58h52a18 18 0 0 0 1-36 26 26 0 0 0-49-6A21 21 0 0 0 22 58Z'
const GOTA = 'M0 -10 C6 -2 9 2 9 6 A9 9 0 0 1 -9 6 C-9 2 -6 -2 0 -10 Z'

export function DefsReporte() {
  return (
    <svg width="0" height="0" aria-hidden="true" focusable="false" style={{ position: 'absolute' }}>
      <defs>
        <linearGradient id="rep-nube" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#ffffff" />
          <stop offset="1" stopColor="#c7dcf5" />
        </linearGradient>
        <radialGradient id="rep-sol" cx="0.4" cy="0.4" r="0.7">
          <stop offset="0" stopColor="#fff3b0" />
          <stop offset="1" stopColor="#fbbf24" />
        </radialGradient>
        <linearGradient id="rep-gota" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#dbeafe" />
          <stop offset="1" stopColor="#60a5fa" />
        </linearGradient>
        <linearGradient id="rep-hoja" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#bbf7d0" />
          <stop offset="1" stopColor="#22c55e" />
        </linearGradient>
        <linearGradient id="rep-tierra" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#d6a46a" />
          <stop offset="1" stopColor="#8a5a2b" />
        </linearGradient>
        <radialGradient id="rep-luna" cx="0.35" cy="0.35" r="0.8">
          <stop offset="0" stopColor="#fefce8" />
          <stop offset="1" stopColor="#fde68a" />
        </radialGradient>
        <mask id="rep-creciente">
          <rect x="0" y="0" width="120" height="100" fill="#ffffff" />
          <circle cx="58" cy="28" r="19" fill="#000000" />
        </mask>
      </defs>
    </svg>
  )
}

const Nubes = () => (
  <>
    <g transform="translate(30 2) scale(0.75)" opacity="0.9"><path d={NUBE} fill="url(#rep-nube)" /></g>
    <g transform="translate(4 16) scale(0.95)"><path d={NUBE} fill="url(#rep-nube)" /></g>
  </>
)

const Hojas = ({ manchas = false }) => (
  <>
    <path d="M60 94 V54" stroke="#bbf7d0" strokeWidth="4" strokeLinecap="round" />
    <path d="M60 76 C34 76 18 58 18 32 C46 32 60 48 60 76 Z" fill="url(#rep-hoja)" />
    <path d="M60 64 C86 64 102 46 102 20 C74 20 60 36 60 64 Z" fill="url(#rep-hoja)" />
    {manchas && (
      <>
        <circle cx="36" cy="48" r="6" fill="#5b3a1e" />
        <circle cx="47" cy="61" r="3.5" fill="#7c4a1e" />
        <circle cx="84" cy="34" r="7" fill="#5b3a1e" />
        <circle cx="74" cy="47" r="3" fill="#7c4a1e" />
      </>
    )}
  </>
)

const DIBUJOS = {
  helada: () => (
    <>
      <circle cx="44" cy="40" r="25" fill="url(#rep-luna)" mask="url(#rep-creciente)" />
      <circle cx="98" cy="18" r="2.5" fill="#ffffff" />
      <circle cx="106" cy="40" r="1.8" fill="#ffffff" opacity="0.7" />
      <circle cx="16" cy="80" r="2" fill="#ffffff" opacity="0.8" />
      <g stroke="#e0f2fe" strokeWidth="3.5" strokeLinecap="round" fill="none">
        <path d="M84 48v36M68.4 57l31.2 18M68.4 75l31.2-18" />
        <path d="M78 52l6 5 6-5M78 80l6-5 6 5" />
      </g>
    </>
  ),
  suelo: () => (
    <>
      <path d="M10 50 Q60 40 110 50 V90 a6 6 0 0 1 -6 6 H16 a6 6 0 0 1 -6 -6 Z" fill="url(#rep-tierra)" />
      <path d="M14 68 Q60 60 106 68" stroke="#6b4423" strokeWidth="2" fill="none" opacity="0.5" />
      <path transform="translate(36 74) scale(0.9)" d={GOTA} fill="url(#rep-gota)" />
      <path transform="translate(64 80)" d={GOTA} fill="url(#rep-gota)" />
      <path transform="translate(90 70) scale(0.7)" d={GOTA} fill="url(#rep-gota)" />
      <path d="M60 46 V26" stroke="#86efac" strokeWidth="3.5" strokeLinecap="round" />
      <path d="M60 34 C48 34 42 26 42 16 C52 16 60 22 60 34 Z" fill="url(#rep-hoja)" />
      <path d="M60 30 C70 30 78 22 78 12 C68 12 60 18 60 30 Z" fill="url(#rep-hoja)" />
    </>
  ),
  calor: () => (
    <>
      <g stroke="#fde68a" strokeWidth="4" strokeLinecap="round">
        {[0, 40, 80, -40, -80].map((g) => (
          <line key={g} x1="58" y1="6" x2="58" y2="0" transform={`rotate(${g} 58 36)`} />
        ))}
      </g>
      <circle cx="58" cy="36" r="22" fill="url(#rep-sol)" />
      <path d="M18 74c8-6 16 6 24 0s16 6 24 0 16 6 24 0 16 6 24 0" stroke="#fed7aa" strokeWidth="4" fill="none" strokeLinecap="round" />
      <path d="M26 88c8-6 16 6 24 0s16 6 24 0 16 6 24 0" stroke="#fed7aa" strokeWidth="4" fill="none" strokeLinecap="round" opacity="0.6" />
    </>
  ),
  lluvia: () => (
    <>
      <Nubes />
      <g stroke="#dbeafe" strokeWidth="3.5" strokeLinecap="round">
        <line x1="26" y1="78" x2="22" y2="88" />
        <line x1="44" y1="82" x2="40" y2="92" />
        <line x1="62" y1="78" x2="58" y2="88" />
        <line x1="80" y1="82" x2="76" y2="92" />
      </g>
    </>
  ),
  aire: () => (
    <>
      <Nubes />
      <g stroke="#e0f2fe" strokeWidth="3.5" strokeLinecap="round" opacity="0.85">
        <line x1="16" y1="80" x2="70" y2="80" />
        <line x1="30" y1="90" x2="96" y2="90" />
        <line x1="80" y1="80" x2="104" y2="80" />
      </g>
    </>
  ),
  lancha: () => <Hojas manchas />,
  hoja: () => <Hojas />,
}

export function IlustracionReporte({ tipo }) {
  const Dibujo = DIBUJOS[tipo] ?? DIBUJOS.hoja
  return (
    <svg viewBox="0 0 120 100" className="ui-ilustracion" aria-hidden="true" focusable="false">
      <Dibujo />
    </svg>
  )
}
