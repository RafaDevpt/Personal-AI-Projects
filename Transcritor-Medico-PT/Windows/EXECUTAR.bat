@echo off
REM ===========================================================================
REM PT-PT: Arranque da aplicacao em Windows.
REM        Cria o ambiente virtual e instala as dependencias na primeira
REM        execucao; nas seguintes arranca directamente.
REM
REM EN-UK: Application launcher for Windows.
REM        Creates the virtual environment and installs dependencies on first
REM        run; subsequent runs start straight away.
REM
REM Created by Redfox using Claude
REM ===========================================================================

setlocal
REM --- PT-PT: A pasta do projecto e a mae desta. Este lancador vive em
REM ---        Windows\ para que Linux e macOS tenham os seus ao lado, sem
REM ---        tres copias do codigo: o que muda entre sistemas e o arranque e
REM ---        os pre-requisitos, nao a aplicacao.
REM --- EN-UK: The project folder is this one's parent. This launcher lives in
REM ---        Windows\ so Linux and macOS can have theirs alongside, with no
REM ---        three copies of the code: what differs between systems is the
REM ---        launch and the prerequisites, not the application.
cd /d "%~dp0.."
title Transcritor Medico PT

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
    echo Primeira execucao: a preparar o ambiente. Pode demorar alguns minutos.
    echo First run: preparing the environment. This may take a few minutes.
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

REM --- PT-PT: Avisar se o ffmpeg faltar (necessario para ler audio)
REM --- EN-UK: Warn if ffmpeg is missing (required to read audio)
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo [AVISO] ffmpeg nao encontrado. A transcricao vai falhar.
    echo         Instale com: winget install Gyan.FFmpeg
    echo.
)

REM --- PT-PT: Arrancar / EN-UK: Launch
set PYTHONPATH=%CD%\src
".venv\Scripts\python.exe" -m transcriber %*

if errorlevel 1 (
    echo.
    echo A aplicacao terminou com erro. Consulte o registo em:
    echo %%APPDATA%%\PortugueseMedicalTranscriber\transcriber.log
    echo.
    pause
)

endlocal
