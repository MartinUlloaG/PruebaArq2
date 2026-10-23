# voltio: módulo de compras (Evaluación Sumativa 2, Arquitectura de Software)

Módulo funcional del **Caso 3: e-commerce masivo de alta concurrencia con tolerancia a fallos**.
Implementa un flujo vertical completo: ingreso con roles → catálogo → compra con reserva de stock
sin sobreventa → pedido guardado en PostgreSQL → consulta de pedidos e inventario.

| Componente | Carpeta | Estado |
|---|---|---|
| Servicio de compras (FastAPI + PostgreSQL) | `servicioCompras/` | Implementado |
| Interfaz (React + Vite + Zustand, MVVM) | `interfaz/` | Implementado |
| Pasarela de pago simulada | `pasarelaSimulada/` | Pendiente (paso 2 de la Saga) |
| Servicio de recomendaciones | `servicioRecomendaciones/` | Pendiente (servicio secundario) |

## Requisitos

- Windows 10/11 (los comandos son para `cmd`; en Linux o macOS solo cambian las rutas del venv)
- Python 3.13
- Node.js 24
- Docker Desktop 29 con Docker Compose 5 (**debe estar abierto** antes de empezar)

## Puesta en marcha (primera vez)

```bat
:: 1. Variables de entorno: copiar la plantilla y cambiar la clave y el secreto JWT
cd C:\comercio
copy .env.ejemplo .env
notepad .env

:: 2. Base de datos (PostgreSQL 16, publicada solo en 127.0.0.1:5440)
docker compose up -d

:: 3. Servicio de compras: dependencias, esquema y datos de demo
cd servicioCompras
python -m venv .venv
.venv\Scripts\activate
pip install -r dependencias.txt
alembic upgrade head
python -m app.infraestructura.semilla

:: 4. Interfaz (en otra consola)
cd C:\comercio\interfaz
npm install
```

La semilla es idempotente: se puede correr varias veces sin duplicar usuarios ni productos.

## Ejecutar

```bat
:: Consola 1: servicio de compras (API en http://127.0.0.1:8000, documentación en /docs)
cd C:\comercio\servicioCompras
.venv\Scripts\activate
uvicorn app.principal:app --reload

:: Consola 2: interfaz (abrir http://localhost:5173)
cd C:\comercio\interfaz
npm run dev
```

La interfaz reenvía `/api` al servicio de compras (ver `interfaz/vite.config.js`), así que no hace falta CORS.

## Usuarios de demostración

> **SOLO PARA DEMO.** Estas claves existen únicamente para probar el módulo en local. En la base
> de datos se guardan con hash **Argon2id** (nunca en texto plano). No reutilizarlas en ningún otro sistema.

| Rol | Correo | Clave | Qué puede hacer |
|---|---|---|---|
| Cliente | `cliente@demo.cl` | `Cliente-Demo-2026` | Ver el catálogo, comprar, ver sus pedidos |
| Operador | `operador@demo.cl` | `Operador-Demo-2026` | Ver el inventario |
| Administrador | `admin@demo.cl` | `Admin-Demo-2026` | Ver el inventario y los usuarios |

En modo desarrollo, la pantalla de ingreso muestra estas cuentas para entrar con un clic.

## Pruebas

```bat
cd C:\comercio\servicioCompras
.venv\Scripts\activate
python -m pytest
```

Requieren la base de datos arriba y migrada. Destacan:

- `pruebas/test_pedidos.py`: **stock 1 y 100 compras simultáneas, exactamente 1 éxito**; 409 sin
  stock, 422 con cantidad inválida, 403 si compra alguien que no es cliente, 401 sin sesión.
- `pruebas/test_autenticacion.py`: un cliente recibe 403 en rutas de operador y administrador;
  mismo mensaje para correo inexistente y clave incorrecta.
- `pruebas/test_esquema.py`: la base de datos rechaza stock, totales y montos negativos; el stock cuadra con los
  movimientos de inventario (entradas − salidas).

Demostración comparativa de sobreventa (la usada en el informe y el video):

```bat
python -m demostraciones.comparar_sobreventa
```

## Estructura

```
servicioCompras/
  app/api/              Endpoints HTTP (validación con Pydantic, roles, códigos de error)
  app/dominio/          Reglas de negocio (compras.py: reserva de stock, paso 1 de la Saga)
  app/infraestructura/  Modelos, Repository (único lugar con consultas), seguridad, semilla
  migraciones/          Alembic
  pruebas/              pytest
interfaz/src/
  vistas/               View (componentes React)
  modelosVista/         ViewModel (estado de sesión con Zustand, hooks de compra y carga)
  servicios/            Acceso a la API (único punto de salida HTTP)
```

## Seguridad en local

- El `.env` no se versiona; `.env.ejemplo` es la plantilla sin secretos.
- PostgreSQL se publica solo en `127.0.0.1`: no queda expuesto a la red local.
- Los tokens JWT (HS256) vencen a los 30 minutos.
