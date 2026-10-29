import { ShoppingBag } from 'lucide-react'
import { useCarrito } from '../modelosVista/useCarrito'
import { formatearPrecio } from '../modelosVista/stock'
import { useRecurso } from '../modelosVista/useRecurso'
import { listarRecomendaciones } from '../servicios/catalogo'

// Servicio secundario: si se cae, aquí solo aparece un aviso y el resto del catálogo sigue igual.
export default function Recomendaciones() {
  const { datos } = useRecurso(listarRecomendaciones)
  const agregarProducto = useCarrito((s) => s.agregarProducto)

  if (!datos) return null
  if (!datos.disponible) {
    return (
      <p role="status" className="mb-8 p-3 text-xs text-[#3d5a80] border border-dashed border-[#293241]/20">
        Las recomendaciones no están disponibles en este momento. Puedes seguir comprando normalmente.
      </p>
    )
  }
  if (datos.productos.length === 0) return null

  return (
    <section aria-labelledby="titulo-recomendaciones" className="mb-10">
      <h2
        id="titulo-recomendaciones"
        className="text-[10px] uppercase tracking-[0.3em] text-[#3d5a80] font-bold mb-3"
      >
        Te puede interesar · Los más vendidos
      </h2>
      <ul className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {datos.productos.map((p) => (
          <li key={p.producto_id} className="p-3 border border-[#293241]/10 bg-[#f4fbfb] flex flex-col">
            <span className="text-xs font-bold uppercase tracking-wider">{p.nombre}</span>
            <span className="text-xs text-[#3d5a80] mt-1">{formatearPrecio(p.precio)}</span>
            <button
              type="button"
              onClick={() => agregarProducto(p)}
              className="mt-2 self-start inline-flex items-center gap-1 text-[10px] uppercase tracking-widest font-bold text-[#ee6c4d] hover:underline"
            >
              <ShoppingBag className="w-3 h-3" /> Agregar
              <span className="sr-only"> {p.nombre}</span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}
