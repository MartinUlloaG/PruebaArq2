\# CONTEXTO DEL PROYECTO: Evaluación Sumativa 2, Arquitectura de Software



\## 1. Quién y qué

\- Estudiante: Martín Ulloa, 5° año Ing. Civil Informática, Universidad Autónoma de Chile. Profesor: Cristopher Rojas. Fecha de entrega: por confirmar.

\- Es la continuación de la Eva 1 (Caso 3: e-commerce masivo de alta concurrencia con tolerancia a fallos, informe en LaTeX del 9-sep-2026, hecho en pareja con Abril Cifuentes).

\- Martín programa todo. Abril no toca código (aporta documento).

\- Es su primera vez con PostgreSQL. Habla en español chileno informal; prefiere respuestas directas y concisas, y entender el concepto antes de recibir código.



\## 2. Qué pide la Eva 2

Implementar un módulo funcional con login y distintos tipos de usuario. Rúbrica:

\- Análisis y justificación de cambios respecto a la Eva 1: 10 pts

\- Documentación y patrones (frameworks con versiones, mín. 2 patrones evidenciados en el código): 25 pts

\- Módulo funcional (flujo de punta a punta, login con roles): 35 pts

\- Atributos de calidad (mín. 3): 15 pts

\- ADRs (mín. 4): 15 pts

Entrega: documento Word o PDF, código fuente con instrucciones de ejecución, video MP4 de 4 a 12 min, mín. 720p. Puede haber defensa individual.

Fuentes originales (mandan sobre este resumen): enunciado y rúbrica en C:\\Users\\ullov\\OneDrive\\Documentos\\Arquitectura de Sfotware Ev.2\\ ("Evaluación Sumativa 2 - Arquitectura de Software 2026.docx" y "Eva UA - Rubrica - Arqui 2.xlsx"). Eva 1 entregada: C:\\Users\\ullov\\OneDrive\\Desktop\\Software\\Arq\_soft\_AbrilC\_y\_MartinU\_.pdf (informe\_v2.tex es posterior al PDF, no es lo entregado). No hay archivo con observaciones del profesor sobre la Eva 1.

Matices de la rúbrica que el resumen omitía: la 3.2 evalúa validaciones y manejo de errores junto con el login; la 3.1 exige que la interfaz envíe datos y se ALMACENEN (no basta con leer); criterio de aceptación: los diagramas deben representar el flujo IMPLEMENTADO (los de la Eva 1 tienen API Gateway y Kafka).

Revisión de avance (informada el 22-oct-2026): no es la entrega final. Se presenta el informe, los avances del sistema y la arquitectura usada. La idea es mantener la arquitectura de la Eva 1 y defenderla; si se cambió algo, hay que justificarlo. Si la justificación no es válida, el trabajo queda hasta ahí; si es válida, se da una semana más. El informe de avance está en el escritorio: C:\\Users\\ullov\\OneDrive\\Desktop\\Informe\_Eva2\_avance.md.



\## 3. Decisiones de la Eva 1 (ya entregadas)

\- UI: MVVM con React + Zustand (persistencia en IndexedDB/AsyncStorage); accesibilidad (aria-live, redundancia al color, extensión de sesión, skip-links).

\- Aplicación: microservicios por dominio (catálogo, inventario, checkout, pagos, recomendaciones, reseñas, logística); Circuit Breaker hacia servicios secundarios; CQRS + Event Sourcing en inventario; idempotencia + Saga orquestada sobre colas (Kafka/RabbitMQ); rate limiting y load shedding en el gateway (caso Ticketmaster 10x).

\- Datos: híbrido (documental para catálogo, relacional para pedidos y pagos, series de tiempo para métricas); cola local de acciones y CRDT add-wins para el carrito móvil.

\- Infra: nube pública; REST, WebSockets, gRPC, mensajería; OAuth2/JWT, mTLS, TLS 1.3, tokenización.

\- Antipatrones declarados: The Blob (checkout) y Golden Hammer.

