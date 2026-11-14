import L from '../../lib/leaflet.js'
import { TILE_SATELITE, areaHa } from './geo.js'

// Ajuste automático del contorno de la parcela a partir de la imagen satelital.
//
// Toma las teselas de Esri bajo el cuadro que puso el usuario y hace una
// segmentación sencilla por color: parte del centro del cuadro y crece por los
// píxeles parecidos sin cruzar bordes fuertes (caminos, cercos, cambios de
// cultivo). De varios umbrales elige el que da un área más cercana a las
// hectáreas declaradas, limpia la máscara y devuelve su contorno simplificado.
//
// Es una aproximación que corre en el navegador. Cuando exista el backend
// (con imágenes multiespectrales y un modelo de segmentación), se reemplaza
// `detectarParcela` por la llamada al servidor manteniendo la misma salida.

const TESELA = 256
const ZOOM_MIN = 12
const ZOOM_MAX = 18
const LADO_OBJETIVO_PX = 200 // lado del cuadro en píxeles al analizar
const MARGEN = 0.6 // ventana de búsqueda = cuadro + 60 % por lado
const UMBRALES = [10, 14, 18, 23, 28, 34, 41, 50]
const RAZON_MIN = 0.4
const RAZON_MAX = 2.5

const crs = L.CRS.EPSG3857

const cargarImagen = (src) =>
  new Promise((resolver, rechazar) => {
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => resolver(img)
    img.onerror = () => rechazar(new Error(`No se pudo cargar ${src}`))
    img.src = src
  })

const urlTesela = (z, x, y) => TILE_SATELITE.url.replace('{z}', z).replace('{x}', x).replace('{y}', y)

async function mosaico(x0, y0, ancho, alto, z) {
  const canvas = document.createElement('canvas')
  canvas.width = ancho
  canvas.height = alto
  const ctx = canvas.getContext('2d', { willReadFrequently: true })
  const tareas = []
  for (let tx = Math.floor(x0 / TESELA); tx <= Math.floor((x0 + ancho - 1) / TESELA); tx++) {
    for (let ty = Math.floor(y0 / TESELA); ty <= Math.floor((y0 + alto - 1) / TESELA); ty++) {
      tareas.push(cargarImagen(urlTesela(z, tx, ty)).then((img) => ctx.drawImage(img, tx * TESELA - x0, ty * TESELA - y0)))
    }
  }
  await Promise.all(tareas)
  return ctx.getImageData(0, 0, ancho, alto).data
}

// Desenfoque de caja separable (reduce la textura de cultivos y copas).
function desenfocar(canal, ancho, alto, r) {
  const tmp = new Float32Array(canal.length)
  const out = new Float32Array(canal.length)
  for (let y = 0; y < alto; y++) {
    for (let x = 0; x < ancho; x++) {
      let s = 0
      let n = 0
      for (let k = -r; k <= r; k++) {
        const xx = x + k
        if (xx >= 0 && xx < ancho) {
          s += canal[y * ancho + xx]
          n++
        }
      }
      tmp[y * ancho + x] = s / n
    }
  }
  for (let y = 0; y < alto; y++) {
    for (let x = 0; x < ancho; x++) {
      let s = 0
      let n = 0
      for (let k = -r; k <= r; k++) {
        const yy = y + k
        if (yy >= 0 && yy < alto) {
          s += tmp[yy * ancho + x]
          n++
        }
      }
      out[y * ancho + x] = s / n
    }
  }
  return out
}

function sobel(lum, ancho, alto) {
  const mag = new Float32Array(lum.length)
  for (let y = 1; y < alto - 1; y++) {
    for (let x = 1; x < ancho - 1; x++) {
      const i = y * ancho + x
      const gx =
        lum[i - ancho + 1] + 2 * lum[i + 1] + lum[i + ancho + 1] - lum[i - ancho - 1] - 2 * lum[i - 1] - lum[i + ancho - 1]
      const gy =
        lum[i + ancho - 1] + 2 * lum[i + ancho] + lum[i + ancho + 1] - lum[i - ancho - 1] - 2 * lum[i - ancho] - lum[i - ancho + 1]
      mag[i] = Math.hypot(gx, gy)
    }
  }
  return mag
}

