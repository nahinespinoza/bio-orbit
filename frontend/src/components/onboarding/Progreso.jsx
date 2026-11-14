export default function Progreso({ paso, total = 2 }) {
  return (
    <div className="onb-progreso">
      <span className="onb-progreso-texto">
        Paso {paso} de {total}
      </span>
      <div
        className="onb-progreso-barra"
        role="progressbar"
        aria-valuemin={1}
        aria-valuemax={total}
        aria-valuenow={paso}
        aria-label={`Paso ${paso} de ${total}`}
      >
        {Array.from({ length: total }, (_, i) => (
          <span key={i} className={i < paso ? 'activo' : ''} />
        ))}
      </div>
    </div>
  )
}
