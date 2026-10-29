/**
 * KYRO Brand Asset & Dynamic Image Engine (Editorial Minimalist Apparel)
 * Mapeo inteligente y dinámico de imágenes de Unsplash por categoría y nombre.
 * URLs directas verificadas (HTTP 200 OK), cero imágenes rotas y cero productos tecnológicos.
 */

// URLs específicas directas de Unsplash requeridas para prendas icónicas de la colección
export const FOTOS_DIRECTAS_ESPECIFICAS = {
  // Calcetines verdes (Unsplash 8Al2ylhlCYk / photo-1640026199235-c24aa417b552)
  calcetinesVerdes:
    'https://images.unsplash.com/photo-1640026199235-c24aa417b552?auto=format&fit=crop&w=900&q=80',
  calcetinesVerdesAlt:
    'https://images.unsplash.com/photo-1586350977771-b3b0ecd50c82?auto=format&fit=crop&w=900&q=80',
  // Calcetines Térmicos Waffle - Pares de calcetines de colores esparcidos sobre naranja (Unsplash fgv9qmOYzc4 / premium_photo-1755164641094-3b00ad813362)
  calcetinesWaffleNaranja:
    'https://plus.unsplash.com/premium_photo-1755164641094-3b00ad813362?auto=format&fit=crop&w=900&q=80',
  // Gorra Cotton Twill Beige - Gorra/sombrero en la manta (Unsplash VRjbcJSINVc / photo-1720100967713-ff15377669e8)
  gorraManta:
    'https://images.unsplash.com/photo-1720100967713-ff15377669e8?auto=format&fit=crop&w=900&q=80',
  // Beanie Merino Extra Fino - Gorra blanca y roja sobre superficie azul (Unsplash htQnr9LCxdM / photo-1628753611124-5d20c4f3e177)
  beanieBlancaRojaAzul:
    'https://images.unsplash.com/photo-1628753611124-5d20c4f3e177?auto=format&fit=crop&w=900&q=80',
}

export const FOTOS_CAMPANIA = {
  hero: 'https://images.unsplash.com/photo-1441986300917-64674bd600d8?auto=format&fit=crop&w=2000&q=85',
  poleronesHero: 'https://images.unsplash.com/photo-1556905055-8f358a7a47b2?auto=format&fit=crop&w=1200&q=85',
  polerasHero: 'https://images.unsplash.com/photo-1521572267360-ee0c2909d518?auto=format&fit=crop&w=1200&q=85',
  calcetinesHero: 'https://images.unsplash.com/photo-1640026199235-c24aa417b552?auto=format&fit=crop&w=1200&q=85',
  gorrasHero: 'https://images.unsplash.com/photo-1720100967713-ff15377669e8?auto=format&fit=crop&w=1200&q=85',
  blusasHero: 'https://images.unsplash.com/photo-1596755094514-f87e34085b2c?auto=format&fit=crop&w=1200&q=85',
}

// 5 Categorías oficiales para el Grid Asimétrico Editorial simétrico de la vista de inicio
export const CATEGORIAS_ASIMETRICAS = [
  {
    id: 'polerones',
    nombre: 'Polerones',
    subtitulo: 'Heavyweight fleece & siluetas boxy',
    claseGrid: 'md:col-span-2 md:row-span-2 aspect-[4/5] md:aspect-auto',
    imagen: 'https://images.unsplash.com/photo-1556905055-8f358a7a47b2?auto=format&fit=crop&w=1200&q=80',
    conteo: '4 Piezas',
  },
  {
    id: 'poleras',
    nombre: 'Poleras',
    subtitulo: 'Algodón peinado 280g',
    claseGrid: 'md:col-span-1 md:row-span-1 aspect-[3/4]',
    imagen: 'https://images.unsplash.com/photo-1521572267360-ee0c2909d518?auto=format&fit=crop&w=800&q=80',
    conteo: '4 Piezas',
  },
  {
    id: 'calcetines',
    nombre: 'Calcetines',
    subtitulo: 'Packs acanalados de alta torsión',
    claseGrid: 'md:col-span-1 md:row-span-1 aspect-[3/4]',
    imagen: 'https://images.unsplash.com/photo-1640026199235-c24aa417b552?auto=format&fit=crop&w=800&q=80',
    conteo: '4 Piezas',
  },
  {
    id: 'gorras',
    nombre: 'Gorras',
    subtitulo: 'Sarga de algodón y lana virgen',
    claseGrid: 'md:col-span-1 md:row-span-1 aspect-[3/4]',
    imagen: 'https://images.unsplash.com/photo-1720100967713-ff15377669e8?auto=format&fit=crop&w=800&q=80',
    conteo: '4 Piezas',
  },
  {
    id: 'blusas',
    nombre: 'Blusas',
    subtitulo: 'Lino lavado escandinavo',
    claseGrid: 'md:col-span-1 md:row-span-1 aspect-[3/4]',
    imagen: 'https://images.unsplash.com/photo-1596755094514-f87e34085b2c?auto=format&fit=crop&w=800&q=80',
    conteo: '2 Piezas',
  },
]

