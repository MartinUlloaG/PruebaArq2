@echo off
chcp 65001 >nul
title Levantar tienda (video)
rem Igual que "Levantar tienda.bat", pero con los tiempos cortos para grabar el video:
rem la reserva dura 45 s en vez de 7 min, asi se alcanza a ver vencer en camara.
rem Las ventanas que se abren desde aqui heredan estas variables.
set SEGUNDOS_RESERVA=45
set SEGUNDOS_MARGEN_CONFIRMACION=15
set PASARELA_SEGUNDOS_PAGO=30
set PASARELA_SEGUNDOS_CONFIRMAR=10
echo Tiempos de video: reserva 45 s, 30 s para pagar en la pasarela, 10 s para confirmar.
echo.
docker info >nul 2>&1
if errorlevel 1 (
  echo Docker Desktop no esta abierto. Abrelo, espera que diga "Engine running" y vuelve a ejecutar esto.
  pause
  exit /b 1
)

cd /d "%~dp0"
echo Postgres, Kafka y Mongo...
docker compose up -d

start "Backend - servicio de compras (8000)" cmd /k "cd servicioCompras && .venv\Scripts\activate && uvicorn app.principal:app"
start "Pasarela simulada (8001)" cmd /k "cd pasarelaSimulada && ..\servicioCompras\.venv\Scripts\activate && uvicorn pasarela:app --port 8001"
start "Servicio de pagos (Kafka)" cmd /k "cd servicioPagos && ..\servicioCompras\.venv\Scripts\activate && python pagos.py"
start "Recomendaciones (gRPC 50051)" cmd /k "cd servicioRecomendaciones && ..\servicioCompras\.venv\Scripts\activate && python recomendaciones.py"
start "Front (5173)" cmd /k "cd interfaz && npm run dev"

echo.
echo Esperando que arranquen...
timeout /t 10 /nobreak >nul
start http://localhost:5173
echo Listo. Para apagar un servicio cierra su ventana (o Ctrl+C dentro de ella).
pause
