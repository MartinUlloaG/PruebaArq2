import { create } from 'zustand'

// Las categorías y los precios salen de los datos de la API, no de una lista fija.
export const TODAS = 'Todos'

export const OPCIONES_ORDEN = [
  { id: 'destacados', etiqueta: 'Destacados' },
  { id: 'precio-menor', etiqueta: 'Precio: Menor a Mayor' },
  { id: 'precio-mayor', etiqueta: 'Precio: Mayor a Menor' },
  { id: 'nombre', etiqueta: 'Nombre: A-Z' },
]

/**
 * ViewModel de Filtros (MVVM): categoría, precio máximo, orden y búsqueda.
 * precioMaximo null = sin tope.
 */
export const useFiltros = create((set) => ({
  categoria: TODAS,
  precioMaximo: null,
  ordenarPor: 'destacados',
  busqueda: '',

  setCategoria: (categoria) => set({ categoria: categoria || TODAS }),
  setPrecioMaximo: (precioMaximo) => {
    const valor = Number(precioMaximo)
    set({ precioMaximo: Number.isFinite(valor) ? valor : null })
  },
  setOrdenarPor: (ordenarPor) => set({ ordenarPor: ordenarPor || 'destacados' }),
  setBusqueda: (busqueda) => set({ busqueda: busqueda ?? '' }),

  limpiarFiltros: () => set({ categoria: TODAS, precioMaximo: null, ordenarPor: 'destacados', busqueda: '' }),
}))

// Rango real de precios del catálogo que llegó de la API.
export function rangoDePrecios(productos = []) {
  if (productos.length === 0) return { minimo: 0, maximo: 0 }
  const precios = productos.map((p) => p.precio)
  return { minimo: Math.min(...precios), maximo: Math.max(...precios) }
}

// Función pura de filtrado y ordenamiento.
export function aplicarFiltros(productos = [], { categoria, precioMaximo, ordenarPor, busqueda }) {
  const termino = String(busqueda || '').trim().toLowerCase()

  const filtrados = productos.filter((p) => {
    if (categoria && categoria !== TODAS && p.categoria !== categoria) return false
    if (precioMaximo !== null && p.precio > precioMaximo) return false
    if (termino) {
      const texto = `${p.nombre} ${p.descripcion ?? ''} ${p.categoria}`.toLowerCase()
      if (!texto.includes(termino)) return false
    }
    return true
  })

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
    default:
      // Destacados: primero lo que tiene stock
      copia.sort((a, b) => (b.disponibles > 0) - (a.disponibles > 0))
  }
  return copia
}
