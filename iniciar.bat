@echo off
rem SyncUp: dois cliques para instalar (na 1a vez) e abrir no navegador.
chcp 65001 >nul
cd /d "%~dp0"

set "PY="
py -3 -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1 && set "PY=py -3"
if not defined PY python -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1 && set "PY=python"
if not defined PY (
    echo Nao achei o Python 3.10 ou mais novo.
    echo Instale pelo site https://www.python.org/downloads/ marcando "Add python.exe to PATH".
    goto erro
)

if not exist ".venv\Scripts\python.exe" (
    echo Criando o ambiente do SyncUp ^(so na primeira vez^)...
    %PY% -m venv .venv || goto erro
)

echo Conferindo as dependencias ^(na primeira vez leva alguns minutos^)...
".venv\Scripts\python.exe" -m pip install -q --disable-pip-version-check -r requirements.txt || goto erro

".venv\Scripts\python.exe" app.py || goto erro
exit /b 0

:erro
echo.
echo Algo deu errado. Leia a mensagem acima.
pause
exit /b 1
