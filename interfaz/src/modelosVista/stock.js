// Reglas de presentación del stock y del precio, compartidas por inventario y catálogo.

export const POCO_STOCK = 5

export function estadoStock(cantidad) {
  if (cantidad === 0) return { texto: 'Agotado', clase: 'agotado' }
  if (cantidad <= POCO_STOCK) return { texto: 'Quedan pocos', clase: 'poco' }
  return { texto: 'Disponible', clase: 'disponible' }
}

// CLP sin decimales: 39990 -> "$39.990"
const formatoCLP = new Intl.NumberFormat('es-CL', {
  style: 'currency',
  currency: 'CLP',
  maximumFractionDigits: 0,
})

export const formatearPrecio = (pesos) => formatoCLP.format(pesos)
