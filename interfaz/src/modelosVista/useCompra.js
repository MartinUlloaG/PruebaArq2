// ViewModel de la compra: qué producto se está comprando y cómo terminó la última compra.
import { useState } from 'react'

import { comprar as comprarEnApi } from '../servicios/pedidos'
import { formatearPrecio } from './stock'

// `alTerminar` recarga el catálogo: tras comprar (o tras un 409) el stock mostrado cambió.
export function useCompra(alTerminar) {
  const [comprando, setComprando] = useState(null) // producto_id en curso
  const [resultado, setResultado] = useState(null) // { tipo: 'exito' | 'error', texto }

  async function comprar(producto) {
    setComprando(producto.producto_id)
    setResultado(null)
    try {
      const pedido = await comprarEnApi(producto.producto_id, 1)
      setResultado({
        tipo: 'exito',
        texto: `Pedido #${pedido.pedido_id}: reservaste ${producto.nombre} por ${formatearPrecio(pedido.total)}.`,
      })
    } catch (error) {
      setResultado({ tipo: 'error', texto: error.message })
    } finally {
      setComprando(null)
      alTerminar()
    }
  }

  return { comprando, resultado, comprar }
}
