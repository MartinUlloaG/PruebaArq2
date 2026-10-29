import { pedir } from './clienteApi'

// Cualquier usuario con sesión. El catálogo viene de MongoDB (modelo de lectura).
export function listarCatalogo() {
  return pedir('/catalogo')
}

// Categorías con cuántas prendas tiene cada una (las calcula Mongo, no el front).
export function listarCategorias() {
  return pedir('/catalogo/categorias')
}

// Más vendidos, desde el servicio de recomendaciones (gRPC detrás del núcleo).
// Si ese servicio está caído responde igual 200, con disponible=false.
export function listarRecomendaciones() {
  return pedir('/recomendaciones')
}
