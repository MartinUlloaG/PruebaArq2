@echo off
chcp 65001 >nul
title Levantar tienda (carga)
rem Igual que "Levantar tienda.bat", pero el nucleo corre con 4 copias (--workers 4) para la
rem simulacion de 100 mil compradores. Se puede porque el JWT no guarda sesion en el servidor.
rem Sin --no-access-log, imprimir 100 mil lineas en la consola de Windows frena al servidor.
rem El load shedding es por proceso: 4 copias x 2 cupos = 8 compras a la vez, igual que con 1 copia.
set COMPRAS_SIMULTANEAS=2
docker info >nul 2>&1
if errorlevel 1 (
  echo Docker Desktop no esta abierto. Abrelo, espera que diga "Engine running" y vuelve a ejecutar esto.
  pause
  exit /b 1
)

cd /d "%~dp0"
echo Postgres, Kafka y Mongo...
docker compose up -d

start "Backend - servicio de compras x4 (8000)" cmd /k "cd servicioCompras && .venv\Scripts\activate && uvicorn app.principal:app --workers 4 --no-access-log"
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
