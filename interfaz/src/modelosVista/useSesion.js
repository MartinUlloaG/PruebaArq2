// ViewModel de la sesión: estado del usuario autenticado y acciones para entrar y salir.
// Las vistas leen de aquí con selectores; nunca llaman a la API directamente.
import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'

import { ingresar as ingresarEnApi } from '../servicios/autenticacion'
import { configurarSesion } from '../servicios/clienteApi'
import { obtenerRutaPrincipalRol } from './roles'
import { useCarrito } from './useCarrito'

const sinSesion = { token: null, usuario: null, expiraEn: null }

/**
 * Limpieza profunda y exhaustiva de todo almacenamiento local y de sesión.
 * Elimina tokens residuales, credenciales previas y estados de carritos cruzados
 * entre roles para evitar colisiones 403.
 */
export function purgarAlmacenamientoLocal() {
  try {
    sessionStorage.removeItem('sesion')
    localStorage.removeItem('sesion')
    localStorage.removeItem('carrito_compras_mvvm')
  } catch (err) {
    console.warn('Aviso al purgar almacenamiento local:', err)
  }
}

export const useSesion = create(
  persist(
    (set) => ({
      ...sinSesion,
      cargando: false,
      error: null, // por qué falló el último ingreso
      aviso: null, // por qué se cerró la sesión (ej. venció)

      async ingresar(correo, clave) {
        // 1. Limpieza absoluta previa: asegurar que ningún token o estado anterior interfiera
        purgarAlmacenamientoLocal()
        set({ ...sinSesion, cargando: true, error: null, aviso: null })

        try {
          const respuesta = await ingresarEnApi(correo, clave)
          const usuarioAutenticado = respuesta.usuario
          const rutaPrincipal = obtenerRutaPrincipalRol(usuarioAutenticado?.rol)

          set({
            token: respuesta.token_acceso,
            usuario: usuarioAutenticado,
            expiraEn: Date.now() + respuesta.expira_en_segundos * 1000,
            cargando: false,
            error: null,
            aviso: null,
          })

          // Devuelve información completa para la redirección limpia
          return {
            ok: true,
            usuario: usuarioAutenticado,
            rol: usuarioAutenticado?.rol,
            ruta: rutaPrincipal,
          }
        } catch (error) {
          purgarAlmacenamientoLocal()
          set({
            ...sinSesion,
            cargando: false,
            error: error.message || 'Error al autenticar las credenciales.',
          })
          return false
        }
      },

      salir(aviso = null) {
        // Limpieza atómica de almacenamiento y estado en memoria
        purgarAlmacenamientoLocal()
        try {
          useCarrito.getState().limpiarCarrito?.()
        } catch {
          // Si el store de carrito aún no está inicializado
        }
        set({
          ...sinSesion,
          cargando: false,
          error: null,
          aviso,
        })
      },

      limpiarMensajes() {
        set({ error: null, aviso: null })
      },
    }),
    {
      name: 'sesion',
      storage: createJSONStorage(() => sessionStorage),
      partialize: ({ token, usuario, expiraEn }) => ({ token, usuario, expiraEn }),
    },
  ),
)

// Selector: hay sesión y no ha vencido.
export const sesionVigente = (estado) => estado.token !== null && estado.expiraEn > Date.now()

configurarSesion({
  obtenerToken: () => useSesion.getState().token,
  alNoAutorizado: (mensaje) => useSesion.getState().salir(mensaje),
})
