import { formatearPrecio } from '../modelosVista/stock'
import { useRecurso } from '../modelosVista/useRecurso'
import { listarMisPedidos } from '../servicios/pedidos'
import EstadoCarga from './EstadoCarga'

// Estados de la Saga: reservado (paso 1), pagado (confirmado) o fallido (stock devuelto).
const ESTADOS = {
  pendiente: 'Pendiente',
  stock_reservado: 'Pago en proceso',
  pagado: 'Pagado',
  fallido: 'Pago fallido, stock devuelto',
}

const formatoFecha = new Intl.DateTimeFormat('es-CL', { dateStyle: 'short', timeStyle: 'short' })

export default function VistaPedidos() {
  const { datos, cargando, error, reintentar } = useRecurso(listarMisPedidos)

  return (
    <>
      <h1>Mis pedidos</h1>
      <p className="bajada">Tus compras, guardadas en el servicio de compras.</p>
      <EstadoCarga cargando={cargando} error={error} reintentar={reintentar}>
        {datos?.length === 0 ? (
          <p className="vacio">Aún no tienes pedidos. Compra algo desde el inicio.</p>
        ) : (
          <table className="tabla">
            <caption className="solo-lector">Pedidos del cliente</caption>
            <thead>
              <tr>
                <th scope="col">Pedido</th>
                <th scope="col">Fecha</th>
                <th scope="col">Productos</th>
                <th scope="col" className="numero">
                  Total
                </th>
                <th scope="col">Estado</th>
              </tr>
            </thead>
            <tbody>
              {datos?.map((pedido) => (
                <tr key={pedido.pedido_id}>
                  <th scope="row">#{pedido.pedido_id}</th>
                  <td>{formatoFecha.format(new Date(pedido.creado_en))}</td>
                  <td>
                    {pedido.items.map((item) => `${item.cantidad} × ${item.nombre}`).join(', ')}
                  </td>
                  <td className="numero">{formatearPrecio(pedido.total)}</td>
                  <td>{ESTADOS[pedido.estado] ?? pedido.estado}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </EstadoCarga>
    </>
  )
}
