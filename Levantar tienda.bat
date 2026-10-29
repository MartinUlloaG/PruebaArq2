@echo off
chcp 65001 >nul
title Levantar tienda
echo Levantando la tienda (cada servicio abre su propia ventana)...
echo.

docker info >nul 2>&1
if errorlevel 1 (
  echo Docker Desktop no esta abierto. Abrelo, espera que diga "Engine running" y vuelve a ejecutar esto.
  pause
  exit /b 1
)

cd /d C:\comercio
echo Postgres, Kafka y Mongo...
docker compose up -d

start "Backend - servicio de compras (8000)" cmd /k "cd /d C:\comercio\servicioCompras && .venv\Scripts\activate && uvicorn app.principal:app"
start "Pasarela simulada (8001)" cmd /k "cd /d C:\comercio\pasarelaSimulada && ..\servicioCompras\.venv\Scripts\activate && uvicorn pasarela:app --port 8001"
start "Servicio de pagos (Kafka)" cmd /k "cd /d C:\comercio\servicioPagos && ..\servicioCompras\.venv\Scripts\activate && python pagos.py"
start "Recomendaciones (gRPC 50051)" cmd /k "cd /d C:\comercio\servicioRecomendaciones && ..\servicioCompras\.venv\Scripts\activate && python recomendaciones.py"
start "Front (5173)" cmd /k "cd /d C:\comercio\interfaz && npm run dev"

echo.
echo Esperando que arranquen...
timeout /t 10 /nobreak >nul
start http://localhost:5173
echo Listo. Para apagar un servicio cierra su ventana (o Ctrl+C dentro de ella).
pause
