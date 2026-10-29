import { useNavigate } from 'react-router-dom'
import { ArrowRight, ArrowUpRight, ChevronDown, SlidersHorizontal } from 'lucide-react'
import { CATEGORIAS_ASIMETRICAS, FOTOS_CAMPANIA } from '../servicios/imagenesPrendas'
import { useFiltros } from '../modelosVista/useFiltros'
import { useSesion } from '../modelosVista/useSesion'
import { ROLES, seccionesPara } from '../modelosVista/roles'

export default function Inicio() {
  const usuario = useSesion((s) => s.usuario)
  const setCategoria = useFiltros((s) => s.setCategoria)
  const navegar = useNavigate()

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
      <section className="relative h-screen w-full flex items-center justify-center overflow-hidden bg-[#293241]">
        <img
          src={FOTOS_CAMPANIA.hero}
          alt="KYRO Campaña Editorial 2026"
          className="absolute inset-0 w-full h-full object-cover object-center opacity-75 scale-100 transition-transform duration-1000 ease-out"
        />
        <div className="absolute inset-0 bg-black/40 backdrop-contrast-[1.05]" />

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
            onClick={() => irACategoria('Todos')}
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

      {/* 2. Sección de Categorías en Grid Asimétrico (Estilo Revista / Lookbook) */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 py-20 md:py-28">
        <header className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-[#293241]/15 pb-6 mb-12">
          <div>
            <span className="text-[10px] md:text-xs uppercase tracking-[0.3em] text-[#3d5a80] font-bold block mb-1">
              Catálogo Modular
            </span>
            <h2 className="text-3xl md:text-4xl font-black uppercase tracking-tight text-[#1e1e1e]">
              Líneas de Diseño
            </h2>
          </div>

          <button
            type="button"
            onClick={() => irACategoria('Todos')}
            className="group inline-flex items-center gap-1.5 text-xs uppercase tracking-[0.2em] font-bold text-[#1e1e1e] hover:text-[#ee6c4d] transition-colors self-start sm:self-auto"
          >
            <span>Ver Catálogo Completo (70 piezas)</span>
            <ArrowUpRight className="w-4 h-4 transition-transform duration-200 group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
          </button>
        </header>

        {/* CSS Grid Asimétrico Editorial */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 md:gap-6">
          {CATEGORIAS_ASIMETRICAS.map((cat, idx) => {
            const esPrincipal = idx === 0
            return (
              <article
                key={cat.id}
                onClick={() => irACategoria(cat.nombre)}
                className={`group relative overflow-hidden bg-[#e0fbfc]/20 cursor-pointer ${
                  esPrincipal
                    ? 'md:col-span-2 md:row-span-2 aspect-[4/5] md:aspect-auto'
                    : 'md:col-span-1 md:row-span-1 aspect-[3/4]'
                }`}
              >
                <img
                  src={cat.imagen}
                  alt={cat.nombre}
                  className="w-full h-full object-cover object-center filter grayscale-[15%] group-hover:grayscale-0 group-hover:scale-105 transition-all duration-700 ease-out"
                  loading="lazy"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent opacity-80 group-hover:opacity-90 transition-opacity" />

                <div className="absolute inset-0 p-6 flex flex-col justify-between z-10">
                  <div className="flex justify-between items-start">
                    <span className="text-[10px] uppercase tracking-[0.25em] text-[#e0fbfc] font-semibold">
                      0{idx + 1}
                    </span>
                    <span className="w-7 h-7 rounded-full border border-white/30 flex items-center justify-center text-white opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                      <ArrowUpRight className="w-3.5 h-3.5" />
                    </span>
                  </div>

                  <div>
                    <span className="text-[10px] uppercase tracking-[0.2em] text-[#ee6c4d] font-bold block mb-1">
                      {cat.conteo}
                    </span>
                    <h3 className="text-xl md:text-2xl font-black uppercase tracking-tight text-white mb-1">
                      {cat.nombre}
                    </h3>
                    <p className="text-xs font-light tracking-wider text-[#e0fbfc]/80 line-clamp-1">
                      {cat.subtitulo}
                    </p>
                  </div>
                </div>
              </article>
            )
          })}
        </div>
      </section>

      {/* Franja de Respiro Minimalista (Ice #e0fbfc) */}
      <section className="bg-[#e0fbfc]/40 border-t border-[#293241]/10 py-16 px-6">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-8 text-center md:text-left">
          <div>
            <h3 className="text-2xl font-black uppercase tracking-tight text-[#293241] mb-2">
              Suscripción a Nuevos Lanzamientos
            </h3>
            <p className="text-xs uppercase tracking-[0.2em] text-[#3d5a80] font-light">
              Entregas limitadas. Sin rebajas masivas ni correos no solicitados.
            </p>
          </div>

          <div className="w-full md:w-auto flex flex-col sm:flex-row gap-2">
            <input
              type="email"
              placeholder="INGRESAR CORREO ELECTRÓNICO"
              className="px-4 py-3 bg-white border border-[#293241]/20 text-xs uppercase tracking-widest placeholder:text-[#3d5a80]/60 focus:outline-none focus:border-[#293241] min-w-[280px]"
            />
            <button
              type="button"
              className="px-6 py-3 bg-[#293241] hover:bg-[#3d5a80] text-white text-xs uppercase tracking-[0.2em] font-bold transition-colors"
            >
              Suscribir
            </button>
          </div>
        </div>
      </section>
    </div>
  )
}
