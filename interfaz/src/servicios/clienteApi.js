// Único punto de salida hacia la API: agrega el token y traduce los errores a mensajes legibles.
// Vite reenvía /api al servicio de compras (ver vite.config.js), así no hace falta CORS.

const BASE = '/api'

export class ErrorApi extends Error {
  constructor(estado, mensaje) {
    super(mensaje)
    this.estado = estado
  }
}

// La sesión se inyecta desde el ViewModel, para que este módulo no dependa de Zustand.
let obtenerToken = () => null
let alNoAutorizado = () => {}

export function configurarSesion(opciones) {
  ;({ obtenerToken, alNoAutorizado } = opciones)
}

const SIN_CONEXION =
  'No hay conexión con el servicio de compras. Revisa que esté encendido e inténtalo de nuevo.'

function mensajeDeError(cuerpo, estado) {
  // El 404 de FastAPI viene en inglés ("Not Found"); los demás detail ya son nuestros, en español.
  if (estado === 404) return 'No encontramos esta información. Inténtalo de nuevo en unos minutos.'
  if (typeof cuerpo?.detail === 'string') return cuerpo.detail
  if (Array.isArray(cuerpo?.detail)) return 'Revisa los datos ingresados.'
  if (estado >= 500) return 'El servidor tuvo un problema. Inténtalo de nuevo en unos segundos.'
  return `Error inesperado (código ${estado}).`
}

export async function pedir(ruta, { metodo = 'GET', cuerpo } = {}) {
  const encabezados = { Accept: 'application/json' }
  if (cuerpo !== undefined) encabezados['Content-Type'] = 'application/json'
  const token = obtenerToken()
  if (token) encabezados.Authorization = `Bearer ${token}`

  let respuesta
  try {
    respuesta = await fetch(BASE + ruta, {
      method: metodo,
      headers: encabezados,
      body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo),
    })
  } catch {
    throw new ErrorApi(0, SIN_CONEXION)
  }

  const datos = await respuesta.json().catch(() => null)
  if (!respuesta.ok) {
    // Si el proxy de Vite no alcanza al servicio, responde 5xx sin JSON.
    const mensaje =
      datos === null && respuesta.status >= 500
        ? SIN_CONEXION
        : mensajeDeError(datos, respuesta.status)
    // 401 con token = la sesión dejó de valer (vencida o adulterada): se cierra.
    if (respuesta.status === 401 && token) alNoAutorizado(mensaje)
    throw new ErrorApi(respuesta.status, mensaje)
  }
  return datos
}
