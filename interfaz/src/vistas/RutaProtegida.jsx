import { Navigate, useLocation } from 'react-router-dom'
import { sesionVigente, useSesion } from '../modelosVista/useSesion'
import VistaSinPermiso from './VistaSinPermiso'

/**
 * Guardián de Rutas MVVM.
 * Si no hay sesión válida: redirige a /ingresar guardando la ruta intentada.
 * Si el rol no está autorizado para esta vista: despliega la VistaSinPermiso informando al usuario.
 */
export default function RutaProtegida({ roles, children }) {
  const vigente = useSesion(sesionVigente)
  const usuario = useSesion((s) => s.usuario)
  const rol = usuario?.rol
  const ubicacion = useLocation()

  if (!vigente || !usuario) {
    return <Navigate to="/ingresar" replace state={{ desde: ubicacion.pathname }} />
  }

  if (roles && !roles.includes(rol)) {
    return <VistaSinPermiso />
  }

  return children
}
