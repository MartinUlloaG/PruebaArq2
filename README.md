# Tienda KYRO · Arquitectura de Software, Eva 2

Tienda para un Cyberday: muchos compradores y poco stock. No vende de más, no cobra dos veces y si
un servicio se cae la compra sigue.

| Parte | Qué hace | Dirección |
|---|---|---|
| `interfaz` | El front (React + Vite + Zustand) | http://localhost:5173 |
| `servicioCompras` | El núcleo: login, catálogo, stock, pedidos y la Saga (FastAPI) | http://127.0.0.1:8000/docs |
| `pasarelaSimulada` | La pasarela de pago, como Webpay (página para poner la tarjeta) | http://127.0.0.1:8001/docs |
| `servicioPagos` | Crea y confirma los pagos en la pasarela (por Kafka) | http://127.0.0.1:8002/estado |
| `servicioRecomendaciones` | Los más vendidos, por gRPC. Si se cae, la tienda sigue | puerto 50051 |
| Docker | PostgreSQL, MongoDB, Kafka y Kafka UI | Kafka UI: http://127.0.0.1:8080 |

## Qué hay que tener instalado

- Windows 10 u 11 (los atajos `.bat` son de Windows; más abajo están los comandos a mano)
- Python 3.13
- Node.js 24
- Docker Desktop, abierto
- Git

## Instalar (una sola vez)

```bat
git clone https://github.com/MartinUlloaG/PruebaArq2.git
cd PruebaArq2
copy .env.ejemplo .env
```

Abrir `.env` y cambiar `POSTGRES_PASSWORD` y `JWT_SECRETO` por cualquier texto largo.

```bat
docker compose up -d

cd servicioCompras
python -m venv .venv
.venv\Scripts\activate
pip install -r dependencias.txt
alembic upgrade head
python -m app.infraestructura.semilla

cd ..\interfaz
npm install
```

La semilla crea 1002 usuarios, 34 prendas y pedidos de ejemplo (la primera vez se demora como un
minuto). Para dejar todo como nuevo: `python -m app.infraestructura.semilla --reiniciar`.

## Levantar

Con Docker Desktop abierto, doble clic en **`Levantar tienda.bat`**. Abre una consola por servicio y
el navegador en http://localhost:5173. Para apagar un servicio se cierra su consola.

A mano, cada línea en una consola distinta, desde la carpeta del repo:

```bat
docker compose up -d
cd servicioCompras && .venv\Scripts\activate && uvicorn app.principal:app
cd pasarelaSimulada && ..\servicioCompras\.venv\Scripts\activate && uvicorn pasarela:app --port 8001
cd servicioPagos && ..\servicioCompras\.venv\Scripts\activate && python pagos.py
cd servicioRecomendaciones && ..\servicioCompras\.venv\Scripts\activate && python recomendaciones.py
cd interfaz && npm run dev
```

Los otros servicios usan el venv de `servicioCompras` (ahí está todo instalado).

## Probar

| Rol | Correo | Clave |
|---|---|---|
| Cliente | cliente@demo.cl (y cliente01 a cliente999) | Cliente-Demo-2026 |
| Operador | operador@demo.cl | Operador-Demo-2026 |
| Administrador | admin@demo.cl | Admin-Demo-2026 |

Al apretar "Ir a pagar" la tienda reserva el stock y manda a la página de la pasarela. Ahí se elige
crédito o débito. Las tarjetas de prueba salen abajo en esa misma página (todas con CVV 123):

| Caso | Número | Vence | Banco (débito) |
|---|---|---|---|
| Crédito, se aprueba | 4111 1111 1111 1111 | 12/29 | |
| Crédito, sin cupo | 5555 5555 5555 4444 | 12/29 | |
| Crédito, vencida | 4000 0000 0000 0002 | 03/24 | |
| Débito, se aprueba | 4000 0566 5566 5556 | 12/29 | RUT 11.111.111-1, clave 1234 |
| Débito, sin saldo | 5200 8282 8282 8210 | 12/29 | RUT 22.222.222-2, clave 1234 |

Cosas que se pueden probar:
- 3 claves malas en el login: la cuenta se bloquea 5 minutos y no entrega token ni con la buena.
- 3 CVV malos o 3 claves del banco malas: la tarjeta o el usuario del banco quedan bloqueados.
- Pago rechazado o "Anular compra": no se cobra y el stock vuelve al tiro.
- Pasarela caída: en http://127.0.0.1:8001/docs, `PUT /simulacion` con `{"modo": "falla"}`. El
  servicio de pagos reintenta, el Circuit Breaker se abre y la reserva vence sola.
- Recomendaciones caído: se cierra su consola y el catálogo sigue funcionando.

La reserva dura 7 minutos. Para verla vencer más rápido está `Levantar tienda (video).bat` (45 s).

## Pruebas automáticas

Con Docker arriba y **los servicios apagados** (las pruebas de Kafka usan los mismos grupos):

```bat
cd servicioCompras
.venv\Scripts\activate
python -m pytest
```

Son 65 pruebas: sobreventa, idempotencia, la Saga por Kafka, el Circuit Breaker, roles y bloqueo
del login.

## Simulaciones de carga

Con la tienda levantada:

- `Simulación Cyberday 1000 compradores.bat`: 1000 compradores por 100 unidades, cada uno con un
  perfil (paga bien, sin cupo, se equivoca de CVV o de clave, anula, se le olvida la clave del login).
- `Simulación 50 usuarios triple clic.bat`: lo mismo, apretando cada botón 3 veces.
- `Simulación Cyberday 100 mil compradores.bat`: 100.000 compradores con un panel en vivo en la
  consola (abrir la ventana maximizada). Botar la pasarela a propósito y mostrar el Circuit Breaker.
  Para esta hay que levantar la tienda con **`Levantar tienda (carga).bat`** (el núcleo con 4 copias).

Las tres revisan al final que no haya sobreventa, que los cobros calcen con los pedidos pagados,
que nadie pague dos veces y que el stock sea el mismo en Postgres, Mongo y la auditoría.

## Carpetas

```
servicioCompras/app/api              endpoints, validaciones, roles y load shedding
servicioCompras/app/dominio          reglas de la compra (la Saga)
servicioCompras/app/infraestructura  modelos, repositorios, Kafka, Circuit Breaker, seguridad
servicioCompras/migraciones          migraciones de Alembic
servicioCompras/pruebas              pytest
servicioCompras/demostraciones       simulaciones de carga y comparación de sobreventa
interfaz/src                         vistas (View), modelosVista (ViewModel) y servicios (API)
protos                               contrato gRPC de recomendaciones
```
