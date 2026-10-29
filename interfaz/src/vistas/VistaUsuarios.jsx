import { useMemo, useState } from 'react'
import { AlertTriangle, CheckCircle2, DollarSign, RefreshCw, Search, ShoppingBag, Users } from 'lucide-react'
import { ROLES } from '../modelosVista/roles'
import { formatearPrecio } from '../modelosVista/stock'
import { useRecurso } from '../modelosVista/useRecurso'
import { listarUsuarios, obtenerResumenAdmin } from '../servicios/paneles'
import EstadoCarga from './EstadoCarga'

export default function VistaUsuarios() {
  const {
    datos: listaUsuarios,
    cargando: cargandoUsuarios,
    error: errorUsuarios,
    reintentar: reintentarUsuarios,
    recargar: recargarUsuarios,
  } = useRecurso(listarUsuarios)

  const {
    datos: metricasAdmin,
    cargando: cargandoMetricas,
    recargar: recargarMetricas,
  } = useRecurso(obtenerResumenAdmin)

  const [busqueda, setBusqueda] = useState('')
  const [rolFiltro, setRolFiltro] = useState('todos') // 'todos' | 'cliente' | 'operador' | 'administrador'

  function actualizarTodo() {
    recargarUsuarios()
    recargarMetricas()
  }

  // Lista de usuarios segura
  const usuarios = useMemo(() => {
    return Array.isArray(listaUsuarios) ? listaUsuarios : []
  }, [listaUsuarios])

  // Métricas calculadas en el backend. Mientras no llegan se muestra "—", nunca un número inventado.
  const metricas = metricasAdmin ?? {}
  const valor = (n, formato = (x) => x) => (n === undefined ? '—' : formato(n))

  // Filtrado de usuarios
  const usuariosFiltrados = useMemo(() => {
    const termino = busqueda.trim().toLowerCase()
    return usuarios.filter((u) => {
      if (rolFiltro !== 'todos' && u.rol !== rolFiltro) return false
      if (termino.length > 0 && !u.correo.toLowerCase().includes(termino)) return false
      return true
    })
  }, [usuarios, rolFiltro, busqueda])

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 py-10 bg-white text-[#1e1e1e]">
      {/* 1. Header Ejecutivo */}
      <header className="border-b border-[#293241]/10 pb-8 mb-8">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="w-2 h-2 rounded-full bg-[#ee6c4d]" />
              <span className="text-[10px] uppercase tracking-[0.3em] font-bold text-[#3d5a80]">
                PANEL DE GOBIERNO / ROL ADMINISTRADOR
              </span>
            </div>
            <h1 className="text-3xl md:text-4xl font-black uppercase tracking-tight text-[#1e1e1e]">
              Control Ejecutivo y Usuarios KYRO
            </h1>
            <p className="text-xs uppercase tracking-[0.18em] text-[#3d5a80] font-light mt-1">
              Supervisión de métricas de facturación, estado transaccional y asignación de roles.
            </p>
          </div>

          <button
            type="button"
            onClick={actualizarTodo}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-[#293241] hover:bg-[#3d5a80] text-white text-xs uppercase tracking-widest font-bold transition-colors cursor-pointer self-start md:self-auto"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${cargandoUsuarios || cargandoMetricas ? 'animate-spin' : ''}`} />
            <span>Sincronizar Panel</span>
          </button>
        </div>

        {/* 2. Tarjetas de Métricas Ejecutivas del Negocio */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-8">
          <div className="p-6 border border-[#293241]/10 bg-white shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] uppercase tracking-widest text-[#3d5a80] font-bold">
                Ingresos Registrados
              </span>
              <DollarSign className="w-4 h-4 text-emerald-600" />
            </div>
            <p className="text-2xl sm:text-3xl font-black text-[#1e1e1e] tabular-nums">
              {valor(metricas.ingresos_totales, formatearPrecio)}
            </p>
            <span className="text-[10px] text-[#3d5a80]/70 uppercase tracking-wider block mt-1">
              Pedidos pagados
            </span>
          </div>

          <div className="p-6 border border-[#293241]/10 bg-white shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] uppercase tracking-widest text-[#3d5a80] font-bold">
                Pedidos Procesados
              </span>
              <ShoppingBag className="w-4 h-4 text-[#3d5a80]" />
            </div>
            <p className="text-2xl sm:text-3xl font-black text-[#293241] tabular-nums">
              {valor(metricas.total_pedidos)}
            </p>
            <span className="text-[10px] text-[#3d5a80]/70 uppercase tracking-wider block mt-1">
              Todos los estados
            </span>
          </div>

          <div className="p-6 border border-[#293241]/10 bg-white shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] uppercase tracking-widest text-[#3d5a80] font-bold">
                Stock Crítico Alerta
              </span>
              <AlertTriangle className="w-4 h-4 text-[#ee6c4d]" />
            </div>
            <p className="text-2xl sm:text-3xl font-black text-[#ee6c4d] tabular-nums">
              {valor(metricas.stock_critico)}
            </p>
            <span className="text-[10px] text-[#3d5a80]/70 uppercase tracking-wider block mt-1">
              Productos con ≤ 5 unidades
            </span>
          </div>

          <div className="p-6 border border-[#293241]/10 bg-white shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] uppercase tracking-widest text-[#3d5a80] font-bold">
                Cuentas Registradas
              </span>
              <Users className="w-4 h-4 text-[#293241]" />
            </div>
            <p className="text-2xl sm:text-3xl font-black text-[#293241] tabular-nums">
              {valor(metricas.total_usuarios)}
            </p>
            <span className="text-[10px] text-[#3d5a80]/70 uppercase tracking-wider block mt-1">
              Seguridad Argon2id + JWT
            </span>
          </div>
        </div>
      </header>

      {/* 3. Filtros y Búsqueda de Usuarios */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div className="flex items-center gap-2">
          {['todos', 'administrador', 'operador', 'cliente'].map((r) => (
            <button
              key={r}
              type="button"
              onClick={() => setRolFiltro(r)}
              className={`px-3 py-1.5 text-[11px] uppercase tracking-wider font-bold transition-colors cursor-pointer ${
                rolFiltro === r
                  ? 'bg-[#293241] text-white'
                  : 'bg-white border border-[#293241]/20 text-[#1e1e1e] hover:border-[#293241]'
              }`}
            >
              {r === 'todos' ? 'Todos' : ROLES[r]?.nombre || r}
            </button>
          ))}
        </div>

        <div className="relative min-w-[240px]">
          <input
            type="text"
            placeholder="BUSCAR POR CORREO..."
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            className="w-full pl-8 pr-3 py-2 bg-transparent border-b border-[#293241]/20 text-xs uppercase tracking-wider placeholder:text-[#3d5a80]/50 focus:outline-none focus:border-[#293241]"
          />
          <Search className="w-3.5 h-3.5 absolute left-1.5 top-1/2 -translate-y-1/2 text-[#3d5a80]" />
        </div>
      </div>

      {/* 4. Tabla de Usuarios y Roles */}
      <EstadoCarga cargando={cargandoUsuarios && usuarios.length === 0} error={errorUsuarios} reintentar={reintentarUsuarios}>
        <div className="border border-[#293241]/10 overflow-x-auto shadow-sm mb-12">
          <table className="w-full text-left text-xs uppercase tracking-wider border-collapse">
            <thead className="bg-[#293241] text-white text-[10px] tracking-[0.2em]">
              <tr>
                <th scope="col" className="py-4 px-4 font-bold">Identidad de Cuenta</th>
                <th scope="col" className="py-4 px-4 font-bold">Rol Asignado</th>
                <th scope="col" className="py-4 px-4 font-bold">Alcance de Operación</th>
                <th scope="col" className="py-4 px-4 font-bold text-right">Seguridad Hash</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#293241]/10 bg-white">
              {usuariosFiltrados.length === 0 ? (
                <tr>
                  <td colSpan={4} className="py-12 text-center text-[#3d5a80] font-light">
                    No se encontraron cuentas bajo este criterio.
                  </td>
                </tr>
              ) : (
                usuariosFiltrados.map((u) => {
                  const rolInfo = ROLES[u.rol] || { nombre: u.rol, puede: 'Acceso básico' }
                  const esAdmin = u.rol === 'administrador'
                  const esOperador = u.rol === 'operador'

                  return (
                    <tr key={u.id} className="hover:bg-[#f4fbfb]/50 transition-colors">
                      {/* Correo e inicial */}
                      <td className="py-4 px-4 font-semibold text-[#1e1e1e]">
                        <div className="flex items-center gap-3">
                          <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs ${
                            esAdmin ? 'bg-[#293241] text-white' : esOperador ? 'bg-[#3d5a80] text-white' : 'bg-gray-200 text-[#1e1e1e]'
                          }`}>
                            {u.correo.charAt(0).toUpperCase()}
                          </div>
                          <div>
                            <span className="block font-mono text-xs">{u.correo}</span>
                            <span className="text-[10px] text-[#3d5a80]/60 lowercase">id: #{u.id}</span>
                          </div>
                        </div>
                      </td>

                      {/* Rol */}
                      <td className="py-4 px-4">
                        <span className={`inline-block px-2.5 py-1 text-[10px] font-bold tracking-widest ${
                          esAdmin
                            ? 'bg-[#293241] text-[#e0fbfc] border border-[#293241]'
                            : esOperador
                            ? 'bg-[#ee6c4d]/10 text-[#ee6c4d] border border-[#ee6c4d]/30'
                            : 'bg-gray-100 text-[#1e1e1e] border border-gray-200'
                        }`}>
                          {rolInfo.nombre}
                        </span>
                      </td>

                      {/* Capacidades del Rol */}
                      <td className="py-4 px-4 text-[#3d5a80] font-light text-[11px] max-w-md">
                        {rolInfo.puede}
                      </td>

                      {/* Hash Info */}
                      <td className="py-4 px-4 text-right">
                        <span className="inline-flex items-center gap-1.5 text-[10px] font-mono text-emerald-800 bg-emerald-50 px-2 py-0.5 border border-emerald-200">
                          <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                          <span>Argon2id</span>
                        </span>
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
