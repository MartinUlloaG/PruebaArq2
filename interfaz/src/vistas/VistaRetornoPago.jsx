import { useNavigate, useSearchParams } from 'react-router-dom'
import { AlertCircle, CheckCircle2, Clock } from 'lucide-react'
import { formatearPrecio } from '../modelosVista/stock'
import { useRetornoPago } from '../modelosVista/useRetornoPago'

// Aquí vuelve el comprador desde la pasarela (url_retorno?token_ws=...).
export default function VistaRetornoPago() {
  const [parametros] = useSearchParams()
  const { cargando, pedido, error } = useRetornoPago(parametros.get('token_ws'))
  const navegar = useNavigate()

  let contenido
  if (cargando) {
    contenido = {
      Icono: Clock,
      clase: 'border-[#293241] bg-[#f4fbfb] text-[#293241]',
      titulo: 'Confirmando tu pago',
      texto: 'Estamos confirmando el cobro con la pasarela. No cierres esta página.',
    }
  } else if (error) {
    contenido = { Icono: AlertCircle, clase: 'border-red-600 bg-red-50 text-red-800', titulo: 'No pudimos confirmar el pago', texto: error }
  } else if (pedido.estado === 'pagado') {
    contenido = {
      Icono: CheckCircle2,
      clase: 'border-emerald-600 bg-emerald-50 text-emerald-800',
      titulo: 'Pago aprobado',
      texto: `Pedido #${pedido.pedido_id} pagado por ${formatearPrecio(pedido.total)} con ${pedido.pago?.medio}.`,
    }
  } else if (pedido.estado === 'fallido') {
    contenido = {
      Icono: AlertCircle,
      clase: 'border-red-600 bg-red-50 text-red-800',
      titulo: 'Pago rechazado',
      texto: `${pedido.pago?.motivo ?? 'La pasarela rechazó el pago.'} No se hizo ningún cobro y el stock que tenías reservado quedó libre.`,
    }
  } else {
    contenido = {
      Icono: Clock,
      clase: 'border-amber-600 bg-amber-50 text-amber-800',
      titulo: 'El pago se está demorando',
      texto: `Pedido #${pedido.pedido_id}: revisa Mis pedidos en un rato. Si no se confirma, la reserva vence sola y no se cobra.`,
    }
  }
  const { Icono } = contenido

  return (
    <div className="max-w-xl mx-auto px-4 py-16">
      <span className="text-[10px] uppercase tracking-[0.3em] text-[#3d5a80] font-bold block mb-1">De vuelta de la pasarela</span>
      <h1 className="text-3xl font-black uppercase tracking-tight text-[#1e1e1e] mb-8">Resultado del pago</h1>

      <div className={`p-6 border-l-2 ${contenido.clase}`} aria-live="polite">
        <p className="flex items-center gap-3 text-sm font-bold uppercase tracking-widest">
          <Icono className="w-5 h-5 flex-shrink-0" />
          <span>{contenido.titulo}</span>
        </p>
        <p className="mt-3 ml-8 text-sm">{contenido.texto}</p>
      </div>

      {!cargando && (
        <div className="mt-8 grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={() => navegar('/pedidos')}
            className="py-3 px-4 border border-[#293241]/20 hover:border-[#293241] text-[11px] uppercase tracking-widest font-bold text-[#293241]"
          >
            Ver mis pedidos
          </button>
          <button
            type="button"
            onClick={() => navegar('/catalogo')}
            className="py-3 px-4 bg-[#ee6c4d] hover:bg-[#d95b3d] text-white text-[11px] uppercase tracking-widest font-bold"
          >
            Seguir comprando
          </button>
        </div>
      )}
    </div>
  )
}
