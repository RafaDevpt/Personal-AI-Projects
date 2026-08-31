@echo off
REM ===========================================================================
REM PT-PT: Arranque da aplicacao em Windows.
REM        Pede elevacao, cria o ambiente virtual e instala as dependencias na
REM        primeira execucao; nas seguintes arranca directamente.
REM        Sem acentos de proposito: a consola do Windows usa CP-850 e
REM        mostraria caracteres trocados.
REM
REM EN-UK: Application launcher for Windows.
REM        Requests elevation, creates the virtual environment and installs
REM        dependencies on first run; subsequent runs start straight away.
REM        Deliberately free of accents: the Windows console uses CP-850 and
REM        would garble them.
REM
REM Created by Redfox using Claude
REM ===========================================================================

setlocal
cd /d "%~dp0.."
title IT Toolkit

REM --- PT-PT: Pedir elevacao. Sem ela o log Security fica inacessivel, o SMART
REM ---        nao devolve nada e os servicos nao arrancam. A aplicacao abre na
REM ---        mesma e diz o que nao vai conseguir fazer, mas vale a pena tentar.
REM --- EN-UK: Request elevation. Without it the Security log is unreadable,
REM ---        SMART returns nothing and services will not start.
net session >nul 2>&1
if errorlevel 1 (
    echo A pedir privilegios de administrador...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs" >nul 2>&1
    exit /b 0
)

REM --- PT-PT: Confirmar que o Python existe / EN-UK: Check Python is present
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERRO] Python nao encontrado no PATH.
    echo        Instale a partir de https://www.python.org/downloads/
    echo        e marque a opcao "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

REM --- PT-PT: Criar ambiente virtual se ainda nao existir
REM --- EN-UK: Create the virtual environment if it does not exist yet
if not exist ".venv\Scripts\python.exe" (
    echo.
    echo Primeira execucao: a preparar o ambiente.
    echo First run: preparing the environment.
    echo.
    python -m venv .venv
    if errorlevel 1 (
        echo [ERRO] Falha ao criar o ambiente virtual.
        pause
        exit /b 1
    )
    ".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [ERRO] Falha ao instalar as dependencias.
        echo        Verifique a ligacao a Internet e o proxy, e tente de novo.
        pause
        exit /b 1
    )
    echo.
    echo Ambiente pronto.
    echo.
)

REM --- PT-PT: Arrancar / EN-UK: Launch
set PYTHONPATH=%CD%\src
".venv\Scripts\python.exe" -m ittoolkit %*

REM --- PT-PT: Codigos 1 e 2 significam "encontrou problemas", nao sao erros da
REM ---        aplicacao. So paramos para mostrar falhas reais.
REM --- EN-UK: Exit codes 1 and 2 mean "problems found", not application
REM ---        failures. Only pause on genuine errors.
if errorlevel 3 (
    echo.
    echo A aplicacao terminou com erro. Consulte o registo em:
    echo %%APPDATA%%\ITToolkit\ittoolkit.log
    echo.
    pause
)

endlocal
