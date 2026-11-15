// Adaptador del reporte semanal: es el único archivo que conoce la forma de
// `resultado_match.json` (cruce de NASA POWER con Sentinel-2 que entrega el
// equipo de datos) y lo convierte al modelo que usa la interfaz.
//
// Reglas: no se inventan textos ni se recalculan semáforos. Los estados salen
// del JSON; las etiquetas cortas, de las tablas de abajo.
import datosFijos from '../datos/resultado_match.json'
import urlVigor from '../datos/capas/vigor_20261027.png'
import urlHumedad from '../datos/capas/humedad_20261027.png'
import { perimetroM } from '../components/flujo-gps/geo.js'

// El color nunca va solo: siempre se muestra con su texto.
export const NIVELES = {
  bien: { color: '#16a34a', nombre: 'Bien' },
  atencion: { color: '#facc15', nombre: 'Atención' },
  problema: { color: '#b91c1c', nombre: 'Problema' },
  exceso: { color: '#1d4ed8', nombre: 'Mucha agua' },
  sin_dato: { color: '#9ca3af', nombre: 'Sin dato' },
}

// De más grave a menos grave
const GRAVEDAD = ['problema', 'exceso', 'atencion', 'bien', 'sin_dato']
const masGrave = (a, b) => (GRAVEDAD.indexOf(a) <= GRAVEDAD.indexOf(b) ? a : b)

const NIVEL_DE_COLOR = { verde: 'bien', amarillo: 'atencion', rojo: 'problema', azul: 'exceso', gris: 'sin_dato' }
const nivelDeColor = (color) => NIVEL_DE_COLOR[color?.toLowerCase()] ?? 'sin_dato'

// Cada cruce pertenece a un tema; si hay un cruce del tema de un indicador, manda el cruce.
const CRUCES = {
  NUTRICION_PROBABLE: { tema: 'salud', texto: 'Faltan nutrientes' },
  VIGOR_BAJO_POR_CLIMA: { tema: 'salud', texto: 'Vigor bajo por el clima' },
  RIEGO_CONFIRMADO: { tema: 'agua', texto: 'Falta agua' },
  RIEGO_PREVENTIVO: { tema: 'agua', texto: 'Riesgo de sequía' },
  HUMEDAD_DISCREPANTE: { tema: 'agua', texto: 'Revisa en campo' },
  EXCESO_AGUA_CONFIRMADO: { tema: 'agua', texto: 'Exceso de agua' },
  EXCESO_AGUA_PREVENTIVO: { tema: 'agua', texto: 'Riesgo de exceso de agua' },
  DANO_HELADA_CONFIRMADO: { tema: 'helada', texto: 'Daño por helada' },
  HELADA_SIN_DANO: { tema: 'helada', texto: 'Helada sin daño' },
  ESTRES_CALOR_CONFIRMADO: { tema: 'calor', texto: 'Estrés por calor' },
  LANCHA_CONFIRMADA: { tema: 'lancha', texto: 'Lancha confirmada' },
  LANCHA_PREVENTIVA: { tema: 'lancha', texto: 'Riesgo de lancha' },
}

// Alertas del mes que viene (NASA POWER)
const ALERTAS = {
  PLAGAS_LANCHA: { titulo: 'Lancha', subtitulo: 'tizón tardío', ilustracion: 'lancha' },
  SEQUIA: { titulo: 'Sequía', subtitulo: '', ilustracion: 'calor' },
  HELADAS: { titulo: 'Heladas', subtitulo: '', ilustracion: 'helada' },
  NUTRIENTES: { titulo: 'Lavado de nutrientes', subtitulo: '', ilustracion: 'hoja' },
}
const RIESGO = { ALTO: 'Riesgo alto', MEDIO: 'Riesgo medio', BAJO: 'Riesgo bajo' }
const PESO_NIVEL_CRUCE = { ALTO: 0, MEDIO: 1, BAJO: 2 }

