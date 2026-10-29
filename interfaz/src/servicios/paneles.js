import { pedir } from './clienteApi'

// Operador y Administrador: stock actual de cada producto.
export function listarInventario() {
  return pedir('/inventario')
}

// Operador y Administrador: recepción (ajuste_entrada) o merma (ajuste_salida).
export function ajustarStock(productoId, cantidad, tipo) {
  return pedir(`/inventario/${productoId}`, {
    metodo: 'PATCH',
    cuerpo: { cantidad: Number(cantidad), tipo },
  })
}

// Solo Administrador: cuentas registradas.
export function listarUsuarios() {
  return pedir('/administracion/usuarios')
}

// Solo Administrador: totales de pedidos, ingresos y stock crítico.
export function obtenerResumenAdmin() {
  return pedir('/administracion/resumen')
}
