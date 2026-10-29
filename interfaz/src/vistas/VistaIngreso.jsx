import { useRef, useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import {
  AlertCircle,
  ArrowRight,
  Check,
  Eye,
  EyeOff,
  Lock,
  Mail,
  ShieldCheck,
} from 'lucide-react'
import { CUENTAS_DEMO, ROLES } from '../modelosVista/roles'
import { sesionVigente, useSesion } from '../modelosVista/useSesion'

function validar(correo, clave) {
  const errores = {}
  if (!correo.trim()) {
    errores.correo = 'Ingresa tu correo electrónico.'
  } else if (!/^\S+@\S+\.\S+$/.test(correo.trim())) {
    errores.correo = 'Formato de correo inválido (ejemplo: cliente@demo.cl).'
  }
  if (!clave) {
    errores.clave = 'Ingresa tu clave de acceso.'
  }
  return errores
}

export default function VistaIngreso() {
  const ingresar = useSesion((s) => s.ingresar)
  const limpiarMensajes = useSesion((s) => s.limpiarMensajes)
  const cargando = useSesion((s) => s.cargando)
  const error = useSesion((s) => s.error)
  const aviso = useSesion((s) => s.aviso)
  const vigente = useSesion(sesionVigente)

  const navegar = useNavigate()
  const ubicacion = useLocation()

  const [correo, setCorreo] = useState('')
  const [clave, setClave] = useState('')
  const [verClave, setVerClave] = useState(false)
  const [erroresCampo, setErroresCampo] = useState({})

  const refCorreo = useRef(null)
  const refClave = useRef(null)
  const refBoton = useRef(null)

  if (vigente) return <Navigate to="/" replace />

  async function enviar(evento) {
    evento.preventDefault()
    const errores = validar(correo, clave)
    setErroresCampo(errores)

    if (errores.correo) return refCorreo.current?.focus()
    if (errores.clave) return refClave.current?.focus()

    const ok = await ingresar(correo, clave)
    if (ok) navegar(ubicacion.state?.desde ?? '/', { replace: true })
  }

  function usarCuentaDemo(cuenta) {
    setCorreo(cuenta.correo)
    setClave(cuenta.clave)
    setErroresCampo({})
    limpiarMensajes()
    refBoton.current?.focus()
  }

  return (
    <div className="min-h-screen w-full grid grid-cols-1 lg:grid-cols-2 bg-white text-[#1e1e1e]">
      {/* 1. Mitad Izquierda: Split-Screen Editorial (Campaña Unsplash de Moda) */}
      <section className="relative hidden lg:block h-full bg-[#293241] overflow-hidden select-none">
        <img
          src="https://images.unsplash.com/photo-1490481651871-ab68de25d43d?auto=format&fit=crop&w=1400&q=85"
          alt="KYRO Campaña Editorial 2026"
          className="absolute inset-0 w-full h-full object-cover object-center opacity-85 filter contrast-[1.05]"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-[#293241] via-black/30 to-black/20" />

        <div className="absolute inset-0 p-16 flex flex-col justify-between z-10 text-white">
          <div className="flex items-center gap-2">
            <span className="text-2xl font-black tracking-widest uppercase text-white">
              KYRO
            </span>
            <span className="w-1.5 h-1.5 rounded-full bg-[#ee6c4d]" />
          </div>

          <div className="max-w-md">
            <span className="text-[10px] uppercase tracking-[0.35em] text-[#e0fbfc] font-semibold block mb-3">
              AUTUMN / WINTER ARCHIVE 2026
            </span>
            <h2 className="text-4xl font-black uppercase tracking-tight leading-tight mb-4 text-white">
              El Arte de la Confección Silenciosa
            </h2>
            <p className="text-xs uppercase tracking-[0.2em] text-[#e0fbfc]/80 font-light leading-relaxed">
              Inicia sesión para gestionar tus pedidos, acceder al inventario y reservar piezas de tiraje limitado.
            </p>
          </div>

          <div className="flex justify-between items-center text-[10px] uppercase tracking-[0.25em] text-white/60 font-mono">
            <span>STUDIO MONOCHROME</span>
            <span>ALL RIGHTS RESERVED</span>
          </div>
        </div>
      </section>

      {/* 2. Mitad Derecha: Formulario Centrado con Espacios Generosos */}
      <main className="flex flex-col justify-between p-8 sm:p-12 md:p-16 lg:p-20 xl:p-24 overflow-y-auto bg-white">
        {/* Cabecera Móvil / Logo */}
        <div className="flex items-center justify-between mb-8">
          <button
            type="button"
            onClick={() => navegar('/')}
            className="flex items-center gap-2 tracking-tighter"
          >
            <span className="text-2xl font-black text-[#293241] tracking-widest uppercase">
              KYRO
            </span>
            <span className="w-1.5 h-1.5 rounded-full bg-[#ee6c4d]" />
          </button>

          <span className="text-[10px] uppercase tracking-[0.25em] font-semibold text-[#3d5a80]">
            Portal de Acceso
          </span>
        </div>

        {/* Formulario Editorial de Inicio de Sesión */}
        <div className="max-w-md w-full mx-auto my-auto">
          <header className="mb-10">
            <span className="text-[10px] uppercase tracking-[0.35em] text-[#3d5a80] font-bold block mb-1">
              CUENTA CLIENTE / OPERADOR
            </span>
            <h1 className="text-3xl sm:text-4xl font-black uppercase tracking-widest text-[#1e1e1e] leading-none mb-3">
              INICIAR SESIÓN
            </h1>
            <p className="text-xs uppercase tracking-[0.18em] text-[#3d5a80]/80 font-light">
              Ingresa tus credenciales para continuar en la plataforma.
            </p>
          </header>

          {/* Mensajes de aviso / error */}
          {aviso && (
            <div className="mb-6 p-4 border-l-2 border-[#3d5a80] bg-[#e0fbfc]/30 flex items-start gap-3">
              <ShieldCheck className="w-4 h-4 text-[#3d5a80] flex-shrink-0 mt-0.5" />
              <p className="text-xs text-[#293241] tracking-wide font-medium">{aviso}</p>
            </div>
          )}

          {error && (
            <div className="mb-6 p-4 border-l-2 border-red-600 bg-red-50 flex items-start gap-3" role="alert">
              <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-red-800 tracking-wide font-medium">{error}</p>
            </div>
          )}

          <form onSubmit={enviar} noValidate className="space-y-8">
            {/* Campo: Correo (Minimalista: solo borde inferior) */}
            <div className="relative">
              <label
                htmlFor="correo"
                className="text-[10px] uppercase tracking-[0.25em] font-bold text-[#3d5a80] block mb-1.5"
              >
                Correo Electrónico
              </label>
              <div className="relative">
                <input
                  ref={refCorreo}
                  id="correo"
                  type="email"
                  inputMode="email"
                  autoComplete="username"
                  spellCheck="false"
                  placeholder="ejemplo@demo.cl"
                  value={correo}
                  onChange={(e) => setCorreo(e.target.value)}
                  className={`w-full bg-transparent border-b ${
                    erroresCampo.correo ? 'border-red-500' : 'border-gray-300'
                  } py-3 text-sm text-[#1e1e1e] placeholder:text-gray-300 focus:border-[#293241] focus:outline-none transition-colors rounded-none`}
                />
                <Mail className="w-4 h-4 absolute right-0 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
              </div>
              {erroresCampo.correo && (
                <p className="text-[11px] text-red-600 tracking-wide mt-1.5 flex items-center gap-1.5">
                  <AlertCircle className="w-3 h-3" />
                  <span>{erroresCampo.correo}</span>
                </p>
              )}
            </div>

            {/* Campo: Clave (Minimalista: solo borde inferior) */}
            <div className="relative">
              <div className="flex justify-between items-baseline mb-1.5">
                <label
                  htmlFor="clave"
                  className="text-[10px] uppercase tracking-[0.25em] font-bold text-[#3d5a80]"
                >
                  Contraseña
                </label>
                <button
                  type="button"
                  onClick={() => setVerClave((v) => !v)}
                  className="text-[10px] uppercase tracking-widest text-[#3d5a80] hover:text-[#1e1e1e] flex items-center gap-1 transition-colors"
                >
                  {verClave ? (
                    <>
                      <EyeOff className="w-3 h-3" />
                      <span>Ocultar</span>
                    </>
                  ) : (
                    <>
                      <Eye className="w-3 h-3" />
                      <span>Mostrar</span>
                    </>
                  )}
                </button>
              </div>

              <div className="relative">
                <input
                  ref={refClave}
                  id="clave"
                  type={verClave ? 'text' : 'password'}
                  autoComplete="current-password"
                  placeholder="••••••••••••"
                  value={clave}
                  onChange={(e) => setClave(e.target.value)}
                  className={`w-full bg-transparent border-b ${
                    erroresCampo.clave ? 'border-red-500' : 'border-gray-300'
                  } py-3 text-sm text-[#1e1e1e] placeholder:text-gray-300 focus:border-[#293241] focus:outline-none transition-colors rounded-none`}
                />
                <Lock className="w-4 h-4 absolute right-0 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
              </div>
              {erroresCampo.clave && (
                <p className="text-[11px] text-red-600 tracking-wide mt-1.5 flex items-center gap-1.5">
                  <AlertCircle className="w-3 h-3" />
                  <span>{erroresCampo.clave}</span>
                </p>
              )}
            </div>

            {/* Botón Principal Sólido en #ee6c4d Coral */}
            <button
              ref={refBoton}
              type="submit"
              disabled={cargando}
              className="w-full py-4 px-6 bg-[#ee6c4d] hover:bg-[#d95b3d] text-white text-xs uppercase tracking-[0.25em] font-black transition-all flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer"
            >
              <span>{cargando ? 'Autenticando...' : 'Iniciar Sesión'}</span>
              <ArrowRight className="w-4 h-4" />
            </button>

            {/* Enlace Sutil "Crear Cuenta" */}
            <div className="text-center pt-2">
              <button
                type="button"
                onClick={() => usarCuentaDemo(CUENTAS_DEMO[0])}
                className="text-xs uppercase tracking-[0.18em] text-[#3d5a80] hover:text-[#1e1e1e] hover:underline transition-colors font-medium"
              >
                ¿No tienes cuenta? Crear cuenta o solicitar acceso →
              </button>
            </div>
          </form>

          {/* Selector Discreto de Cuentas Demo de Prueba */}
          {import.meta.env.DEV && (
            <div className="mt-12 pt-8 border-t border-[#293241]/10">
              <span className="text-[10px] uppercase tracking-[0.25em] font-bold text-[#3d5a80] block mb-3">
                Accesos de Evaluación Rápida:
              </span>
              <div className="grid grid-cols-3 gap-2">
                {CUENTAS_DEMO.map((c) => (
                  <button
                    key={c.rol}
                    type="button"
                    onClick={() => usarCuentaDemo(c)}
                    className="py-2.5 px-3 border border-gray-200 hover:border-[#293241] bg-white text-[10px] uppercase tracking-wider font-bold text-[#293241] transition-colors text-center"
                  >
                    {ROLES[c.rol].nombre}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer Minimalista */}
        <footer className="text-center pt-8 border-t border-[#293241]/5">
          <p className="text-[10px] uppercase tracking-[0.25em] text-[#3d5a80]/60 font-mono">
            KYRO STUDIO © 2026. SERVICIO SEGURO DE AUTENTICACIÓN.
          </p>
        </footer>
      </main>
    </div>
  )
}
