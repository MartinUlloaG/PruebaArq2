import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Package, RefreshCw } from 'lucide-react'
import { formatearPrecio } from '../modelosVista/stock'
import { useRecurso } from '../modelosVista/useRecurso'
import { listarMisPedidos } from '../servicios/pedidos'
import EstadoCarga from './EstadoCarga'

// Estados de la Saga, en texto (no solo color).
const ESTADOS = {
  stock_reservado: { texto: 'Pago en proceso', clase: 'bg-amber-50 text-amber-800 border-amber-300' },
  pagado: { texto: 'Pagado', clase: 'bg-emerald-50 text-emerald-800 border-emerald-300' },
  fallido: { texto: 'Pago fallido, stock devuelto', clase: 'bg-red-50 text-red-800 border-red-300' },
  pendiente: { texto: 'Pendiente', clase: 'bg-gray-50 text-gray-700 border-gray-300' },
}

const formatoFecha = new Intl.DateTimeFormat('es-CL', { dateStyle: 'short', timeStyle: 'short' })

export default function VistaPedidos() {
  const navegar = useNavigate()
  const { datos, cargando, error, reintentar, recargar } = useRecurso(listarMisPedidos)
  const pedidos = datos ?? []
  const hayEnProceso = pedidos.some((p) => p.estado === 'stock_reservado')

  // Mientras algún pago siga en proceso, se vuelve a consultar cada 2 segundos.
  useEffect(() => {
    if (!hayEnProceso) return
    const intervalo = setInterval(recargar, 2000)
    return () => clearInterval(intervalo)
  }, [hayEnProceso, recargar])

  return (
    <div className="max-w-5xl mx-auto px-4 py-12">
      <header className="flex justify-between items-end border-b border-[#293241]/10 pb-6 mb-8">
        <div>
          <span className="text-[10px] uppercase tracking-[0.3em] text-[#3d5a80] font-bold block mb-1">
            Guardados en el servicio de compras
          </span>
          <h1 className="text-3xl font-black uppercase tracking-tight text-[#1e1e1e]">Mis Pedidos</h1>
        </div>
        <button
          type="button"
          onClick={recargar}
          className="inline-flex items-center gap-2 px-4 py-2 bg-[#293241] hover:bg-[#3d5a80] text-white text-xs uppercase tracking-widest font-bold"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Actualizar</span>
        </button>
      </header>

      <EstadoCarga cargando={cargando && pedidos.length === 0} error={error} reintentar={reintentar}>
        {pedidos.length === 0 ? (
          <div className="p-16 border border-dashed border-[#293241]/20 text-center">
            <Package className="w-8 h-8 text-[#3d5a80] mx-auto mb-3 opacity-40" />
            <p className="text-xs uppercase tracking-widest font-bold text-[#1e1e1e] mb-4">Aún no tienes pedidos</p>
            <button
              type="button"
              onClick={() => navegar('/catalogo')}
              className="px-6 py-2.5 bg-[#ee6c4d] text-white text-xs uppercase tracking-widest font-bold"
            >
              Ir al catálogo
            </button>
          </div>
        ) : (
          <ul className="space-y-4">
            {pedidos.map((p) => {
              const estado = ESTADOS[p.estado] ?? { texto: p.estado, clase: 'border-gray-300' }
              return (
                <li
                  key={p.pedido_id}
                  className="p-6 border border-[#293241]/10 bg-white flex flex-col md:flex-row justify-between md:items-center gap-4"
                >
                  <div>
                    <span className="text-[10px] font-mono tracking-widest text-[#3d5a80] block mb-1">
                      PEDIDO #{p.pedido_id} — {formatoFecha.format(new Date(p.creado_en))}
                    </span>
                    <p className="text-xs uppercase tracking-wider font-bold text-[#1e1e1e]">
                      {p.items.map((i) => `${i.cantidad} × ${i.nombre}`).join(' • ')}
                    </p>
                  </div>
                  <div className="flex items-center gap-6">
                    <span className="text-sm font-bold font-mono text-[#293241]">{formatearPrecio(p.total)}</span>
                    <span className={`px-3 py-1 text-[10px] uppercase tracking-widest font-bold border ${estado.clase}`}>
                      {estado.texto}
                    </span>
                  </div>
                </li>
              )
            })}
          </ul>
        )}
      </EstadoCarga>
    </div>
  )
}
