import { pedir } from './clienteApi'

// Cualquier usuario con sesión.
export function listarCatalogo() {
  return pedir('/catalogo')
}
