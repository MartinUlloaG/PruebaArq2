import { pedir } from './clienteApi'

export function ingresar(correo, clave) {
  return pedir('/autenticacion/ingresar', { metodo: 'POST', cuerpo: { correo, clave } })
}
