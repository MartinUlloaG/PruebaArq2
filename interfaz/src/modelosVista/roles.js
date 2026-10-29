// Qué puede hacer cada rol. Lo usan el inicio, la navegación y las cuentas de demo.
// Esto solo decide qué se MUESTRA: quien realmente autoriza es la API (403).

export const ROLES = {
  cliente: { nombre: 'Cliente', puede: 'Compra en el catálogo y revisa sus pedidos.' },
  operador: { nombre: 'Operador', puede: 'Revisa el stock y registra ajustes de inventario.' },
  administrador: { nombre: 'Administrador', puede: 'Gestiona usuarios y productos, y ve el stock.' },
}

export const SECCIONES = [
  {
    ruta: '/catalogo',
    nombre: 'Catálogo',
    descripcion: 'Colección de prendas y accesorios.',
    roles: ['cliente'],
  },
  {
    ruta: '/pedidos',
    nombre: 'Mis pedidos',
    descripcion: 'Tus compras y en qué estado van.',
    roles: ['cliente'],
  },
  {
    ruta: '/inventario',
    nombre: 'Inventario',
    descripcion: 'Stock disponible de cada producto.',
    roles: ['operador', 'administrador'],
  },
  {
    ruta: '/usuarios',
    nombre: 'Usuarios',
    descripcion: 'Cuentas registradas y el rol de cada una.',
    roles: ['administrador'],
  },
]

export const seccionesPara = (rol) => SECCIONES.filter((s) => s.roles.includes(rol))

// SOLO DEMO: las mismas cuentas que crea la semilla del backend.
// La vista de ingreso las muestra únicamente en modo desarrollo.
export const CUENTAS_DEMO = [
  { rol: 'cliente', correo: 'cliente@demo.cl', clave: 'Cliente-Demo-2026' },
  { rol: 'operador', correo: 'operador@demo.cl', clave: 'Operador-Demo-2026' },
  { rol: 'administrador', correo: 'admin@demo.cl', clave: 'Admin-Demo-2026' },
]
