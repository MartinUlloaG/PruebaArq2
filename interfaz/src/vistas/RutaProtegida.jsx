import { Navigate, useLocation } from 'react-router-dom'

import { sesionVigente, useSesion } from '../modelosVista/useSesion'
import VistaSinPermiso from './VistaSinPermiso'

// Sin sesión: al login, recordando a dónde quería ir. Con rol no permitido: aviso de acceso.
// Es solo comodidad de interfaz; la API vuelve a verificar y responde 401/403.
export default function RutaProtegida({ roles, children }) {
  const vigente = useSesion(sesionVigente)
  const rol = useSesion((s) => s.usuario?.rol)
  const ubicacion = useLocation()

  if (!vigente) return <Navigate to="/ingresar" replace state={{ desde: ubicacion.pathname }} />
  if (roles && !roles.includes(rol)) return <VistaSinPermiso />
  return children
}
