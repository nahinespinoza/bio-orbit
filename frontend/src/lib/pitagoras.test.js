import assert from 'node:assert/strict'
import { test } from 'node:test'
import { agruparDescartes, alertasDeParcela, crearSolicitud, obtenerCultivos, recomendarCultivos, textoAdvertencia } from './pitagoras.js'

const formulario = { cultivo: 'papa', prioridad: 'speed', altitud: '3588', riego: 'no', fertilidad: 'unknown', drenaje: 'good' }

test('envía preferencias en el contrato del motor y conserva los datos desconocidos', async (t) => {
  t.mock.method(globalThis, 'fetch', async (url, opciones) => {
    assert.equal(url, '/api/pitagoras/v1/recommend')
    assert.equal(opciones.method, 'POST')
    const enviado = JSON.parse(opciones.body)
    assert.deepEqual(enviado.previous_crops, ['papa'])
    assert.deepEqual(enviado.priorities, ['speed'])
    assert.deepEqual(enviado.climate, { altitude_masl: 3588, irrigation: 'no' })
    assert.equal(enviado.soil.fertility, 'unknown')
    assert.equal(enviado.soil.drainage, 'good')
    assert.equal(enviado.rotation_cycles, 4)
    return Response.json({ status: 'ok', recommendation: { name: 'Lizas', score: 61.3, rotation: { cycles: 1 } } })
  })
  const resultado = await recomendarCultivos(formulario)
  assert.equal(resultado.recommendation.rotation.cycles, 1, 'una rotación parcial no debe convertirse en cuatro ciclos')
})

test('sin altura de ubicación conserva el drenaje y no inventa altitud ni historial para tierra nueva', () => {
  for (const altitud of ['', null, undefined]) {
    const entrada = crearSolicitud({ ...formulario, cultivo: 'new_land', altitud, drenaje: 'poor' })
    assert.equal(entrada.new_land, true)
    assert.deepEqual(entrada.previous_crops, [])
    assert.equal(entrada.climate.altitude_masl, null)
    assert.equal(entrada.soil.drainage, 'poor')
  }
})

test('conserva el estado sin candidatos para mostrar las causas del motor', async (t) => {
  const resultado = { status: 'no_candidates', discarded: [{ crop: 'papa', reason: 'No se repite el mismo cultivo.' }] }
  t.mock.method(globalThis, 'fetch', async () => Response.json(resultado))
  assert.deepEqual(await recomendarCultivos(formulario), resultado)
})

test('muestra el error de validación del motor y no crea una recomendación de respaldo', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => Response.json({ errors: [{ message: 'Corrige el cultivo anterior.' }] }, { status: 422 }))
  await assert.rejects(recomendarCultivos(formulario), /Corrige el cultivo anterior/)
})

test('un proxy caído o el HTML de la SPA no se interpretan como una respuesta válida', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => new Response('<html>Bad gateway</html>', { status: 502, headers: { 'Content-Type': 'text/html' } }))
  await assert.rejects(obtenerCultivos(), /servicio de Pitágoras no está disponible/)
})

test('rechaza respuestas incompletas y catálogos mal formados', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => Response.json({ status: 'ok' }))
  await assert.rejects(recomendarCultivos(formulario), /incompleta/)
  await assert.rejects(obtenerCultivos(), /lista de cultivos/)
})

test('cancelar al salir de la pantalla aborta la consulta', async (t) => {
  const control = new AbortController()
  t.mock.method(globalThis, 'fetch', async (_, { signal }) => new Promise((resolve, reject) => {
    signal.addEventListener('abort', () => reject(new DOMException('Abortado', 'AbortError')), { once: true })
  }))
  const pendiente = recomendarCultivos(formulario, control.signal)
  control.abort()
  await assert.rejects(pendiente, { name: 'AbortError' })
})

test('no atribuye las alertas de Toacaso a otras parcelas', () => {
  const remota = { rule: 'lancha', signal: { sources: ['remote_sensing'] } }
  const mixta = { rule: 'helada', signal: { sources: ['farmer', 'remote_sensing'] } }
  const propia = { rule: 'sequia', signal: { sources: ['farmer'] } }
  const cultivo = { advisories: [remota, mixta, propia] }
  assert.deepEqual(alertasDeParcela(cultivo, false), [propia])
  assert.deepEqual(alertasDeParcela(cultivo, true), [remota, mixta, propia])
})

test('agrupa motivos repetidos sin confundir la altura con la falta de riego', () => {
  const descartados = [
    { crop: 'trigo', filter: 'F4-climate', reason: 'Altitud 3588 m por encima del rango del cultivo (0–3300 m).' },
    { crop: 'qaniwa', filter: 'F4-climate', reason: 'Altitud 3588 m por debajo del rango del cultivo (3800–4200 m).' },
    { crop: 'papa', filter: 'F1', reason: 'No se repite el mismo cultivo en el mismo lote.' },
    { crop: 'barbecho', filter: 'NON_COMMERCIAL_RULE', reason: 'Cultivo sin mercado.' },
    { crop: 'pasto', filter: 'NON_COMMERCIAL_RULE', reason: 'Cultivo sin mercado.' },
    { crop: 'maiz', filter: 'F4-climate', reason: 'El cultivo requiere riego y el lote es de secano.' },
  ]
  const cultivos = [{ crop_id: 'qaniwa', name: 'Qañiwa (cañihua)' }]
  assert.deepEqual(agruparDescartes(descartados, cultivos), [
    { motivo: 'Fuera del rango de altura del cultivo.', nombres: ['trigo', 'Qañiwa (cañihua)'] },
    { motivo: 'No repetir en el mismo lote.', nombres: ['papa'] },
    { motivo: 'Sin mercado; solo con suelo pobre o compactado, o tras dos ciclos muy exigentes.', nombres: ['barbecho', 'pasto'] },
    { motivo: 'El cultivo requiere riego y el lote es de secano.', nombres: ['maiz'] },
  ])
  assert.deepEqual(agruparDescartes(), [])
})

test('resume las advertencias sin perder qué datos faltan', () => {
  assert.equal(textoAdvertencia('Datos faltantes que se puntuaron como neutros: market_value, aptitude.'),
    'Sin datos (valor neutro): mercado, adaptación al terreno.')
})