const percentil = (arr, p) => {
  const copia = Float32Array.from(arr).sort()
  return copia[Math.min(copia.length - 1, Math.floor(p * copia.length))]
}

const mediana = (valores) => {
  const v = [...valores].sort((a, b) => a - b)
  return v[Math.floor(v.length / 2)]
}

// Crecimiento de región desde las semillas: píxeles con color parecido y sin borde fuerte.
function crecer(semillas, dist, mag, umbral, bordeMax, ancho, alto) {
  const n = ancho * alto
  const mascara = new Uint8Array(n)
  const cola = new Int32Array(n)
  let ini = 0
  let fin = 0
  for (const i of semillas) {
    if (dist[i] < umbral && !mascara[i]) {
      mascara[i] = 1
      cola[fin++] = i
    }
  }
  let tocaBorde = false
  while (ini < fin) {
    const i = cola[ini++]
    const x = i % ancho
    const y = (i - x) / ancho
    if (x === 0 || y === 0 || x === ancho - 1 || y === alto - 1) tocaBorde = true
    const vecinos = [x > 0 ? i - 1 : -1, x < ancho - 1 ? i + 1 : -1, y > 0 ? i - ancho : -1, y < alto - 1 ? i + ancho : -1]
    for (const j of vecinos) {
      if (j >= 0 && !mascara[j] && dist[j] < umbral && mag[j] < bordeMax) {
        mascara[j] = 1
        cola[fin++] = j
      }
    }
  }
  return { mascara, cuenta: fin, tocaBorde }
}

// Erosión / dilatación con núcleo cuadrado (separable).
function morfologia(mascara, ancho, alto, r, dilatar) {
  const pasada = (entrada, horizontal) => {
    const salida = new Uint8Array(entrada.length)
    for (let y = 0; y < alto; y++) {
      for (let x = 0; x < ancho; x++) {
        let valor = dilatar ? 0 : 1
        for (let k = -r; k <= r; k++) {
          const xx = horizontal ? x + k : x
          const yy = horizontal ? y : y + k
          const v = xx < 0 || yy < 0 || xx >= ancho || yy >= alto ? 0 : entrada[yy * ancho + xx]
          if (dilatar && v) { valor = 1; break }
          if (!dilatar && !v) { valor = 0; break }
        }
        salida[y * ancho + x] = valor
      }
    }
    return salida
  }
  return pasada(pasada(mascara, true), false)
}

// Rellena huecos: todo fondo no alcanzable desde el borde pasa a ser parcela.
function rellenarHuecos(mascara, ancho, alto) {
  const fuera = new Uint8Array(mascara.length)
  const cola = []
  const meter = (i) => {
    if (!mascara[i] && !fuera[i]) {
      fuera[i] = 1
      cola.push(i)
    }
  }
  for (let x = 0; x < ancho; x++) { meter(x); meter((alto - 1) * ancho + x) }
  for (let y = 0; y < alto; y++) { meter(y * ancho); meter(y * ancho + ancho - 1) }
  while (cola.length) {
    const i = cola.pop()
    const x = i % ancho
    if (x > 0) meter(i - 1)
    if (x < ancho - 1) meter(i + 1)
    if (i >= ancho) meter(i - ancho)
    if (i < (alto - 1) * ancho) meter(i + ancho)
  }
  const salida = new Uint8Array(mascara.length)
  for (let i = 0; i < salida.length; i++) salida[i] = fuera[i] ? 0 : 1
  return salida
}

