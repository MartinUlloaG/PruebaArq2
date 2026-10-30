import { useNavigate } from 'react-router-dom'
import { AlertCircle, ArrowRight, CheckCircle2, Clock, Minus, Plus, ShoppingBag, Trash2, X } from 'lucide-react'
import { seleccionarCantidadTotal, seleccionarTotal, useCarrito } from '../modelosVista/useCarrito'
import { useCompra } from '../modelosVista/useCompra'
import { formatearPrecio } from '../modelosVista/stock'

const ICONOS = { exito: CheckCircle2, error: AlertCircle, aviso: Clock }
const ESTILOS = {
  exito: 'bg-emerald-50 text-emerald-800 border-emerald-600',
  error: 'bg-red-50 text-red-800 border-red-600',
  aviso: 'bg-amber-50 text-amber-800 border-amber-600',
}

// `alTerminar` recarga el catálogo: después de comprar el stock mostrado cambió.
export default function VistaCarrito({ alTerminar = () => {} }) {
  const productos = useCarrito((s) => s.productos)
  const abierto = useCarrito((s) => s.abierto)
  const cerrarCarrito = useCarrito((s) => s.cerrarCarrito)
  const eliminarProducto = useCarrito((s) => s.eliminarProducto)
  const actualizarCantidad = useCarrito((s) => s.actualizarCantidad)
  const limpiarCarrito = useCarrito((s) => s.limpiarCarrito)
  const cantidadTotal = useCarrito(seleccionarCantidadTotal)
  const total = useCarrito(seleccionarTotal)
  const navegar = useNavigate()

  // ViewModel de la compra: reserva y manda a la pasarela. El carrito se vacía al volver, si se pagó.
  const { etapa, resultado, comprar } = useCompra()
  const procesando = etapa !== null

  if (!abierto) return null

  async function pagar() {
    await comprar(productos)
    alTerminar()
  }

  const Icono = resultado ? ICONOS[resultado.tipo] : null

  return (
    <aside className="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true" aria-labelledby="titulo-bolsa">
      <div className="fixed inset-0 bg-[#293241]/60 backdrop-blur-sm" onClick={procesando ? undefined : cerrarCarrito} />

      <div className="relative z-10 w-full max-w-md h-full bg-white text-[#1e1e1e] flex flex-col shadow-2xl border-l border-[#293241]/10">
        <header className="flex items-center justify-between px-6 py-5 bg-[#293241] text-white">
          <div className="flex items-center gap-3">
            <ShoppingBag className="w-5 h-5 text-[#e0fbfc]" />
            <h2 id="titulo-bolsa" className="text-xs uppercase tracking-[0.25em] font-black text-white">
              Bolsa de Compras
            </h2>
            <span className="text-[10px] tracking-widest px-2 py-0.5 bg-[#ee6c4d] text-white font-bold">
              {cantidadTotal} {cantidadTotal === 1 ? 'ITEM' : 'ITEMS'}
            </span>
          </div>
          <button
            type="button"
            onClick={cerrarCarrito}
            disabled={procesando}
            className="p-1 text-white/80 hover:text-white transition-colors"
            aria-label="Cerrar bolsa"
          >
            <X className="w-5 h-5" />
          </button>
        </header>

        {/* Resultado de la compra: región viva para que el lector de pantalla lo anuncie */}
        <div aria-live="polite">
          {procesando && (
            <p className="flex items-center gap-3 mx-6 mt-4 p-3 text-xs bg-[#f4fbfb] border-l-2 border-[#293241]">
              <Clock className="w-4 h-4 flex-shrink-0" />
              {
                {
                  reservando: 'Reservando el stock…',
                  en_fila: 'Hay mucha demanda: estás en la fila, reintentando…',
                  conectando: 'Stock reservado. Conectando con la pasarela de pago…',
                  redirigiendo: 'Te estamos llevando a la pasarela de pago…',
                }[etapa]
              }
            </p>
          )}
          {resultado && (
            <div className={`mx-6 mt-4 p-3 text-xs border-l-2 ${ESTILOS[resultado.tipo]}`}>
              <p className="flex items-center gap-3">
                <Icono className="w-4 h-4 flex-shrink-0" />
                <span>{resultado.texto}</span>
              </p>
              {resultado.tipo !== 'error' && (
                <button
                  type="button"
                  onClick={() => {
                    cerrarCarrito()
                    navegar('/pedidos')
                  }}
                  className="mt-2 ml-7 underline font-bold"
                >
                  Ver mis pedidos
                </button>
              )}
            </div>
          )}
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-6">
          {productos.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center py-16 text-[#3d5a80]">
              <ShoppingBag className="w-12 h-12 stroke-[1] mb-3 opacity-40" />
              <p className="text-xs uppercase tracking-[0.2em] font-bold text-[#1e1e1e]">Tu bolsa está vacía</p>
            </div>
          ) : (
            <ul className="divide-y divide-[#293241]/10">
              {productos.map((prod) => (
                <li key={prod.producto_id} className="py-4 first:pt-0 last:pb-0">
                  <div className="flex justify-between items-start gap-2">
                    <h3 className="text-xs uppercase tracking-wider font-bold text-[#1e1e1e]">{prod.nombre}</h3>
                    <button
                      type="button"
                      onClick={() => eliminarProducto(prod.producto_id)}
                      disabled={procesando}
                      className="text-[#3d5a80]/60 hover:text-red-600 transition-colors p-0.5"
                      aria-label={`Eliminar ${prod.nombre}`}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                  <span className="text-[11px] text-[#3d5a80] font-mono block mt-0.5">
                    {formatearPrecio(prod.precio)} c/u
                  </span>
                  <div className="flex justify-between items-end pt-2">
                    <div className="inline-flex items-center border border-[#293241]/20 bg-white">
                      <button
                        type="button"
                        onClick={() => actualizarCantidad(prod.producto_id, prod.cantidad - 1)}
                        disabled={procesando}
                        className="w-7 h-7 flex items-center justify-center hover:bg-[#e0fbfc]/30 disabled:opacity-30"
                        aria-label={`Quitar uno de ${prod.nombre}`}
                      >
                        <Minus className="w-3 h-3" />
                      </button>
                      <span className="w-7 text-center text-xs font-bold tabular-nums">{prod.cantidad}</span>
                      <button
                        type="button"
                        onClick={() => actualizarCantidad(prod.producto_id, prod.cantidad + 1)}
                        disabled={prod.cantidad >= prod.disponibles || procesando}
                        className="w-7 h-7 flex items-center justify-center hover:bg-[#e0fbfc]/30 disabled:opacity-30"
                        aria-label={`Agregar uno de ${prod.nombre}`}
                      >
                        <Plus className="w-3 h-3" />
                      </button>
                    </div>
                    <span className="text-xs font-bold tabular-nums text-[#293241]">
                      {formatearPrecio(prod.precio * prod.cantidad)}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        {productos.length > 0 && (
          <footer className="border-t border-[#293241]/10 p-6 bg-white space-y-4">
            <div className="flex justify-between items-baseline">
              <span className="text-xs uppercase tracking-[0.2em] font-black text-[#1e1e1e]">Total</span>
              <strong className="text-xl font-black text-[#293241] tabular-nums">{formatearPrecio(total)}</strong>
            </div>
            <div className="grid grid-cols-[1fr_2fr] gap-2">
              <button
                type="button"
                onClick={limpiarCarrito}
                disabled={procesando}
                className="py-3 px-3 border border-[#293241]/20 hover:border-[#293241] text-[11px] uppercase tracking-widest font-bold text-[#293241] transition-colors disabled:opacity-50"
              >
                Vaciar
              </button>
              <button
                type="button"
                onClick={pagar}
                disabled={procesando}
                className="py-3.5 px-4 bg-[#ee6c4d] hover:bg-[#d95b3d] text-white text-xs uppercase tracking-[0.25em] font-black flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
              >
                <span>{procesando ? 'Procesando…' : 'Ir a pagar'}</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </footer>
        )}
      </div>
    </aside>
  )
}
