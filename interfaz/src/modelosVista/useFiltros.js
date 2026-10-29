import { create } from 'zustand'

export const CATEGORIAS_KYRO = [
  'Todos',
  'Polerones',
  'Poleras',
  'Calcetines',
  'Gorras',
  'Blusas',
]

export const OPCIONES_ORDEN = [
  { id: 'destacados', etiqueta: 'Destacados' },
  { id: 'precio-menor', etiqueta: 'Precio: Menor a Mayor' },
  { id: 'precio-mayor', etiqueta: 'Precio: Mayor a Menor' },
  { id: 'nombre', etiqueta: 'Nombre: A-Z' },
]

export const PRECIO_MINIMO_DEFAULT = 0
export const PRECIO_MAXIMO_DEFAULT = 250000

/**
 * ViewModel de Filtros de KYRO (MVVM)
 * Administra el estado global editorial de filtros, categorías, rango de precio y ordenamiento.
 */
export const useFiltros = create((set) => ({
  categoria: 'Todos',
  precioMinimo: PRECIO_MINIMO_DEFAULT,
  precioMaximo: PRECIO_MAXIMO_DEFAULT,
  ordenarPor: 'destacados',
  busqueda: '',

  // Acciones
  setCategoria: (categoria) => set({ categoria }),
  setPrecioMaximo: (precioMaximo) => set({ precioMaximo: Number(precioMaximo) }),
  setPrecioMinimo: (precioMinimo) => set({ precioMinimo: Number(precioMinimo) }),
  setRangoPrecio: (min, max) => set({ precioMinimo: Number(min), precioMaximo: Number(max) }),
  setOrdenarPor: (ordenarPor) => set({ ordenarPor }),
  setBusqueda: (busqueda) => set({ busqueda }),

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
 * Función pura que filtra y ordena los productos según el estado de useFiltros.
 */
export function aplicarFiltros(productos = [], filtros) {
  const { categoria, precioMinimo, precioMaximo, ordenarPor, busqueda } = filtros
  const termino = (busqueda || '').trim().toLowerCase()

  // 1. Filtrado
  const filtrados = productos.filter((p) => {
    // Categoría
    if (categoria !== 'Todos') {
      const catProd = (p.categoria || '').toLowerCase()
      if (catProd !== categoria.toLowerCase()) return false
    }

    // Precio
    const precio = Number(p.precio) || 0
    if (precio < precioMinimo || precio > precioMaximo) return false

    // Búsqueda
    if (termino.length > 0) {
      const nombre = (p.nombre || '').toLowerCase()
      const desc = (p.descripcion || '').toLowerCase()
      if (!nombre.includes(termino) && !desc.includes(termino)) {
        return false
      }
    }

    return true
  })

  // 2. Ordenamiento
  const copia = [...filtrados]
  switch (ordenarPor) {
    case 'precio-menor':
      copia.sort((a, b) => a.precio - b.precio)
      break
    case 'precio-mayor':
      copia.sort((a, b) => b.precio - a.precio)
      break
    case 'nombre':
      copia.sort((a, b) => a.nombre.localeCompare(b.nombre))
      break
    case 'destacados':
    default:
      // Mantener orden natural o por disponibilidad
      copia.sort((a, b) => (b.disponibles > 0 ? 1 : 0) - (a.disponibles > 0 ? 1 : 0))
      break
  }

  return copia
}
