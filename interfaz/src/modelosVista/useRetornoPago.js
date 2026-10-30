// ViewModel de la vuelta desde la pasarela: confirmar el pago y esperar el resultado de la Saga.
import { useEffect, useRef, useState } from 'react'

import { confirmarPago, obtenerPedido } from '../servicios/pedidos'
import { useCarrito } from './useCarrito'

// El cobro se confirma por Kafka (servicio de pagos -> pasarela): se consulta cada segundo.
const ESPERA_MS = 1000
const MAXIMO_CONSULTAS = 30

const pausa = (ms) => new Promise((listo) => setTimeout(listo, ms))

export function useRetornoPago(token) {
  const [estado, setEstado] = useState({ cargando: true, pedido: null, error: null })
  const iniciado = useRef(false)

  useEffect(() => {
    // StrictMode corre el efecto dos veces. Igual daría lo mismo: el servidor pide la
    // confirmación una sola vez por pedido.
    if (iniciado.current) return
    iniciado.current = true

    async function confirmar() {
      try {
        if (!token) throw new Error('Falta el comprobante de la pasarela de pago.')
        let pedido = await confirmarPago(token)
        for (let i = 0; pedido.estado === 'stock_reservado' && i < MAXIMO_CONSULTAS; i++) {
          await pausa(ESPERA_MS)
          pedido = await obtenerPedido(pedido.pedido_id)
        }
        // El carrito se vacía solo si se cobró; si no, queda para intentarlo de nuevo.
        if (pedido.estado === 'pagado') useCarrito.getState().limpiarCarrito()
        setEstado({ cargando: false, pedido, error: null })
      } catch (error) {
        setEstado({ cargando: false, pedido: null, error: error.message })
      }
    }
    confirmar()
  }, [token])

  return estado
}
