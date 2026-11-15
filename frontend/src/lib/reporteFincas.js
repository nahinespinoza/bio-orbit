// Reporte semanal de cada finca (modelo de lib/reporte.js, de la rama panel-resultados).
// - La parcela de Toacaso tiene datos reales del remote-sensing (con la imagen de zonas).
// - Cualquier otra finca muestra esos mismos datos marcados «Datos de ejemplo», porque el
//   remote-sensing solo existe para Toacaso.
import datosFijos from '../datos/resultado_match.json'
import { fincaPreanalizada, normalizarReporte } from './reporte.js'

let toacaso = null
export const reporteToacaso = () => (toacaso ??= fincaPreanalizada().reporte)

let ejemplo = null
export const reporteEjemplo = () => (ejemplo ??= { ...normalizarReporte(datosFijos), ejemplo: true, capas: null })
