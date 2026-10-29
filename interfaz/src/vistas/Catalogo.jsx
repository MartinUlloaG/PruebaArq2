import { useMemo, useState } from 'react'
import {
  Filter,
  Search,
  ShoppingBag,
  SlidersHorizontal,
  X,
  Check,
  ChevronDown,
} from 'lucide-react'
import { seleccionarCantidadTotal, useCarrito } from '../modelosVista/useCarrito'
import {
  aplicarFiltros,
  CATEGORIAS_KYRO,
  OPCIONES_ORDEN,
  PRECIO_MAXIMO_DEFAULT,
  PRECIO_MINIMO_DEFAULT,
  useFiltros,
} from '../modelosVista/useFiltros'
import { formatearPrecio, POCO_STOCK } from '../modelosVista/stock'
import { useRecurso } from '../modelosVista/useRecurso'
import { listarCatalogo } from '../servicios/catalogo'
import { generarCatalogoSimulado70 } from '../servicios/imagenesPrendas'
import EstadoCarga from './EstadoCarga'
import VistaCarrito from './VistaCarrito'

export default function Catalogo() {
  const { datos, cargando, error, reintentar } = useRecurso(listarCatalogo)

  // ViewModel useCarrito
  const agregarProducto = useCarrito((s) => s.agregarProducto)
  const abrirCarrito = useCarrito((s) => s.abrirCarrito)
  const productosEnCarrito = useCarrito((s) => s.productos)
  const cantidadTotal = useCarrito(seleccionarCantidadTotal)

  // ViewModel useFiltros
  const categoria = useFiltros((s) => s.categoria)
  const precioMaximo = useFiltros((s) => s.precioMaximo)
  const ordenarPor = useFiltros((s) => s.ordenarPor)
  const busqueda = useFiltros((s) => s.busqueda)
  const setCategoria = useFiltros((s) => s.setCategoria)
  const setPrecioMaximo = useFiltros((s) => s.setPrecioMaximo)
  const setOrdenarPor = useFiltros((s) => s.setOrdenarPor)
  const setBusqueda = useFiltros((s) => s.setBusqueda)
  const limpiarFiltros = useFiltros((s) => s.limpiarFiltros)

  // Estado local para drawer de filtros en móviles
  const [sidebarMovilAbierta, setSidebarMovilAbierta] = useState(false)

  // Mock de 70 prendas vinculadas con los IDs reales del backend
  const catalogo70 = useMemo(() => {
    return generarCatalogoSimulado70(datos)
  }, [datos])

  // Aplicación reactiva de filtros y ordenamiento
  const productosFiltrados = useMemo(() => {
    return aplicarFiltros(catalogo70, {
      categoria,
      precioMinimo: PRECIO_MINIMO_DEFAULT,
      precioMaximo,
      ordenarPor,
      busqueda,
    })
  }, [catalogo70, categoria, precioMaximo, ordenarPor, busqueda])

  // Conteos editoriales por categoría
  const conteoCategorias = useMemo(() => {
    const conteo = { Todos: catalogo70.length }
    for (const cat of CATEGORIAS_KYRO) {
      if (cat !== 'Todos') {
        conteo[cat] = catalogo70.filter(
          (p) => (p.categoria || '').toLowerCase() === cat.toLowerCase()
        ).length
      }
    }
    return conteo
  }, [catalogo70])

  const hayFiltrosActivos =
    categoria !== 'Todos' ||
    precioMaximo < PRECIO_MAXIMO_DEFAULT ||
    busqueda.trim().length > 0

  return (
    <div className="w-full bg-white text-[#1e1e1e]">
      {/* 1. Header Editorial del Catálogo */}
      <header className="border-b border-[#293241]/10 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 py-8 flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div>
            <span className="text-[10px] uppercase tracking-[0.35em] text-[#3d5a80] font-bold block mb-1">
              KYRO / ARCHIVE COLLECTION
            </span>
            <h1 className="text-3xl md:text-5xl font-black uppercase tracking-tight text-[#1e1e1e]">
              {categoria === 'Todos' ? 'Catálogo General' : `Colección ${categoria}`}
            </h1>
            <p className="text-xs uppercase tracking-[0.2em] text-[#3d5a80] font-light mt-1">
              {productosFiltrados.length} piezas curadas
            </p>
          </div>

          <div className="flex items-center gap-3 self-end md:self-auto">
            {/* Botón Filtros Móvil */}
            <button
              type="button"
              onClick={() => setSidebarMovilAbierta(true)}
              className="md:hidden inline-flex items-center gap-2 px-4 py-2.5 border border-[#293241]/20 text-xs uppercase tracking-widest font-bold"
            >
              <SlidersHorizontal className="w-3.5 h-3.5 text-[#293241]" />
              <span>Filtros</span>
            </button>

            {/* Selector de Orden */}
            <div className="relative">
              <select
                value={ordenarPor}
                onChange={(e) => setOrdenarPor(e.target.value)}
                className="appearance-none bg-white border border-[#293241]/20 px-4 py-2.5 pr-8 text-xs uppercase tracking-widest font-medium text-[#1e1e1e] focus:outline-none focus:border-[#293241] cursor-pointer"
              >
                {OPCIONES_ORDEN.map((opt) => (
                  <option key={opt.id} value={opt.id}>
                    {opt.etiqueta}
                  </option>
                ))}
              </select>
              <ChevronDown className="w-3.5 h-3.5 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none text-[#293241]/60" />
            </div>

            {/* Botón Carrito Minimalista */}
            <button
              type="button"
              onClick={abrirCarrito}
              className="inline-flex items-center gap-2.5 px-5 py-2.5 bg-[#293241] hover:bg-[#3d5a80] text-white transition-colors"
              aria-label={`Abrir carrito con ${cantidadTotal} productos`}
            >
              <ShoppingBag className="w-4 h-4 text-[#e0fbfc]" />
              <span className="text-xs uppercase tracking-[0.2em] font-bold">Bolsa</span>
              {cantidadTotal > 0 && (
                <span className="w-5 h-5 rounded-full bg-[#ee6c4d] text-white text-[10px] font-bold flex items-center justify-center">
                  {cantidadTotal}
                </span>
              )}
            </button>
          </div>
        </div>
      </header>

      {/* 2. Layout Editorial: Sidebar Limpio (Sin cajas) + Grid de Productos */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 py-12">
        <EstadoCarga cargando={cargando} error={error} reintentar={reintentar}>
          <div className="grid grid-cols-1 md:grid-cols-[220px_1fr] lg:grid-cols-[250px_1fr] gap-12 lg:gap-16 items-start">
            
            {/* SIDEBAR IZQUIERDO EDITORIAL */}
            <aside
              className={`fixed inset-y-0 left-0 z-50 w-72 bg-white p-6 shadow-2xl transition-transform duration-300 md:static md:w-auto md:p-0 md:shadow-none md:translate-x-0 ${
                sidebarMovilAbierta ? 'translate-x-0' : '-translate-x-full'
              }`}
            >
              {/* Botón cerrar para móvil */}
              <div className="flex md:hidden justify-between items-center pb-4 mb-6 border-b border-[#293241]/10">
                <span className="text-xs uppercase tracking-[0.25em] font-bold">Filtros</span>
                <button type="button" onClick={() => setSidebarMovilAbierta(false)}>
                  <X className="w-5 h-5 text-[#1e1e1e]" />
                </button>
              </div>

              <div className="space-y-8 sticky top-28">
                {/* Cabecera Sidebar */}
                <div className="flex justify-between items-baseline border-b border-[#293241]/15 pb-3">
                  <h2 className="text-xs uppercase tracking-[0.25em] font-black text-[#293241]">
                    Filtrar Por
                  </h2>
                  {hayFiltrosActivos && (
                    <button
                      type="button"
                      onClick={limpiarFiltros}
                      className="text-[10px] uppercase tracking-widest text-[#ee6c4d] hover:underline font-semibold"
                    >
                      Limpiar
                    </button>
                  )}
                </div>

                {/* Búsqueda Minimalista */}
                <div className="border-b border-[#293241]/10 pb-6">
                  <span className="text-[10px] uppercase tracking-[0.25em] text-[#3d5a80] font-bold block mb-3">
                    Buscar
                  </span>
                  <div className="relative">
                    <input
                      type="text"
                      placeholder="PALABRA CLAVE..."
                      value={busqueda}
                      onChange={(e) => setBusqueda(e.target.value)}
                      className="w-full bg-transparent border-b border-[#293241]/20 py-2 pl-6 pr-2 text-xs uppercase tracking-wider placeholder:text-[#3d5a80]/50 focus:outline-none focus:border-[#293241]"
                    />
                    <Search className="w-3.5 h-3.5 absolute left-0 top-1/2 -translate-y-1/2 text-[#3d5a80]" />
                    {busqueda && (
                      <button
                        type="button"
                        onClick={() => setBusqueda('')}
                        className="absolute right-0 top-1/2 -translate-y-1/2"
                      >
                        <X className="w-3.5 h-3.5 text-[#3d5a80]" />
                      </button>
                    )}
                  </div>
                </div>

                {/* Categorías (Texto editorial puro con líneas finas) */}
                <div className="border-b border-[#293241]/10 pb-6">
                  <span className="text-[10px] uppercase tracking-[0.25em] text-[#3d5a80] font-bold block mb-3">
                    Líneas
                  </span>
                  <ul className="space-y-2.5">
                    {CATEGORIAS_KYRO.map((cat) => {
                      const activo = categoria === cat
                      const total = conteoCategorias[cat] ?? 0
                      return (
                        <li key={cat}>
                          <button
                            type="button"
                            onClick={() => {
                              setCategoria(cat)
                              setSidebarMovilAbierta(false)
                            }}
                            className={`w-full flex items-center justify-between text-left text-xs uppercase tracking-[0.15em] transition-colors py-1 ${
                              activo
                                ? 'font-black text-[#1e1e1e] pl-2 border-l-2 border-[#ee6c4d]'
                                : 'font-normal text-[#1e1e1e]/60 hover:text-[#1e1e1e]'
                            }`}
                          >
                            <span>{cat}</span>
                            <span className="text-[10px] tabular-nums font-mono opacity-60">
                              {total}
                            </span>
                          </button>
                        </li>
                      )
                    })}
                  </ul>
                </div>

                {/* Rango de Precio (Minimal Slider) */}
                <div className="border-b border-[#293241]/10 pb-6">
                  <div className="flex justify-between items-baseline mb-3">
                    <span className="text-[10px] uppercase tracking-[0.25em] text-[#3d5a80] font-bold">
                      Precio Máximo
                    </span>
                    <span className="text-xs font-bold tabular-nums text-[#293241]">
                      {formatearPrecio(precioMaximo)}
                    </span>
                  </div>

                  <input
                    type="range"
                    min={15000}
                    max={250000}
                    step={5000}
                    value={precioMaximo}
                    onChange={(e) => setPrecioMaximo(e.target.value)}
                    className="w-full accent-[#ee6c4d] h-1 bg-[#293241]/20 cursor-pointer"
                  />

                  <div className="flex justify-between text-[10px] uppercase tracking-widest text-[#3d5a80]/60 mt-2 font-mono">
                    <span>$15.000</span>
                    <span>$250.000</span>
                  </div>
                </div>

                {/* Pie editorial del Sidebar */}
                <div className="pt-2">
                  <p className="text-[10px] uppercase tracking-widest text-[#3d5a80]/60 leading-relaxed font-light">
                    Colección oficial KYRO. Calce holgado unisex. Materiales orgánicos certificados.
                  </p>
                </div>
              </div>
            </aside>

            {/* GRID DERECHO DE PRODUCTOS (Completamente plano, editorial) */}
            <main className="min-w-0">
              {productosFiltrados.length === 0 ? (
                <div className="border border-dashed border-[#293241]/20 p-16 text-center">
                  <Search className="w-8 h-8 text-[#3d5a80] mx-auto mb-3 opacity-50" />
                  <h3 className="text-sm uppercase tracking-[0.2em] font-bold text-[#1e1e1e] mb-1">
                    Sin coincidencias en esta selección
                  </h3>
                  <p className="text-xs text-[#3d5a80] font-light max-w-sm mx-auto mb-6">
                    Ajusta los filtros de precio o selecciona otra línea del catálogo.
                  </p>
                  <button
                    type="button"
                    onClick={limpiarFiltros}
                    className="px-6 py-2.5 bg-[#293241] text-white text-xs uppercase tracking-widest font-bold"
                  >
                    Restablecer Todo
                  </button>
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-x-6 gap-y-12">
                  {productosFiltrados.map((prod) => {
                    const idReal = prod.producto_id
                    const itemEnCarrito = productosEnCarrito.find(
                      (i) => (i.producto_id ?? i.id) === idReal
                    )
                    const enCarrito = itemEnCarrito ? itemEnCarrito.cantidad : 0
                    const agotado = prod.disponibles === 0

                    return (
                      <article
                        key={prod.id}
                        className="group flex flex-col bg-white select-none"
                      >
                        {/* Contenedor de Imagen: ~85% de la tarjeta, completamente plano */}
                        <div className="relative aspect-[3/4] bg-[#f4fbfb] overflow-hidden">
                          <img
                            src={prod.imagen}
                            alt={prod.nombre}
                            className={`w-full h-full object-cover object-center filter grayscale-[10%] group-hover:grayscale-0 transition-transform duration-700 ease-out group-hover:scale-105 ${
                              agotado ? 'opacity-50 grayscale' : ''
                            }`}
                            loading="lazy"
                          />

                          {/* Micro-interacción: Al hacer hover, la imagen se oscurece sutilmente */}
                          <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors duration-300 pointer-events-none" />

                          {/* Badge discreto de categoría */}
                          <span className="absolute top-2.5 left-2.5 bg-black/70 backdrop-blur-sm text-white text-[9px] uppercase tracking-[0.2em] font-medium px-2 py-0.5 z-10">
                            {prod.categoria}
                          </span>

                          {/* Overlay de Agotado */}
                          {agotado && (
                            <div className="absolute inset-0 bg-black/50 backdrop-blur-[1px] flex items-center justify-center z-10">
                              <span className="text-[11px] uppercase tracking-[0.3em] font-black text-white px-3 py-1 border border-white">
                                Agotado
                              </span>
                            </div>
                          )}

                          {/* Botón de acción #ee6c4d con ícono lucide-react revelado suavemente en hover */}
                          <div className="absolute bottom-3 inset-x-3 z-20 opacity-0 translate-y-2 group-hover:opacity-100 group-hover:translate-y-0 transition-all duration-300 ease-out">
                            <button
                              type="button"
                              disabled={agotado}
                              onClick={() => agregarProducto(prod)}
                              className="w-full py-3 px-3 bg-[#ee6c4d] hover:bg-[#d95b3d] text-white text-[11px] font-bold uppercase tracking-[0.2em] flex items-center justify-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              <ShoppingBag className="w-3.5 h-3.5 text-white" />
                              <span>
                                {agotado
                                  ? 'Sin Stock'
                                  : enCarrito > 0
                                  ? `En Bolsa (${enCarrito}) +`
                                  : 'Agregar a la Bolsa'}
                              </span>
                            </button>
                          </div>
                        </div>

                        {/* Detalles de la Tarjeta Editorial (Plana, tipografía nítida) */}
                        <div className="pt-3 flex flex-col flex-grow">
                          <span className="text-[10px] uppercase tracking-[0.25em] text-[#3d5a80] font-semibold mb-0.5">
                            {prod.categoria}
                          </span>

                          <h3 className="text-xs uppercase tracking-[0.15em] font-bold text-[#1e1e1e] line-clamp-1 mb-1">
                            {prod.nombre}
                          </h3>

                          <div className="mt-auto flex items-baseline justify-between pt-1">
                            <span className="text-sm font-semibold text-[#1e1e1e] tabular-nums">
                              {formatearPrecio(prod.precio)}
                            </span>
                            {prod.disponibles > 0 && prod.disponibles <= POCO_STOCK && (
                              <span className="text-[10px] uppercase tracking-wider text-[#ee6c4d] font-bold">
                                Últimas {prod.disponibles}
                              </span>
                            )}
                          </div>
                        </div>
                      </article>
                    )
                  })}
                </div>
              )}
            </main>
          </div>
        </EstadoCarga>
      </div>

      {/* Drawer lateral de la bolsa (useCarrito) */}
      <VistaCarrito />
    </div>
  )
}
