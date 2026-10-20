import { pedir } from './clienteApi'

// Operador y administrador.
export function listarInventario() {
  return pedir('/inventario')
}

// Solo administrador.
export function listarUsuarios() {
  return pedir('/administracion/usuarios')
}
