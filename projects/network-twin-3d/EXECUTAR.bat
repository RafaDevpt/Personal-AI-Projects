@echo off
REM ===========================================================================
REM PT-PT: Arranque do Network Twin 3D em Windows.
REM
REM        Duplo clique. Na primeira execucao prepara o ambiente; nas seguintes
REM        arranca directamente. Pode arrastar um projeto.json para cima deste
REM        ficheiro para o abrir logo.
REM
REM        A janela usa o WebView2 (Edge), que ja vem no Windows 10 e 11.
REM        Nao pede elevacao, e nao precisa: so le ficheiros que o utilizador
REM        escolhe. Nada sai do PC.
REM
REM EN-UK: Network Twin 3D launcher for Windows. Double-click; drag a
REM        projeto.json onto this file to open it straight away. The window
REM        uses WebView2 (Edge), already present on Windows 10 and 11. No
REM        elevation: it only reads files the user picks. Nothing leaves the PC.
REM
REM Created by Redfox using Claude
REM ===========================================================================

chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo  Network Twin 3D
echo  ---------------
echo.

REM --- PT-PT: Python / EN-UK: Python ----------------------------------------
where python >nul 2>&1
if errorlevel 1 (
    echo  [ERRO] O Python nao foi encontrado.
    echo         Instale de https://www.python.org/downloads/
    echo         IMPORTANTE: marque "Add Python to PATH" durante a instalacao.
    echo.
    pause
    exit /b 1
)

REM --- PT-PT: O atalho da Microsoft Store abre a loja em vez de correr Python.
REM EN-UK: The Microsoft Store shim opens the Store instead of running Python.
for /f "delims=" %%P in ('where python 2^>nul') do (
    echo %%P | find /i "\Microsoft\WindowsApps\" >nul
    if not errorlevel 1 (
        echo  [ERRO] O python.exe encontrado e o atalho da Microsoft Store.
        echo         Instale de https://www.python.org/downloads/ e desligue os
        echo         aliases do python.exe em Definicoes ^> Aplicacoes ^>
        echo         Aliases de execucao de aplicacoes.
        echo.
        pause
        exit /b 1
    )
)

python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if errorlevel 1 (
    echo  [ERRO] O Python encontrado e demasiado antigo. E preciso 3.10 ou superior.
    python --version
    echo.
    pause
    exit /b 1
)

REM --- PT-PT: Ambiente virtual / EN-UK: Virtual environment -----------------
if not exist ".venv\Scripts\python.exe" (
    echo  Primeira execucao: a preparar o ambiente.
    echo  First run: preparing the environment.
    echo.
    python -m venv .venv
    if errorlevel 1 (
        echo  [ERRO] Falha ao criar o ambiente virtual.
        echo.
        pause
        exit /b 1
    )
    .venv\Scripts\python.exe -m pip install --upgrade pip --quiet
    .venv\Scripts\python.exe -m pip install -r requirements.txt
    if errorlevel 1 (
        echo  [ERRO] Falha ao instalar as dependencias.
        echo         Verifique a ligacao a Internet e o proxy.
        echo.
        pause
        exit /b 1
    )
    echo  [OK] Ambiente pronto.
    echo.
)

REM --- PT-PT: Arrancar / EN-UK: Launch --------------------------------------
set "PYTHONPATH=%~dp0src"
set "PYTHONIOENCODING=utf-8"
.venv\Scripts\python.exe -m nettwin %*
set CODIGO=%errorlevel%

REM PT-PT: Pausa so quando correu mal. O codigo 1 do --validar significa "ha
REM        erros na rede", nao "a aplicacao falhou" — mas so aparece em modo
REM        sem janela, onde quem chamou quer ver o resultado na mesma.
REM EN-UK: Pause only when something went wrong.
if not "%CODIGO%"=="0" (
    echo.
    echo  Terminou com o codigo %CODIGO%.
    pause
)
exit /b %CODIGO%
