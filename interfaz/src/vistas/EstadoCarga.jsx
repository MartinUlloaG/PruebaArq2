import { IconoError } from './Iconos'

// Estados compartidos de las listas: cargando y error con opción de reintentar.
export default function EstadoCarga({ cargando, error, reintentar, children }) {
  if (cargando) {
    return (
      <p className="cargando" role="status">
        Cargando…
      </p>
    )
  }
  if (error) {
    return (
      <div className="mensaje mensaje--error" role="alert">
        <IconoError />
        <span>{error}</span>
        <button type="button" className="boton-texto" onClick={reintentar}>
          Reintentar
        </button>
      </div>
    )
  }
  return children
}
