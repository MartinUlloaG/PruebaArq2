import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'

/**
 * ViewModel del Carrito de Compras (MVVM)
 * Administra el estado global de los productos seleccionados y la lógica de negocio del carrito.
 * Utiliza el middleware `persist` para garantizar tolerancia a fallos y resiliencia ante recargas.
 */
export const useCarrito = create(
  persist(
    (set, get) => ({
      // Arreglo de productos en el carrito
      productos: [],
      abierto: false,

      // Control visual del panel/modal
      abrirCarrito: () => set({ abierto: true }),
      cerrarCarrito: () => set({ abierto: false }),
      setAbierto: (abierto) => set({ abierto }),

      // Agrega un producto o incrementa su cantidad si ya existe
      agregarProducto: (producto, cantidad = 1) => {
        const { productos } = get()
        const id = producto.producto_id ?? producto.id
        const existente = productos.find((p) => (p.producto_id ?? p.id) === id)

        if (existente) {
          const maximo = producto.disponibles ?? existente.disponibles ?? 99
          const nuevaCantidad = Math.min(existente.cantidad + cantidad, maximo)

          set({
            productos: productos.map((p) =>
              (p.producto_id ?? p.id) === id
                ? { ...p, cantidad: nuevaCantidad }
                : p
            ),
          })
        } else {
          set({
            productos: [
              ...productos,
              {
                producto_id: id,
                nombre: producto.nombre,
                precio: producto.precio,
                disponibles: producto.disponibles ?? 99,
                cantidad: Math.max(1, cantidad),
              },
            ],
          })
        }
      },

      // Elimina un producto por su identificador
      eliminarProducto: (productoId) => {
        set({
          productos: get().productos.filter(
            (p) => (p.producto_id ?? p.id) !== productoId
          ),
        })
      },

      // Actualiza la cantidad directamente (decremento/incremento)
      actualizarCantidad: (productoId, nuevaCantidad) => {
        if (nuevaCantidad <= 0) {
          get().eliminarProducto(productoId)
          return
        }
        set({
          productos: get().productos.map((p) => {
            if ((p.producto_id ?? p.id) === productoId) {
              const maximo = p.disponibles ?? 99
              return { ...p, cantidad: Math.min(nuevaCantidad, maximo) }
            }
            return p
          }),
        })
      },

      // Calcula y retorna el total en dinero de todos los productos
      obtenerTotal: () => {
        return get().productos.reduce(
          (acumulado, p) => acumulado + p.precio * p.cantidad,
          0
        )
      },

      // Vacía el carrito por completo
      limpiarCarrito: () => {
        set({ productos: [] })
      },
    }),
    {
      name: 'carrito_compras_mvvm',
      storage: createJSONStorage(() => localStorage),
      // Solo persistimos la colección de productos en almacenamiento local
      partialize: (state) => ({ productos: state.productos }),
    }
  )
)

// Selectores derivados (útiles para suscripciones directas en componentes de React)
export const seleccionarTotal = (estado) =>
  estado.productos.reduce((total, p) => total + p.precio * p.cantidad, 0)

export const seleccionarCantidadTotal = (estado) =>
  estado.productos.reduce((cantidad, p) => cantidad + p.cantidad, 0)
