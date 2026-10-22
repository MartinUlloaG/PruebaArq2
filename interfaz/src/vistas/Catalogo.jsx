import { estadoStock, formatearPrecio, POCO_STOCK } from '../modelosVista/stock'
import { useRecurso } from '../modelosVista/useRecurso'
import { listarCatalogo } from '../servicios/catalogo'
import EstadoCarga from './EstadoCarga'

// Texto de disponibilidad para el cliente: el número exacto solo importa cuando queda poco.
function textoDisponibles(cantidad) {
  if (cantidad === 0) return 'Agotado'
  if (cantidad <= POCO_STOCK) return cantidad === 1 ? 'Queda 1' : `Quedan ${cantidad}`
  return 'Disponible'
}

export default function Catalogo() {
  const { datos, cargando, error, reintentar } = useRecurso(listarCatalogo)

  return (
    <section aria-labelledby="titulo-catalogo">
      <h2 id="titulo-catalogo">Catálogo</h2>
      <EstadoCarga cargando={cargando} error={error} reintentar={reintentar}>
        {datos?.length === 0 ? (
          <p className="vacio">No hay productos publicados por ahora.</p>
        ) : (
          <ul className="catalogo">
            {datos?.map((producto) => {
              const estado = estadoStock(producto.disponibles)
              return (
                <li
                  key={producto.producto_id}
                  className={`producto${producto.disponibles === 0 ? ' producto--agotado' : ''}`}
                >
                  <h3 className="producto__nombre">{producto.nombre}</h3>
                  {producto.descripcion && (
                    <p className="producto__descripcion">{producto.descripcion}</p>
                  )}
                  <div className="producto__pie">
                    <span className="producto__precio">{formatearPrecio(producto.precio)}</span>
                    <span className={`estado-stock estado-stock--${estado.clase}`}>
                      {textoDisponibles(producto.disponibles)}
                    </span>
                  </div>
                </li>
              )
            })}
          </ul>
        )}
      </EstadoCarga>
    </section>
  )
}
