import { useEffect, useRef } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'

import { ROLES, seccionesPara } from '../modelosVista/roles'
import { useSesion } from '../modelosVista/useSesion'

// Estructura común de las páginas con sesión: encabezado, navegación según rol y contenido.
export default function Marco() {
  const usuario = useSesion((s) => s.usuario)
  const expiraEn = useSesion((s) => s.expiraEn)
  const salir = useSesion((s) => s.salir)
  const { pathname } = useLocation()
  const refContenido = useRef(null)
  const primeraVez = useRef(true)

  // Al cambiar de página, el foco va al contenido: el lector de pantalla no queda perdido arriba.
  useEffect(() => {
    if (primeraVez.current) {
      primeraVez.current = false
      return
    }
    refContenido.current?.focus()
  }, [pathname])

  // Cierra la sesión justo cuando vence el token, sin esperar a que la API responda 401.
  useEffect(() => {
    const temporizador = setTimeout(
      () => salir('Tu sesión expiró por seguridad. Vuelve a ingresar para continuar.'),
      Math.max(expiraEn - Date.now(), 0),
    )
    return () => clearTimeout(temporizador)
  }, [expiraEn, salir])

  return (
    <div className="marco">
      <a className="saltar" href="#contenido">
        Saltar al contenido
      </a>
      <header className="marco__encabezado">
        <NavLink to="/" className="marca" aria-label="Tienda Arquitectura de Software, ir al inicio">
          Tienda Arquitectura de Software
        </NavLink>
        <nav aria-label="Secciones" className="marco__nav">
          <NavLink to="/" end>
            Inicio
          </NavLink>
          {seccionesPara(usuario.rol).map((s) => (
            <NavLink key={s.ruta} to={s.ruta}>
              {s.nombre}
            </NavLink>
          ))}
        </nav>
        <div className="marco__cuenta">
          <span className="marco__correo">{usuario.correo}</span>
          <span className={`etiqueta-rol etiqueta-rol--${usuario.rol}`}>{ROLES[usuario.rol].nombre}</span>
          <button type="button" className="boton-secundario" onClick={() => salir()}>
            Cerrar sesión
          </button>
        </div>
      </header>
      <main id="contenido" ref={refContenido} tabIndex={-1} className="marco__contenido">
        <Outlet />
      </main>
    </div>
  )
}
