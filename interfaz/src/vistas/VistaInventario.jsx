import { useEffect, useMemo, useState } from 'react'
import { AlertTriangle, CheckCircle2, RefreshCw, Search } from 'lucide-react'
import { formatearPrecio, POCO_STOCK } from '../modelosVista/stock'
import { useRecurso } from '../modelosVista/useRecurso'
import { ajustarStock, listarInventario } from '../servicios/paneles'
import EstadoCarga from './EstadoCarga'

export default function VistaInventario() {
  const { datos, cargando, error, reintentar, recargar } = useRecurso(listarInventario)

  const [busqueda, setBusqueda] = useState('')
  const [categoriaSeleccionada, setCategoriaSeleccionada] = useState('Todos')
  const [filtroEstado, setFiltroEstado] = useState('todos') // 'todos' | 'critico' | 'agotado' | 'disponible'
  const [autoSincronizar, setAutoSincronizar] = useState(false)
  const [accionEnCurso, setAccionEnCurso] = useState(null) // ID del producto procesando ajuste
  const [mensajeExito, setMensajeExito] = useState(null)
  const [errorAjuste, setErrorAjuste] = useState(null)

  // Polling automático cada 5 segundos si el operador activa la sincronización en vivo
  useEffect(() => {
    if (!autoSincronizar) return
    const intervalo = setInterval(() => {
      recargar()
    }, 5000)
    return () => clearInterval(intervalo)
  }, [autoSincronizar, recargar])

  // Desvanecer alertas tras 4 segundos
  useEffect(() => {
    if (!mensajeExito) return
    const timer = setTimeout(() => setMensajeExito(null), 4000)
    return () => clearTimeout(timer)
  }, [mensajeExito])

  const listaProductos = useMemo(() => datos ?? [], [datos])

  // Las categorías salen de los productos que llegaron de la API.
  const categoriasFiltro = useMemo(
    () => ['Todos', ...new Set(listaProductos.map((p) => p.categoria).filter(Boolean))].sort((a, b) =>
      a === 'Todos' ? -1 : b === 'Todos' ? 1 : a.localeCompare(b),
    ),
    [listaProductos],
  )

  // Métricas operativas en tiempo real
  const metricas = useMemo(() => {
    const totalSKUs = listaProductos.length
    const unidadesTotales = listaProductos.reduce((acc, p) => acc + (p.cantidad || 0), 0)
    const criticos = listaProductos.filter((p) => p.cantidad > 0 && p.cantidad <= POCO_STOCK).length
    const agotados = listaProductos.filter((p) => p.cantidad === 0).length
    return { totalSKUs, unidadesTotales, criticos, agotados }
  }, [listaProductos])

  // Filtrado reactivo de la tabla de inventario
  const productosFiltrados = useMemo(() => {
    const termino = busqueda.trim().toLowerCase()
    return listaProductos.filter((p) => {
      // Filtro Categoría
      if (categoriaSeleccionada !== 'Todos') {
        const cat = (p.categoria || '').toLowerCase()
        if (cat !== categoriaSeleccionada.toLowerCase()) return false
      }

      // Filtro Estado
      if (filtroEstado === 'critico') {
        if (!(p.cantidad > 0 && p.cantidad <= POCO_STOCK)) return false
      } else if (filtroEstado === 'agotado') {
        if (p.cantidad !== 0) return false
      } else if (filtroEstado === 'disponible') {
        if (p.cantidad <= POCO_STOCK) return false
      }

      // Búsqueda por nombre o ID
      if (termino.length > 0) {
        const coincideNombre = String(p.nombre || '').toLowerCase().includes(termino)
        const coincideId = String(p.producto_id).includes(termino)
        if (!coincideNombre && !coincideId) return false
      }

      return true
    })
  }, [listaProductos, categoriaSeleccionada, filtroEstado, busqueda])

  // Recepción (+) o merma (-). Después se vuelve a leer el stock real desde la API.
  async function manejarAjuste(productoId, cantidad, tipo) {
    setAccionEnCurso(productoId)
    setErrorAjuste(null)
    try {
      await ajustarStock(productoId, cantidad, tipo)
      setMensajeExito(
        `${tipo === 'ajuste_entrada' ? `Recepción de ${cantidad}` : `Salida de ${cantidad}`} registrada para SKU #${productoId}.`,
      )
    } catch (err) {
      setErrorAjuste(err.message)
    } finally {
      recargar()
      setAccionEnCurso(null)
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 py-10 bg-white text-[#1e1e1e]">
      {/* 1. Header del Operador */}
      <header className="border-b border-[#293241]/10 pb-8 mb-8">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="w-2 h-2 rounded-full bg-[#ee6c4d]" />
              <span className="text-[10px] uppercase tracking-[0.3em] font-bold text-[#3d5a80]">
                PANEL OPERATIVO Y LOGÍSTICA / ROL OPERADOR
              </span>
            </div>
            <h1 className="text-3xl md:text-4xl font-black uppercase tracking-tight text-[#1e1e1e]">
              Control de Inventario KYRO
            </h1>
            <p className="text-xs uppercase tracking-[0.18em] text-[#3d5a80] font-light mt-1">
              Monitoreo en tiempo real de existencias, reservas y ajustes de almacén.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Interruptor de sincronización en vivo */}
            <label className="inline-flex items-center gap-2 px-3 py-2 border border-[#293241]/20 bg-gray-50 text-[11px] uppercase tracking-wider font-semibold cursor-pointer select-none">
              <input
                type="checkbox"
                checked={autoSincronizar}
                onChange={(e) => setAutoSincronizar(e.target.checked)}
                className="accent-[#ee6c4d]"
              />
              <span>Sincronización en Vivo (5s)</span>
            </label>

            {/* Botón Actualizar */}
            <button
              type="button"
              onClick={() => recargar()}
              disabled={cargando}
              className="inline-flex items-center gap-2 px-4 py-2 bg-[#293241] hover:bg-[#3d5a80] text-white text-xs uppercase tracking-widest font-bold transition-colors cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${cargando ? 'animate-spin' : ''}`} />
              <span>Actualizar</span>
            </button>
          </div>
        </div>

        {/* 2. Tarjetas KPI de Almacén */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-8">
          <div className="p-5 border border-[#293241]/10 bg-[#f4fbfb]/50">
            <span className="text-[10px] uppercase tracking-widest text-[#3d5a80] font-bold block mb-1">
              Total SKUs en Sistema
            </span>
            <p className="text-2xl font-black text-[#293241] tabular-nums">
              {metricas.totalSKUs}
            </p>
          </div>

          <div className="p-5 border border-[#293241]/10 bg-[#f4fbfb]/50">
            <span className="text-[10px] uppercase tracking-widest text-[#3d5a80] font-bold block mb-1">
              Unidades Totales Físicas
            </span>
            <p className="text-2xl font-black text-[#293241] tabular-nums">
              {metricas.unidadesTotales}
            </p>
          </div>

          <div className="p-5 border border-[#ee6c4d]/20 bg-[#ee6c4d]/5">
            <span className="text-[10px] uppercase tracking-widest text-[#ee6c4d] font-bold block mb-1">
              Stock Crítico (≤ 5)
            </span>
            <p className="text-2xl font-black text-[#ee6c4d] tabular-nums">
              {metricas.criticos}
            </p>
          </div>

          <div className="p-5 border border-red-200 bg-red-50/50">
            <span className="text-[10px] uppercase tracking-widest text-red-700 font-bold block mb-1">
              Agotados Sin Stock
            </span>
            <p className="text-2xl font-black text-red-800 tabular-nums">
              {metricas.agotados}
            </p>
          </div>
        </div>

        {/* Notificaciones de éxito o error */}
        {mensajeExito && (
          <div className="mt-4 p-4 bg-emerald-50 border-l-4 border-emerald-600 flex items-center gap-3 animate-fadeIn">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            <p className="text-xs text-emerald-800 font-medium tracking-wide">{mensajeExito}</p>
          </div>
        )}

        {errorAjuste && (
          <div className="mt-4 p-4 bg-red-50 border-l-4 border-red-600 flex items-center gap-3 animate-fadeIn">
            <AlertTriangle className="w-4 h-4 text-red-600 flex-shrink-0" />
            <p className="text-xs text-red-800 font-medium tracking-wide">{errorAjuste}</p>
          </div>
        )}
      </header>

      {/* 3. Filtros y Búsqueda Operativa */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div className="flex flex-wrap items-center gap-2">
          {categoriasFiltro.map((cat) => (
            <button
              key={cat}
              type="button"
              onClick={() => setCategoriaSeleccionada(cat)}
              className={`px-3 py-1.5 text-[11px] uppercase tracking-wider font-bold transition-colors cursor-pointer ${
                categoriaSeleccionada === cat
                  ? 'bg-[#293241] text-white'
                  : 'bg-white border border-[#293241]/20 text-[#1e1e1e] hover:border-[#293241]'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-3">
          <select
            value={filtroEstado}
            onChange={(e) => setFiltroEstado(e.target.value)}
            className="px-3 py-2 bg-white border border-[#293241]/20 text-xs uppercase tracking-wider font-semibold focus:outline-none focus:border-[#293241]"
          >
            <option value="todos">Todos los Estados</option>
            <option value="disponible">Disponibles</option>
            <option value="critico">Stock Crítico</option>
            <option value="agotado">Agotados</option>
          </select>

          <div className="relative min-w-[220px]">
            <input
              type="text"
              placeholder="BUSCAR SKU O PRENDA..."
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
              className="w-full pl-8 pr-3 py-2 bg-transparent border-b border-[#293241]/20 text-xs uppercase tracking-wider placeholder:text-[#3d5a80]/50 focus:outline-none focus:border-[#293241]"
            />
            <Search className="w-3.5 h-3.5 absolute left-1.5 top-1/2 -translate-y-1/2 text-[#3d5a80]" />
          </div>
        </div>
      </div>

      {/* 4. Tabla de Stock y Gestión Operativa */}
      <EstadoCarga cargando={cargando && listaProductos.length === 0} error={error} reintentar={reintentar}>
        <div className="border border-[#293241]/10 overflow-x-auto shadow-sm">
          <table className="w-full text-left text-xs uppercase tracking-wider border-collapse">
            <thead className="bg-[#293241] text-white text-[10px] tracking-[0.2em]">
              <tr>
                <th scope="col" className="py-4 px-4 font-bold">Prenda</th>
                <th scope="col" className="py-4 px-3 font-bold">Línea</th>
                <th scope="col" className="py-4 px-3 font-bold text-right">Precio Unitario</th>
                <th scope="col" className="py-4 px-4 font-bold text-center">Stock Actual</th>
                <th scope="col" className="py-4 px-3 font-bold text-center">Estado Auditoría</th>
                <th scope="col" className="py-4 px-4 font-bold text-right">Acciones de Almacén</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#293241]/10 bg-white">
              {productosFiltrados.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-[#3d5a80] font-light">
                    No se encontraron productos coincidentes en este filtro.
                  </td>
                </tr>
              ) : (
                productosFiltrados.map((item) => {
                  const id = item.producto_id
                  const stock = item.cantidad
                  const agotado = stock === 0
                  const critico = stock > 0 && stock <= POCO_STOCK
                  const procesando = accionEnCurso === id

                  return (
                    <tr
                      key={id}
                      className="hover:bg-[#f4fbfb]/50 transition-colors"
                    >
                      {/* Prenda & Miniatura */}
                      <td className="py-3.5 px-4 font-semibold text-[#1e1e1e]">
                        <span className="block font-bold text-xs">{item.nombre}</span>
                        <span className="text-[10px] text-[#3d5a80] font-mono">SKU-{String(id).padStart(3, '0')}</span>
                      </td>

                      {/* Categoría */}
                      <td className="py-3.5 px-3 text-[#3d5a80] font-medium text-[11px]">
                        {item.categoria ?? '—'}
                      </td>

                      {/* Precio */}
                      <td className="py-3.5 px-3 text-right font-semibold text-[#1e1e1e] tabular-nums">
                        {formatearPrecio(item.precio)}
                      </td>

                      {/* Cantidad / Unidades */}
                      <td className="py-3.5 px-4 text-center font-bold text-base tabular-nums">
                        <span className={agotado ? 'text-red-600' : critico ? 'text-[#ee6c4d]' : 'text-[#293241]'}>
                          {stock}
                        </span>
                      </td>

                      {/* Estado Badge */}
                      <td className="py-3.5 px-3 text-center">
                        {agotado ? (
                          <span className="inline-block px-2.5 py-1 bg-red-100 text-red-800 text-[9px] font-black tracking-widest border border-red-300">
                            Agotado
                          </span>
                        ) : critico ? (
                          <span className="inline-block px-2.5 py-1 bg-[#ee6c4d]/10 text-[#ee6c4d] text-[9px] font-black tracking-widest border border-[#ee6c4d]/30">
                            Crítico ({stock})
                          </span>
                        ) : (
                          <span className="inline-block px-2.5 py-1 bg-emerald-50 text-emerald-800 text-[9px] font-bold tracking-widest border border-emerald-200">
                            Disponible
                          </span>
                        )}
                      </td>

                      {/* Acciones de Ajuste en Tiempo Real */}
                      <td className="py-3.5 px-4 text-right">
                        <div className="inline-flex items-center gap-1.5 justify-end">
                          <button
                            type="button"
                            disabled={procesando || agotado}
                            onClick={() => manejarAjuste(id, 1, 'ajuste_salida')}
                            title="Descontar 1 unidad (merma / daño)"
                            className="px-2 py-1 border border-gray-300 hover:border-red-600 hover:text-red-600 bg-white text-[10px] font-bold transition-colors disabled:opacity-30 cursor-pointer"
                          >
                            -1
                          </button>

                          <button
                            type="button"
                            disabled={procesando}
                            onClick={() => manejarAjuste(id, 5, 'ajuste_entrada')}
                            title="Recibir pack de 5 unidades"
                            className="px-2.5 py-1 border border-[#293241]/20 hover:border-[#293241] bg-white text-[10px] font-bold text-[#293241] transition-colors cursor-pointer"
                          >
                            +5
                          </button>

                          <button
                            type="button"
                            disabled={procesando}
                            onClick={() => manejarAjuste(id, 10, 'ajuste_entrada')}
                            title="Recibir lote de 10 unidades de fábrica"
                            className="px-2.5 py-1 bg-[#ee6c4d] hover:bg-[#d95b3d] text-white text-[10px] font-bold transition-colors cursor-pointer"
                          >
                            +10
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </EstadoCarga>
    </div>
  )
}