\- Defendió microservicios porque el aislamiento de fallos es una restricción de negocio no negociable. Por eso el módulo debe mostrar aislamiento real (servicios separados), no un monolito.



\## 4. Alcance de la demo y cambios a justificar (Análisis 10 pts)

Se implementan 3 servicios: servicioCompras (núcleo), pasarelaSimulada (pasarela externa con latencia y fallas configurables) y servicioRecomendaciones (secundario, se puede apagar). Los demás dominios se declaran fuera de alcance. Cambios respecto a la Eva 1, cada uno a justificar:

1\. Event Sourcing real pasa a una tabla de movimientos de inventario solo-inserción (auditoría de sobreventas sin event store).

2\. La Saga se orquesta dentro de servicioCompras, sin broker. El broker queda como evolución.

3\. Catálogo en PostgreSQL. MongoDB queda como arquitectura objetivo.

4\. REST entre servicios en vez de gRPC y mTLS.

5\. Sobreventa resuelta con UPDATE condicional (cantidad >= n). Es una variante del versionado optimista declarado en la Eva 1.



\## 5. Stack decidido y por qué

\- Backend: FastAPI. Decisión tomada bajo restricción de plazo y de familiaridad del equipo, DECLARADA como restricción. NO hubo spike empírico, así que NO escribir "empíricamente" en el ADR. Existe una matriz ponderada (pesos congelados: rendimiento de I/O 25%, control transaccional con Postgres 20%, soporte de resiliencia 15%, seguridad 15%, protocolos declarados 10%, testabilidad 10%, riesgo de plazo 5%). Alternativas a puntuar con documentación oficial: NestJS, Spring Boot, ASP.NET Core, Django. Razón de la matriz: evitar el antipatrón Golden Hammer que el propio informe declara.

\- Frontend: React + Vite + Zustand. Razones: coherencia con la Eva 1, ecosistema, y los re-renders son controlables y medibles (React Profiler y selectores de Zustand). Evidencia pendiente: contar renders del modal de checkout con y sin selectores.

\- BD: PostgreSQL 16. Razones: transacciones ACID para stock y pedidos, restricción UNIQUE para la clave de idempotencia, bloqueo de filas contra sobreventa, y prioriza consistencia (CP). NO justificar "por la cantidad de datos".

\- Contenedores: Docker Compose (la Eva 1 declaró contenedores por microservicio, y apagar un servicio con docker stop sirve para la demo de aislamiento).

\- Versiones instaladas (van a la tabla de stack del documento): Python 3.13, FastAPI 0.143.3, Starlette 1.8.0, SQLAlchemy 2.1.5, Alembic 1.20.0, Pydantic 2.14.1, pydantic-settings 2.16.0, psycopg 3.3.6, PyJWT 2.15.1, pwdlib (argon2) 0.3.1, uvicorn 0.54.0, pytest 9.1.1, httpx 0.28.1, PostgreSQL 16.15, Docker 29.8.2, Compose 5.6.0, create-vite 9.2.1 (linter: ESLint). Frontend (verificado en interfaz\package.json): React 19.2.8, react-dom 19.2.8, zustand 5.0.15, react-router-dom 7.18.4.



\## 6. Estructura (C:\\comercio, Windows, se usa cmd)

\- servicioCompras\\app\\{api, dominio, infraestructura}, app\\principal.py (entrada: uvicorn app.principal:app --reload), app\\configuracion.py, servicioCompras\\pruebas, servicioCompras\\.venv, servicioCompras\\dependencias.txt

\- pasarelaSimulada, servicioRecomendaciones (vacíos por ahora, cada uno tendrá su propio venv)

\- interfaz (Vite + React; src\\vistas = View, src\\modelosVista = ViewModel con stores Zustand, src\\servicios = acceso a la API)

\- documentos, docker-compose.yml, .env (NO LEER NI IMPRIMIR), .gitignore (.env, .venv, node\_modules, \_\_pycache\_\_)

\- Convenciones: nombres de carpetas y archivos en español salvo los que las herramientas exigen. Carpetas contenedoras en camelCase (servicioCompras); paquetes y módulos Python en minúscula; servicios dentro de docker-compose en minúscula (Docker exige minúsculas en imágenes).



