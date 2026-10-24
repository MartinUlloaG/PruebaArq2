// ViewModel de la compra: qué producto se está comprando y cómo terminó la última compra.
import { useState } from 'react'

import { comprar as comprarEnApi, obtenerPedido } from '../servicios/pedidos'
import { formatearPrecio } from './stock'

// El pago viaja por Kafka y se resuelve después: se consulta el pedido cada segundo.
const ESPERA_MS = 1000
const MAXIMO_CONSULTAS = 20

const pausa = (ms) => new Promise((listo) => setTimeout(listo, ms))

async function esperarPago(pedidoId) {
  for (let i = 0; i < MAXIMO_CONSULTAS; i++) {
    await pausa(ESPERA_MS)
    const pedido = await obtenerPedido(pedidoId)
    if (pedido.estado !== 'stock_reservado') return pedido
  }
  return null // sigue en proceso
}

// `alTerminar` recarga el catálogo: tras comprar, o si el pago falló y el stock volvió.
export function useCompra(alTerminar) {
  const [comprando, setComprando] = useState(null) // producto_id en curso
  const [etapa, setEtapa] = useState(null) // 'reservando' | 'pagando'
  const [resultado, setResultado] = useState(null) // { tipo: 'exito' | 'error' | 'aviso', texto }

  async function comprar(producto) {
    setComprando(producto.producto_id)
    setEtapa('reservando')
    setResultado(null)
    try {
      // Una clave nueva por cada clic en Comprar (crypto.randomUUID existe en localhost y HTTPS).
      const reservado = await comprarEnApi(producto.producto_id, 1, crypto.randomUUID())
      setEtapa('pagando')
      const pedido = await esperarPago(reservado.pedido_id)
      if (pedido === null) {
        setResultado({
          tipo: 'aviso',
          texto: `Pedido #${reservado.pedido_id}: el pago se está demorando. Revisa Mis pedidos en un rato.`,
        })
      } else if (pedido.estado === 'pagado') {
        setResultado({
          tipo: 'exito',
          texto: `Pedido #${pedido.pedido_id} pagado: compraste ${producto.nombre} por ${formatearPrecio(pedido.total)}.`,
        })
      } else {
        setResultado({
          tipo: 'error',
          texto: `El pago del pedido #${pedido.pedido_id} no se pudo completar. El stock quedó libre.`,
        })
      }
    } catch (error) {
      setResultado({ tipo: 'error', texto: error.message })
    } finally {
      setComprando(null)
      setEtapa(null)
      alTerminar()
    }
  }

  return { comprando, etapa, resultado, comprar }
}
