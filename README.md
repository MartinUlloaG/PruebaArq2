# Tienda Arquitectura de Software - Eva 2

Son 4 partes:
- servicioCompras: el backend (FastAPI + PostgreSQL)
- servicioPagos: lee los pagos desde Kafka y cobra en la pasarela
- pasarelaSimulada: la pasarela de pago, corre aparte en el puerto 8001
- interfaz: el front (React + Vite + Zustand)

servicioRecomendaciones todavía no está terminado.

## Versiones

- Python 3.13
- Node.js 24
- Docker Desktop abierto (si no está abierto la base de datos no levanta)

## Primera vez

Copiar el .env.ejemplo como .env y cambiar la clave de la base y el secreto del JWT:

```bat
cd C:\comercio
copy .env.ejemplo .env
notepad .env
```

Levantar la base de datos y Kafka:

```bat
docker compose up -d
```

Instalar el backend, crear las tablas y cargar los datos de prueba:

```bat
cd C:\comercio\servicioCompras
python -m venv .venv
.venv\Scripts\activate
pip install -r dependencias.txt
alembic upgrade head
python -m app.infraestructura.semilla
```

La semilla se puede correr varias veces, no duplica nada.

Instalar el front:

```bat
cd C:\comercio\interfaz
npm install
```

## Cómo levantarlo

Cada servicio en una sola consola

con Docker Desktop abierto en C:\comercio: `docker compose up -d` (levanta Postgres y Kafka)

Consola 1 - backend (queda en http://127.0.0.1:8000)

```bat
cd C:\comercio\servicioCompras
.venv\Scripts\activate
uvicorn app.principal:app --reload
```

Consola 2 - pasarela (usa el mismo venv del backend porque ya tiene FastAPI):

```bat
cd C:\comercio\pasarelaSimulada
..\servicioCompras\.venv\Scripts\activate
uvicorn pasarela:app --port 8001
```

Consola 3 - servicio de pagos (también usa el venv del backend):

```bat
cd C:\comercio\servicioPagos
..\servicioCompras\.venv\Scripts\activate
python pagos.py
```

Consola 4 - front (abrir http://localhost:5173):

```bat
cd C:\comercio\interfaz
npm run dev
```


## Probar la pasarela

En http://127.0.0.1:8001/docs con PUT /simulacion se cambia el modo sin reiniciarla:
- aprueba: aprueba todo
- rechaza: rechaza el pago y el stock se devuelve
- lenta: se demora más de los 2 segundos que espera el backend
- falla: responde error 503

Si falla 3 veces seguidas se abre el Circuit Breaker. Si no se puede pagar, al minuto el stock vuelve.
En GET /cobros se ven los cobros hechos.

## Usuarios de prueba

Estas claves son solo para probar en local. En la base se guardan con hash Argon2id.

- Cliente: cliente@demo.cl / Cliente-Demo-2026 (ve el catálogo, compra y ve sus pedidos)
- Operador: operador@demo.cl / Operador-Demo-2026 (ve el inventario)
- Administrador: admin@demo.cl / Admin-Demo-2026 (ve el inventario y los usuarios)


## Pruebas

Con la base de datos arriba:

```bat
cd C:\comercio\servicioCompras
.venv\Scripts\activate
python -m pytest
```

Las más importantes:
- test_pedidos.py: 100 compras al mismo tiempo de un producto con stock 1 y solo 1 se acepta
- test_saga_kafka.py: la compra pasando por Kafka
- test_circuit_breaker.py: los estados cerrado, abierto y semiabierto
- test_autenticacion.py: un cliente no puede entrar a las rutas del operador ni del administrador
- test_esquema.py: la base no deja stock negativo y el stock cuadra con los movimientos

La comparación de sobreventa que sale en el informe:

```bat
python -m demostraciones.comparar_sobreventa
```

## Carpetas

```
servicioCompras/app/api              endpoints, validaciones y roles
servicioCompras/app/dominio          reglas de la compra (la Saga)
servicioCompras/app/infraestructura  modelos, repositorios, seguridad, circuit breaker
servicioCompras/migraciones          alembic
servicioCompras/pruebas              pytest
servicioPagos                        servicio de pagos
interfaz/src/vistas                  las pantallas (View)
interfaz/src/modelosVista            el estado (ViewModel)
interfaz/src/servicios               las llamadas a la API
```

## Seguridad

- El token de sesión dura 30 minutos.
