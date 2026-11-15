// Datos quemados de la Parcela 1 (ruta /prueba), sacados de remote-sensing/:
//  - resumen-parcela1.json: el resumen para presentar (lo que se muestra en pantalla).
//  - remote-sensing-parcela1.json: lo generado por frontend/scripts/generar_remote_sensing.py
//    (píxeles de Sentinel-2 para el mapa, clima mensual de NASA POWER y textos de las alertas).
import resumen from '../data/resumen-parcela1.json'
import datos from '../data/remote-sensing-parcela1.json'

export const RS_PARCELA1 = { ...datos, resumen }
