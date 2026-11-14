// Acceso a datos de NASA POWER (https://power.larc.nasa.gov), que permite CORS.
//  - Lluvia diaria GPM IMERG (IMERG_PRECTOT, mm/día, malla 0,1° ≈ 10 km), 2015–2024.
//  - Humedad del suelo en raíces (GWETROOT, 0–1) y temperatura (T2M, °C) mensuales
//    de MERRA-2 (malla 0,5° × 0,625°).
// Las respuestas se guardan en localStorage por celda para no repetir la descarga.
// Si no hay conexión se usa un perfil de ejemplo y se marca `simulado: true`.

const BASE = 'https://power.larc.nasa.gov/api/temporal'
export const PERIODO = { inicio: 2015, fin: 2024 }
const VERSION_CACHE = 'v2'
const RELLENO = -999

const claveCache = (tipo, lat, lng) => `nasa:${VERSION_CACHE}:${tipo}:${lat.toFixed(2)}:${lng.toFixed(2)}`

function leerCache(clave) {
  try {
    const v = localStorage.getItem(clave)
    return v ? JSON.parse(v) : null
  } catch {
    return null
  }
}

function guardarCache(clave, valor) {
  try {
    localStorage.setItem(clave, JSON.stringify(valor))
  } catch {
    // Sin almacenamiento disponible: se vuelve a descargar la próxima vez.
  }
}

async function pedir(url, señal) {
  const r = await fetch(url, { signal: señal })
  if (!r.ok) throw new Error(`NASA POWER respondió ${r.status}`)
  const json = await r.json()
  return json.properties.parameter
}

// Devuelve { 2015: [12 totales mensuales en mm], ... } con null en meses sin datos.
async function lluviaMensual(lat, lng, señal) {
  const clave = claveCache('imerg', lat, lng)
  const guardado = leerCache(clave)
  if (guardado) return guardado

  const url =
    `${BASE}/daily/point?parameters=IMERG_PRECTOT&community=AG&format=JSON&time-standard=UTC` +
    `&latitude=${lat.toFixed(4)}&longitude=${lng.toFixed(4)}` +
    `&start=${PERIODO.inicio}0101&end=${PERIODO.fin}1231`
  const diario = (await pedir(url, señal)).IMERG_PRECTOT

  // Un dato ausente no es lo mismo que "no llovió": solo se suman días válidos y
  // se cuentan aparte los días válidos de cada mes.
  const suma = {}
  const validos = {}
  for (const [fecha, mm] of Object.entries(diario)) {
    const año = fecha.slice(0, 4)
    const mes = Number(fecha.slice(4, 6)) - 1
    suma[año] ??= Array(12).fill(0)
    validos[año] ??= Array(12).fill(0)
    if (mm == null || mm === RELLENO || mm < 0) continue
    suma[año][mes] += mm
    validos[año][mes]++
  }
  // Los días que no vienen en la respuesta también son faltantes. Un mes con más
  // de 5 días sin dato se marca null en vez de sumarlo incompleto.
  const porAño = {}
  for (let año = PERIODO.inicio; año <= PERIODO.fin; año++) {
    porAño[año] = Array.from({ length: 12 }, (_, mes) => {
      const diasDelMes = new Date(Date.UTC(año, mes + 1, 0)).getUTCDate()
      const ok = validos[año]?.[mes] ?? 0
      return diasDelMes - ok > 5 ? null : Math.round(suma[año][mes])
    })
  }
  guardarCache(clave, porAño)
  return porAño
}

// Devuelve { humedad: {2015: [12]}, temperatura: {2015: [12]} }
async function climaMensual(lat, lng, señal) {
  const clave = claveCache('merra2', lat, lng)
  const guardado = leerCache(clave)
  if (guardado) return guardado

  const url =
    `${BASE}/monthly/point?parameters=GWETROOT,T2M&community=AG&format=JSON` +
    `&latitude=${lat.toFixed(4)}&longitude=${lng.toFixed(4)}` +
    `&start=${PERIODO.inicio}&end=${PERIODO.fin}`
  const p = await pedir(url, señal)

  const agrupar = (serie) => {
    const out = {}
    for (const [clave, v] of Object.entries(serie)) {
      const mes = Number(clave.slice(4, 6))
      if (mes === 13) continue // el mes 13 es el promedio anual
      const año = clave.slice(0, 4)
      out[año] ??= Array(12).fill(null)
      out[año][mes - 1] = v == null || v === RELLENO ? null : v
    }
    return out
  }
  const resultado = { humedad: agrupar(p.GWETROOT), temperatura: agrupar(p.T2M) }
  guardarCache(clave, resultado)
  return resultado
}

// Perfil de ejemplo (valle interandino) para cuando no hay conexión.
function datosDeEjemplo() {
  const lluviaBase = [150, 140, 190, 180, 110, 55, 35, 25, 60, 110, 125, 120]
  const humedadBase = [0.78, 0.8, 0.82, 0.84, 0.83, 0.8, 0.77, 0.74, 0.72, 0.73, 0.76, 0.77]
  const tempBase = [10.6, 10.7, 10.6, 10.6, 10.3, 9.1, 8.9, 9.1, 9.7, 10.5, 10.7, 10.5]
  const lluvia = {}
  const humedad = {}
  const temperatura = {}
  for (let año = PERIODO.inicio; año <= PERIODO.fin; año++) {
    const k = año - PERIODO.inicio
    lluvia[año] = lluviaBase.map((v, m) => Math.max(0, Math.round(v * (1 + 0.45 * Math.sin(k * 2.3 + m * 1.7)))))
    humedad[año] = humedadBase.map((v, m) => +(v + 0.04 * Math.sin(k * 1.9 + m)).toFixed(2))
    temperatura[año] = tempBase.map((v, m) => +(v + 0.5 * Math.sin(k + m * 0.8)).toFixed(1))
  }
  return { lluvia, humedad, temperatura }
}

// Con mala señal en el campo la petición puede quedar colgada: pasado este
// tiempo se cancela y se muestran datos de ejemplo con opción de reintentar.
const TIEMPO_MAXIMO = 25000

export async function obtenerDatosNasa({ lat, lng }, señal) {
  const control = new AbortController()
  const reloj = setTimeout(() => control.abort(), TIEMPO_MAXIMO)
  const reenviar = () => control.abort()
  señal?.addEventListener('abort', reenviar, { once: true })
  try {
    const [lluvia, clima] = await Promise.all([
      lluviaMensual(lat, lng, control.signal),
      climaMensual(lat, lng, control.signal),
    ])
    return { lluvia, ...clima, simulado: false }
  } catch (error) {
    // Cancelado desde fuera (la pantalla se cerró): no hay nada que mostrar.
    if (señal?.aborted) throw error
    const motivo = control.signal.aborted ? 'La NASA tardó demasiado en responder' : error.message
    return { ...datosDeEjemplo(), simulado: true, error: motivo }
  } finally {
    clearTimeout(reloj)
    señal?.removeEventListener('abort', reenviar)
  }
}
