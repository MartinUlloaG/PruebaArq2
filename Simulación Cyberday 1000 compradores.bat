@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
title Simulacion Cyberday 1000 compradores
cd /d "%~dp0servicioCompras"
call .venv\Scripts\activate
python -m demostraciones.simulacion_cyberday %*
echo.
pause
