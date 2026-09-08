@echo off
REM ===========================================================================
REM PT-PT: Arranque da VMware Fleet Console em Windows.
REM
REM        Duplo clique. Na primeira execucao prepara o ambiente; nas seguintes
REM        arranca directamente.
REM
REM        Nao pede elevacao, e nao precisa: esta ferramenta nao le nada da
REM        maquina local. Fala com o vCenter pela rede, e as permissoes que lhe
REM        interessam sao as da conta do vSphere.
REM
REM        A pagina de codigo passa a 65001 (UTF-8) logo no inicio. Sem isso, os
REM        caracteres de desenho e os acentos saem trocados numa consola
REM        portuguesa — que fica com a pagina 850 por omissao.
REM
REM EN-UK: VMware Fleet Console launcher for Windows. Double-click. It asks for
REM        no elevation and needs none: this tool reads nothing from the local
REM        machine. The code page is switched to 65001 (UTF-8) at the start,
REM        without which the drawing characters and accents come out wrong on a
REM        Portuguese console, which defaults to 850.
REM
REM Created by Redfox using Claude
REM ===========================================================================

chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo  VMware Fleet Console
echo  --------------------
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

REM --- PT-PT: O atalho da Microsoft Store.
REM
REM     Uma instalacao limpa do Windows traz um python.exe no PATH que abre a
REM     loja em vez de correr Python. Sem esta verificacao, o que acontece a
REM     seguir e a Store abrir-se sozinha e ninguem perceber porque.
REM
REM EN-UK: The Microsoft Store shim. Without this check, what happens next is
REM     the Store opening on its own and nobody understanding why.
REM --------------------------------------------------------------------------
for /f "delims=" %%P in ('where python 2^>nul') do (
    echo %%P | find /i "\Microsoft\WindowsApps\" >nul
    if not errorlevel 1 (
        echo  [ERRO] O python.exe encontrado e o atalho da Microsoft Store.
        echo         Nao e o Python: abre a loja.
        echo.
        echo         Instale de https://www.python.org/downloads/ e depois va a
        echo         Definicoes ^> Aplicacoes ^> Aliases de execucao de aplicacoes
        echo         e desligue os do python.exe.
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
.venv\Scripts\python.exe -m vfc %*
set CODIGO=%errorlevel%

REM PT-PT: A pausa so acontece quando alguma coisa correu mal. Numa saida
REM        limpa, uma janela que fica aberta a dizer "prima uma tecla" e ruido.
REM EN-UK: The pause only happens when something went wrong. On a clean exit, a
REM        window left open saying "press any key" is noise.
if not "%CODIGO%"=="0" (
    echo.
    echo  A aplicacao terminou com o codigo %CODIGO%.
    pause
)
exit /b %CODIGO%
