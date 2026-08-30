@echo off
REM ===========================================================================
REM PT-PT: Arranque da aplicacao em Windows.
REM        Cria o ambiente virtual e instala as dependencias na primeira
REM        execucao; nas seguintes arranca directamente.
REM
REM        Nao pede elevacao, ao contrario das outras ferramentas. Esta nao le
REM        nada da maquina local: fala com equipamento de rede por SSH e
REM        escreve ficheiros na pasta do utilizador. Correr como administrador
REM        nao lhe daria nada e so aumentava o que pode correr mal.
REM
REM        Sem acentos de proposito: a consola do Windows usa CP-850 e
REM        mostraria caracteres trocados.
REM
REM EN-UK: Application launcher for Windows.
REM        Creates the virtual environment and installs dependencies on first
REM        run; subsequent runs start straight away.
REM
REM        It does not request elevation, unlike the other tools. This one
REM        reads nothing from the local machine: it talks to network equipment
REM        over SSH and writes files into the user's folder. Running as
REM        administrator would gain it nothing and only widen what can go wrong.
REM
REM Created by Redfox using Claude
REM ===========================================================================

setlocal
cd /d "%~dp0"
title Network Config Builder

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
set PYTHONPATH=%~dp0src
".venv\Scripts\python.exe" -m netconfig %*

REM --- PT-PT: O codigo 1 significa "encontrou problemas na validacao" e o 2
REM ---        "nao chegou ao equipamento". Nenhum deles e uma falha da
REM ---        aplicacao, por isso nao paramos o ecra.
REM --- EN-UK: Code 1 means "found validation problems" and 2 "could not reach
REM ---        the device". Neither is an application failure, so no pause.
if errorlevel 3 (
    echo.
    echo A aplicacao terminou com erro. Consulte o registo em:
    echo %%APPDATA%%\NetworkConfigBuilder\netconfig.log
    echo.
    pause
)

endlocal
