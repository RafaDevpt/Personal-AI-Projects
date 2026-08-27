@echo off
REM ===========================================================================
REM PT-PT: Arranque da aplicacao em Windows.
REM        Cria o ambiente virtual e instala as dependencias na primeira
REM        execucao; nas seguintes arranca directamente.
REM        Sem acentos de proposito: a consola do Windows usa CP-850 e
REM        mostraria caracteres trocados.
REM
REM EN-UK: Application launcher for Windows. Creates the virtual environment
REM        and installs dependencies on first run.
REM
REM Created by Redfox using Claude
REM ===========================================================================

setlocal
cd /d "%~dp0"
title PDF Suite

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

set PYTHONPATH=%~dp0src
".venv\Scripts\python.exe" -m pdfsuite %*

REM --- PT-PT: Codigo 1 significa "nao havia nada a fazer", nao e um erro.
REM --- EN-UK: Exit code 1 means "nothing to do", not a failure.
if errorlevel 2 (
    echo.
    echo A aplicacao terminou com erro. Consulte o registo em:
    echo %%APPDATA%%\PDFSuite\pdfsuite.log
    echo.
    pause
)

endlocal
