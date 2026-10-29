import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  ArrowRight,
  Check,
  CheckCircle2,
  Clock,
  CreditCard,
  History,
  Loader2,
  Lock,
  MapPin,
  Package,
  ShieldCheck,
  ShoppingBag,
  Truck,
  User,
} from 'lucide-react'
import {
  seleccionarCantidadTotal,
  seleccionarTotal,
  useCarrito,
} from '../modelosVista/useCarrito'
import { useSesion } from '../modelosVista/useSesion'
import { formatearPrecio } from '../modelosVista/stock'
import { obtenerDetallesPrenda } from '../servicios/imagenesPrendas'
import { listarMisPedidos } from '../servicios/pedidos'
import { useRecurso } from '../modelosVista/useRecurso'
import EstadoCarga from './EstadoCarga'

const formatoFecha = new Intl.DateTimeFormat('es-CL', {
  dateStyle: 'short',
  timeStyle: 'short',
})

export default function VistaPedidos() {
  const navegar = useNavigate()
  const usuario = useSesion((s) => s.usuario)
  const token = useSesion((s) => s.token)

  // ViewModel useCarrito
  const productos = useCarrito((s) => s.productos)
  const total = useCarrito(seleccionarTotal)
  const cantidadTotal = useCarrito(seleccionarCantidadTotal)
  const limpiarCarrito = useCarrito((s) => s.limpiarCarrito)

  // Consulta opcional de pedidos históricos en el backend
  const { datos: pedidosHistoricos, cargando: cargandoHistorico, reintentar } =
    useRecurso(listarMisPedidos)

  // Estados de flujo de Checkout
  const [tabIdentificacion, setTabIdentificacion] = useState(usuario ? 'registrado' : 'invitado')
  const [pasoActivo, setPasoActivo] = useState(2) // 1: Identificación, 2: Envío, 3: Pago
  const [estadoCheckout, setEstadoCheckout] = useState('formulario') // 'formulario' | 'procesando' | 'confirmado' | 'historial'
  const [numeroOrdenConfirmada, setNumeroOrdenConfirmada] = useState('')

  // Formulario de Envío
  const [datosEnvio, setDatosEnvio] = useState({
    nombre: usuario ? usuario.correo.split('@')[0].toUpperCase() : 'MARTIN ULLOA',
    correo: usuario ? usuario.correo : 'cliente@demo.cl',
    direccion: 'AV. PROVIDENCIA 1240, DPTO 804',
    ciudad: 'SANTIAGO',
    region: 'METROPOLITANA',
    telefono: '+56 9 8765 4321',
  })

  function actualizarCampo(e) {
    const { name, value } = e.target
    setDatosEnvio((prev) => ({ ...prev, [name]: value }))
  }

  // Simulación de Compra (Mock de Pasarela de Pagos KYRO)
  async function finalizarCompra(e) {
    e.preventDefault()
    if (productos.length === 0) return

    // 1. Cambia a estado de procesando con spinner minimalista de lucide-react
    setEstadoCheckout('procesando')

    // 2. Si existe sesión y backend, enviamos en segundo plano con idempotencia para sincronizar con PostgreSQL
    try {
      if (token && productos.length > 0) {
        for (const prod of productos) {
          const id = prod.producto_id ?? prod.id
          await fetch('/api/pedidos', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Accept: 'application/json',
              Authorization: `Bearer ${token}`,
              'Idempotency-Key': crypto.randomUUID(),
            },
            body: JSON.stringify({
              producto_id: id,
              cantidad: prod.cantidad,
            }),
          }).catch(() => null)
        }
      }
    } catch {
      // Si la pasarela falla en demo, el mock visual continúa según requerimiento
    }

    // 3. Temporizador de 2 segundos de simulación de pasarela de alta gama
    setTimeout(() => {
      const codigoRandom = `#KYRO-${Math.floor(100000 + Math.random() * 900000)}`
      setNumeroOrdenConfirmada(codigoRandom)
      setEstadoCheckout('confirmado')
    }, 2000)
  }

  function volverALaTienda() {
    limpiarCarrito()
    navegar('/catalogo')
  }

  // PANTALLA 1: Procesando Pago (Spinner Minimalista)
  if (estadoCheckout === 'procesando') {
    return (
      <div className="min-h-[75vh] flex flex-col items-center justify-center text-center px-4 py-20 bg-white">
        <Loader2 className="w-10 h-10 text-[#ee6c4d] animate-spin mb-6 stroke-[1.5]" />
        <span className="text-[10px] uppercase tracking-[0.35em] text-[#3d5a80] font-bold block mb-2">
          PASARELA DE PAGO KYRO SECURE
        </span>
        <h2 className="text-2xl md:text-3xl font-black uppercase tracking-widest text-[#1e1e1e] mb-3">
          PROCESANDO PAGO...
        </h2>
        <p className="text-xs uppercase tracking-[0.2em] text-[#3d5a80]/80 font-light max-w-sm leading-relaxed">
          Verificando autorización bancaria, reserva de inventario y cifrado de extremo a extremo.
        </p>
      </div>
    )
  }

  // PANTALLA 2: Pedido Confirmado (Pantalla Limpia Editorial)
  if (estadoCheckout === 'confirmado') {
    return (
      <div className="max-w-3xl mx-auto px-4 py-20 md:py-28 text-center bg-white">
        <div className="w-16 h-16 mx-auto mb-6 flex items-center justify-center border border-black/10 bg-[#e0fbfc]/40">
          <CheckCircle2 className="w-8 h-8 text-[#293241] stroke-[1.5]" />
        </div>

        <span className="text-[11px] uppercase tracking-[0.35em] text-[#ee6c4d] font-bold block mb-2">
          TRANSACCIÓN COMPLETADA CON ÉXITO
        </span>

        <h1 className="text-4xl md:text-5xl font-black uppercase tracking-tight text-[#1e1e1e] mb-4">
          ¡PEDIDO CONFIRMADO!
        </h1>

        <div className="inline-block bg-[#f4fbfb] border border-[#293241]/15 px-6 py-3 my-4">
          <span className="text-xs uppercase tracking-[0.25em] text-[#3d5a80] font-semibold block mb-0.5">
            NÚMERO DE ORDEN
          </span>
          <strong className="text-xl md:text-2xl font-black tracking-widest text-[#293241] font-mono">
            {numeroOrdenConfirmada}
          </strong>
        </div>

        <p className="text-xs uppercase tracking-[0.18em] text-[#3d5a80] font-light max-w-lg mx-auto leading-relaxed my-6">
          Hemos enviado la confirmación y el comprobante fiscal a tu correo{' '}
          <strong className="font-semibold text-[#1e1e1e]">{datosEnvio.correo}</strong>.
          Tu paquete será despachado a la dirección indicada.
        </p>

        {/* Resumen del despacho */}
        <div className="max-w-md mx-auto p-6 border-y border-[#293241]/10 text-left my-8 space-y-2 text-xs uppercase tracking-wider">
          <div className="flex justify-between text-[#3d5a80]">
            <span>Destinatario:</span>
            <strong className="text-[#1e1e1e]">{datosEnvio.nombre}</strong>
          </div>
          <div className="flex justify-between text-[#3d5a80]">
            <span>Entrega en:</span>
            <strong className="text-[#1e1e1e] text-right">{datosEnvio.direccion}, {datosEnvio.ciudad}</strong>
          </div>
          <div className="flex justify-between text-[#3d5a80]">
            <span>Total Cobrado:</span>
            <strong className="text-[#ee6c4d] font-mono text-sm">{formatearPrecio(total)}</strong>
          </div>
        </div>

        <button
          type="button"
          onClick={volverALaTienda}
          className="inline-flex items-center gap-2 px-8 py-4 bg-[#ee6c4d] hover:bg-[#d95b3d] text-white text-xs uppercase tracking-[0.25em] font-black transition-colors"
        >
          <span>Volver a la Tienda</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    )
  }

  // PANTALLA 3: Historial de pedidos anteriores (si el usuario pulsa en ver órdenes pasadas)
  if (estadoCheckout === 'historial') {
    return (
      <div className="max-w-5xl mx-auto px-4 py-12">
        <div className="flex justify-between items-end border-b border-[#293241]/10 pb-6 mb-8">
          <div>
            <span className="text-[10px] uppercase tracking-[0.3em] text-[#3d5a80] font-bold block mb-1">
              REGISTRO DE CLIENTE
            </span>
            <h1 className="text-3xl font-black uppercase tracking-tight text-[#1e1e1e]">
              Historial de Órdenes
            </h1>
          </div>
          <button
            type="button"
            onClick={() => setEstadoCheckout('formulario')}
            className="text-xs uppercase tracking-widest font-bold text-[#ee6c4d] hover:underline flex items-center gap-1.5"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Volver al Checkout</span>
          </button>
        </div>

        <EstadoCarga cargando={cargandoHistorico} reintentar={reintentar}>
          {!pedidosHistoricos || pedidosHistoricos.length === 0 ? (
            <div className="p-16 border border-dashed border-[#293241]/20 text-center">
              <Package className="w-8 h-8 text-[#3d5a80] mx-auto mb-3 opacity-40" />
              <p className="text-xs uppercase tracking-widest font-bold text-[#1e1e1e]">
                No hay pedidos registrados previamente
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {pedidosHistoricos.map((p) => (
                <article key={p.pedido_id} className="p-6 border border-[#293241]/10 bg-white flex flex-col md:flex-row justify-between md:items-center gap-4">
                  <div>
                    <span className="text-[10px] font-mono tracking-widest text-[#3d5a80] block mb-1">
                      ORDEN #{p.pedido_id} — {formatoFecha.format(new Date(p.creado_en))}
                    </span>
                    <h3 className="text-xs uppercase tracking-wider font-bold text-[#1e1e1e]">
                      {p.items?.map((i) => `${i.cantidad}x ${i.nombre}`).join(' • ') || 'Prendas KYRO'}
                    </h3>
                  </div>
                  <div className="flex items-center gap-6">
                    <span className="text-sm font-bold font-mono text-[#293241]">
                      {formatearPrecio(p.total)}
                    </span>
                    <span className="px-3 py-1 text-[10px] uppercase tracking-widest font-bold border border-[#293241]/20 bg-[#e0fbfc]/30 text-[#293241]">
                      {p.estado === 'pagado' ? 'PAGADO' : p.estado}
                    </span>
                  </div>
                </article>
              ))}
            </div>
          )}
        </EstadoCarga>
      </div>
    )
  }

  // PANTALLA PRINCIPAL: CHECKOUT EN 2 COLUMNAS (70% FLUJO / 30% STICKY RESUMEN)
  return (
    <div className="w-full bg-white text-[#1e1e1e]">
      {/* Encabezado del Checkout */}
      <header className="border-b border-[#293241]/10 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 py-8 flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4">
          <div>
            <span className="text-[10px] uppercase tracking-[0.35em] text-[#3d5a80] font-bold block mb-1">
              KYRO / FINALIZACIÓN DE COMPRA
            </span>
            <h1 className="text-3xl md:text-4xl font-black uppercase tracking-tight text-[#1e1e1e]">
              Caja &amp; Checkout
            </h1>
          </div>

          <div className="flex items-center gap-4 text-xs uppercase tracking-wider">
            <button
              type="button"
              onClick={() => setEstadoCheckout('historial')}
              className="text-[#3d5a80] hover:text-[#1e1e1e] flex items-center gap-1.5 transition-colors font-medium"
            >
              <History className="w-3.5 h-3.5" />
              <span>Ver Órdenes Anteriores</span>
            </button>
            <span className="text-gray-300">|</span>
            <span className="flex items-center gap-1.5 text-emerald-700 font-semibold">
              <Lock className="w-3.5 h-3.5" />
              <span>Cifrado SSL 256-bit</span>
            </span>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 py-12">
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_380px] xl:grid-cols-[1fr_420px] gap-12 lg:gap-16 items-start">
          
          {/* COLUMNA IZQUIERDA (70%): Flujo UX de Compra */}
          <section className="space-y-12">
            
            {/* PASO 1: Identificación (Acordeón / Tabs limpios) */}
            <div className="border-b border-[#293241]/10 pb-10">
              <div className="flex items-center gap-3 mb-6">
                <span className="w-6 h-6 border border-[#293241] text-[#293241] text-xs font-bold flex items-center justify-center">
                  01
                </span>
                <h2 className="text-sm uppercase tracking-[0.25em] font-black text-[#293241]">
                  Identificación del Cliente
                </h2>
              </div>

              {usuario ? (
                <div className="p-4 bg-[#f4fbfb] border border-[#293241]/10 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-[#293241] text-white flex items-center justify-center">
                      <User className="w-4 h-4" />
                    </div>
                    <div>
                      <span className="text-[10px] uppercase tracking-wider text-[#3d5a80] block font-semibold">
                        Sesión Verificada
                      </span>
                      <strong className="text-xs uppercase tracking-widest text-[#1e1e1e]">
                        {usuario.correo}
                      </strong>
                    </div>
                  </div>
                  <span className="text-[10px] uppercase tracking-widest text-emerald-700 font-bold flex items-center gap-1">
                    <Check className="w-3.5 h-3.5" /> Activo
                  </span>
                </div>
              ) : (
                <div className="space-y-4">
                  {/* Selector tipo acordeón / pestañas */}
                  <div className="grid grid-cols-2 border border-[#293241]/20">
                    <button
                      type="button"
                      onClick={() => setTabIdentificacion('invitado')}
                      className={`py-3 text-xs uppercase tracking-[0.2em] font-bold transition-colors ${
                        tabIdentificacion === 'invitado'
                          ? 'bg-[#293241] text-white'
                          : 'bg-white text-[#3d5a80] hover:text-[#1e1e1e]'
                      }`}
                    >
                      ¿Comprar como Invitado?
                    </button>
                    <button
                      type="button"
                      onClick={() => setTabIdentificacion('login')}
                      className={`py-3 text-xs uppercase tracking-[0.2em] font-bold transition-colors ${
                        tabIdentificacion === 'login'
                          ? 'bg-[#293241] text-white'
                          : 'bg-white text-[#3d5a80] hover:text-[#1e1e1e]'
                      }`}
                    >
                      Iniciar Sesión
                    </button>
                  </div>

                  {tabIdentificacion === 'invitado' ? (
                    <div className="pt-2">
                      <p className="text-xs text-[#3d5a80] font-light uppercase tracking-wider mb-4">
                        Continuarás sin contraseña. Te enviaremos el comprobante y el seguimiento a tu correo.
                      </p>
                      <div>
                        <label className="text-[10px] uppercase tracking-[0.25em] font-bold text-[#3d5a80] block mb-1">
                          Correo para Notificaciones
                        </label>
                        <input
                          type="email"
                          name="correo"
                          value={datosEnvio.correo}
                          onChange={actualizarCampo}
                          placeholder="tu-correo@ejemplo.cl"
                          className="w-full bg-transparent border-b border-gray-300 py-2.5 text-sm text-[#1e1e1e] focus:border-[#293241] focus:outline-none transition-colors"
                        />
                      </div>
                    </div>
                  ) : (
                    <div className="pt-2 text-center py-4 bg-[#f4fbfb] border border-[#293241]/10">
                      <p className="text-xs uppercase tracking-wider text-[#3d5a80] mb-3">
                        Accede con tu cuenta para acumular historial y agilizar tus compras.
                      </p>
                      <button
                        type="button"
                        onClick={() => navegar('/ingresar', { state: { desde: '/pedidos' } })}
                        className="px-6 py-2.5 bg-[#293241] text-white text-xs uppercase tracking-widest font-bold"
                      >
                        Ir al Inicio de Sesión
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* PASO 2: Datos de Envío (Formulario Minimalista con solo border-b) */}
            <form id="form-checkout" onSubmit={finalizarCompra} className="space-y-8">
              <div className="border-b border-[#293241]/10 pb-10">
                <div className="flex items-center gap-3 mb-6">
                  <span className="w-6 h-6 border border-[#293241] text-[#293241] text-xs font-bold flex items-center justify-center">
                    02
                  </span>
                  <h2 className="text-sm uppercase tracking-[0.25em] font-black text-[#293241]">
                    Dirección de Despacho
                  </h2>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-6">
                  <div className="md:col-span-2">
                    <label className="text-[10px] uppercase tracking-[0.25em] font-bold text-[#3d5a80] block mb-1">
                      Nombre Completo del Receptor
                    </label>
                    <input
                      required
                      type="text"
                      name="nombre"
                      value={datosEnvio.nombre}
                      onChange={actualizarCampo}
                      placeholder="NOMBRE Y APELLIDO"
                      className="w-full bg-transparent border-b border-gray-300 py-2.5 text-sm uppercase text-[#1e1e1e] focus:border-[#293241] focus:outline-none transition-colors"
                    />
                  </div>

                  <div className="md:col-span-2">
                    <label className="text-[10px] uppercase tracking-[0.25em] font-bold text-[#3d5a80] block mb-1">
                      Calle, Número y Depto
                    </label>
                    <input
                      required
                      type="text"
                      name="direccion"
                      value={datosEnvio.direccion}
                      onChange={actualizarCampo}
                      placeholder="DIRECCIÓN EXACTA"
                      className="w-full bg-transparent border-b border-gray-300 py-2.5 text-sm uppercase text-[#1e1e1e] focus:border-[#293241] focus:outline-none transition-colors"
                    />
                  </div>

                  <div>
                    <label className="text-[10px] uppercase tracking-[0.25em] font-bold text-[#3d5a80] block mb-1">
                      Ciudad / Comuna
                    </label>
                    <input
                      required
                      type="text"
                      name="ciudad"
                      value={datosEnvio.ciudad}
                      onChange={actualizarCampo}
                      placeholder="SANTIAGO"
                      className="w-full bg-transparent border-b border-gray-300 py-2.5 text-sm uppercase text-[#1e1e1e] focus:border-[#293241] focus:outline-none transition-colors"
                    />
                  </div>

                  <div>
                    <label className="text-[10px] uppercase tracking-[0.25em] font-bold text-[#3d5a80] block mb-1">
                      Teléfono de Contacto
                    </label>
                    <input
                      required
                      type="tel"
                      name="telefono"
                      value={datosEnvio.telefono}
                      onChange={actualizarCampo}
                      placeholder="+56 9 ..."
                      className="w-full bg-transparent border-b border-gray-300 py-2.5 text-sm text-[#1e1e1e] focus:border-[#293241] focus:outline-none transition-colors"
                    />
                  </div>
                </div>

                {/* Opción de envío seleccionada */}
                <div className="mt-8 p-4 bg-[#f4fbfb] border border-[#293241]/10 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Truck className="w-5 h-5 text-[#293241]" />
                    <div>
                      <strong className="text-xs uppercase tracking-wider block text-[#1e1e1e]">
                        Despacho Prioritario KYRO
                      </strong>
                      <span className="text-[11px] text-[#3d5a80] font-light">
                        Entrega estimada en 24 a 48 horas hábiles
                      </span>
                    </div>
                  </div>
                  <span className="text-xs font-bold text-emerald-800 uppercase tracking-widest font-mono">
                    GRATIS
                  </span>
                </div>
              </div>

              {/* PASO 3: Método de Pago & Botón Final */}
              <div className="pt-2">
                <div className="flex items-center gap-3 mb-6">
                  <span className="w-6 h-6 border border-[#293241] text-[#293241] text-xs font-bold flex items-center justify-center">
                    03
                  </span>
                  <h2 className="text-sm uppercase tracking-[0.25em] font-black text-[#293241]">
                    Método de Pago
                  </h2>
                </div>

                <div className="p-4 border border-[#293241] bg-white flex items-center justify-between mb-8">
                  <div className="flex items-center gap-3">
                    <CreditCard className="w-5 h-5 text-[#ee6c4d]" />
                    <div>
                      <strong className="text-xs uppercase tracking-wider block text-[#1e1e1e]">
                        Pasarela Segura (Webpay Plus / Débito / Crédito)
                      </strong>
                      <span className="text-[11px] text-[#3d5a80] font-light">
                        Transacción protegida con token criptográfico
                      </span>
                    </div>
                  </div>
                  <span className="w-2.5 h-2.5 rounded-full bg-[#ee6c4d]" />
                </div>

                {/* Botón Final "FINALIZAR COMPRA" en #ee6c4d Coral */}
                <button
                  type="submit"
                  disabled={productos.length === 0}
                  className="w-full py-4 px-6 bg-[#ee6c4d] hover:bg-[#d95b3d] text-white text-xs uppercase tracking-[0.25em] font-black flex items-center justify-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                >
                  <span>FINALIZAR COMPRA ({formatearPrecio(total)})</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </form>
          </section>

          {/* COLUMNA DERECHA (30%): Resumen del Pedido (Sticky, useCarrito) */}
          <aside className="sticky top-28 bg-[#f4fbfb] border border-[#293241]/15 p-6 md:p-8 space-y-6">
            <div className="flex justify-between items-baseline border-b border-[#293241]/10 pb-4">
              <h2 className="text-xs uppercase tracking-[0.25em] font-black text-[#293241]">
                Resumen del Pedido
              </h2>
              <span className="text-[10px] font-mono uppercase tracking-widest text-[#3d5a80]">
                {cantidadTotal} {cantidadTotal === 1 ? 'PIEZA' : 'PIEZAS'}
              </span>
            </div>

            {/* Lista de productos en la bolsa */}
            {productos.length === 0 ? (
              <div className="py-8 text-center text-[#3d5a80]">
                <ShoppingBag className="w-8 h-8 mx-auto mb-2 opacity-40 stroke-[1]" />
                <p className="text-xs uppercase tracking-wider font-bold text-[#1e1e1e]">
                  Tu bolsa está vacía
                </p>
                <button
                  type="button"
                  onClick={() => navegar('/catalogo')}
                  className="text-[11px] uppercase tracking-widest text-[#ee6c4d] hover:underline font-bold mt-2 block mx-auto"
                >
                  Ir al Catálogo →
                </button>
              </div>
            ) : (
              <ul className="divide-y divide-[#293241]/10 max-h-[360px] overflow-y-auto pr-2">
                {productos.map((prod) => {
                  const id = prod.producto_id ?? prod.id
                  const detalles = obtenerDetallesPrenda(id, prod.nombre)
                  const img = prod.imagen_url || prod.imagen || detalles.url

                  return (
                    <li key={id} className="py-3.5 first:pt-0 last:pb-0 flex gap-3 items-center">
                      <img
                        src={img}
                        alt={prod.nombre}
                        className="w-14 h-16 object-cover bg-white border border-[#293241]/10 flex-shrink-0"
                      />
                      <div className="flex-1 min-w-0">
                        <h4 className="text-xs uppercase tracking-wider font-bold text-[#1e1e1e] truncate">
                          {prod.nombre}
                        </h4>
                        <span className="text-[11px] text-[#3d5a80] font-mono block">
                          Cant: {prod.cantidad} × {formatearPrecio(prod.precio)}
                        </span>
                      </div>
                      <span className="text-xs font-bold font-mono text-[#293241]">
                        {formatearPrecio(prod.precio * prod.cantidad)}
                      </span>
                    </li>
                  )
                })}
              </ul>
            )}

            {/* Desglose de Precios */}
            <div className="space-y-2 border-t border-[#293241]/10 pt-4 text-xs uppercase tracking-wider">
              <div className="flex justify-between text-[#3d5a80]">
                <span>Subtotal</span>
                <span className="font-mono text-[#1e1e1e] font-semibold">{formatearPrecio(total)}</span>
              </div>
              <div className="flex justify-between text-[#3d5a80]">
                <span>Despacho</span>
                <span className="font-mono text-emerald-700 font-bold">GRATIS</span>
              </div>
              <div className="flex justify-between items-baseline pt-3 border-t border-[#293241]/10">
                <span className="text-xs uppercase tracking-[0.25em] font-black text-[#1e1e1e]">
                  Total a Pagar
                </span>
                <strong className="text-2xl font-black text-[#293241] font-mono tabular-nums">
                  {formatearPrecio(total)}
                </strong>
              </div>
            </div>

            {/* Garantía de Compra */}
            <div className="pt-4 border-t border-[#293241]/10 flex items-center gap-2.5 text-[10px] uppercase tracking-wider text-[#3d5a80]/80">
              <ShieldCheck className="w-4 h-4 text-[#293241] flex-shrink-0" />
              <span>Garantía de cambio por 30 días sin costo en todas las prendas KYRO.</span>
            </div>
          </aside>
        </div>
      </div>
    </div>
  )
}
