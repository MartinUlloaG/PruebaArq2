@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
title Simulacion Cyberday 100 mil compradores
rem Antes: levantar la tienda con "Levantar tienda (carga).bat" (nucleo con 4 copias).
rem Abre esta ventana maximizada: el panel ocupa toda la pantalla.
cd /d "%~dp0servicioCompras"
call .venv\Scripts\activate
python -m demostraciones.simulacion_100k %*
echo.
pause