\## 7. Infraestructura local

\- docker-compose.yml: servicio base-de-datos, imagen postgres:16, volumen datos\_postgres, restart unless-stopped, puerto publicado como 127.0.0.1:${POSTGRES\_PORT}:5432.

\- .env en la raíz: POSTGRES\_USER=compras, POSTGRES\_DB=compras, POSTGRES\_PORT=5440 y POSTGRES\_PASSWORD (secreto, solo local).

\- Se usa el puerto 5440 porque 5432, 5433 y 5434 están ocupados por herramientas de su trabajo. Se publica solo en 127.0.0.1 para que la BD no quede expuesta a la red local (va a la sección de seguridad del documento).

\- app\\configuracion.py lee el .env con pydantic-settings (las variables de entorno reales tienen prioridad; al meter el servicio en Docker se pasará POSTGRES\_HOST=base-de-datos). app\\infraestructura\\base.py define Base, el motor (pool 10, pool\_pre\_ping, connect\_timeout 5) y Sesion.



\## 8. Modelo de datos (app\\infraestructura\\modelos.py)

Tablas: usuarios (rol: cliente, operador, administrador; clave con hash Argon2), productos, inventario (CHECK cantidad >= 0), pedidos + items\_pedido (precio congelado al comprar), movimientos\_inventario (solo inserción), pagos (UNIQUE por pedido), claves\_idempotencia (PK compuesta usuario\_id + clave, huella SHA-256 del cuerpo, respuesta guardada en JSONB).

Decisiones de diseño (ADR/defensa):

\- Plata como entero en pesos (CLP sin decimales), nunca float.

\- Reglas también en la BD (CHECK y UNIQUE): última defensa si falla la lógica.

\- Estados como texto con CHECK, no ENUM de Postgres (cambiar un ENUM exige ALTER TYPE).

\- Idempotencia por INSERT sobre clave primaria, atómico. No "consultar y luego insertar", que tiene condición de carrera. Misma clave + mismo cuerpo devuelve la respuesta guardada. Misma clave + cuerpo distinto es error 422.

\- Sesiones síncronas (más simples de razonar en transacciones; FastAPI corre los endpoints def en un pool de hilos).

\- Tipos de movimiento: reserva (-n), liberacion (+n), ajuste\_entrada (+n), ajuste\_salida (-n). NO existe "venta": vender es que el pedido pase a "pagado"; su stock ya salió con la reserva. Invariante (probado en test\_esquema.py y test\_pedidos.py): inventario.cantidad == entradas - salidas (RepositorioInventario.saldo\_movimientos).

\- naming\_convention con pk, fk, uq e ix, SIN ck: cada CHECK escribe su nombre completo en modelos.py (ck\_<tabla>\_<columna>), igual al de la BD. CHECK total >= 0 en pedidos y monto >= 0 en pagos (migración ab1f2b63b89a). inventario.producto\_id con autoincrement=False.

\- Sobreventa: UPDATE inventario SET cantidad = cantidad - n WHERE producto\_id = :id AND cantidad >= n RETURNING cantidad. Sin filas devueltas = sin stock = 409. Medido: con "leer y después escribir", 100 compras simultáneas de 1 unidad aceptan entre 10 y 15 compras (stock final 0, el CHECK no lo detecta); con UPDATE condicional, exactamente 1.



\## 9. Estado actual

Hecho y verificado: venv e instalación de dependencias, endpoint /salud responde 200, front de Vite corriendo con la plantilla, contenedor de Postgres corriendo y conexión desde Python probada (select 1 devuelve 1), repo git local (sin GitHub). Commits: "Estructura inicial del proyecto" (e3bc28c), "Configuración de conexión a la base de datos" (c52d8bd). Pieza 1 TERMINADA (19-oct-2026): base.py y modelos.py creados (convención de nombres de restricciones; movimientos con ajuste_entrada/ajuste_salida). Alembic en servicioCompras\migraciones (la URL sale de configuracion.py); migración inicial e0d0df2cd543 probada con upgrade/downgrade/upgrade. Semilla idempotente (python -m app.infraestructura.semilla): usuarios demo cliente@demo.cl, operador@demo.cl, admin@demo.cl; 6 productos, uno agotado y uno con stock 1. 5 pruebas en pruebas\test_esquema.py pasando (python -m pytest). Host por defecto 127.0.0.1: con "localhost" Windows probaba IPv6 primero y cada conexión tardaba hasta 2 min. (La prueba del invariante ya se generalizó en la pieza A.)

