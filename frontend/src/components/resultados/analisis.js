// Motor de análisis del panel de resultados. Todo lo "difícil" ocurre aquí para
// que la interfaz solo muestre conclusiones en lenguaje sencillo.
//
//  · Lluvia y humedad: datos reales de NASA POWER (ver src/lib/nasa.js).
//  · Mapa de salud por zonas: SIMULADO a partir de la forma de la parcela, a la
//    espera de conectar índices de vegetación HLS (Landsat + Sentinel-2, 30 m).
//  · Rotaciones: reglas transparentes cruzando el calendario de cada cultivo
//    con la lluvia histórica. El umbral de cada cultivo aproxima lo que consume
//    en su etapa delicada (ETc de referencia FAO, ~3–5 mm/día). Fechas y umbrales son de referencia (INIAP / UCE,
//    valle de Tumbaco) y deben validarse con un técnico local.

import { PERIODO } from '../../lib/nasa.js'

export const MESES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
export const MESES_LARGOS = [
  'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
  'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
]

// Paleta de estado (reservada: nunca se usa para series).
export const ESTADOS = {
  bien: { nombre: 'Bien', color: '#0ca30c', peso: 100 },
  atencion: { nombre: 'Atención', color: '#fab219', peso: 65 },
  problema: { nombre: 'Problema', color: '#ec835a', peso: 35 },
  grave: { nombre: 'Grave', color: '#d03b3b', peso: 10 },
}
export const ORDEN_ESTADOS = ['bien', 'atencion', 'problema', 'grave']

export const estadoDePuntaje = (p) => (p >= 75 ? 'bien' : p >= 55 ? 'atencion' : p >= 35 ? 'problema' : 'grave')

// ---------------------------------------------------------------------------
// Utilidades
// ---------------------------------------------------------------------------

const limitar = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v))

function cuantil(ordenados, q) {
  if (!ordenados.length) return null
  const pos = (ordenados.length - 1) * q
  const base = Math.floor(pos)
  const resto = pos - base
  const sig = ordenados[base + 1] ?? ordenados[base]
  return ordenados[base] + resto * (sig - ordenados[base])
}

