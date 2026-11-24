@echo off
REM Inicia la tienda Franchesco en http://127.0.0.1:8000
cd /d "%~dp0"

if not exist venv\Scripts\python.exe (
    echo Creando entorno virtual...
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" -m venv venv || python -m venv venv
    venv\Scripts\python.exe -m pip install -r requirements.txt
)

venv\Scripts\python.exe manage.py migrate
if not exist db_cargada.flag (
    venv\Scripts\python.exe manage.py cargar_datos && echo ok > db_cargada.flag
)
echo.
echo  Tienda:  http://127.0.0.1:8000/
echo  Panel:   http://127.0.0.1:8000/panel/   (admin@franchesco.com / Admin1234!)
echo.
venv\Scripts\python.exe manage.py runserver
