// ViewModel genérico para listas que vienen de la API: datos, carga y error.
import { useCallback, useEffect, useState } from 'react'

// `cargar` debe ser una función estable (definida a nivel de módulo), si no se recarga en cada render.
export function useRecurso(cargar) {
  const [estado, setEstado] = useState({ datos: null, error: null, cargando: true })
  const [intento, setIntento] = useState(0)

  useEffect(() => {
    let vigente = true // evita escribir estado si la vista ya se desmontó
    cargar()
      .then((datos) => vigente && setEstado({ datos, error: null, cargando: false }))
      .catch((error) => vigente && setEstado({ datos: null, error: error.message, cargando: false }))
    return () => {
      vigente = false
    }
  }, [cargar, intento])

  const reintentar = useCallback(() => {
    setEstado((anterior) => ({ ...anterior, error: null, cargando: true }))
    setIntento((n) => n + 1)
  }, [])

  // Vuelve a pedir los datos sin mostrar "Cargando…": la lista no parpadea ni pierde el foco.
  // Estable entre renders (useCallback), así se puede usar en un setInterval.
  const recargar = useCallback(() => setIntento((n) => n + 1), [])

  return { ...estado, reintentar, recargar }
}
