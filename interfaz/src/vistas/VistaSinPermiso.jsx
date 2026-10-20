import { Link } from 'react-router-dom'

import { ROLES } from '../modelosVista/roles'
import { useSesion } from '../modelosVista/useSesion'
import { IconoCandado } from './Iconos'

export default function VistaSinPermiso() {
  const rol = useSesion((s) => s.usuario?.rol)

  return (
    <div className="sin-permiso">
      <IconoCandado />
      <h1>No tienes acceso a esta sección</h1>
      <p className="bajada">
        Tu cuenta es de {ROLES[rol]?.nombre.toLowerCase() ?? 'otro rol'} y esta sección es para
        otro rol. Si necesitas entrar, pídele acceso a un administrador.
      </p>
      <Link to="/" className="boton-secundario">
        Volver al inicio
      </Link>
    </div>
  )
}
