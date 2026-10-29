/**
 * KYRO Brand Asset & Mock Catalog Engine (Editorial High-End Fashion)
 * Inspirado en Zara, COS y SSENSE.
 */

export const FOTOS_CAMPANIA = {
  hero: 'https://images.unsplash.com/photo-1490481651871-ab68de25d43d?auto=format&fit=crop&w=2000&q=85',
  poleronesHero: 'https://images.unsplash.com/photo-1556905055-8f358a7a47b2?auto=format&fit=crop&w=1200&q=85',
  polerasHero: 'https://images.unsplash.com/photo-1521572267360-ee0c2909d518?auto=format&fit=crop&w=1200&q=85',
  calcetinesHero: 'https://images.unsplash.com/photo-1582966779680-9286eb792b2e?auto=format&fit=crop&w=1200&q=85',
  gorrasHero: 'https://images.unsplash.com/photo-1588850561407-ed78c282e89b?auto=format&fit=crop&w=1200&q=85',
  blusasHero: 'https://images.unsplash.com/photo-1564257631407-4deb129f0e4f?auto=format&fit=crop&w=1200&q=85',
}

// Categorías para el Grid Asimétrico Editorial
export const CATEGORIAS_ASIMETRICAS = [
  {
    id: 'polerones',
    nombre: 'Polerones',
    subtitulo: 'Heavyweight fleece & siluetas boxy',
    claseGrid: 'md:col-span-2 md:row-span-2 aspect-[4/5]',
    imagen: 'https://images.unsplash.com/photo-1556905055-8f358a7a47b2?auto=format&fit=crop&w=1200&q=80',
    conteo: '24 Piezas',
  },
  {
    id: 'poleras',
    nombre: 'Poleras',
    subtitulo: 'Algodón peinado 280g',
    claseGrid: 'md:col-span-1 md:row-span-1 aspect-[3/4]',
    imagen: 'https://images.unsplash.com/photo-1521572267360-ee0c2909d518?auto=format&fit=crop&w=800&q=80',
    conteo: '18 Piezas',
  },
  {
    id: 'blusas',
    nombre: 'Blusas',
    subtitulo: 'Lino lavado escandinavo',
    claseGrid: 'md:col-span-1 md:row-span-1 aspect-[3/4]',
    imagen: 'https://images.unsplash.com/photo-1564257631407-4deb129f0e4f?auto=format&fit=crop&w=800&q=80',
    conteo: '12 Piezas',
  },
  {
    id: 'gorras',
    nombre: 'Gorras',
    subtitulo: 'Sarga de algodón y lana virgen',
    claseGrid: 'md:col-span-1 md:row-span-1 aspect-[3/4]',
    imagen: 'https://images.unsplash.com/photo-1588850561407-ed78c282e89b?auto=format&fit=crop&w=800&q=80',
    conteo: '8 Piezas',
  },
  {
    id: 'calcetines',
    nombre: 'Calcetines',
    subtitulo: 'Packs acanalados de alta torsión',
    claseGrid: 'md:col-span-1 md:row-span-1 aspect-[3/4]',
    imagen: 'https://images.unsplash.com/photo-1582966779680-9286eb792b2e?auto=format&fit=crop&w=800&q=80',
    conteo: '10 Piezas',
  },
]

// Banco curado de 16 imágenes de alta moda para interpolar el catálogo de 70 prendas
const IMAGENES_KYRO = [
  {
    categoria: 'Polerones',
    url: 'https://images.unsplash.com/photo-1556905055-8f358a7a47b2?auto=format&fit=crop&w=900&q=80',
    nombre: 'HOODIE 01 HEAVYWEIGHT',
  },
  {
    categoria: 'Poleras',
    url: 'https://images.unsplash.com/photo-1521572267360-ee0c2909d518?auto=format&fit=crop&w=900&q=80',
    nombre: 'POLERA ESSENTIAL BOXY',
  },
  {
    categoria: 'Calcetines',
    url: 'https://images.unsplash.com/photo-1582966779680-9286eb792b2e?auto=format&fit=crop&w=900&q=80',
    nombre: 'PACK 3 CALCETINES RIB',
  },
  {
    categoria: 'Gorras',
    url: 'https://images.unsplash.com/photo-1588850561407-ed78c282e89b?auto=format&fit=crop&w=900&q=80',
    nombre: 'GORRA COTTON TWILL',
  },
  {
    categoria: 'Blusas',
    url: 'https://images.unsplash.com/photo-1564257631407-4deb129f0e4f?auto=format&fit=crop&w=900&q=80',
    nombre: 'BLUSA LINO ESTRUCTURADA',
  },
  {
    categoria: 'Polerones',
    url: 'https://images.unsplash.com/photo-1578632767115-351597cf2477?auto=format&fit=crop&w=900&q=80',
    nombre: 'CREWNECK FLEECE MINIMAL',
  },
  {
    categoria: 'Poleras',
    url: 'https://images.unsplash.com/photo-1583743814966-8936f5b7be1a?auto=format&fit=crop&w=900&q=80',
    nombre: 'POLERA BLACK DROP-SHOULDER',
  },
  {
    categoria: 'Calcetines',
    url: 'https://images.unsplash.com/photo-1586350977771-b3b0abd50c82?auto=format&fit=crop&w=900&q=80',
    nombre: 'CALCETÍN MID-CALF SPORT',
  },
  {
    categoria: 'Polerones',
    url: 'https://images.unsplash.com/photo-1509967419530-da38b4704bc6?auto=format&fit=crop&w=900&q=80',
    nombre: 'SWEATER RELAXED OVERSIZED',
  },
  {
    categoria: 'Poleras',
    url: 'https://images.unsplash.com/photo-1618354691373-d851c5c3a990?auto=format&fit=crop&w=900&q=80',
    nombre: 'POLERA BLANCA RAW CUT',
  },
  {
    categoria: 'Blusas',
    url: 'https://images.unsplash.com/photo-1551488831-00ddcb6c6bd3?auto=format&fit=crop&w=900&q=80',
    nombre: 'CAMISA OVERSIZE POPELINA',
  },
  {
    categoria: 'Gorras',
    url: 'https://images.unsplash.com/photo-1534215754734-18e55d13e346?auto=format&fit=crop&w=900&q=80',
    nombre: 'BEANIE MERINO EXTRAFINA',
  },
  {
    categoria: 'Polerones',
    url: 'https://images.unsplash.com/photo-1620799140408-edc6dcb6d633?auto=format&fit=crop&w=900&q=80',
    nombre: 'HOODIE ZIPPER MONOCHROME',
  },
  {
    categoria: 'Poleras',
    url: 'https://images.unsplash.com/photo-1503342217505-b0a15ec3261c?auto=format&fit=crop&w=900&q=80',
    nombre: 'POLERA SLAB ORGANIC',
  },
  {
    categoria: 'Calcetines',
    url: 'https://images.unsplash.com/photo-1552902865-b72c031ac5ea?auto=format&fit=crop&w=900&q=80',
    nombre: 'CALCETINES WAFFLE KNIT',
  },
  {
    categoria: 'Blusas',
    url: 'https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?auto=format&fit=crop&w=900&q=80',
    nombre: 'TÚNICA LINO NÓRDICO',
  },
]

