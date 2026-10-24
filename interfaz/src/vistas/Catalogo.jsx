import { useCompra } from '../modelosVista/useCompra'
import { estadoStock, formatearPrecio, POCO_STOCK } from '../modelosVista/stock'
import { useRecurso } from '../modelosVista/useRecurso'
import { listarCatalogo } from '../servicios/catalogo'
import EstadoCarga from './EstadoCarga'
import { IconoError } from './Iconos'

// Texto de disponibilidad para el cliente: el número exacto solo importa cuando queda poco.
function textoDisponibles(cantidad) {
  if (cantidad === 0) return 'Agotado'
  if (cantidad <= POCO_STOCK) return cantidad === 1 ? 'Queda 1' : `Quedan ${cantidad}`
  return 'Disponible'
}

export default function Catalogo() {
  const { datos, cargando, error, reintentar, recargar } = useRecurso(listarCatalogo)
  const { comprando, resultado, comprar } = useCompra(recargar)

  return (
    <section aria-labelledby="titulo-catalogo">
      <h2 id="titulo-catalogo">Catálogo</h2>

      {/* Región viva siempre presente: el lector de pantalla anuncia el resultado de la compra. */}
      <div aria-live="polite">
        {resultado && (
          <p className={`mensaje mensaje--${resultado.tipo}`}>
            {resultado.tipo === 'error' && <IconoError />}
            <span>{resultado.texto}</span>
          </p>
        )}
      </div>

      <EstadoCarga cargando={cargando} error={error} reintentar={reintentar}>
        {datos?.length === 0 ? (
          <p className="vacio">No hay productos publicados por ahora.</p>
        ) : (
          <ul className="catalogo">
            {datos?.map((producto) => {
              const estado = estadoStock(producto.disponibles)
              const agotado = producto.disponibles === 0
              const enCurso = comprando === producto.producto_id
              return (
                <li
                  key={producto.producto_id}
                  className={`producto${agotado ? ' producto--agotado' : ''}`}
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
                  <button
                    type="button"
                    className="boton-principal producto__comprar"
                    disabled={agotado || comprando !== null}
                    onClick={() => comprar(producto)}
                  >
                    {enCurso ? 'Pagando…' : agotado ? 'Sin stock' : 'Comprar'}
                    <span className="solo-lector"> {producto.nombre}</span>
                  </button>
                </li>
              )
            })}
          </ul>
        )}
      </EstadoCarga>
    </section>
  )
}
