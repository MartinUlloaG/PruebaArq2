import { useMemo, useState } from 'react'
import { ChevronDown, Search, ShoppingBag, SlidersHorizontal, X } from 'lucide-react'
import { seleccionarCantidadTotal, useCarrito } from '../modelosVista/useCarrito'
import {
  aplicarFiltros,
  OPCIONES_ORDEN,
  rangoDePrecios,
  TODAS,
  useFiltros,
} from '../modelosVista/useFiltros'
import { formatearPrecio, POCO_STOCK } from '../modelosVista/stock'
import { useRecurso } from '../modelosVista/useRecurso'
import { listarCatalogo, listarCategorias } from '../servicios/catalogo'
import EstadoCarga from './EstadoCarga'
import VistaCarrito from './VistaCarrito'

// Atributos del documento de Mongo que se muestran en la tarjeta (cambian según la prenda).
function Atributos({ atributos }) {
  const { color, tallas, material } = atributos ?? {}
  return (
    <dl className="mt-2 space-y-0.5 text-[10px] uppercase tracking-wider text-[#3d5a80]">
      {color && (
        <div className="flex gap-1">
          <dt className="font-bold">Color:</dt>
          <dd>{color}</dd>
        </div>
      )}
      {tallas?.length > 0 && (
        <div className="flex gap-1">
          <dt className="font-bold">Tallas:</dt>
          <dd>{tallas.join(' · ')}</dd>
        </div>
      )}
      {material && (
        <div className="flex gap-1">
          <dt className="font-bold">Material:</dt>
          <dd>{material}</dd>
        </div>
      )}
    </dl>
  )
}

