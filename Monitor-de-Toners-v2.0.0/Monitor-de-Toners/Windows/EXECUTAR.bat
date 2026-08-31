@echo off
REM ===========================================================================
REM PT-PT: Arranque da aplicacao em Windows.
REM        Cria o ambiente virtual e instala as dependencias na primeira
REM        execucao; nas seguintes arranca directamente.
REM        Sem acentos de proposito: a consola do Windows usa CP-850 e
REM        mostraria caracteres trocados.
REM
REM EN-UK: Application launcher for Windows.
REM        Creates the virtual environment and installs dependencies on first
REM        run; subsequent runs start straight away.
REM        Deliberately free of accents: the Windows console uses CP-850 and
REM        would garble them.
REM
REM Created by Redfox using Claude
REM ===========================================================================

setlocal
cd /d "%~dp0"
title Monitor de Toners

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
        echo        Verifique a ligacao a Internet e tente novamente.
        pause
        exit /b 1
    )
    echo.
    echo Ambiente pronto.
    echo.
)

REM --- PT-PT: Arrancar / EN-UK: Launch
set PYTHONPATH=%~dp0src
".venv\Scripts\python.exe" -m tonermon %*

REM --- PT-PT: Codigo 1 significa "ha toners em alerta", nao e um erro.
REM ---        So mostramos a pausa em falhas reais.
REM --- EN-UK: Exit code 1 means "toners are in alert", not an error.
REM ---        Only pause on genuine failures.
if errorlevel 2 (
    echo.
    echo A aplicacao terminou com erro. Consulte o registo em:
    echo %%APPDATA%%\HPTonerMonitor\tonermon.log
    echo.
    pause
)

endlocal