// Se queda con la componente conexa que contiene el píxel `inicio`.
function componente(mascara, ancho, inicio) {
  const salida = new Uint8Array(mascara.length)
  if (!mascara[inicio]) return { mascara: salida, cuenta: 0 }
  const cola = [inicio]
  salida[inicio] = 1
  let cuenta = 0
  while (cola.length) {
    const i = cola.pop()
    cuenta++
    const x = i % ancho
    for (const j of [x > 0 ? i - 1 : -1, x < ancho - 1 ? i + 1 : -1, i - ancho, i + ancho]) {
      if (j >= 0 && j < mascara.length && mascara[j] && !salida[j]) {
        salida[j] = 1
        cola.push(j)
      }
    }
  }
  return { mascara: salida, cuenta }
}

function envolventeConvexa(puntos) {
  const p = [...puntos].sort((a, b) => a[0] - b[0] || a[1] - b[1])
  const cruz = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
  const inferior = []
  for (const q of p) {
    while (inferior.length >= 2 && cruz(inferior[inferior.length - 2], inferior[inferior.length - 1], q) <= 0) inferior.pop()
    inferior.push(q)
  }
  const superior = []
  for (const q of p.reverse()) {
    while (superior.length >= 2 && cruz(superior[superior.length - 2], superior[superior.length - 1], q) <= 0) superior.pop()
    superior.push(q)
  }
  return inferior.slice(0, -1).concat(superior.slice(0, -1))
}

// Quita vértices casi alineados con sus vecinos hasta dejar un polígono limpio.
function simplificar(poligono, tolerancia) {
  let pts = poligono
  let cambio = true
  while (cambio && pts.length > 4) {
    cambio = false
    let peor = -1
    let menor = Infinity
    for (let i = 0; i < pts.length; i++) {
      const a = pts[(i - 1 + pts.length) % pts.length]
      const b = pts[i]
      const c = pts[(i + 1) % pts.length]
      const largo = Math.hypot(c[0] - a[0], c[1] - a[1]) || 1
      const d = Math.abs((c[0] - a[0]) * (a[1] - b[1]) - (a[0] - b[0]) * (c[1] - a[1])) / largo
      if (d < menor) {
        menor = d
        peor = i
      }
    }
    if (menor < tolerancia) {
      pts = pts.filter((_, i) => i !== peor)
      cambio = true
    }
  }
  return pts
}

/**
 * @param {[number, number][]} cuadro esquinas [lat, lng] del cuadro del usuario
 * @param {number} hectareas superficie declarada
 * @returns {Promise<{ ok: boolean, poligono?: [number, number][], area?: number, motivo?: string }>}
 */