export default function Catalogo() {
  const { datos, cargando, error, reintentar, recargar } = useRecurso(listarCatalogo)
  const { datos: categorias, recargar: recargarCategorias } = useRecurso(listarCategorias)
  const productos = useMemo(() => datos ?? [], [datos])

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

  // Control del drawer de filtros en dispositivos móviles
  const [sidebarMovilAbierta, setSidebarMovilAbierta] = useState(false)

  const rango = useMemo(() => rangoDePrecios(productos), [productos])
  const tope = precioMaximo ?? rango.maximo

  const productosFiltrados = useMemo(
    () => aplicarFiltros(productos, { categoria, precioMaximo, ordenarPor, busqueda }),
    [productos, categoria, precioMaximo, ordenarPor, busqueda],
  )

  const lineas = [{ nombre: TODAS, productos: productos.length }, ...(categorias ?? [])]
  const hayFiltrosActivos = categoria !== TODAS || precioMaximo !== null || busqueda.trim().length > 0

  return (
    <div className="w-full bg-white text-[#1e1e1e]">
      {/* 1. Header del Catálogo */}
      <header className="border-b border-[#293241]/10 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 py-8 flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div>
            <span className="text-[10px] uppercase tracking-[0.35em] text-[#3d5a80] font-bold block mb-1">
              KYRO / CATÁLOGO
            </span>
            <h1 className="text-3xl md:text-5xl font-black uppercase tracking-tight text-[#1e1e1e]">
              {categoria === TODAS ? 'Catálogo General' : categoria}
            </h1>
            <p className="text-xs uppercase tracking-[0.2em] text-[#3d5a80] font-light mt-1">
              {productosFiltrados.length} prendas
            </p>
          </div>

          <div className="flex items-center gap-3 self-end md:self-auto">
            <button
              type="button"
              onClick={() => setSidebarMovilAbierta(true)}
              className="md:hidden inline-flex items-center gap-2 px-4 py-2.5 border border-[#293241]/20 text-xs uppercase tracking-widest font-bold hover:bg-gray-50"
            >
              <SlidersHorizontal className="w-3.5 h-3.5 text-[#293241]" />
              <span>Filtros</span>
            </button>

            <div className="relative">
              <select
                value={ordenarPor}
                onChange={(e) => setOrdenarPor(e.target.value)}
                aria-label="Ordenar"
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

            <button
              type="button"
              onClick={abrirCarrito}
              className="inline-flex items-center gap-2.5 px-5 py-2.5 bg-[#293241] hover:bg-[#3d5a80] text-white transition-colors cursor-pointer"
              aria-label={`Abrir bolsa con ${cantidadTotal} prendas`}
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

      {/* 2. Filtros + grilla */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-[220px_1fr] lg:grid-cols-[250px_1fr] gap-12 lg:gap-16 items-start">
          {sidebarMovilAbierta && (
            <div
              className="fixed inset-0 bg-black/50 z-40 md:hidden"
              onClick={() => setSidebarMovilAbierta(false)}
            />
          )}

          <aside
            className={`fixed inset-y-0 left-0 z-50 w-72 bg-white p-6 shadow-2xl transition-transform duration-300 overflow-y-auto max-h-screen md:sticky md:top-24 md:z-10 md:self-start md:w-auto md:p-0 md:shadow-none md:translate-x-0 md:max-h-[calc(100vh-7rem)] ${
              sidebarMovilAbierta ? 'translate-x-0' : '-translate-x-full'
            }`}
          >
            <div className="flex md:hidden justify-between items-center pb-4 mb-6 border-b border-[#293241]/10">
              <span className="text-xs uppercase tracking-[0.25em] font-bold">Filtros</span>
              <button
                type="button"
                onClick={() => setSidebarMovilAbierta(false)}
                className="p-1 hover:text-[#ee6c4d]"
                aria-label="Cerrar filtros"
              >
                <X className="w-5 h-5 text-[#1e1e1e]" />
              </button>
            </div>

            <div className="space-y-8 md:pr-2">
              <div className="flex justify-between items-baseline border-b border-[#293241]/15 pb-3">
                <h2 className="text-xs uppercase tracking-[0.25em] font-black text-[#293241]">
                  Filtrar Por
                </h2>
                {hayFiltrosActivos && (
                  <button
                    type="button"
                    onClick={limpiarFiltros}
                    className="text-[10px] uppercase tracking-widest text-[#ee6c4d] hover:underline font-semibold cursor-pointer"
                  >
                    Limpiar
                  </button>
                )}
              </div>

              {/* Búsqueda */}
              <div className="border-b border-[#293241]/10 pb-6">
                <label
                  htmlFor="buscar-catalogo"
                  className="text-[10px] uppercase tracking-[0.25em] text-[#3d5a80] font-bold block mb-3"
                >
                  Buscar
                </label>
                <div className="relative">
                  <input
                    id="buscar-catalogo"
                    type="text"
                    value={busqueda}
                    onChange={(e) => setBusqueda(e.target.value)}
                    className="w-full bg-transparent border-b border-[#293241]/20 py-2 pl-6 pr-6 text-xs uppercase tracking-wider focus:outline-none focus:border-[#293241]"
                  />
                  <Search className="w-3.5 h-3.5 absolute left-0 top-1/2 -translate-y-1/2 text-[#3d5a80]" />
                  {busqueda && (
                    <button
                      type="button"
                      onClick={() => setBusqueda('')}
                      className="absolute right-0 top-1/2 -translate-y-1/2 p-1 text-[#3d5a80] hover:text-[#1e1e1e]"
                      aria-label="Borrar búsqueda"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </div>

              {/* Categorías (con sus conteos desde la API) */}
              <div className="border-b border-[#293241]/10 pb-6">
                <span className="text-[10px] uppercase tracking-[0.25em] text-[#3d5a80] font-bold block mb-3">
                  Líneas
                </span>
                <ul className="space-y-2.5">
                  {lineas.map((linea) => {
                    const activo = categoria === linea.nombre
                    return (
                      <li key={linea.nombre}>
                        <button
                          type="button"
                          onClick={() => {
                            setCategoria(linea.nombre)
                            setSidebarMovilAbierta(false)
                          }}
                          className={`w-full flex items-center justify-between text-left text-xs uppercase tracking-[0.15em] transition-colors py-1 cursor-pointer ${
                            activo
                              ? 'font-black text-[#1e1e1e] pl-2 border-l-2 border-[#ee6c4d]'
                              : 'font-normal text-[#1e1e1e]/60 hover:text-[#1e1e1e]'
                          }`}
                        >
                          <span>{linea.nombre}</span>
                          <span className="text-[10px] tabular-nums font-mono opacity-60">
                            {linea.productos}
                          </span>
                        </button>
                      </li>
                    )
                  })}
                </ul>
              </div>

              {/* Precio máximo (el rango sale de los precios reales) */}
              {rango.maximo > rango.minimo && (
                <div className="border-b border-[#293241]/10 pb-6">
                  <div className="flex justify-between items-baseline mb-3">
                    <label
                      htmlFor="precio-maximo"
                      className="text-[10px] uppercase tracking-[0.25em] text-[#3d5a80] font-bold"
                    >
                      Precio Máximo
                    </label>
                    <span className="text-xs font-bold tabular-nums text-[#293241]">
                      {formatearPrecio(tope)}
                    </span>
                  </div>
                  <input
                    id="precio-maximo"
                    type="range"
                    min={rango.minimo}
                    max={rango.maximo}
                    step={1000}
                    value={tope}
                    onChange={(e) => setPrecioMaximo(e.target.value)}
                    className="w-full accent-[#ee6c4d] h-1.5 bg-[#293241]/20 cursor-pointer"
                  />
                  <div className="flex justify-between text-[10px] uppercase tracking-widest text-[#3d5a80]/60 mt-2 font-mono">
                    <span>{formatearPrecio(rango.minimo)}</span>
                    <span>{formatearPrecio(rango.maximo)}</span>
                  </div>
                </div>
              )}
            </div>
          </aside>

          {/* Grilla de productos */}
          <main className="min-w-0">
            <EstadoCarga cargando={cargando && productos.length === 0} error={error} reintentar={reintentar}>
              {productosFiltrados.length === 0 ? (
                <div className="border border-dashed border-[#293241]/20 p-16 text-center bg-gray-50/50">
                  <Search className="w-8 h-8 text-[#3d5a80] mx-auto mb-3 opacity-50" />
                  <h3 className="text-sm uppercase tracking-[0.2em] font-bold text-[#1e1e1e] mb-1">
                    Sin coincidencias en esta selección
                  </h3>
                  <button
                    type="button"
                    onClick={limpiarFiltros}
                    className="mt-4 px-6 py-2.5 bg-[#293241] hover:bg-[#3d5a80] text-white text-xs uppercase tracking-widest font-bold transition-colors cursor-pointer"
                  >
                    Restablecer Filtros
                  </button>
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                  {productosFiltrados.map((prod) => {
                    const enCarrito =
                      productosEnCarrito.find((i) => i.producto_id === prod.producto_id)?.cantidad ?? 0
                    const agotado = prod.disponibles === 0
                    const sinMas = enCarrito >= prod.disponibles

                    return (
                      <article
                        key={prod.producto_id}
                        className={`flex flex-col border border-[#293241]/10 bg-white p-5 ${agotado ? 'opacity-60' : ''}`}
                      >
                        <span className="text-[10px] uppercase tracking-[0.25em] text-[#3d5a80] font-semibold">
                          {prod.categoria}
                        </span>
                        <h3 className="text-sm uppercase tracking-[0.12em] font-bold text-[#1e1e1e] mt-1">
                          {prod.nombre}
                        </h3>
                        {prod.descripcion && (
                          <p className="text-xs text-[#3d5a80] font-light mt-1">{prod.descripcion}</p>
                        )}
                        <Atributos atributos={prod.atributos} />

                        <div className="mt-auto pt-4 flex items-baseline justify-between">
                          <span className="text-base font-semibold text-[#1e1e1e] tabular-nums">
                            {formatearPrecio(prod.precio)}
                          </span>
                          {/* El estado del stock también va en texto, no solo en color */}
                          <span
                            className={`text-[10px] uppercase tracking-wider font-bold ${
                              agotado
                                ? 'text-red-700'
                                : prod.disponibles <= POCO_STOCK
                                  ? 'text-[#ee6c4d]'
                                  : 'text-emerald-700'
                            }`}
                          >
                            {agotado
                              ? 'Agotado'
                              : prod.disponibles <= POCO_STOCK
                                ? `Últimas ${prod.disponibles}`
                                : `${prod.disponibles} disponibles`}
                          </span>
                        </div>

                        <button
                          type="button"
                          disabled={agotado || sinMas}
                          onClick={() => agregarProducto(prod)}
                          className="mt-3 w-full py-3 px-3 bg-[#ee6c4d] hover:bg-[#d95b3d] text-white text-[11px] font-bold uppercase tracking-[0.2em] flex items-center justify-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                        >
                          <ShoppingBag className="w-3.5 h-3.5 text-white" />
                          <span>
                            {agotado
                              ? 'Sin Stock'
                              : enCarrito > 0
                                ? `En Bolsa (${enCarrito}) +`
                                : 'Agregar a la Bolsa'}
                          </span>
                          <span className="sr-only"> {prod.nombre}</span>
                        </button>
                      </article>
                    )
                  })}
                </div>
              )}
            </EstadoCarga>
          </main>
        </div>
      </div>

      <VistaCarrito
        alTerminar={() => {
          recargar()
          recargarCategorias()
        }}
      />
    </div>
  )
}
