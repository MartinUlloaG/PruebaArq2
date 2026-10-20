import { ROLES } from '../modelosVista/roles'
import { useRecurso } from '../modelosVista/useRecurso'
import { listarUsuarios } from '../servicios/paneles'
import EstadoCarga from './EstadoCarga'

export default function VistaUsuarios() {
  const { datos, cargando, error, reintentar } = useRecurso(listarUsuarios)

  return (
    <>
      <h1>Usuarios</h1>
      <p className="bajada">Cuentas registradas en la tienda y el rol de cada una.</p>
      <EstadoCarga cargando={cargando} error={error} reintentar={reintentar}>
        <table className="tabla">
          <caption className="solo-lector">Usuarios y sus roles</caption>
          <thead>
            <tr>
              <th scope="col">Correo</th>
              <th scope="col">Rol</th>
            </tr>
          </thead>
          <tbody>
            {datos?.map((u) => (
              <tr key={u.id}>
                <th scope="row">{u.correo}</th>
                <td>
                  <span className={`etiqueta-rol etiqueta-rol--${u.rol}`}>{ROLES[u.rol].nombre}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </EstadoCarga>
    </>
  )
}
