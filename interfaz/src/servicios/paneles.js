import { pedir } from './clienteApi'

// Operador y Administrador: listar inventario actual con stocks y categorías
export function listarInventario() {
  return pedir('/inventario')
}

// Operador y Administrador: registrar ajustes o recepción de mercancía en tiempo real
export function ajustarStock(productoId, cantidad, tipo = 'ajuste_entrada') {
  return pedir(`/inventario/${productoId}`, {
    metodo: 'PATCH',
    cuerpo: {
      cantidad: Number(cantidad),
      tipo,
    },
  }).catch(() => {
    // Fallback retrocompatible por si el backend recibe POST /inventario/ajuste
    return pedir('/inventario/ajuste', {
      metodo: 'POST',
      cuerpo: {
        producto_id: Number(productoId),
        cantidad: Number(cantidad),
        tipo,
      },
    })
  })
}

// Solo Administrador: listar usuarios registrados
export function listarUsuarios() {
  return pedir('/administracion/usuarios')
}

// Solo Administrador: métricas de negocio ejecutivas (pedidos, ingresos, stock crítico)
export function obtenerResumenAdmin() {
  return pedir('/administracion/resumen')
}
