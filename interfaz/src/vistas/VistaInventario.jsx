import { estadoStock } from '../modelosVista/stock'
import { useRecurso } from '../modelosVista/useRecurso'
import { listarInventario } from '../servicios/paneles'
import EstadoCarga from './EstadoCarga'

export default function VistaInventario() {
  const { datos, cargando, error, reintentar } = useRecurso(listarInventario)

  return (
    <>
      <h1>Inventario</h1>
      <p className="bajada">Unidades disponibles para vender de cada producto.</p>
      <EstadoCarga cargando={cargando} error={error} reintentar={reintentar}>
        <table className="tabla">
          <caption className="solo-lector">Stock por producto</caption>
          <thead>
            <tr>
              <th scope="col">Producto</th>
              <th scope="col" className="numero">
                Unidades
              </th>
              <th scope="col">Estado</th>
            </tr>
          </thead>
          <tbody>
            {datos?.map((fila) => {
              const estado = estadoStock(fila.cantidad)
              return (
                <tr key={fila.producto_id}>
                  <th scope="row">{fila.nombre}</th>
                  <td className="numero">{fila.cantidad}</td>
                  <td>
                    <span className={`estado-stock estado-stock--${estado.clase}`}>{estado.texto}</span>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </EstadoCarga>
    </>
  )
}
