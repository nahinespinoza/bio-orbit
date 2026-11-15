// Parcela de papa que monitorea el remote-sensing (Toacaso / Sigchos, Cotopaxi).
// Copias de remote-sensing/sentinel_2/datos_sentinel/{papas_parcela.geojson, datos/parcela.json}.
import geojson from '../data/parcela-monitoreada.json'
import info from '../data/parcela-monitoreada-info.json'
import { areaHa, perimetroM } from '../components/flujo-gps/geo.js'

const poligonoGeo = geojson.features.find((f) => f.geometry.type === 'Polygon')

// GeoJSON usa [lng, lat] y repite el primer vértice al final; Leaflet usa [lat, lng] sin repetir.
const anillo = poligonoGeo.geometry.coordinates[0].map(([lng, lat]) => [lat, lng])
const poligono = anillo.slice(0, -1)

export const ZONA = 'Toacaso / Sigchos'

export const CENTRO = [info.lat, info.lon]

// Mismo formato que la ubicación del GPS (`precision: null` = no viene del celular).
export const UBICACION = { lat: info.lat, lng: info.lon, precision: null, zona: ZONA, altitud: info.altitud_msnm }

const comoParcela = (poligono) => ({ poligono, area: areaHa(poligono), perimetro: perimetroM(poligono) })

// Mismo formato que una parcela dibujada en la app.
export const PARCELA = comoParcela(poligono)

// Fincas de EJEMPLO para la ruta /prueba: contornos ajustados a mano en la app
// (con "Editar") sobre lotes cerca de Toacaso, sin datos de remote-sensing.
export const FINCAS_EJEMPLO = [
  {
    id: 'ejemplo-2',
    nombre: 'Parcela 2 Papa',
    zona: ZONA,
    parcelas: [
      [[-0.7491652, -78.7682042], [-0.7484518, -78.7678716], [-0.7485001, -78.7670830], [-0.7487200, -78.7666646], [-0.7488595, -78.7666699], [-0.7495407, -78.7672171], [-0.7494442, -78.7682310]],
      [[-0.7507530, -78.7690464], [-0.7505384, -78.7686118], [-0.7508227, -78.7679735], [-0.7513162, -78.7681130], [-0.7518043, -78.7683651], [-0.7515200, -78.7692609]],
    ].map(comoParcela),
  },
  {
    id: 'ejemplo-3',
    nombre: 'Parcela 3 Papa',
    zona: ZONA,
    parcelas: [
      [[-0.7512572, -78.7579206], [-0.7509997, -78.7573037], [-0.7510158, -78.7571856], [-0.7520189, -78.7566385], [-0.7521851, -78.7568155], [-0.7522710, -78.7571159], [-0.7514664, -78.7578186]],
    ].map(comoParcela),
  },
]
