// ViewModel de la compra del carrito: en qué etapa va y cómo terminó.
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

// `alPagar` se llama solo si el pago se aprobó (ahí se vacía el carrito).
export function useCompra(alPagar) {
  const [etapa, setEtapa] = useState(null) // null | 'reservando' | 'pagando'
  const [resultado, setResultado] = useState(null) // { tipo: 'exito' | 'error' | 'aviso', texto }

  async function comprar(items) {
    if (items.length === 0) return
    setEtapa('reservando')
    setResultado(null)
    try {
      // Una clave nueva por cada clic en Pagar (crypto.randomUUID existe en localhost y HTTPS).
      const reservado = await comprarEnApi(items, crypto.randomUUID())
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
          texto: `Pedido #${pedido.pedido_id} pagado por ${formatearPrecio(pedido.total)}.`,
        })
        alPagar(pedido)
      } else {
        setResultado({
          tipo: 'error',
          texto: `El pago del pedido #${pedido.pedido_id} no se pudo completar. El stock quedó libre.`,
        })
      }
    } catch (error) {
      setResultado({ tipo: 'error', texto: error.message })
    } finally {
      setEtapa(null)
    }
  }

  return { etapa, resultado, comprar, limpiarResultado: () => setResultado(null) }
}