Pieza 2 TERMINADA (19-oct-2026): login JWT HS256 (30 min, secreto JWT_SECRETO en .env, obligatorio; .env.ejemplo versionado). Rutas: POST /autenticacion/ingresar, GET /autenticacion/yo, GET /inventario (operador y administrador), GET /administracion/usuarios (administrador). Mismo mensaje y mismo tiempo de respuesta (hash ficticio) cuando el correo no existe. Repository en app/infraestructura/repositorios.py. 18 pruebas pasando. Front (tienda ficticia "voltio"): ingreso con cuentas de demo (solo en modo desarrollo), rutas protegidas por rol, pantalla de sin permiso, inventario y usuarios, modo oscuro y móvil. Vite reenvía /api a 127.0.0.1:8000 (sin CORS). Token en sessionStorage (alternativa cookie httpOnly para el ADR). Los hooks se llaman useSesion/useRecurso porque React exige el prefijo "use". Para levantar: en servicioCompras "uvicorn app.principal:app --reload" y en interfaz "npm run dev".

Catálogo para clientes (commit 6cbdc37): GET /catalogo (cualquier rol con sesión), cards de productos.

Pieza A TERMINADA (22-oct-2026, commit 630f9ed): decisiones 1 a 4 aplicadas (ver sección 8). Migración ab1f2b63b89a probada con upgrade/downgrade/upgrade; "alembic check" sin diferencias.

Pieza 3 TERMINADA (22-oct-2026, commit a9f8d8f): compra con reserva de stock. app/dominio/compras.py (paso 1 de la Saga, MAXIMO\_POR\_COMPRA = 10), RepositorioInventario.reservar (UPDATE condicional + movimiento "reserva"), RepositorioPedidos, RepositorioProductos. API: POST /pedidos (solo cliente; 201, 404 producto inexistente o inactivo, 409 sin stock, 422 cantidad fuera de 1..10, 403 otro rol, 401 sin sesión) y GET /pedidos (mis pedidos). Front: botón Comprar en el catálogo (región aria-live con el resultado, recarga silenciosa del stock) y vista "Mis pedidos". Prueba de cierre: stock 1 y 100 compras simultáneas, exactamente 1 éxito (3 de 3 corridas). Demostración: python -m demostraciones.comparar\_sobreventa. Flujo verificado por HTTP a través del proxy de Vite; falta revisarlo visualmente en el navegador (Playwright no tenía Chrome instalado).

Pieza C TERMINADA (22-oct-2026): README.md en la raíz (instalación, ejecución, pruebas, usuarios demo marcados SOLO DEMO con Argon2id). CONTEXTO.md sale del .gitignore y se versiona.

Total: 36 pruebas pasando (python -m pytest). Pedidos de la demo quedan en estado "stock\_reservado" hasta que exista el pago (pieza 4).

Pendiente para la semana extra, en orden: pieza 4 (pasarelaSimulada + pago + idempotencia + compensación con "liberacion"), pieza 5 (Circuit Breaker), diagramas actualizados al flujo implementado, video. Docker por servicio (pieza 6) y recomendaciones solo si sobra tiempo.



\## 10. Plan de trabajo (una pieza por vez, cada una cierra con una prueba que debe pasar)

1\. Alembic: configurar, migración inicial desde los modelos, datos de prueba (productos, stock, usuarios por rol).

2\. Login con roles y JWT. Prueba: un cliente recibe 403 en rutas de operador o administrador. Roles propuestos: cliente (catálogo, compra, sus pedidos), operador (ajustes de inventario), administrador (usuarios y productos).