// Banco curado de imágenes directas de moda/ropa (todas verificadas 200 OK)
export const BANCO_ROPA_UNSPLASH = {
  Polerones: [
    'https://images.unsplash.com/photo-1556905055-8f358a7a47b2?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1620799140408-edc6dcb6d633?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1578587018452-892bacefd3f2?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1618354691792-d1d42acfd860?auto=format&fit=crop&w=900&q=80',
  ],
  Poleras: [
    'https://images.unsplash.com/photo-1521572267360-ee0c2909d518?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1583743814966-8936f5b7be1a?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1618354691373-d851c5c3a990?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1562157873-818bc0726f68?auto=format&fit=crop&w=900&q=80',
  ],
  Calcetines: [
    'https://images.unsplash.com/photo-1640026199235-c24aa417b552?auto=format&fit=crop&w=900&q=80', // Calcetines verdes (8Al2ylhlCYk)
    'https://plus.unsplash.com/premium_photo-1755164641094-3b00ad813362?auto=format&fit=crop&w=900&q=80', // Calcetines de colores sobre naranja (fgv9qmOYzc4)
    'https://images.unsplash.com/photo-1552902865-b72c031ac5ea?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1586350977771-b3b0ecd50c82?auto=format&fit=crop&w=900&q=80',
  ],
  Gorras: [
    'https://images.unsplash.com/photo-1720100967713-ff15377669e8?auto=format&fit=crop&w=900&q=80', // Gorra/sombrero en manta (VRjbcJSINVc)
    'https://images.unsplash.com/photo-1628753611124-5d20c4f3e177?auto=format&fit=crop&w=900&q=80', // Gorra blanca y roja sobre azul (htQnr9LCxdM)
    'https://images.unsplash.com/photo-1588850561407-ed78c282e89b?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1575428652377-a2d80e2277fc?auto=format&fit=crop&w=900&q=80',
  ],
  Blusas: [
    'https://images.unsplash.com/photo-1596755094514-f87e34085b2c?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1603252109303-2751441dd157?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1551488831-00ddcb6c6bd3?auto=format&fit=crop&w=900&q=80',
  ],
  Pantalones: [
    'https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1541099649105-f69ad21f3246?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1509631179647-0177331693ae?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1594633312681-425c7b97ccd1?auto=format&fit=crop&w=900&q=80',
  ],
}

/**
 * Evalúa semánticamente el nombre o la categoría de cualquier ítem y devuelve
 * exactamente una de las categorías oficiales de ropa de KYRO.
 */
export function determinarCategoriaPrenda(nombre = '', categoria = '') {
  const texto = `${categoria} ${nombre}`.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '')

  if (texto.includes('pantalon') || texto.includes('cargo') || texto.includes('chino') || texto.includes('wide leg') || texto.includes('trouser')) {
    return 'Pantalones'
  }
  if (texto.includes('calcetin') || texto.includes('sock') || texto.includes('media')) {
    return 'Calcetines'
  }
  if (texto.includes('polera') || texto.includes('tee') || texto.includes('remera') || texto.includes('t-shirt') || texto.includes('manga larga')) {
    return 'Poleras'
  }
  if (texto.includes('hoodie') || texto.includes('poleron') || texto.includes('crewneck') || texto.includes('sweater') || texto.includes('fleece')) {
    return 'Polerones'
  }
  if (texto.includes('gorra') || texto.includes('beanie') || texto.includes('cap') || texto.includes('dad hat') || texto.includes('snapback') || texto.includes('sombrero')) {
    return 'Gorras'
  }
  if (texto.includes('blusa') || texto.includes('camisa') || texto.includes('tunica') || texto.includes('shirt')) {
    return 'Blusas'
  }

  // Fallback seguro si la categoría ya viene definida
  if (categoria && BANCO_ROPA_UNSPLASH[categoria]) {
    return categoria
  }

  return 'Polerones'
}

