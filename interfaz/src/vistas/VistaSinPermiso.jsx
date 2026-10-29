import { Link } from 'react-router-dom'
import { ShieldAlert } from 'lucide-react'
import { ROLES, obtenerRutaPrincipalRol } from '../modelosVista/roles'
import { useSesion } from '../modelosVista/useSesion'

export default function VistaSinPermiso() {
  const rol = useSesion((s) => s.usuario?.rol)
  const rutaInicio = obtenerRutaPrincipalRol(rol)
  const nombreRol = ROLES[rol]?.nombre ?? 'invitado'

  return (
    <div className="min-h-[70vh] flex flex-col items-center justify-center p-8 text-center bg-white text-[#1e1e1e]">
      <div className="w-16 h-16 rounded-full bg-[#ee6c4d]/10 text-[#ee6c4d] flex items-center justify-center mb-6">
        <ShieldAlert className="w-8 h-8" />
      </div>

      <span className="text-[10px] uppercase tracking-[0.3em] text-[#ee6c4d] font-bold block mb-2">
        Acceso Denegado (403)
      </span>

      <h1 className="text-2xl sm:text-3xl font-black uppercase tracking-tight text-[#1e1e1e] mb-3">
        Sección Restringida para tu Rol
      </h1>

      <p className="text-xs uppercase tracking-widest text-[#3d5a80] max-w-md mb-8 leading-relaxed font-light">
        Has iniciado sesión con el rol <strong className="font-bold text-[#1e1e1e]">{nombreRol}</strong>. Esta sección requiere permisos específicos asignados a otro perfil.
      </p>

      <div className="flex flex-wrap gap-4 justify-center">
        <Link
          to={rutaInicio}
          className="px-6 py-3 bg-[#293241] hover:bg-[#3d5a80] text-white text-xs uppercase tracking-[0.2em] font-bold transition-colors"
        >
          Ir a mi panel principal
        </Link>
        <Link
          to="/"
          className="px-6 py-3 border border-[#293241]/20 hover:border-[#293241] text-[#1e1e1e] text-xs uppercase tracking-[0.2em] font-bold transition-colors"
        >
          Volver a Inicio
        </Link>
      </div>
    </div>
  )
}
