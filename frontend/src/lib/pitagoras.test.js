import assert from 'node:assert/strict'
import { test } from 'node:test'
import { agruparDescartes, alertasDeParcela, crearSolicitud, obtenerCultivos, recomendarCultivos, referenciasDe, textoAdvertencia } from './pitagoras.js'

const formulario = { cultivo: 'papa', prioridad: 'speed', riego: 'rain_only', drenaje: 'no' }

test('envía las respuestas de la pantalla al contrato de /v1/recommendations', async (t) => {
  t.mock.method(globalThis, 'fetch', async (url, opciones) => {
    assert.equal(url, '/api/pitagoras/v1/recommendations')
    assert.equal(opciones.method, 'POST')
    assert.deepEqual(JSON.parse(opciones.body), {
      previous_crop: 'papa', priority: 'speed', irrigation: 'rain_only', waterlogging: 'no',
    })
    return Response.json({ status: 'ok', recommendation: { name: 'Lizas', affinity: 61.3, rotation: [{ cycle: 1 }] } })
  })
  const resultado = await recomendarCultivos(formulario)
  assert.equal(resultado.recommendation.rotation.length, 1, 'una rotación parcial no debe convertirse en cuatro ciclos')
})

test('tierra nueva se envía como new_land y no se manda altitud ni fertilidad', () => {
  assert.deepEqual(crearSolicitud({ ...formulario, cultivo: 'new_land', drenaje: 'long' }),
    { previous_crop: 'new_land', priority: 'speed', irrigation: 'rain_only', waterlogging: 'long' })
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

test('muestra el mensaje de los errores 502 y 503 del servicio', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => Response.json({ detail: { code: 'LLM_ERROR', message: 'El modelo no respondió: Timeout' } }, { status: 502 }))
  await assert.rejects(recomendarCultivos(formulario), /El modelo no respondió/)
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

test('no atribuye las alertas de Toacaso a fincas sin monitoreo', () => {
  const cultivo = { advisories: [{ level: 'ALTO', message: 'Helada' }] }
  assert.deepEqual(alertasDeParcela(cultivo, false), [])
  assert.deepEqual(alertasDeParcela(cultivo, true), cultivo.advisories)
  assert.deepEqual(alertasDeParcela({}, true), [])
})

test('resuelve las referencias de un motivo contra las fuentes del resultado', () => {
  const resultado = { sources: [{ id: 'F1', title: 'Manual', url: null }, { id: 'F2', title: 'Guía', url: 'https://x.test' }] }
  assert.deepEqual(referenciasDe(resultado, ['F2', 'F9']).map((f) => f.id), ['F2'])
  assert.deepEqual(referenciasDe({}, ['F1']), [])
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