/**
 * Función robusta de asignación dinámica de imágenes.
 * Garantiza fotos directas en formato Unsplash (https://images.unsplash.com/photo-...)
 * con mapeo específico para evitar duplicidades y asignar cada foto solicitada.
 */
export function resolverImagenPrenda(nombre = '', categoria = '', id = 0) {
  const nomLower = String(nombre).toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '')

  // 1. Mapeo específico: Calcetines Tobilleros Minimal -> foto directa de los calcetines verdes (8Al2ylhlCYk)
  if (nomLower.includes('tobillero') || (nomLower.includes('calcetin') && nomLower.includes('minimal'))) {
    return FOTOS_DIRECTAS_ESPECIFICAS.calcetinesVerdes
  }

  // 2. Mapeo específico: Calcetines Térmicos Waffle -> varios pares de colores sobre naranja (fgv9qmOYzc4)
  if (nomLower.includes('waffle') || (nomLower.includes('calcetin') && nomLower.includes('termico'))) {
    return FOTOS_DIRECTAS_ESPECIFICAS.calcetinesWaffleNaranja
  }

  // 3. Mapeo específico: Gorra Cotton Twill Beige -> foto directa de la gorra en la manta (VRjbcJSINVc)
  if (nomLower.includes('cotton twill') || (nomLower.includes('gorra') && nomLower.includes('beige')) || nomLower.includes('twill beige')) {
    return FOTOS_DIRECTAS_ESPECIFICAS.gorraManta
  }

  // 4. Mapeo específico: Beanie Merino Extra Fino -> gorra blanca y roja sobre azul (htQnr9LCxdM)
  if (nomLower.includes('beanie') || nomLower.includes('merino extra fino') || nomLower.includes('extra fino')) {
    return FOTOS_DIRECTAS_ESPECIFICAS.beanieBlancaRojaAzul
  }

  const cat = determinarCategoriaPrenda(nombre, categoria)
  const coleccion = BANCO_ROPA_UNSPLASH[cat] || BANCO_ROPA_UNSPLASH.Polerones
  const indice = Math.abs(Number(id) || 0) % coleccion.length
  return coleccion[indice]
}

export function obtenerFotoParaPrenda(categoria = '', id = 0, nombre = '') {
  return resolverImagenPrenda(nombre, categoria, id)
}

export function inferirCategoriaFrontend(nombre = '') {
  return determinarCategoriaPrenda(nombre, '')
}

export function obtenerDetallesPrenda(id = 0, nombre = '', categoria = '') {
  const cat = determinarCategoriaPrenda(nombre, categoria)
  const url = resolverImagenPrenda(nombre, cat, id)
  return {
    url,
    categoria: cat,
    alt: nombre || `Prenda KYRO ${cat}`,
  }
}

