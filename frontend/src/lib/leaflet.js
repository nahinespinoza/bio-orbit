// leaflet-draw y leaflet.sync esperan encontrar `L` como variable global.
// Este módulo la expone antes de que se carguen los plugins.
import L from 'leaflet'
import iconUrl from 'leaflet/dist/images/marker-icon.png'
import iconRetinaUrl from 'leaflet/dist/images/marker-icon-2x.png'
import shadowUrl from 'leaflet/dist/images/marker-shadow.png'

window.L = L
// Arreglo de un error de leaflet-draw 1.0.4 al dibujar rectángulos ("type is not defined").
window.type = ''

// Sin esto los punteros no aparecen con bundlers (Vite/Webpack).
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({ iconUrl, iconRetinaUrl, shadowUrl })

export default L