const ADJETIVOS_KYRO = ['EDICIÓN 01', 'ESTRUCTURADO', 'MINIMAL', 'HEAVYWEIGHT', 'RAW', 'ARCHIVE', 'STUDIO', 'MONOCHROME']

/**
 * Genera el catálogo enriquecido de ~70 productos garantizando:
 * 1. Todos los productos reales del backend están presentes con sus IDs verdaderos.
 * 2. Las réplicas simuladas reutilizan IDs válidos del backend (para que agregar al carrito y pagar nunca falle con 404/500 en la BD).
 * 3. Categorías asignadas equitativamente entre las 5 categorías.
 */
export function generarCatalogoSimulado70(datosBackend = []) {
  const baseBackend = Array.isArray(datosBackend) && datosBackend.length > 0 ? datosBackend : []
  const TOTAL_OBJETIVO = 70
  const resultado = []

  for (let i = 0; i < TOTAL_OBJETIVO; i++) {
    // Si hay datos del backend, asociamos cada item a un producto backend existente para no romper la BD en el checkout
    const backendRef = baseBackend.length > 0 ? baseBackend[i % baseBackend.length] : null
    const idReal = backendRef ? (backendRef.producto_id ?? backendRef.id) : (i + 1)
    const disponiblesReales = backendRef ? backendRef.disponibles : 15

    const templateImg = IMAGENES_KYRO[i % IMAGENES_KYRO.length]
    const adj = ADJETIVOS_KYRO[i % ADJETIVOS_KYRO.length]
    const numSerie = String(i + 1).padStart(2, '0')

    // Variar precios dentro de una escala creíble (ej: $14.990 a $129.990)
    const factorPrecio = (i * 37) % 8
    const precioBase =
      templateImg.categoria === 'Polerones' ? 49990 + factorPrecio * 10000 :
      templateImg.categoria === 'Blusas' ? 39990 + factorPrecio * 7000 :
      templateImg.categoria === 'Poleras' ? 24990 + factorPrecio * 4000 :
      templateImg.categoria === 'Gorras' ? 19990 + factorPrecio * 3000 :
      12990 + factorPrecio * 2000

    // Si es el primer set de productos, conservamos el precio exacto del backend para consistencia
    const precioFinal = (i < baseBackend.length && backendRef?.precio) ? backendRef.precio : precioBase

    resultado.push({
      id: `${idReal}-${i}`, // Clave única para listas React
      producto_id: idReal, // ID real para enviar al backend en POST /pedidos
      nombre: i < baseBackend.length && !backendRef.nombre.toLowerCase().includes('audí') ? backendRef.nombre.toUpperCase() : `${templateImg.nombre} ${adj} #${numSerie}`,
      descripcion: `Prenda editorial de la serie KYRO Archive. Confeccionada con algodón de alto gramaje y líneas puras.`,
      precio: precioFinal,
      disponibles: i === 4 ? 0 : (disponiblesReales ?? 10), // Un producto agotado para validar UX de stock
      categoria: templateImg.categoria,
      imagen: templateImg.url,
      imagen_url: templateImg.url,
    })
  }

  return resultado
}

export function obtenerDetallesPrenda(id = 0, nombre = '') {
  const norm = IMAGENES_KYRO[Math.abs(Number(id) || 0) % IMAGENES_KYRO.length]
  return {
    url: norm.url,
    categoria: norm.categoria,
    alt: nombre || norm.nombre,
  }
}