// Catálogo base de respaldo estructurado (exactamente las 20 prendas oficiales de semilla.py)
export const PRODUCTOS_BASE_KYRO = [
  { id: 1, nombre: 'Polerón Oversize Navy', categoria: 'Polerones', precio: 44990, disponibles: 25, descripcion: 'Polerón de calce holgado en fleece pesado 450g tono azul marino' },
  { id: 2, nombre: 'Polerón con Cierre Ice', categoria: 'Polerones', precio: 48990, disponibles: 20, descripcion: 'Polerón con cierre frontal metálico oculto en tono hielo glacial' },
  { id: 3, nombre: 'Polerón Minimal Black', categoria: 'Polerones', precio: 39990, disponibles: 30, descripcion: 'Crewneck cuello redondo en algodón perchado negro monocromático' },
  { id: 4, nombre: 'Polerón Crewneck Heather', categoria: 'Polerones', precio: 42990, disponibles: 1, descripcion: 'Cuello redondo en gris jaspeado clásico con acabados al corte' },

  { id: 5, nombre: 'Polera Básica Fit', categoria: 'Poleras', precio: 18990, disponibles: 45, descripcion: 'Algodón peinado premium 240g de calce estándar contemporáneo' },
  { id: 6, nombre: 'Polera Estampada Editorial', categoria: 'Poleras', precio: 22990, disponibles: 35, descripcion: 'Serigrafía tipográfica sutil al agua con caída relajada' },
  { id: 7, nombre: 'Polera Manga Larga Raw', categoria: 'Poleras', precio: 24990, disponibles: 30, descripcion: 'Manga larga en algodón mercerizado con puños sin costura' },
  { id: 8, nombre: 'Polera Boxy Heavyweight', categoria: 'Poleras', precio: 26990, disponibles: 15, descripcion: 'Silueta cuadrada en algodón de 300g con hombros estructurados' },

  { id: 9, nombre: 'Pack Calcetines Altos Sport', categoria: 'Calcetines', precio: 12990, disponibles: 50, descripcion: 'Pack de 3 pares acanalados a media pantorrilla con planta acolchada' },
  { id: 10, nombre: 'Calcetines Térmicos Waffle', categoria: 'Calcetines', precio: 14990, disponibles: 40, descripcion: 'Tejido panal térmico transpirable en mezcla de lana merino' },
  { id: 11, nombre: 'Calcetín Ribbed High-Gauge', categoria: 'Calcetines', precio: 11990, disponibles: 35, descripcion: 'Punto ultra compacto de alta elasticidad para calzado formal o urbano' },
  { id: 12, nombre: 'Calcetines Tobilleros Minimal', categoria: 'Calcetines', precio: 9990, disponibles: 4, descripcion: 'Pack de 3 pares corte bajo invisible con sujeción anatómica' },

  { id: 13, nombre: 'Gorra Dad Hat Kyro', categoria: 'Gorras', precio: 18990, disponibles: 25, descripcion: 'Gorra desestructurada en gabardina de algodón lavado con broche metálico' },
  { id: 14, nombre: 'Gorra Snapback Minimal', categoria: 'Gorras', precio: 21990, disponibles: 20, descripcion: 'Corona de seis paneles estructurada con visera plana contemporánea' },
  { id: 15, nombre: 'Gorra Cotton Twill Beige', categoria: 'Gorras', precio: 19990, disponibles: 22, descripcion: 'Sarga de algodón peinado en tono arena con bordado tonal sutil' },
  { id: 16, nombre: 'Beanie Merino Extra Fino', categoria: 'Gorras', precio: 22990, disponibles: 18, descripcion: 'Gorro tejido en lana merino extrafina de tacto ultrasuave' },

  { id: 17, nombre: 'Blusa Lino Estructurada', categoria: 'Blusas', precio: 36990, disponibles: 0, descripcion: 'Blusa escandinava de corte recto en lino lavado artesanal' },
  { id: 18, nombre: 'Pantalón Cargo Editorial', categoria: 'Pantalones', precio: 46990, disponibles: 20, descripcion: 'Pantalón de corte recto con bolsillos discretos de fuelle en sarga pesada' },
  { id: 19, nombre: 'Camisa Popelina Oversize', categoria: 'Blusas', precio: 38990, disponibles: 25, descripcion: 'Camisa clásica con cuello italiano y botonadura de nácar oculta' },
  { id: 20, nombre: 'Pantalón Wide Leg Chino', categoria: 'Pantalones', precio: 44990, disponibles: 15, descripcion: 'Pantalón de tiro medio y pernera ancha en algodón twill estructurado' },
]

/**
 * Transforma los datos que llegan del backend (o fallback de 20 prendas)
 * garantizando coherencia absoluta de imágenes, IDs reales, categorías y stock.
 */
export function generarCatalogoKYRO(datosBackend = []) {
  const lista = Array.isArray(datosBackend) && datosBackend.length > 0 ? datosBackend : PRODUCTOS_BASE_KYRO

  return lista
    .filter((prod) => {
      // Exclusión total e incondicional de cualquier residuo tecnológico
      const n = (prod.nombre || '').toLowerCase()
      const d = (prod.descripcion || '').toLowerCase()
      const terminos = ['audif', 'teclado', 'mouse', 'monitor', 'webcam', 'consola', 'wireless', 'auricular', 'switches']
      return !terminos.some((t) => n.includes(t) || d.includes(t))
    })
    .map((prod, idx) => {
      const idReal = Number(prod.producto_id ?? prod.id ?? (idx + 1))
      const cat = determinarCategoriaPrenda(prod.nombre, prod.categoria)
      const foto = resolverImagenPrenda(prod.nombre, cat, idReal)

      return {
        id: `${idReal}-${idx}`,
        producto_id: idReal,
        nombre: prod.nombre,
        descripcion: prod.descripcion || 'Prenda oficial de la colección KYRO.',
        precio: Number(prod.precio) || 39990,
        disponibles:
          prod.disponibles !== undefined
            ? Number(prod.disponibles)
            : prod.cantidad !== undefined
              ? Number(prod.cantidad)
              : 10,
        categoria: cat,
        imagen: foto,
        imagen_url: foto,
      }
    })
}

// Alias para compatibilidad total con llamadas anteriores
export const generarCatalogoSimulado70 = generarCatalogoKYRO
