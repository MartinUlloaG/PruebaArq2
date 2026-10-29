@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
title Simulacion de 100 usuarios
cd /d C:\comercio\servicioCompras
call .venv\Scripts\activate
python -m demostraciones.simulacion_100_usuarios %*
echo.
pause
