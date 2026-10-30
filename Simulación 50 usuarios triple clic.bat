@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
title Simulacion 50 usuarios con triple clic
cd /d "%~dp0servicioCompras"
call .venv\Scripts\activate
python -m demostraciones.simulacion_cyberday --usuarios 50 --stock 20 --repeticiones 3
echo.
pause
