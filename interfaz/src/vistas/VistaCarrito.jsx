import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Minus,
  Plus,
  ShoppingBag,
  Trash2,
  X,
} from 'lucide-react'
import {
  seleccionarCantidadTotal,
  seleccionarTotal,
  useCarrito,
} from '../modelosVista/useCarrito'
import { useSesion } from '../modelosVista/useSesion'
import { formatearPrecio } from '../modelosVista/stock'
import { obtenerDetallesPrenda } from '../servicios/imagenesPrendas'

export default function VistaCarrito() {
  // Lectura del ViewModel (useCarrito)
  const productos = useCarrito((s) => s.productos)
  const abierto = useCarrito((s) => s.abierto)
  const cerrarCarrito = useCarrito((s) => s.cerrarCarrito)
  const eliminarProducto = useCarrito((s) => s.eliminarProducto)
  const actualizarCantidad = useCarrito((s) => s.actualizarCantidad)
  const limpiarCarrito = useCarrito((s) => s.limpiarCarrito)
  const cantidadTotal = useCarrito(seleccionarCantidadTotal)
  const total = useCarrito(seleccionarTotal)

  // Token de sesión
  const token = useSesion((s) => s.token)
  const navegar = useNavigate()

  const [procesando, setProcesando] = useState(false)
  const [mensajeEstado, setMensajeEstado] = useState(null)

  if (!abierto) return null

  // Acción "Confirmar y Pagar" hacia POST /pedidos con idempotencia
  async function confirmarYPagar() {
    if (productos.length === 0) return

    setProcesando(true)
    setMensajeEstado(null)

    try {
      for (const prod of productos) {
        const id = prod.producto_id ?? prod.id
        const claveIdempotencia = crypto.randomUUID()

        const respuesta = await fetch('/api/pedidos', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Accept: 'application/json',
            Authorization: `Bearer ${token}`,
            'Idempotency-Key': claveIdempotencia,
          },
          body: JSON.stringify({
            producto_id: id,
            cantidad: prod.cantidad,
          }),
        })

        if (!respuesta.ok) {
          const errorData = await respuesta.json().catch(() => null)
          throw new Error(
            errorData?.detail || `Error al procesar producto #${id} (código ${respuesta.status})`
          )
        }
      }

      limpiarCarrito()
      setMensajeEstado({
        tipo: 'exito',
        texto: 'Pedido confirmado exitosamente. Procesando orden en pasarela.',
      })

      setTimeout(() => {
        cerrarCarrito()
        navegar('/pedidos')
      }, 1500)
    } catch (error) {
      setMensajeEstado({
        tipo: 'error',
        texto: error.message || 'Error en la comunicación con la pasarela de pagos.',
      })
    } finally {
      setProcesando(false)
    }
  }

  return (
    <aside
      className="fixed inset-0 z-50 flex justify-end"
      role="dialog"
      aria-modal="true"
      aria-labelledby="titulo-bolsa-kyro"
    >
      {/* Backdrop con blur sutil */}
      <div
        className="fixed inset-0 bg-[#293241]/60 backdrop-blur-sm transition-opacity duration-300"
        onClick={cerrarCarrito}
      />

      {/* Panel Lateral Drawer (Completamente plano, editorial) */}
      <div className="relative z-10 w-full max-w-md h-full bg-white text-[#1e1e1e] flex flex-col shadow-2xl animate-in slide-in-from-right duration-300 border-l border-[#293241]/10">
        
        {/* Cabecera (#293241 Navy) */}
        <header className="flex items-center justify-between px-6 py-5 bg-[#293241] text-white">
          <div className="flex items-center gap-3">
            <ShoppingBag className="w-5 h-5 text-[#e0fbfc]" />
            <h2 id="titulo-bolsa-kyro" className="text-xs uppercase tracking-[0.25em] font-black text-white">
              Bolsa de Compras
            </h2>
            <span className="text-[10px] tracking-widest px-2 py-0.5 bg-[#ee6c4d] text-white font-bold">
              {cantidadTotal} {cantidadTotal === 1 ? 'ITEM' : 'ITEMS'}
            </span>
          </div>

          <button
            type="button"
            onClick={cerrarCarrito}
            className="p-1 text-white/80 hover:text-white transition-colors"
            aria-label="Cerrar bolsa"
          >
            <X className="w-5 h-5" />
          </button>
        </header>

        {/* Mensaje de Estado */}
        {mensajeEstado && (
          <div
            className={`flex items-center gap-3 mx-6 mt-4 p-3 text-xs tracking-wide font-medium ${
              mensajeEstado.tipo === 'error'
                ? 'bg-red-50 text-red-800 border-l-2 border-red-600'
                : 'bg-emerald-50 text-emerald-800 border-l-2 border-emerald-600'
            }`}
          >
            {mensajeEstado.tipo === 'error' ? (
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
            ) : (
              <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
            )}
            <span>{mensajeEstado.texto}</span>
          </div>
        )}

        {/* Lista de Productos */}
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
          {productos.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center py-16 text-[#3d5a80]">
              <ShoppingBag className="w-12 h-12 stroke-[1] mb-3 opacity-40" />
              <p className="text-xs uppercase tracking-[0.2em] font-bold text-[#1e1e1e] mb-1">
                Tu bolsa está vacía
              </p>
              <p className="text-[11px] font-light max-w-xs text-[#3d5a80]/80">
                Selecciona prendas del catálogo para incorporarlas a tu pedido.
              </p>
            </div>
          ) : (
            <ul className="divide-y divide-[#293241]/10">
              {productos.map((prod) => {
                const id = prod.producto_id ?? prod.id
                const detalles = obtenerDetallesPrenda(id, prod.nombre)
                const imagenItem = prod.imagen_url || prod.imagen || detalles.url

                return (
                  <li key={id} className="py-4 first:pt-0 last:pb-0 flex gap-4">
                    <img
                      src={imagenItem}
                      alt={prod.nombre}
                      className="w-20 h-24 object-cover object-center bg-[#f4fbfb] border border-[#293241]/10 flex-shrink-0"
                    />

                    <div className="flex-1 flex flex-col justify-between">
                      <div>
                        <div className="flex justify-between items-start gap-2">
                          <h4 className="text-xs uppercase tracking-wider font-bold text-[#1e1e1e] line-clamp-1">
                            {prod.nombre}
                          </h4>
                          <button
                            type="button"
                            onClick={() => eliminarProducto(id)}
                            disabled={procesando}
                            className="text-[#3d5a80]/60 hover:text-red-600 transition-colors p-0.5"
                            title="Eliminar de la bolsa"
                            aria-label={`Eliminar ${prod.nombre}`}
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                        <span className="text-[11px] text-[#3d5a80] font-mono block mt-0.5">
                          {formatearPrecio(prod.precio)} c/u
                        </span>
                      </div>

                      {/* Controles de Cantidad y Subtotal */}
                      <div className="flex justify-between items-end pt-2">
                        <div className="inline-flex items-center border border-[#293241]/20 bg-white">
                          <button
                            type="button"
                            onClick={() => actualizarCantidad(id, prod.cantidad - 1)}
                            disabled={procesando}
                            className="w-7 h-7 flex items-center justify-center text-[#1e1e1e] hover:bg-[#e0fbfc]/30 transition-colors disabled:opacity-30"
                            aria-label="Disminuir"
                          >
                            <Minus className="w-3 h-3" />
                          </button>
                          <span className="w-7 text-center text-xs font-bold tabular-nums">
                            {prod.cantidad}
                          </span>
                          <button
                            type="button"
                            onClick={() => actualizarCantidad(id, prod.cantidad + 1)}
                            disabled={prod.cantidad >= (prod.disponibles ?? 99) || procesando}
                            className="w-7 h-7 flex items-center justify-center text-[#1e1e1e] hover:bg-[#e0fbfc]/30 transition-colors disabled:opacity-30"
                            aria-label="Aumentar"
                          >
                            <Plus className="w-3 h-3" />
                          </button>
                        </div>

                        <span className="text-xs font-bold tabular-nums text-[#293241]">
                          {formatearPrecio(prod.precio * prod.cantidad)}
                        </span>
                      </div>
                    </div>
                  </li>
                )
              })}
            </ul>
          )}
        </div>

        {/* Resumen y Botón Pagar (#ee6c4d Coral) */}
        {productos.length > 0 && (
          <footer className="border-t border-[#293241]/10 p-6 bg-white space-y-4">
            <div className="space-y-1.5">
              <div className="flex justify-between text-[11px] uppercase tracking-wider text-[#3d5a80]">
                <span>Subtotal ({cantidadTotal} piezas)</span>
                <span className="font-mono">{formatearPrecio(total)}</span>
              </div>
              <div className="flex justify-between text-[11px] uppercase tracking-wider text-[#3d5a80]">
                <span>Despacho Editorial</span>
                <span className="font-mono text-emerald-700 font-bold">GRATUITO</span>
              </div>
              <div className="flex justify-between items-baseline pt-2 border-t border-[#293241]/10">
                <span className="text-xs uppercase tracking-[0.2em] font-black text-[#1e1e1e]">
                  Total a Pagar
                </span>
                <strong className="text-xl font-black text-[#293241] tabular-nums">
                  {formatearPrecio(total)}
                </strong>
              </div>
            </div>

            <div className="grid grid-cols-[1fr_2fr] gap-2 pt-2">
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
                onClick={confirmarYPagar}
                disabled={procesando}
                className="py-3.5 px-4 bg-[#ee6c4d] hover:bg-[#d95b3d] text-white text-xs uppercase tracking-[0.25em] font-black flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
              >
                <span>{procesando ? 'Procesando...' : 'Pagar Pedido'}</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </footer>
        )}
      </div>
    </aside>
  )
}
