// Vocabulario único de la salud del cultivo en toda la app.
export const ETIQUETAS_SALUD = { bien: 'Sana', atencion: 'En alerta', problema: 'Débil', grave: 'Crítica' }

// { sana, alerta, critico } (resumen del remote-sensing) → segmentos de BarraSalud
export const segmentosSalud = ({ sana, alerta, critico }) => [
  { estado: 'bien', porcentaje: sana },
  { estado: 'atencion', porcentaje: alerta },
  { estado: 'grave', porcentaje: critico },
]
