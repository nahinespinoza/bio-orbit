// Check con trazo animado, halo y destellos para las pantallas de confirmación.
export default function CheckAnimado() {
  return (
    <div className="fg-check-wrap" aria-hidden="true">
      <span className="fg-check-halo" />
      {Array.from({ length: 8 }, (_, i) => (
        <span key={i} className="fg-chispa" style={{ '--angulo': `${i * 45}deg` }} />
      ))}
      <svg className="fg-check" viewBox="0 0 96 96">
        <circle className="fg-check-circulo" cx="48" cy="48" r="44" pathLength="1" />
        <path className="fg-check-marca" d="M29 50 l13 13 l25 -28" pathLength="1" />
      </svg>
    </div>
  )
}
