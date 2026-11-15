// La misma ruta funciona con el proxy de Vite y con el proxy Nginx de Compose (proxy/).
const API = '/api'
// /v1/recommendations hace una llamada al modelo de lenguaje (~20 s): tarda más que el catálogo.
const LIMITE_MS = 60000

export const PRIORIDADES = [
  { id: 'market_value', nombre: 'Valor de venta', detalle: 'Priorizar el mercado' },
  { id: 'speed', nombre: 'Cosechar antes', detalle: 'Un ciclo más corto' },
  { id: 'fewer_pests', nombre: 'Menos plagas', detalle: 'Cuidar el próximo cultivo' },
  { id: 'low_labor', nombre: 'Menos trabajo', detalle: 'Reducir la mano de obra' },
]

export const RIEGOS = [
  { id: 'rain_only', nombre: 'Solo lluvia' },
  { id: 'pump', nombre: 'Bomba' },
  { id: 'canal', nombre: 'Acequia o canal' },
  { id: 'sprinkler_drip', nombre: 'Aspersión o goteo' },
  { id: 'manual', nombre: 'Manual (regadera o manguera)' },
]

export const ENCHARCAMIENTOS = [
  { id: 'no', nombre: 'No, se absorbe rápido' },
  { id: 'briefly', nombre: 'Solo por un rato' },
  { id: 'long', nombre: 'Sí, por mucho tiempo' },
]

// El servicio devuelve la confianza en español.
export const CONFIANZA = { alta: 'Alta', media: 'Media', baja: 'Baja' }

export function crearSolicitud(datos) {
  return {
    previous_crop: datos.cultivo,
    priority: datos.prioridad,
    irrigation: datos.riego,
    waterlogging: datos.drenaje,
  }
}

async function consultar(ruta, { signal, ...opciones } = {}) {
  const control = new AbortController()
  const cancelar = () => control.abort()
  signal?.addEventListener('abort', cancelar, { once: true })
  if (signal?.aborted) control.abort()
  const limite = setTimeout(cancelar, LIMITE_MS)
  try {
    const respuesta = await fetch(`${API}${ruta}`, { ...opciones, signal: control.signal })
    const contenido = respuesta.headers.get('content-type') ?? ''
    if (!contenido.includes('application/json')) throw new Error('El servicio de Pitágoras no está disponible. Intenta de nuevo en un momento.')
    const datos = await respuesta.json()
    if (!respuesta.ok) {
      const errores = datos.errors?.map((e) => e.message).join(' ') || datos.detail?.message
      throw new Error(errores || 'No pudimos consultar a Pitágoras. Revisa tu conexión e inténtalo de nuevo.')
    }
    return datos
  } catch (error) {
    if (signal?.aborted) throw error
    if (error.name === 'AbortError') throw new Error('Pitágoras está tardando en responder. Inténtalo de nuevo.')
    if (error instanceof TypeError) throw new Error('No pudimos conectar con Pitágoras. Revisa tu conexión e inténtalo de nuevo.')
    throw error
  } finally {
    clearTimeout(limite)
    signal?.removeEventListener('abort', cancelar)
  }
}

export async function obtenerCultivos(signal) {
  const datos = await consultar('/v1/crops', { signal })
  if (!Array.isArray(datos) || !datos.length || datos.some((c) => !c.crop_id || !c.name)) {
    throw new Error('No se pudo cargar la lista de cultivos. Inténtalo de nuevo.')
  }
  return datos
}

export async function recomendarCultivos(datos, signal) {
  const resultado = await consultar('/v1/recommendations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(crearSolicitud(datos)),
    signal,
  })
  if (resultado.status === 'no_candidates') return resultado
  if (resultado.status !== 'ok' || !resultado.recommendation?.name || !Number.isFinite(resultado.recommendation.affinity)) {
    throw new Error('La recomendación llegó incompleta. Inténtalo de nuevo.')
  }
  return resultado
}

// El servicio evalúa siempre la captura de Toacaso (remote-sensing). Sus alertas
// no se atribuyen a una finca que no está monitoreada.
export function alertasDeParcela(cultivo, monitoreada) {
  return monitoreada ? cultivo.advisories ?? [] : []
}

export function referenciasDe(resultado, ids = []) {
  const fuentes = resultado.sources ?? []
  return ids.map((id) => fuentes.find((f) => f.id === id)).filter(Boolean)
}

export function textoAdvertencia(texto) {
  return texto
    .replace('Datos faltantes que se puntuaron como neutros:', 'Sin datos (valor neutro):')
    .replaceAll('fewer_pests', 'plagas').replaceAll('market_value', 'mercado')
    .replaceAll('low_labor', 'mano de obra').replaceAll('speed', 'duración del cultivo')
    .replaceAll('aptitude', 'adaptación al terreno')
    .replace('que cumpla F1 y F2 con el grafo', 'compatible con las reglas de rotación')
    .replace('un cultivo «ender»', 'un cultivo de cierre')
}

export function agruparDescartes(descartados = [], cultivos = []) {
  const grupos = new Map()
  for (const descarte of descartados) {
    const motivo = descarte.filter === 'F4-climate' && descarte.reason.startsWith('Altitud ')
      ? 'Fuera del rango de altura del cultivo.'
      : descarte.filter === 'NON_COMMERCIAL_RULE'
        ? 'Sin mercado; solo con suelo pobre o compactado, o tras dos ciclos muy exigentes.'
        : descarte.reason === 'No se repite el mismo cultivo en el mismo lote.'
          ? 'No repetir en el mismo lote.'
          : textoAdvertencia(descarte.reason)
    const nombre = cultivos.find((c) => c.crop_id === descarte.crop)?.name ?? descarte.crop
    const nombres = grupos.get(motivo) ?? []
    nombres.push(nombre)
    grupos.set(motivo, nombres)
  }
  return Array.from(grupos, ([motivo, nombres]) => ({ motivo, nombres }))
}
