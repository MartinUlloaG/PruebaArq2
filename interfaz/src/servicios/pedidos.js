import { pedir } from './clienteApi'

// Solo clientes: la API responde 403 a los demás roles.
export function comprar(productoId, cantidad) {
  return pedir('/pedidos', { metodo: 'POST', cuerpo: { producto_id: productoId, cantidad } })
}

export function listarMisPedidos() {
  return pedir('/pedidos')
}
