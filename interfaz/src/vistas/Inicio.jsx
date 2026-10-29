import { useNavigate } from 'react-router-dom'
import { ArrowRight, ArrowUpRight, ChevronDown } from 'lucide-react'
import { listarCategorias } from '../servicios/catalogo'
import { TODAS, useFiltros } from '../modelosVista/useFiltros'
import { useRecurso } from '../modelosVista/useRecurso'
import { useSesion } from '../modelosVista/useSesion'
import { ROLES, seccionesPara } from '../modelosVista/roles'

const sinCategorias = () => Promise.resolve([])

export default function Inicio() {
  const usuario = useSesion((s) => s.usuario)
  const setCategoria = useFiltros((s) => s.setCategoria)
  const navegar = useNavigate()
  const esCliente = usuario?.rol === 'cliente'
  // Las categorías y sus conteos vienen de Mongo. Solo el cliente ve el catálogo.
  const { datos: categorias } = useRecurso(esCliente ? listarCategorias : sinCategorias)
  const totalPrendas = (categorias ?? []).reduce((suma, c) => suma + c.productos, 0)

  function irACategoria(categoria) {
    setCategoria(categoria)
    navegar('/catalogo')
  }

  return (
    <div className="w-full bg-white text-[#1e1e1e]">
      {/* Aviso funcional para roles de administración / bodega */}
      {usuario?.rol && usuario.rol !== 'cliente' && (
        <aside className="border-b border-[#293241]/10 bg-[#e0fbfc]/30 px-6 py-3">
          <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#ee6c4d]" />
              <p className="text-xs uppercase tracking-widest font-semibold text-[#293241]">
                Sesión: {ROLES[usuario.rol].nombre} — {ROLES[usuario.rol].puede}
              </p>
            </div>
            <div className="flex gap-2">
              {seccionesPara(usuario.rol).map((s) => (
                <button
                  key={s.ruta}
                  type="button"
                  onClick={() => navegar(s.ruta)}
                  className="text-xs uppercase tracking-wider font-semibold px-3 py-1 border border-[#293241]/20 hover:border-[#293241] bg-white transition-colors"
                >
                  {s.nombre}
                </button>
              ))}
            </div>
          </div>
        </aside>
      )}

      {/* 1. Hero Section Inmersivo (h-screen, editorial minimalista) */}
      <section className="relative h-[70vh] w-full flex items-center justify-center overflow-hidden bg-[#293241]">

        <div className="relative z-10 text-center px-4 max-w-4xl mx-auto flex flex-col items-center">
          <span className="text-[11px] md:text-xs uppercase tracking-[0.35em] text-[#e0fbfc] font-medium mb-3">
            Otoño / Invierno 2026
          </span>

          <h1 className="text-7xl sm:text-8xl md:text-9xl font-black text-white tracking-tighter uppercase leading-none select-none mb-4">
            KYRO
          </h1>

          <p className="text-xs md:text-sm text-[#e0fbfc]/90 uppercase tracking-[0.25em] font-light max-w-md mx-auto leading-relaxed mb-8">
            Prendas de alta confección. Líneas puras, volumen calculado y ausencia de ruido.
          </p>

          {/* Botón Fantasma (Ghost Button) Minimalista */}
          <button
            type="button"
            onClick={() => irACategoria(TODAS)}
            className="group inline-flex items-center gap-3 px-8 py-3.5 border border-white/80 text-white hover:bg-white hover:text-[#1e1e1e] transition-all duration-300 text-xs uppercase tracking-[0.25em] font-bold"
          >
            <span>Explorar Colección</span>
            <ArrowRight className="w-3.5 h-3.5 transition-transform duration-300 group-hover:translate-x-1" />
          </button>
        </div>

        {/* Indicador sutil de scroll */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-10 flex flex-col items-center gap-1 opacity-70">
          <span className="text-[10px] uppercase tracking-[0.3em] text-white/80 font-light">Scroll</span>
          <ChevronDown className="w-4 h-4 text-white animate-bounce" />
        </div>
      </section>

      {/* Declaración de Marca (Manifesto Strip) */}
      <section className="border-y border-[#293241]/10 py-12 px-6 bg-white">
        <div className="max-w-5xl mx-auto text-center">
          <p className="text-xs uppercase tracking-[0.3em] text-[#3d5a80] font-semibold mb-3">
            KYRO Architecture &amp; Apparel
          </p>
          <p className="text-xl md:text-2xl font-light text-[#1e1e1e] tracking-tight leading-relaxed">
            «La reducción como forma de expresión máxima. Confeccionamos exclusivamente con tejidos nobles de gramaje pesado, priorizando la durabilidad y la elegancia austera.»
          </p>
        </div>
      </section>

      {/* 2. Categorías: nombre y cantidad de prendas desde la API */}
      {esCliente && (
        <section className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 py-20">
          <header className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-[#293241]/15 pb-6 mb-12">
            <h2 className="text-3xl md:text-4xl font-black uppercase tracking-tight text-[#1e1e1e]">
              Líneas
            </h2>
            <button
              type="button"
              onClick={() => irACategoria(TODAS)}
              className="group inline-flex items-center gap-1.5 text-xs uppercase tracking-[0.2em] font-bold text-[#1e1e1e] hover:text-[#ee6c4d] transition-colors self-start sm:self-auto"
            >
              <span>Ver catálogo completo ({totalPrendas} prendas)</span>
              <ArrowUpRight className="w-4 h-4" />
            </button>
          </header>

          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 md:gap-6">
            {(categorias ?? []).map((cat, idx) => (
              <button
                key={cat.nombre}
                type="button"
                onClick={() => irACategoria(cat.nombre)}
                className="group text-left p-6 border border-[#293241]/10 bg-[#f4fbfb] hover:bg-[#293241] hover:text-white transition-colors cursor-pointer"
              >
                <span className="text-[10px] uppercase tracking-[0.25em] text-[#ee6c4d] font-semibold">
                  {String(idx + 1).padStart(2, '0')}
                </span>
                <h3 className="text-xl md:text-2xl font-black uppercase tracking-tight mt-6">{cat.nombre}</h3>
                <p className="text-xs uppercase tracking-wider opacity-70 mt-1">
                  {cat.productos} prendas · {cat.unidades} unidades
                </p>
              </button>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
