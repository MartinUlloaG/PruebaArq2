import { pedir } from './clienteApi'

// Cualquier usuario con sesión. El catálogo viene de MongoDB (modelo de lectura).
export function listarCatalogo() {
  return pedir('/catalogo')
}

// Categorías con cuántas prendas tiene cada una (las calcula Mongo, no el front).
export function listarCategorias() {
  return pedir('/catalogo/categorias')
}