3\. Catálogo y stock con control de concurrencia. Prueba: stock 1 y 100 solicitudes simultáneas, exactamente 1 éxito.

4\. Checkout con idempotencia contra pasarelaSimulada (Saga: reservar stock, autorizar pago, confirmar; compensar si falla). Prueba: la misma clave dos veces genera un solo cobro.

5\. Circuit Breaker (clase propia, visible en el código) hacia pasarela y recomendaciones. Prueba: servicio caído y el checkout sigue respondiendo de forma controlada.

6\. Servicios en docker-compose (cada uno con Dockerfile, imagen base Python 3.13).

7\. Front: login, catálogo, checkout, panel operador/administrador.

8\. README con instrucciones de ejecución, documento, ADRs y video. Incluye actualizar los diagramas (componentes, despliegue y secuencia) al flujo IMPLEMENTADO: la rúbrica lo exige como criterio de aceptación.

Estado del plan (22-oct-2026): 1, 2 y 3 hechas; README hecho; 7 a medias (falta checkout con pago); 4, 5, 6, diagramas y video pendientes.



Patrones que deben verse en el código (mín. 2): Circuit Breaker, Repository (capa infraestructura), Adapter/Strategy para pasarelas de pago, receptor idempotente.

Atributos de calidad a demostrar (cada uno con prueba medible): disponibilidad (breaker, servicios secundarios caídos), integridad y consistencia (sin sobreventa, sin cobro doble), seguridad (JWT, roles, Argon2, BD solo en 127.0.0.1).

ADRs candidatos (mín. 4, con campo Alternativas): microservicios con alcance reducido; stack (FastAPI con su matriz); PostgreSQL; idempotencia por clave única; Circuit Breaker propio; sobreventa con UPDATE condicional.



\## 11. Correcciones pendientes al documento de la Eva 1

\- La portada dice "Universidad Autónoma de Talca", pero el logo es Universidad Autónoma de Chile.

\- La Figura 2 muestra nombre, dirección y teléfono. Usar datos inventados.

\- Comillas rotas en LaTeX (en 2.2 y en 2.6) y paréntesis sin cerrar en 2.1.

\- El checkout mostrado tiene ciudad Linares con región Metropolitana.

\- Falta nombrar los motores de BD, la tabla de stack con versiones y el campo "Alternativas" en cada decisión. Falta la sección de atributos de calidad.



\## 12. Cosas que se aprendieron (para no repetir)

\- Docker Desktop debe estar abierto con el motor corriendo, si no aparece el error de npipe docker\_engine y las conexiones dan timeout. Falta activar "Start Docker Desktop when you sign in".

\- Notepad puede guardar con extensión .txt: elegir "Todos los archivos".

\- El venv guarda rutas absolutas: no renombrar ni mover carpetas.

\- Python instalado es 3.13 (no 3.12).



\## 13. Reglas de trabajo para el asistente

\- Explicar el concepto y la decisión ANTES de escribir código. Una funcionalidad por vez.

\- Código legible, comentarios en español, nombres en español. Sin sobreingeniería: es un módulo defendible, no un producto.

\- Martín debe poder explicar cada línea en una defensa individual. Si el enunciado exige declarar el uso de IA, se declarará.

\- Cada pieza termina con pruebas ejecutadas. Commits chicos en español, uno por funcionalidad. Si las pruebas de la pieza pasan, commitear sin pedir permiso y mostrar el resumen del diff después.

\- Priorizar por rúbrica (módulo 35, documentación y patrones 25, calidad 15, ADRs 15, análisis 10). No construir nada que no sume puntos ahí.

\- CONTEXTO.md SÍ se commitea (no tiene secretos). Al terminar cada pieza se actualiza la sección 9 y se commitea, para que un chat perdido no cueste trabajo.

\- Nunca leer, imprimir ni commitear el .env ni secretos. Comandos para Windows (cmd).

\- Antes de cambiar una decisión de este documento, preguntar. Si se cambia, actualizar este archivo.