// Generador pseudoaleatorio con semilla: la misma finca da siempre el mismo resultado.
function aleatorio(semilla) {
  let a = semilla >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

const semillaDe = (lat, lng) => Math.abs(Math.round(lat * 1e5) * 73856093 ^ Math.round(lng * 1e5) * 19349663)

function dentroDe([lat, lng], poligono) {
  let dentro = false
  for (let i = 0, j = poligono.length - 1; i < poligono.length; j = i++) {
    const [yi, xi] = poligono[i]
    const [yj, xj] = poligono[j]
    if (yi > lat !== yj > lat && lng < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) dentro = !dentro
  }
  return dentro
}

const DIRECCIONES = ['norte', 'noreste', 'este', 'sureste', 'sur', 'suroeste', 'oeste', 'noroeste']

function direccion(dx, dy) {
  if (Math.hypot(dx, dy) < 0.18) return 'centro'
  const grados = (Math.atan2(dx, dy) * 180) / Math.PI
  return DIRECCIONES[Math.round(((grados + 360) % 360) / 45) % 8]
}

// Mínimo de años con dato para hablar de "lo normal" en un mes.
export const MIN_AÑOS = 5

export const listaTexto = (items) =>
  items.length <= 1 ? items.join('') : `${items.slice(0, -1).join(', ')} y ${items[items.length - 1]}`

export const textoZona = (dir) => (dir === 'centro' ? 'el centro' : `la parte ${dir}`)

// "jun – sep" a partir de una lista de índices de mes (admite cruce de año).
function rangoMeses(indices) {
  if (!indices.length) return null
  const set = new Set(indices)
  let inicio = indices[0]
  while (set.has((inicio + 11) % 12) && (inicio + 11) % 12 !== indices[0]) inicio = (inicio + 11) % 12
  let fin = inicio
  while (set.has((fin + 1) % 12) && (fin + 1) % 12 !== inicio) fin = (fin + 1) % 12
  return inicio === fin ? MESES_LARGOS[inicio] : `${MESES_LARGOS[inicio]} a ${MESES_LARGOS[fin]}`
}

// ---------------------------------------------------------------------------
// Lluvia (GPM IMERG)
// ---------------------------------------------------------------------------

export function resumenLluvia(lluvia) {
  const años = Object.keys(lluvia).sort()
  const meses = MESES.map((_, m) => {
    const valores = años.map((a) => lluvia[a][m]).filter((v) => v != null)
    const ord = [...valores].sort((a, b) => a - b)
    // Un mes sin suficientes años válidos queda en null ("sin datos"), nunca en 0 mm.
    const suficiente = ord.length >= MIN_AÑOS
    const redondo = (q) => (suficiente ? Math.round(cuantil(ord, q)) : null)
    return {
      mes: m,
      valores,
      n: valores.length,
      mediana: redondo(0.5),
      p20: redondo(0.2),
      p80: redondo(0.8),
      min: suficiente ? ord[0] : null,
      max: suficiente ? ord[ord.length - 1] : null,
    }
  })
  const conDatos = meses.filter((m) => m.mediana != null)
  const totales = años
    .filter((a) => lluvia[a].length === 12 && lluvia[a].every((v) => v != null))
    .map((a) => ({ año: a, total: lluvia[a].reduce((s, v) => s + v, 0) }))
  const anual = totales.length ? Math.round(totales.reduce((s, t) => s + t.total, 0) / totales.length) : null
  const promedioMes = conDatos.length ? conDatos.reduce((s, m) => s + m.mediana, 0) / conDatos.length : null
  // La época seca solo se describe si los 12 meses tienen datos (si no, el rango podría mentir).
  const secos = conDatos.length === 12 ? conDatos.filter((m) => m.mediana < promedioMes * 0.6).map((m) => m.mes) : []
  const masSeco = conDatos.length ? conDatos.reduce((a, b) => (b.mediana < a.mediana ? b : a)) : null
  const masLluvioso = conDatos.length ? conDatos.reduce((a, b) => (b.mediana > a.mediana ? b : a)) : null
  const añoSeco = totales.length ? totales.reduce((a, b) => (b.total < a.total ? b : a)) : null

  return {
    meses,
    anual,
    promedioMes,
    años: años.length,
    añosCompletos: totales.length,
    mesesSinDatos: meses.filter((m) => m.mediana == null).map((m) => m.mes),
    masSeco,
    masLluvioso,
    temporadaSeca: rangoMeses(secos),
    añoSeco,
  }
}

// Mediana de una serie mensual {año: [12]} para un mes dado; null si no hay datos.
function medianaMes(series, mes) {
  const v = Object.values(series)
    .map((serie) => serie[mes])
    .filter((x) => x != null)
    .sort((a, b) => a - b)
  return cuantil(v, 0.5)
}

// ---------------------------------------------------------------------------
// Mapa de salud por zonas (simulado, ver nota al inicio)
// ---------------------------------------------------------------------------

const CLASIFICAR = {
  verdor: (v) => (v > 0.5 ? 'bien' : v > 0.36 ? 'atencion' : v > 0.24 ? 'problema' : 'grave'),
  humedad: (v) => (v > 0.45 ? 'bien' : v > 0.32 ? 'atencion' : v > 0.2 ? 'problema' : 'grave'),
}

export function zonasParcela(parcela, ubicacion, humedadMes) {
  const { poligono, area } = parcela
  const azar = aleatorio(semillaDe(ubicacion.lat, ubicacion.lng))
  const lats = poligono.map((p) => p[0])
  const lngs = poligono.map((p) => p[1])
  const [s, n, o, e] = [Math.min(...lats), Math.max(...lats), Math.min(...lngs), Math.max(...lngs)]

  const lado = Math.sqrt(area * 10000)
  const tam = limitar(lado / 15, 10, 30) // metros por celda (como un píxel de satélite)
  const cosLat = Math.cos((ubicacion.lat * Math.PI) / 180)
  const dLat = tam / 111320
  const dLng = tam / (111320 * cosLat)

  // Cada capa tiene su propio "foco" de problema para que el patrón sea coherente.
  const foco = () => ({ x: azar() * 1.2 - 0.6, y: azar() * 1.2 - 0.6, r: 0.25 + azar() * 0.2 })
  const focoVerdor = foco()
  const focoHumedad = foco()
  const fase = Array.from({ length: 6 }, () => azar() * Math.PI * 2)
  const pendiente = azar() * Math.PI * 2
  const ajusteHumedad = humedadMes == null ? 0 : (humedadMes - 0.65) * 0.8

  const celdas = []
  for (let lat = s; lat < n; lat += dLat) {
    for (let lng = o; lng < e; lng += dLng) {
      const centro = [lat + dLat / 2, lng + dLng / 2]
      if (!dentroDe(centro, poligono)) continue
      const x = ((centro[1] - o) / (e - o)) * 2 - 1
      const y = ((centro[0] - s) / (n - s)) * 2 - 1
      const ondas = (f) => 0.11 * Math.sin(x * 3.1 + fase[f]) * Math.cos(y * 2.7 + fase[f + 1])
      const golpe = (c) => Math.exp(-((x - c.x) ** 2 + (y - c.y) ** 2) / (2 * c.r * c.r))

      const verdor = 0.64 + ondas(0) + 0.06 * (azar() - 0.5) - 0.5 * golpe(focoVerdor)
      const humedad =
        0.5 + ajusteHumedad + ondas(2) + 0.08 * (x * Math.cos(pendiente) + y * Math.sin(pendiente)) +
        0.06 * (azar() - 0.5) - 0.32 * golpe(focoHumedad)

      celdas.push({
        limites: [[lat, lng], [lat + dLat, lng + dLng]],
        x,
        y,
        estado: { verdor: CLASIFICAR.verdor(verdor), humedad: CLASIFICAR.humedad(humedad) },
      })
    }
  }

  const resumir = (capa) => {
    const cuenta = Object.fromEntries(ORDEN_ESTADOS.map((k) => [k, 0]))
    celdas.forEach((c) => cuenta[c.estado[capa]]++)
    const total = celdas.length || 1
    const distribucion = ORDEN_ESTADOS.map((k) => ({
      estado: k,
      porcentaje: (cuenta[k] / total) * 100,
      hectareas: (cuenta[k] / total) * area,
    }))
    const malas = celdas.filter((c) => c.estado[capa] === 'problema' || c.estado[capa] === 'grave')
    const promedio = (k) => malas.reduce((s, c) => s + c[k], 0) / (malas.length || 1)
    const latMala = malas.reduce((acc, c) => acc + (c.limites[0][0] + c.limites[1][0]) / 2, 0) / (malas.length || 1)
    const lngMala = malas.reduce((acc, c) => acc + (c.limites[0][1] + c.limites[1][1]) / 2, 0) / (malas.length || 1)
    const puntaje = Math.round(distribucion.reduce((acc, d) => acc + (d.porcentaje / 100) * ESTADOS[d.estado].peso, 0))
    return {
      distribucion,
      puntaje,
      normal: distribucion[0].porcentaje,
      afectadas: malas.length ? {
        hectareas: (malas.length / total) * area,
        porcentaje: (malas.length / total) * 100,
        zona: direccion(promedio('x'), promedio('y')),
        centro: [latMala, lngMala],
      } : null,
    }
  }

  // `simulado` se apaga cuando las celdas vengan de imágenes reales (HLS / Sentinel-2).
  return { simulado: true, celdas, tamCelda: Math.round(tam), verdor: resumir('verdor'), humedad: resumir('humedad') }
}

// ---------------------------------------------------------------------------
// Rotaciones
// ---------------------------------------------------------------------------

// Campaña agrícola de octubre a septiembre (índice 0 = octubre).
// `sensible`: meses (desde la siembra) de la etapa más delicada al agua.
export const CULTIVOS = {
  maiz: {
    nombre: 'Maíz', color: '#eda100', inicio: 0, duracion: 8, sensible: [4, 5],
    etapa: 'floración', umbral: 150, leguminosa: false,
  },
  frejol: {
    nombre: 'Fréjol', color: '#e87ba4', inicio: 0, duracion: 4, sensible: [1, 2],
    etapa: 'floración', umbral: 110, leguminosa: true,
  },
  cebada: {
    nombre: 'Cebada', color: '#2a78d6', inicio: 3, duracion: 6, sensible: [2, 3],
    etapa: 'espigado', umbral: 100, leguminosa: false,
  },
}

export const PLANES = [
  { id: 'actual', nombre: 'Lo que haces hoy', secuencia: ['maiz', 'maiz', 'maiz', 'maiz'] },
  { id: 'alternar', nombre: 'Alternar con fréjol', secuencia: ['frejol', 'maiz', 'frejol', 'maiz'] },
  { id: 'cambiar', nombre: 'Cambiar de cultivos', secuencia: ['cebada', 'cebada', 'frejol', 'frejol'] },
]

const mesCalendario = (indiceCampaña) => (indiceCampaña + 9) % 12 // 0 → octubre

export const PREFERENCIAS_INICIALES = { riego: 'aveces', maiz: 'si', prioridad: 'suelo' }

const FACTOR_RIEGO = { si: 0.2, aveces: 0.6, no: 1 }

export function compararRotaciones(lluviaResumen, prefs) {
  const nAños = lluviaResumen.años

  // Fracción de años en que un mes recibió menos lluvia que el umbral del cultivo.
  const riesgoMes = (mes, umbral) => {
    const { valores, mediana } = lluviaResumen.meses[mes]
    if (mediana == null) return { secos: 0, total: 0 }
    return {
      secos: valores.filter((v) => v < umbral).length,
      total: valores.length,
    }
    // total === 0 → no hay datos de ese mes; el riesgo queda "desconocido", no en 0.
  }

  const planes = PLANES.map((plan) => {
    const meses = []
    const etapas = []
    plan.secuencia.forEach((id, ciclo) => {
      const c = CULTIVOS[id]
      for (let i = 0; i < 12; i++) {
        const desde = i - c.inicio
        const ocupado = desde >= 0 && desde < c.duracion
        const sensible = ocupado && c.sensible.includes(desde)
        let riesgo = 0
        if (sensible) {
          const r = riesgoMes(mesCalendario(i), c.umbral)
          riesgo = r.total ? (r.secos / r.total) * FACTOR_RIEGO[prefs.riego] : null
          etapas.push({ ciclo, cultivo: id, mes: mesCalendario(i), ...r, riesgo })
        }
        meses.push({ cultivo: ocupado ? id : null, mes: mesCalendario(i), sensible, riesgo })
      }
    })

    const cubiertos = meses.filter((m) => m.cultivo).length
    const descubiertos = meses.length - cubiertos
    const leguminosas = plan.secuencia.filter((id) => CULTIVOS[id].leguminosa).length
    const diversidad = new Set(plan.secuencia).size
    const repeticiones = plan.secuencia.filter((id, i) => i > 0 && plan.secuencia[i - 1] === id).length
    const ciclosMaiz = plan.secuencia.filter((id) => id === 'maiz').length

    const medidas = etapas.filter((e) => e.total > 0)
    const sinDatos = etapas.filter((e) => e.total === 0)
    const riesgoMedio = medidas.length ? medidas.reduce((s, e) => s + e.riesgo, 0) / medidas.length : null
    const puntajes = {
      suelo: Math.round(limitar(20 + 40 * (cubiertos / meses.length) + 12 * leguminosas + 8 * (diversidad - 1) - 5 * repeticiones, 0, 100)),
      // null = no hay lluvia registrada para sus etapas delicadas: no se puntúa.
      agua: riesgoMedio == null ? null : Math.round(100 * (1 - riesgoMedio)),
      plagas: Math.max(10, 100 - 30 * repeticiones),
    }
    const pesos = { suelo: 0.25, agua: 0.25, plagas: 0.25, [prefs.prioridad]: 0.5 }
    const claves = Object.keys(puntajes).filter((k) => puntajes[k] != null)
    const sumaPesos = claves.reduce((s, k) => s + pesos[k], 0)
    const total = Math.round(claves.reduce((s, k) => s + puntajes[k] * pesos[k], 0) / sumaPesos)
    const descartado = prefs.maiz === 'si' && ciclosMaiz === 0
      ? 'No incluye maíz y nos dijiste que lo necesitas.'
      : null

    // Etapa con más años secos (en bruto, sin riego) para explicarla.
    const peor = medidas.length ? medidas.reduce((a, b) => (b.secos / b.total > a.secos / a.total ? b : a)) : null

    const razones = []
    if (repeticiones === 0) razones.push({ tipo: 'bien', texto: 'Cambia de cultivo cada ciclo: corta el ciclo de plagas y enfermedades.' })
    else razones.push({ tipo: 'mal', texto: `Repite ${CULTIVOS[plan.secuencia.find((id, i) => plan.secuencia[i + 1] === id)].nombre.toLowerCase()} seguido: plagas y enfermedades se acumulan.` })
    if (leguminosas) razones.push({ tipo: 'bien', texto: 'El fréjol devuelve nitrógeno al suelo y ahorra abono.' })
    razones.push(
      descubiertos > 20
        ? { tipo: 'mal', texto: `El suelo queda sin plantas ${descubiertos} de 48 meses: más riesgo de erosión. Deja el rastrojo encima.` }
        : { tipo: 'bien', texto: `El suelo queda cubierto la mayor parte del tiempo (${cubiertos} de 48 meses).` },
    )
    if (peor) {
      const nombre = CULTIVOS[peor.cultivo]
      const fraccion = `${peor.secos} de ${peor.total} años`
      razones.push(
        peor.secos / peor.total >= 0.3
          ? { tipo: 'mal', fuente: true, texto: `La ${nombre.etapa} del ${nombre.nombre.toLowerCase()} cae en ${MESES_LARGOS[peor.mes]}: llovió menos de ${nombre.umbral} mm en ${fraccion}.` }
          : { tipo: 'bien', fuente: true, texto: peor.secos
            ? `${sinDatos.length ? 'En las etapas con datos' : 'Las etapas delicadas caen en meses lluviosos'}: faltó lluvia solo ${fraccion}.`
            : `${sinDatos.length ? 'En las etapas con datos' : 'Las etapas delicadas caen en meses lluviosos'}: no faltó lluvia en ${peor.total} años.` },
      )
    }
    if (sinDatos.length) {
      const nombresMes = listaTexto([...new Set(sinDatos.map((e) => MESES_LARGOS[e.mes]))])
      razones.push({ tipo: 'neutro', texto: `Faltan datos de lluvia de ${nombresMes}: no pudimos medir el riesgo de agua ahí.` })
    }
    if (prefs.maiz === 'si' && ciclosMaiz > 0 && ciclosMaiz < 4) {
      razones.push({ tipo: 'neutro', texto: `Cosechas maíz ${ciclosMaiz} de cada 4 años.` })
    }

    return { ...plan, meses, etapas, puntajes, total, descartado, razones, descubiertos, cubiertos }
  })

  const candidatos = planes.filter((p) => !p.descartado)
  const recomendado = candidatos.reduce((a, b) => (b.total > a.total ? b : a), candidatos[0])
  return { planes, recomendado: recomendado?.id, periodo: `${PERIODO.inicio}–${PERIODO.fin}`, años: nAños, ejemplo: Boolean(lluviaResumen.ejemplo) }
}

// ---------------------------------------------------------------------------
// Resultado completo + recomendaciones
// ---------------------------------------------------------------------------

export function analizarFinca({ datos, parcela, ubicacion, fecha = new Date() }) {
  const mesActual = fecha.getMonth()
  const lluvia = { ...resumenLluvia(datos.lluvia), ejemplo: datos.simulado }
  const humedadMes = medianaMes(datos.humedad, mesActual)
  const zonas = zonasParcela(parcela, ubicacion, humedadMes)
  const t = medianaMes(datos.temperatura, mesActual)
  const temperatura = t == null ? null : Math.round(t * 10) / 10

  // Puntaje general: hoy sale SOLO de la simulación por zonas. La interfaz debe
  // mostrarlo como ejemplo mientras `zonas.simulado` sea true.
  const puntaje = Math.round(0.6 * zonas.verdor.puntaje + 0.4 * zonas.humedad.puntaje)
  const estado = estadoDePuntaje(puntaje)

  const acciones = []

  // Consejos por zona: únicamente con datos observados de la parcela.
  if (!zonas.simulado) {
    const zv = zonas.verdor.afectadas
    if (zv && zv.porcentaje >= 6) {
      acciones.push({
        id: 'verdor',
        nivel: zv.porcentaje > 20 ? 'problema' : 'atencion',
        icono: 'hoja',
        titulo: `Revisa ${textoZona(zv.zona)} de tu finca`,
        texto: `${formato(zv.hectareas)} ha se ven menos verdes que el resto. Camina esa zona y busca hojas amarillas, plagas o charcos.`,
        accion: { tipo: 'mapa', capa: 'verdor', texto: 'Ver en el mapa' },
      })
    }
    const zh = zonas.humedad.afectadas
    if (zh && zh.porcentaje >= 8) {
      acciones.push({
        id: 'humedad',
        nivel: 'atencion',
        icono: 'gota',
        titulo: `${textoZona(zh.zona).replace(/^./, (c) => c.toUpperCase())} está más seca`,
        texto: 'Si puedes regar, empieza por ahí. Si no, cubre el suelo con rastrojo para que no pierda agua.',
        accion: { tipo: 'mapa', capa: 'humedad', texto: 'Ver en el mapa' },
      })
    }
  }

  // Consejo de lluvia: solo con la serie real de NASA y con datos de los meses que vienen.
  const sig = [1, 2].map((d) => lluvia.meses[(mesActual + d) % 12])
  if (datos.simulado) {
    acciones.push({
      id: 'sin-datos',
      nivel: 'info',
      icono: 'nube',
      titulo: 'Sin datos reales de lluvia',
      texto: 'No pudimos conectar con la NASA, así que no te damos consejos de lluvia. Reintenta cuando tengas señal.',
      accion: { tipo: 'reintentar', texto: 'Reintentar' },
    })
  } else if (sig.some((m) => m.mediana == null)) {
    acciones.push({
      id: 'lluvia',
      nivel: 'info',
      icono: 'nube',
      titulo: 'Faltan datos de lluvia para los próximos meses',
      texto: `No hay suficientes registros de la NASA para ${listaTexto(sig.filter((m) => m.mediana == null).map((m) => MESES_LARGOS[m.mes]))} en esta zona, así que no damos consejo de lluvia.`,
      accion: { tipo: 'lluvia', texto: 'Ver la lluvia' },
    })
  } else if (sig.every((m) => m.mediana >= 80)) {
    acciones.push({
      id: 'lluvia',
      nivel: 'bien',
      icono: 'lluvia',
      titulo: 'Vienen meses de lluvia en tu zona',
      texto: `Lo normal en ${MESES_LARGOS[sig[0].mes]} y ${MESES_LARGOS[sig[1].mes]} es ${sig[0].mediana} y ${sig[1].mediana} mm. Buen momento para sembrar si tienes la semilla lista.`,
      accion: { tipo: 'lluvia', texto: 'Ver la lluvia' },
    })
  } else if (sig[0].mediana < 45) {
    acciones.push({
      id: 'lluvia',
      nivel: 'atencion',
      icono: 'sol',
      titulo: 'Se acerca la época seca en tu zona',
      texto: `En ${MESES_LARGOS[sig[0].mes]} suelen caer solo ${sig[0].mediana} mm. Guarda agua y evita sembrar sin riego.`,
      accion: { tipo: 'lluvia', texto: 'Ver la lluvia' },
    })
  } else {
    acciones.push({
      id: 'lluvia',
      nivel: 'atencion',
      icono: 'lluvia',
      titulo: 'Lluvia moderada en las próximas semanas',
      texto: `Lo normal en ${MESES_LARGOS[sig[0].mes]} es ${sig[0].mediana} mm (entre ${sig[0].p20} y ${sig[0].p80} mm la mayoría de años).`,
      accion: { tipo: 'lluvia', texto: 'Ver la lluvia' },
    })
  }

  return {
    fecha,
    mesActual,
    puntaje,
    estado,
    diagnosticoSimulado: zonas.simulado,
    zonas,
    lluvia,
    humedadMes,
    temperatura,
    acciones,
    simulado: datos.simulado,
  }
}

export const formato = (n, d = 1) => n.toLocaleString('es', { maximumFractionDigits: d })

// Solo para diagnósticos con datos observados. Con la simulación se usa MENSAJE_SIMULADO.
export const MENSAJE_ESTADO = {
  bien: { titulo: 'Tu finca se ve bien', texto: 'La mayor parte del terreno está verde y con humedad.' },
  atencion: { titulo: 'Tu finca necesita atención', texto: 'Hay zonas que conviene revisar esta semana.' },
  problema: { titulo: 'Hay problemas en tu finca', texto: 'Varias zonas se ven débiles. Revísalas pronto.' },
  grave: { titulo: 'Tu finca necesita ayuda', texto: 'Gran parte del terreno se ve mal. Busca apoyo técnico.' },
}

export const MENSAJE_SIMULADO = {
  titulo: 'Ejemplo: así se verá tu diagnóstico',
  texto: 'El verdor y la humedad por zonas aún son simulados. No tomes decisiones con este puntaje.',
}
