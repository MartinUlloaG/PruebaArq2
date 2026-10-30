import { useState } from 'react'

import { comprar as comprarEnApi, obtenerPedido } from '../servicios/pedidos'

// La transacción en la pasarela se crea por Kafka (servicio de pagos): se consulta el
// pedido hasta que aparece la URL donde se paga.
const ESPERA_MS = 700
const MAXIMO_CONSULTAS = 30
// Con mucha demanda la tienda responde 503 (load shedding): se reintenta con la MISMA
// clave de idempotencia, así un reintento nunca crea un segundo pedido.
const MAXIMO_REINTENTOS = 10

const pausa = (ms) => new Promise((listo) => setTimeout(listo, ms))

async function esperarUrlDePago(pedidoId) {
  for (let i = 0; i < MAXIMO_CONSULTAS; i++) {
    await pausa(ESPERA_MS)
    const pedido = await obtenerPedido(pedidoId)
    if (pedido.pago?.url_pago || pedido.estado !== 'stock_reservado') return pedido
  }
  return null // la pasarela no respondió a tiempo
}

async function reservar(items, clave, alEsperar) {
  for (let intento = 1; ; intento++) {
    try {
      return await comprarEnApi(items, clave)
    } catch (error) {
      if (error.estado !== 503 || intento === MAXIMO_REINTENTOS) throw error
      alEsperar()
      await pausa(2000 + Math.random() * 1000)
    }
  }
}

export function useCompra() {
  const [etapa, setEtapa] = useState(null) 
  const [resultado, setResultado] = useState(null) 

  async function comprar(items) {
    if (items.length === 0) return
    setEtapa('reservando')
    setResultado(null)
    try {
      
      const reservado = await reservar(items, crypto.randomUUID(), () => setEtapa('en_fila'))
      setEtapa('conectando')
      const pedido = await esperarUrlDePago(reservado.pedido_id)
      if (pedido?.pago?.url_pago) {
        setEtapa('redirigiendo')
        window.location.assign(pedido.pago.url_pago) 
        return
      }
      setResultado(
        pedido === null
          ? {
              tipo: 'aviso',
              texto: `Pedido #${reservado.pedido_id}: la pasarela de pago no responde. Tu stock queda reservado unos minutos; intenta pagar desde Mis pedidos.`,
            }
          : { tipo: 'error', texto: `No se pudo iniciar el pago del pedido #${pedido.pedido_id}. El stock quedó libre.` },
      )
    } catch (error) {
      setResultado({ tipo: 'error', texto: error.message })
    }
    setEtapa(null)
  }

  return { etapa, resultado, comprar, limpiarResultado: () => setResultado(null) }
}
