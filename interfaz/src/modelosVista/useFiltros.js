import { create } from 'zustand'

export const CATEGORIAS_KYRO = [
  'Todos',
  'Polerones',
  'Poleras',
  'Calcetines',
  'Gorras',
  'Blusas',
  'Pantalones',
]

export const OPCIONES_ORDEN = [
  { id: 'destacados', etiqueta: 'Destacados' },
  { id: 'precio-menor', etiqueta: 'Precio: Menor a Mayor' },
  { id: 'precio-mayor', etiqueta: 'Precio: Mayor a Menor' },
  { id: 'nombre', etiqueta: 'Nombre: A-Z' },
]

export const PRECIO_MINIMO_DEFAULT = 5000
export const PRECIO_MAXIMO_DEFAULT = 60000

/**
 * ViewModel de Filtros KYRO (MVVM)
 * Administra el estado global editorial de filtros, categorías, rango de precio y ordenamiento.
 */
export const useFiltros = create((set) => ({
  categoria: 'Todos',
  precioMinimo: PRECIO_MINIMO_DEFAULT,
  precioMaximo: PRECIO_MAXIMO_DEFAULT,
  ordenarPor: 'destacados',
  busqueda: '',

  // Acciones fluidas
  setCategoria: (categoria) => set({ categoria: categoria || 'Todos' }),
  setPrecioMaximo: (precioMaximo) => {
    const val = Number(precioMaximo)
    set({ precioMaximo: Number.isFinite(val) ? val : PRECIO_MAXIMO_DEFAULT })
  },
  setPrecioMinimo: (precioMinimo) => {
    const val = Number(precioMinimo)
    set({ precioMinimo: Number.isFinite(val) ? val : PRECIO_MINIMO_DEFAULT })
  },
  setRangoPrecio: (min, max) => {
    const numMin = Number(min)
    const numMax = Number(max)
    set({
      precioMinimo: Number.isFinite(numMin) ? numMin : PRECIO_MINIMO_DEFAULT,
      precioMaximo: Number.isFinite(numMax) ? numMax : PRECIO_MAXIMO_DEFAULT,
    })
  },
  setOrdenarPor: (ordenarPor) => set({ ordenarPor: ordenarPor || 'destacados' }),
  setBusqueda: (busqueda) => set({ busqueda: busqueda ?? '' }),

  limpiarFiltros: () =>
    set({
      categoria: 'Todos',
      precioMinimo: PRECIO_MINIMO_DEFAULT,
      precioMaximo: PRECIO_MAXIMO_DEFAULT,
      ordenarPor: 'destacados',
      busqueda: '',
    }),
}))

/**
 * Función pura de filtrado y ordenamiento.
 * Altamente optimizada: evita congelamientos y errores por valores nulos/indefinidos.
 */
export function aplicarFiltros(productos = [], filtros = {}) {
  if (!Array.isArray(productos) || productos.length === 0) return []

  const {
    categoria = 'Todos',
    precioMinimo = PRECIO_MINIMO_DEFAULT,
    precioMaximo = PRECIO_MAXIMO_DEFAULT,
    ordenarPor = 'destacados',
    busqueda = '',
  } = filtros || {}

  const termino = String(busqueda || '').trim().toLowerCase()
  const min = Number.isFinite(Number(precioMinimo)) ? Number(precioMinimo) : PRECIO_MINIMO_DEFAULT
  const max = Number.isFinite(Number(precioMaximo)) ? Number(precioMaximo) : PRECIO_MAXIMO_DEFAULT

  // 1. Filtrado seguro
  const filtrados = productos.filter((p) => {
    if (!p) return false

    // Categoría
    if (categoria && categoria !== 'Todos') {
      const catProd = String(p.categoria || '').trim().toLowerCase()
      if (catProd !== categoria.trim().toLowerCase()) return false
    }

    // Precio
    const precio = Number(p.precio) || 0
    if (precio < min || precio > max) return false

    // Búsqueda en nombre, descripción y categoría
    if (termino.length > 0) {
      const nombre = String(p.nombre || '').toLowerCase()
      const desc = String(p.descripcion || '').toLowerCase()
      const cat = String(p.categoria || '').toLowerCase()
      if (!nombre.includes(termino) && !desc.includes(termino) && !cat.includes(termino)) {
        return false
      }
    }

    return true
  })

  // 2. Ordenamiento determinista
  const copia = [...filtrados]
  switch (ordenarPor) {
    case 'precio-menor':
      copia.sort((a, b) => (Number(a.precio) || 0) - (Number(b.precio) || 0))
      break
    case 'precio-mayor':
      copia.sort((a, b) => (Number(b.precio) || 0) - (Number(a.precio) || 0))
      break
    case 'nombre':
      copia.sort((a, b) => String(a.nombre || '').localeCompare(String(b.nombre || '')))
      break
    case 'destacados':
    default:
      copia.sort((a, b) => ((b.disponibles || 0) > 0 ? 1 : 0) - ((a.disponibles || 0) > 0 ? 1 : 0))
      break
  }

  return copia
}