const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
const MESES_CORTOS = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']

// ---------- Formatos ----------

const conMayuscula = (t) => t.charAt(0).toLocaleUpperCase('es') + t.slice(1)

const decimal = (n) => n.toLocaleString('es', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
const entero = (n) => Math.round(n).toLocaleString('es')

// 'dd/mm/aaaa' o 'aaaa-mm-dd' → Date local (sin el desfase de zona horaria de `new Date('aaaa-mm-dd')`)
function leerFecha(texto) {
  if (!texto) return null
  const partes = texto.split(/[/-]/).map(Number)
  const [a, m, d] = texto.includes('/') ? [partes[2], partes[1], partes[0]] : partes
  if (!a || !m || !d) return null
  return new Date(a, m - 1, d)
}

const diaMes = (f) => `${f.getDate()} de ${MESES[f.getMonth()]}`
const diaCorto = (f) => `${f.getDate()} ${MESES_CORTOS[f.getMonth()]}`

// «Del 21 al 27 de octubre» · «Del 28 de octubre al 3 de noviembre»
function periodo(inicio, fin) {
  const a = leerFecha(inicio)
  const b = leerFecha(fin)
  if (!a || !b) return null
  if (a.getMonth() === b.getMonth()) return `Del ${a.getDate()} al ${diaMes(b)}`
  return `Del ${diaMes(a)} al ${diaMes(b)}`
}

// ---------- Semáforos y cruces ----------

// «PRECAUCIÓN - Madrugadas Frías» → «Madrugadas frías»
function textoEstado(estado) {
  if (!estado) return null
  const despues = estado.includes(' - ') ? estado.split(' - ').slice(1).join(' - ') : estado
  return conMayuscula(despues.trim().toLocaleLowerCase('es'))
}

function leerSemaforo(s) {
  if (!s) return null
  return { nivel: nivelDeColor(s.color), texto: textoEstado(s.estado), mensaje: s.mensaje ?? null }
}

const nivelDeCruce = (c) => (c.confirmada && c.nivel === 'ALTO' ? 'problema' : 'atencion')

function leerCruce(c) {
  const conocido = CRUCES[c.codigo]
  return {
    codigo: c.codigo,
    tema: conocido?.tema ?? null,
    texto: conocido?.texto ?? c.titulo ?? null,
    nivel: nivelDeCruce(c),
    confirmada: Boolean(c.confirmada),
    riesgo: RIESGO[c.nivel] ?? null,
    peso: PESO_NIVEL_CRUCE[c.nivel] ?? 3,
    mensaje: c.mensaje ?? null,
  }
}

// Si hay varios cruces de un tema: primero el confirmado, luego el de nivel más alto.
function cruceDelTema(cruces, tema) {
  return cruces
    .filter((c) => c.tema === tema)
    .sort((a, b) => Number(b.confirmada) - Number(a.confirmada) || a.peso - b.peso)[0] ?? null
}

// ---------- Modelo ----------

export function normalizarReporte(json) {
  const o = json?.output
  const c = o?.cruce_ultima_captura
  const clima = c?.clima_nasa_alineado
  const s2 = o?.parcela_sentinel2
  const semana = clima?.estado_actual_7d
  const lote = s2?.estado_actual_lote
  const reparto = lote?.distribucion_parcela_pct

  const cruces = (c?.cruces_evaluados ?? []).filter((x) => x?.codigo).map(leerCruce)
  const foto = leerFecha(s2?.fecha_ultima_captura)

  const sem = {
    helada: leerSemaforo(clima?.semaforos?.estado_helada),
    riego: leerSemaforo(clima?.semaforos?.estado_riego),
    calor: leerSemaforo(clima?.semaforos?.estado_estres_calor),
    vigor: leerSemaforo(s2?.semaforos?.estado_vigor),
    humedad: leerSemaforo(s2?.semaforos?.estado_humedad_parcela),
  }

  // Agua: el peor entre el suelo de la zona (NASA) y las hojas de la parcela (Sentinel-2)
  const aguaBase = [sem.riego, sem.humedad]
    .filter(Boolean)
    .sort((a, b) => GRAVEDAD.indexOf(a.nivel) - GRAVEDAD.indexOf(b.nivel))[0] ?? null

  // Estado y mensaje de un indicador: manda el cruce de su tema si existe
  const estadoDe = (tema, base) => {
    const cruce = tema ? cruceDelTema(cruces, tema) : null
    if (cruce) return { estado: { nivel: cruce.nivel, texto: cruce.texto }, mensaje: cruce.mensaje }
    if (base) return { estado: { nivel: base.nivel, texto: base.texto }, mensaje: base.mensaje }
    return { estado: null, mensaje: null }
  }

  const historial = (campo) =>
    (o?.historial_cruces ?? [])
      .map((h) => {
        const f = leerFecha(h?.fecha_captura)
        return f ? { dia: diaCorto(f), nivel: nivelDeColor(h?.sentinel2?.[campo]) } : null
      })
      .filter(Boolean)

  const tempMin = semana?.temp_min_semana_parcela ?? semana?.temp_min_semana
  const tempMax = semana?.temp_max_semana_parcela ?? semana?.temp_max_semana

  const candidatos = [
    reparto?.sano != null && {
      id: 'salud', grupo: 'parcela', titulo: 'Salud del cultivo', tono: 'verde', ilustracion: 'hoja',
      valor: entero(reparto.sano), unidad: '%', etiqueta: 'de la parcela se ve sana',
      ...estadoDe('salud', sem.vigor),
      partes: [
        { etiqueta: 'Sana', texto: `${entero(reparto.sano)} %`, nivel: 'bien' },
        reparto.alerta != null && { etiqueta: 'En alerta', texto: `${entero(reparto.alerta)} %`, nivel: 'atencion' },
        reparto.critico != null && { etiqueta: 'Crítica', texto: `${entero(reparto.critico)} %`, nivel: 'problema' },
        reparto.suelo_desnudo > 0 && { etiqueta: 'Sin cultivo', texto: `${entero(reparto.suelo_desnudo)} %`, nivel: 'sin_dato' },
        lote?.sector_mas_afectado && { etiqueta: 'Sector más afectado', texto: conMayuscula(lote.sector_mas_afectado), nivel: null },
      ].filter(Boolean),
      historial: historial('vigor'),
    },
    semana?.humedad_raiz_pct != null && {
      id: 'agua', grupo: 'parcela', titulo: 'Agua', tono: 'tierra', ilustracion: 'suelo',
      valor: entero(semana.humedad_raiz_pct), unidad: '%', etiqueta: 'humedad en las raíces',
      ...estadoDe('agua', aguaBase),
      partes: [
        sem.riego && { etiqueta: 'En el suelo (zona)', texto: sem.riego.texto, nivel: sem.riego.nivel },
        sem.humedad && { etiqueta: 'En las hojas (tu parcela)', texto: sem.humedad.texto, nivel: sem.humedad.nivel },
      ].filter(Boolean),
      historial: historial('humedad'),
    },
    tempMin != null && {
      id: 'helada', grupo: 'clima', titulo: 'Heladas', tono: 'noche', ilustracion: 'helada',
      valor: decimal(tempMin), unidad: '°C', etiqueta: 'la noche más fría',
      ...estadoDe('helada', sem.helada), partes: [], historial: [],
    },
    tempMax != null && {
      id: 'calor', grupo: 'clima', titulo: 'Calor', tono: 'fuego', ilustracion: 'calor',
      valor: decimal(tempMax), unidad: '°C', etiqueta: 'el día más caliente',
      ...estadoDe('calor', sem.calor), partes: [], historial: [],
    },
    semana?.lluvia_7d != null && {
      id: 'lluvia', grupo: 'clima', titulo: 'Lluvia', tono: 'azul', ilustracion: 'lluvia',
      valor: decimal(semana.lluvia_7d), unidad: 'mm', etiqueta: 'llovió en la semana',
      estado: null, mensaje: null, partes: [], historial: [],
    },
    semana?.humedad_relativa_pct != null && {
      id: 'aire', grupo: 'clima', titulo: 'Humedad del aire', tono: 'turquesa', ilustracion: 'aire',
      valor: entero(semana.humedad_relativa_pct), unidad: '%', etiqueta: 'humedad en el aire',
      estado: null, mensaje: null, partes: [], historial: [],
    },
  ]
  const indicadores = candidatos.filter(Boolean)

  // Alerta principal: la alerta cruzada confirmada (puede no haber)
  const principal = o?.alerta_cruzada_confirmada?.codigo ? leerCruce(o.alerta_cruzada_confirmada) : null
  const alertaPrincipal = principal && {
    texto: principal.texto,
    nivel: principal.nivel,
    confirmada: principal.confirmada,
    mensaje: principal.mensaje,
    // Panel que abre (solo si hay un indicador de ese tema)
    indicadorId: indicadores.some((i) => i.id === principal.tema) ? principal.tema : null,
  }

  // Alertas del mes: lo que ya cubre un cruce de salud (lavado de nutrientes) se quita,
  // y la lancha toma los datos del cruce de lancha si existe.
  const hayCruceSalud = cruces.some((x) => x.tema === 'salud')
  const cruceLancha = cruceDelTema(cruces, 'lancha')
  const alertas = (clima?.alertas_preventivas ?? [])
    .filter((a) => a?.codigo && !(a.codigo === 'NUTRIENTES' && hayCruceSalud))
    .map((a) => {
      const tabla = ALERTAS[a.codigo]
      const base = {
        id: a.codigo,
        titulo: tabla?.titulo ?? a.titulo,
        subtitulo: tabla?.subtitulo ?? '',
        ilustracion: tabla?.ilustracion ?? 'hoja',
      }
      if (a.codigo === 'PLAGAS_LANCHA' && cruceLancha) {
        return {
          ...base,
          // Con daño confirmado se dice; si no, queda el nivel de riesgo
          riesgo: cruceLancha.confirmada ? cruceLancha.texto : (cruceLancha.riesgo ?? RIESGO[a.nivel]),
          nivel: cruceLancha.nivel,
          mensaje: cruceLancha.mensaje,
        }
      }
      return { ...base, riesgo: RIESGO[a.nivel] ?? null, nivel: 'atencion', mensaje: a.mensaje ?? null }
    })

  return {
    zona: o?.zona ?? null,
    periodoClima: periodo(clima?.fecha_inicio, clima?.fecha_fin),
    fotoFecha: foto ? `Foto del ${diaMes(foto)}` : null,
    fotoDias: s2?.dias_desde_ultima_foto ?? null,
    alertaPrincipal,
    indicadores,
    alertas,
    mesAlertas: clima?.mes_proyectado?.toLocaleLowerCase('es') ?? null,
  }
}

// Nivel más grave entre los indicadores con estado
export function peorNivel(reporte) {
  const niveles = (reporte?.indicadores ?? []).map((i) => i.estado?.nivel).filter(Boolean)
  const reales = niveles.filter((n) => n !== 'sin_dato')
  return reales.length ? reales.reduce(masGrave) : 'sin_dato'
}

// La parcela de Toacaso del JSON, lista para la lista de fincas de App
export function fincaPreanalizada() {
  const ubicacion = datosFijos.input?.sentinel2?.ubicacion
  const anillo = ubicacion?.poligono_geojson?.features?.[0]?.geometry?.coordinates?.[0] ?? []
  // GeoJSON viene como [lng, lat] y repite el primer punto al final
  const poligono = anillo.map(([lng, lat]) => [lat, lng])
  const [primero, ultimo] = [poligono[0], poligono.at(-1)]
  if (poligono.length > 1 && primero[0] === ultimo[0] && primero[1] === ultimo[1]) poligono.pop()

  return {
    id: 'finca-toacaso',
    nombre: 'Toacaso',
    preanalizada: true,
    ubicacion: { lat: ubicacion?.latitud, lng: ubicacion?.longitud, precision: null },
    parcelas: [{ poligono, area: ubicacion?.area_ha, perimetro: perimetroM(poligono) }],
    analisis: null,
    reporte: {
      ...normalizarReporte(datosFijos),
      ejemplo: false,
      capas: {
        vigor: urlVigor,
        humedad: urlHumedad,
        limites: datosFijos.output?.parcela_sentinel2?.capas_visuales?.bounds_latlon ?? null,
      },
    },
  }
}

// ---------- Conexión con el backend ----------

const URL_BACKEND = import.meta.env.VITE_BACKEND_URL?.replace(/\/+$/, '')
const TIEMPO_MAXIMO = 6000

// Lee el cruce del backend (`GET /parcelas/1/match`); si no hay URL configurada,
// tarda o falla (hoy falla por CORS), usa la copia fija. Nunca muestra un error.
async function leerMatch(señal) {
  if (!URL_BACKEND) return datosFijos
  const control = new AbortController()
  const reloj = setTimeout(() => control.abort(), TIEMPO_MAXIMO)
  const reenviar = () => control.abort()
  señal?.addEventListener('abort', reenviar, { once: true })
  try {
    const r = await fetch(`${URL_BACKEND}/parcelas/1/match`, { signal: control.signal })
    if (!r.ok) throw new Error(`El backend respondió ${r.status}`)
    const json = await r.json()
    if (!json?.output) throw new Error('Respuesta sin `output`')
    return json
  } catch (error) {
    // Cancelado desde fuera (la pantalla se cerró): no hay nada que mostrar.
    if (señal?.aborted) throw error
    return datosFijos
  } finally {
    clearTimeout(reloj)
    señal?.removeEventListener('abort', reenviar)
  }
}

function esperar(ms, señal) {
  return new Promise((listo, fallo) => {
    if (señal?.aborted) {
      fallo(señal.reason)
      return
    }
    const cancelar = () => {
      clearTimeout(id)
      fallo(señal.reason)
    }
    const id = setTimeout(() => {
      señal?.removeEventListener('abort', cancelar)
      listo()
    }, ms)
    señal?.addEventListener('abort', cancelar, { once: true })
  })
}

// Reporte de una finca registrada por el usuario. Hoy el backend solo tiene la
// parcela de Toacaso, así que se muestran esos datos marcados como «Datos de ejemplo».
// Aquí irá la llamada a la API con el polígono de `finca` cuando exista.
export async function obtenerReporte(_finca, señal) {
  const [json] = await Promise.all([leerMatch(señal), esperar(1800, señal)])
  return { ...normalizarReporte(json), ejemplo: true, capas: null }
}

// Lo que abre el panel especializado: un indicador o una alerta del mes con la misma forma
export function detalleDe(reporte, id) {
  const indicador = reporte?.indicadores.find((i) => i.id === id)
  if (indicador) return indicador
  const a = reporte?.alertas.find((x) => x.id === id)
  if (!a) return null
  return {
    id: a.id, grupo: 'alerta', titulo: reporte.mesAlertas ? `Para ${reporte.mesAlertas}` : a.titulo,
    tono: 'ocre', ilustracion: a.ilustracion, valor: a.titulo, unidad: null, etiqueta: a.subtitulo,
    estado: a.riesgo ? { nivel: a.nivel, texto: a.riesgo } : null, mensaje: a.mensaje, partes: [], historial: [],
  }
}
