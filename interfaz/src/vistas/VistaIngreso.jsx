import { useRef, useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'

import { CUENTAS_DEMO, ROLES } from '../modelosVista/roles'
import { sesionVigente, useSesion } from '../modelosVista/useSesion'
import { IconoError, IconoReloj } from './Iconos'

function validar(correo, clave) {
  const errores = {}
  if (!correo.trim()) errores.correo = 'Escribe tu correo.'
  else if (!/^\S+@\S+\.\S+$/.test(correo.trim()))
    errores.correo = 'Revisa el correo: debe tener la forma nombre@dominio.cl.'
  if (!clave) errores.clave = 'Escribe tu clave.'
  return errores
}

export default function VistaIngreso() {
  // Selectores de Zustand: la vista se vuelve a pintar solo si cambia lo que lee.
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
    if (errores.correo) return refCorreo.current.focus()
    if (errores.clave) return refClave.current.focus()

    const ok = await ingresar(correo, clave)
    if (ok) navegar(ubicacion.state?.desde ?? '/', { replace: true })
  }

  function usarCuentaDemo(cuenta) {
    setCorreo(cuenta.correo)
    setClave(cuenta.clave)
    setErroresCampo({})
    limpiarMensajes()
    refBoton.current.focus() // queda listo para presionar Enter
  }

  return (
    <div className="ingreso">
      <a className="saltar" href="#formulario-ingreso">
        Saltar al formulario
      </a>
      <header className="ingreso__marca">
        <span className="marca">Tienda Arquitectura de Software</span>
      </header>

      <main className="ingreso__cuerpo">
        <section className="ingreso__formulario" aria-labelledby="titulo-ingreso">
          <h1 id="titulo-ingreso">Ingresa a tu cuenta</h1>
          <p className="bajada">Usa el correo y la clave de tu cuenta de la tienda.</p>

          {aviso && (
            <p className="mensaje mensaje--aviso" role="status">
              <IconoReloj />
              <span>{aviso}</span>
            </p>
          )}
          {/* Región siempre presente: el lector de pantalla anuncia el error apenas aparece. */}
          <div role="alert" aria-atomic="true">
            {error && (
              <p className="mensaje mensaje--error">
                <IconoError />
                <span>{error}</span>
              </p>
            )}
          </div>

          <form id="formulario-ingreso" onSubmit={enviar} noValidate>
            <div className="campo">
              <label htmlFor="correo">Correo</label>
              <input
                ref={refCorreo}
                id="correo"
                type="email"
                inputMode="email"
                autoComplete="username"
                spellCheck="false"
                value={correo}
                onChange={(e) => setCorreo(e.target.value)}
                aria-invalid={Boolean(erroresCampo.correo)}
                aria-describedby={erroresCampo.correo ? 'correo-error' : undefined}
              />
              {erroresCampo.correo && (
                <p id="correo-error" className="campo__error">
                  <IconoError />
                  {erroresCampo.correo}
                </p>
              )}
            </div>

            <div className="campo">
              <label htmlFor="clave">Clave</label>
              <div className="campo__clave">
                <input
                  ref={refClave}
                  id="clave"
                  type={verClave ? 'text' : 'password'}
                  autoComplete="current-password"
                  value={clave}
                  onChange={(e) => setClave(e.target.value)}
                  aria-invalid={Boolean(erroresCampo.clave)}
                  aria-describedby={erroresCampo.clave ? 'clave-error' : undefined}
                />
                <button
                  type="button"
                  className="boton-texto"
                  aria-controls="clave"
                  onClick={() => setVerClave((v) => !v)}
                >
                  {verClave ? 'Ocultar clave' : 'Mostrar clave'}
                </button>
              </div>
              {erroresCampo.clave && (
                <p id="clave-error" className="campo__error">
                  <IconoError />
                  {erroresCampo.clave}
                </p>
              )}
            </div>

            <button ref={refBoton} type="submit" className="boton-principal" disabled={cargando}>
              {cargando ? 'Ingresando…' : 'Ingresar'}
            </button>
          </form>
        </section>

        {import.meta.env.DEV && (
          <aside className="demo" aria-labelledby="titulo-demo">
            <h2 id="titulo-demo">Cuentas de demostración</h2>
            <p className="bajada">
              Elige un rol para completar el formulario. Cada rol ve partes distintas de la tienda.
            </p>
            <ul className="demo__lista">
              {CUENTAS_DEMO.map((cuenta) => (
                <li key={cuenta.rol}>
                  <button
                    type="button"
                    className={`credencial credencial--${cuenta.rol}`}
                    onClick={() => usarCuentaDemo(cuenta)}
                  >
                    <span className="credencial__rol">{ROLES[cuenta.rol].nombre}</span>
                    <span className="credencial__correo">{cuenta.correo}</span>
                    <span className="credencial__permisos">{ROLES[cuenta.rol].puede}</span>
                  </button>
                </li>
              ))}
            </ul>
          </aside>
        )}
      </main>
    </div>
  )
}
