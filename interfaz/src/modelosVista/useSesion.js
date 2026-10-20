// (El prefijo "use" lo exige React para reconocer hooks.)
// ViewModel de la sesión: estado del usuario autenticado y acciones para entrar y salir.
// Las vistas leen de aquí con selectores; nunca llaman a la API directamente.
import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'

import { ingresar as ingresarEnApi } from '../servicios/autenticacion'
import { configurarSesion } from '../servicios/clienteApi'

const sinSesion = { token: null, usuario: null, expiraEn: null }

export const useSesion = create(
  persist(
    (set) => ({
      ...sinSesion,
      cargando: false,
      error: null, // por qué falló el último ingreso
      aviso: null, // por qué se cerró la sesión (ej. venció)

      async ingresar(correo, clave) {
        set({ cargando: true, error: null, aviso: null })
        try {
          const respuesta = await ingresarEnApi(correo, clave)
          set({
            token: respuesta.token_acceso,
            usuario: respuesta.usuario,
            expiraEn: Date.now() + respuesta.expira_en_segundos * 1000,
            cargando: false,
          })
          return true
        } catch (error) {
          set({ cargando: false, error: error.message })
          return false
        }
      },

      salir(aviso = null) {
        set({ ...sinSesion, error: null, aviso })
      },

      limpiarMensajes() {
        set({ error: null, aviso: null })
      },
    }),
    {
      name: 'sesion',
      // sessionStorage: la sesión muere al cerrar la pestaña. (Alternativa más segura:
      // cookie httpOnly, que JavaScript no puede leer; queda declarada en el ADR.)
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