export async function detectarParcela(cuadro, hectareas) {
  try {
    const limites = L.latLngBounds(cuadro)
    const centro = limites.getCenter()
    const mppZoom0 = 156543.03392 * Math.cos((centro.lat * Math.PI) / 180)
    const ladoM = Math.sqrt(hectareas * 10000)
    const z = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, Math.round(Math.log2((mppZoom0 * LADO_OBJETIVO_PX) / ladoM))))
    const mpp = mppZoom0 / 2 ** z

    const nw = crs.latLngToPoint(limites.getNorthWest(), z)
    const se = crs.latLngToPoint(limites.getSouthEast(), z)
    const lado = Math.max(se.x - nw.x, se.y - nw.y)
    const x0 = Math.floor(nw.x - lado * MARGEN)
    const y0 = Math.floor(nw.y - lado * MARGEN)
    const ancho = Math.ceil(se.x + lado * MARGEN) - x0
    const alto = Math.ceil(se.y + lado * MARGEN) - y0
    const n = ancho * alto

    const rgba = await mosaico(x0, y0, ancho, alto, z)
    const r = new Float32Array(n)
    const g = new Float32Array(n)
    const b = new Float32Array(n)
    for (let i = 0; i < n; i++) {
      r[i] = rgba[i * 4]
      g[i] = rgba[i * 4 + 1]
      b[i] = rgba[i * 4 + 2]
    }
    const radio = Math.max(1, Math.round(lado / 80))
    const rs = desenfocar(r, ancho, alto, radio)
    const gs = desenfocar(g, ancho, alto, radio)
    const bs = desenfocar(b, ancho, alto, radio)
    const lum = new Float32Array(n)
    for (let i = 0; i < n; i++) lum[i] = 0.299 * rs[i] + 0.587 * gs[i] + 0.114 * bs[i]
    const mag = sobel(lum, ancho, alto)
    const bordeMax = percentil(mag, 0.88)

    // Semillas: el 40 % central del cuadro
    const cx = (nw.x + se.x) / 2 - x0
    const cy = (nw.y + se.y) / 2 - y0
    const semi = lado * 0.2
    const semillas = []
    for (let y = Math.round(cy - semi); y <= Math.round(cy + semi); y++) {
      for (let x = Math.round(cx - semi); x <= Math.round(cx + semi); x++) {
        if (x >= 0 && y >= 0 && x < ancho && y < alto) semillas.push(y * ancho + x)
      }
    }
    const ref = [
      mediana(semillas.map((i) => rs[i])),
      mediana(semillas.map((i) => gs[i])),
      mediana(semillas.map((i) => bs[i])),
    ]
    const dist = new Float32Array(n)
    for (let i = 0; i < n; i++) dist[i] = Math.hypot(rs[i] - ref[0], gs[i] - ref[1], bs[i] - ref[2])

    // Elegir el umbral cuya región se parezca más al área declarada
    const objetivo = (hectareas * 10000) / (mpp * mpp)
    let mejor = null
    for (const umbral of UMBRALES) {
      const region = crecer(semillas, dist, mag, umbral, bordeMax, ancho, alto)
      if (region.cuenta < objetivo * 0.15) continue
      const puntaje = Math.abs(Math.log(region.cuenta / objetivo)) + (region.tocaBorde ? 1.5 : 0)
      if (!mejor || puntaje < mejor.puntaje) mejor = { ...region, puntaje }
    }
    if (!mejor) return { ok: false, motivo: 'sin-region' }

    // Limpieza: cerrar, rellenar huecos, abrir y quedarse con la parte central
    const rm = Math.max(1, Math.round(lado / 60))
    let mascara = morfologia(morfologia(mejor.mascara, ancho, alto, rm, true), ancho, alto, rm, false)
    mascara = rellenarHuecos(mascara, ancho, alto)
    mascara = morfologia(morfologia(mascara, ancho, alto, rm, false), ancho, alto, rm, true)
    // Arranca desde la semilla más parecida al color de referencia que siga en la máscara
    let inicio = -1
    for (const i of semillas) {
      if (mascara[i] && (inicio < 0 || dist[i] < dist[inicio])) inicio = i
    }
    if (inicio < 0) return { ok: false, motivo: 'sin-region' }
    const final = componente(mascara, ancho, inicio)

    // Contorno: envolvente convexa de los píxeles de borde, simplificada
    const borde = []
    for (let i = 0; i < n; i++) {
      if (!final.mascara[i]) continue
      const x = i % ancho
      const y = (i - x) / ancho
      if (x === 0 || y === 0 || x === ancho - 1 || y === alto - 1 ||
          !final.mascara[i - 1] || !final.mascara[i + 1] || !final.mascara[i - ancho] || !final.mascara[i + ancho]) {
        borde.push([x + 0.5, y + 0.5])
      }
    }
    if (borde.length < 3) return { ok: false, motivo: 'sin-region' }
    const contornoPx = simplificar(envolventeConvexa(borde), Math.max(1.5, lado * 0.03))
    const poligono = contornoPx.map(([x, y]) => {
      const ll = crs.pointToLatLng(L.point(x0 + x, y0 + y), z)
      return [ll.lat, ll.lng]
    })
    const area = areaHa(poligono)
    const razon = area / hectareas
    if (poligono.length < 3 || razon < RAZON_MIN || razon > RAZON_MAX) return { ok: false, motivo: 'fuera-de-rango', area }
    return { ok: true, poligono, area }
  } catch (error) {
    return { ok: false, motivo: error.message }
  }
}
