import { Link } from 'react-router-dom'

import { ROLES, seccionesPara } from '../modelosVista/roles'
import { useSesion } from '../modelosVista/useSesion'
import Catalogo from './Catalogo'

export default function VistaInicio() {
  const usuario = useSesion((s) => s.usuario)
  const secciones = seccionesPara(usuario.rol)

  return (
    <>
      <h1>Hola, {usuario.correo.split('@')[0]}</h1>
      <p className="bajada">
        Ingresaste como <strong>{ROLES[usuario.rol].nombre.toLowerCase()}</strong>.{' '}
        {ROLES[usuario.rol].puede}
      </p>

      {usuario.rol !== 'cliente' ? (
        <ul className="accesos">
          {secciones.map((s) => (
            <li key={s.ruta}>
              <Link to={s.ruta} className="acceso">
                <span className="acceso__nombre">{s.nombre}</span>
                <span className="acceso__descripcion">{s.descripcion}</span>
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <Catalogo />
      )}
    </>
  )
}
