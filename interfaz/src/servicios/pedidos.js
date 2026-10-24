import { pedir } from './clienteApi'

// Solo clientes: la API responde 403 a los demás roles.
// La clave de idempotencia identifica ESTA compra: si la solicitud se repite
// (reintento de red), el servidor devuelve la misma respuesta y no cobra dos veces.
export function comprar(productoId, cantidad, claveIdempotencia) {
  return pedir('/pedidos', {
    metodo: 'POST',
    cuerpo: { producto_id: productoId, cantidad },
    encabezadosExtra: { 'Idempotency-Key': claveIdempotencia },
  })
}

// Para seguir el pago: stock_reservado (en proceso), pagado o fallido.
export function obtenerPedido(pedidoId) {
  return pedir(`/pedidos/${pedidoId}`)
}

export function listarMisPedidos() {
  return pedir('/pedidos')
}
