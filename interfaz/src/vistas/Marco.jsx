import { useEffect, useRef, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { LogOut, Menu, X } from 'lucide-react'
import { ROLES, seccionesPara } from '../modelosVista/roles'
import { useSesion } from '../modelosVista/useSesion'

export default function Marco() {
  const usuario = useSesion((s) => s.usuario)
  const expiraEn = useSesion((s) => s.expiraEn)
  const salir = useSesion((s) => s.salir)
  const { pathname } = useLocation()
  const navegar = useNavigate()
  const refContenido = useRef(null)
  const primeraVez = useRef(true)

  const [menuMovilAbierto, setMenuMovilAbierto] = useState(false)

  useEffect(() => {
    if (primeraVez.current) {
      primeraVez.current = false
      return
    }
    refContenido.current?.focus()
    setMenuMovilAbierto(false)
  }, [pathname])

  useEffect(() => {
    if (!expiraEn) return
    const tiempoRestante = expiraEn - Date.now()
    if (tiempoRestante <= 0) {
      salir('Tu sesión expiró por seguridad. Vuelve a ingresar para continuar.')
      navegar('/ingresar', { replace: true })
      return
    }
    const temporizador = setTimeout(() => {
      salir('Tu sesión expiró por seguridad. Vuelve a ingresar para continuar.')
      navegar('/ingresar', { replace: true })
    }, tiempoRestante)
    return () => clearTimeout(temporizador)
  }, [expiraEn, salir, navegar])

  // Si no hay usuario en sesión, evitamos renderizar el layout para prevenir accesos indebidos
  if (!usuario) {
    return null
  }

  const secciones = seccionesPara(usuario.rol)
  const rolInfo = ROLES[usuario.rol] || { nombre: usuario.rol, puede: '' }

  function handleSalir() {
    salir()
    navegar('/ingresar', { replace: true })
  }

  return (
    <div className="min-h-screen flex flex-col bg-white text-[#1e1e1e]">
      <a
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-[#293241] focus:text-white focus:text-xs focus:uppercase focus:tracking-widest"
        href="#contenido"
      >
        Saltar al contenido
      </a>

      {/* Navbar Editorial KYRO (#293241 Navy) */}
      <header className="sticky top-0 z-40 bg-[#293241] text-white border-b border-white/10 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 h-20 flex items-center justify-between gap-6">
          
          <div className="flex items-center gap-4">
            {/* Botón Menú Móvil */}
            <button
              type="button"
              onClick={() => setMenuMovilAbierto((v) => !v)}
              className="sm:hidden p-2 text-white hover:text-[#e0fbfc] focus:outline-none"
              aria-label="Abrir menú de navegación"
            >
              {menuMovilAbierto ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>

            {/* Logo KYRO */}
            <NavLink
              to="/"
              className="flex items-center gap-2 group tracking-tighter"
              aria-label="KYRO inicio"
            >
              <span className="text-2xl md:text-3xl font-black text-white tracking-widest uppercase transition-opacity group-hover:opacity-80">
                KYRO
              </span>
              <span className="w-1.5 h-1.5 rounded-full bg-[#ee6c4d]" />
            </NavLink>
          </div>

          {/* Enlaces de Navegación de Escritorio */}
          <nav aria-label="Navegación principal" className="hidden sm:flex items-center gap-1 md:gap-2">
            <NavLink
              to="/"
              end
              className={({ isActive }) =>
                `px-3 py-2 text-xs uppercase tracking-[0.2em] font-semibold transition-colors ${
                  isActive
                    ? 'text-white border-b-2 border-[#ee6c4d]'
                    : 'text-[#e0fbfc]/80 hover:text-white'
                }`
              }
            >
              Inicio
            </NavLink>

            {secciones.map((s) => (
              <NavLink
                key={s.ruta}
                to={s.ruta}
                className={({ isActive }) =>
                  `px-3 py-2 text-xs uppercase tracking-[0.2em] font-semibold transition-colors ${
                    isActive
                      ? 'text-white border-b-2 border-[#ee6c4d]'
                      : 'text-[#e0fbfc]/80 hover:text-white'
                  }`
                }
              >
                {s.nombre}
              </NavLink>
            ))}
          </nav>

          {/* Cuenta de Usuario & Salir */}
          <div className="flex items-center gap-3">
            <div className="hidden lg:flex items-center gap-2 text-right">
              <span className="text-[11px] uppercase tracking-wider text-[#e0fbfc]/80 font-mono">
                {usuario.correo}
              </span>
              <span className="text-[9px] uppercase tracking-widest font-bold px-2 py-0.5 border border-[#ee6c4d] text-[#ee6c4d]">
                {rolInfo.nombre}
              </span>
            </div>

            <button
              type="button"
              onClick={handleSalir}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 border border-white/20 hover:border-white text-[11px] uppercase tracking-wider font-semibold text-white transition-colors cursor-pointer"
              title="Cerrar sesión"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Salir</span>
            </button>
          </div>
        </div>

        {/* Menú Desplegable Móvil */}
        {menuMovilAbierto && (
          <nav
            aria-label="Navegación móvil"
            className="sm:hidden bg-[#1e2530] border-t border-white/10 px-4 py-4 space-y-2 animate-fadeIn"
          >
            <div className="pb-3 border-b border-white/10 mb-2">
              <p className="text-[10px] uppercase tracking-widest text-[#e0fbfc]/60">Sesión actual</p>
              <p className="text-xs font-mono text-white truncate">{usuario.correo}</p>
              <span className="inline-block mt-1 text-[9px] uppercase tracking-wider font-bold px-2 py-0.5 bg-[#ee6c4d] text-white">
                {rolInfo.nombre}
              </span>
            </div>

            <NavLink
              to="/"
              end
              onClick={() => setMenuMovilAbierto(false)}
              className={({ isActive }) =>
                `block px-3 py-2 text-xs uppercase tracking-widest font-semibold ${
                  isActive ? 'text-[#ee6c4d] font-bold' : 'text-white/80'
                }`
              }
            >
              Inicio
            </NavLink>

            {secciones.map((s) => (
              <NavLink
                key={s.ruta}
                to={s.ruta}
                onClick={() => setMenuMovilAbierto(false)}
                className={({ isActive }) =>
                  `block px-3 py-2 text-xs uppercase tracking-widest font-semibold ${
                    isActive ? 'text-[#ee6c4d] font-bold' : 'text-white/80'
                  }`
                }
              >
                {s.nombre}
              </NavLink>
            ))}
          </nav>
        )}
      </header>

      {/* Contenedor Principal */}
      <main id="contenido" ref={refContenido} tabIndex={-1} className="flex-1 focus:outline-none">
        <Outlet />
      </main>

      {/* Footer Editorial KYRO (#293241 Navy) */}
      <footer className="border-t border-[#293241]/10 bg-[#293241] text-[#e0fbfc] py-16 px-4 sm:px-6 md:px-8 mt-24">
        <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-4 gap-12 text-xs">
          <div>
            <h4 className="text-xl font-black text-white uppercase tracking-widest mb-3">
              KYRO
            </h4>
            <p className="text-[11px] tracking-wider text-[#e0fbfc]/70 uppercase font-light leading-relaxed">
              Marca de moda minimalista de alta gama. Confección en tejidos pesados de silueta pura.
            </p>
          </div>

          <div>
            <h5 className="text-xs uppercase tracking-[0.25em] font-bold text-white mb-3">
              Líneas
            </h5>
            <ul className="space-y-2 uppercase tracking-wider text-[#e0fbfc]/80">
              <li>Polerones Heavyweight</li>
              <li>Poleras Essential Boxy</li>
              <li>Calcetines High-Gauge</li>
              <li>Gorras Cotton Twill</li>
              <li>Blusas Lino Nórdico</li>
            </ul>
          </div>

          <div>
            <h5 className="text-xs uppercase tracking-[0.25em] font-bold text-white mb-3">
              Arquitectura
            </h5>
            <ul className="space-y-2 uppercase tracking-wider text-[#e0fbfc]/80">
              <li>Patrón Estricto MVVM</li>
              <li>React 19 + Zustand</li>
              <li>FastAPI + PostgreSQL</li>
              <li>Saga Pattern con Kafka</li>
            </ul>
          </div>

          <div>
            <h5 className="text-xs uppercase tracking-[0.25em] font-bold text-white mb-3">
              Garantía de Edición
            </h5>
            <p className="text-[11px] tracking-wider text-[#e0fbfc]/70 uppercase font-light leading-relaxed mb-4">
              Cada prenda se numera y produce en tirajes limitados con algodón orgánico trazable.
            </p>
            <span className="text-[10px] uppercase tracking-widest font-bold text-[#ee6c4d]">
              KYRO STUDIO © 2026. TODOS LOS DERECHOS RESERVADOS.
            </span>
          </div>
        </div>
      </footer>
    </div>
  )
}
