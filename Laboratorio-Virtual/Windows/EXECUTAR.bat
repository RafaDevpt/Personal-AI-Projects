@echo off
REM ===========================================================================
REM PT-PT: Arranque do Laboratorio Virtual em Windows.
REM
REM        O `-ExecutionPolicy Bypass` aplica-se **a este processo e mais nada**.
REM        Nao altera a politica da maquina, nao pede elevacao para o fazer, e
REM        acaba quando a janela fecha. E a diferenca entre correr um script e
REM        mudar a configuracao de seguranca de alguem para sempre -- e ha
REM        instrucoes na Internet que ensinam a segunda coisa para resolver a
REM        primeira.
REM
REM        Nao se pede elevacao aqui. O programa corre sem ela e diz o que nao
REM        consegue fazer: so o Hyper-V precisa de administrador, e so na altura
REM        de criar a maquina. Pedir elevacao a cabeca, para depois nao ser
REM        preciso, ensina o utilizador a carregar em "Sim" sem ler.
REM
REM EN-UK: Virtual Lab launcher for Windows.
REM
REM        `-ExecutionPolicy Bypass` applies **to this process only**. It does
REM        not change the machine's policy -- which is the difference between
REM        running a script and permanently changing somebody's security
REM        settings, and there are instructions online teaching the second to
REM        solve the first.
REM
REM        No elevation is requested here. The program runs without it and says
REM        what it cannot do.
REM
REM Created by Redfox using Claude
REM ===========================================================================

setlocal
cd /d "%~dp0"

where powershell >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Nao encontrei o PowerShell nesta maquina.
    echo        Isto nao devia acontecer num Windows 10 ou 11.
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0src\LaboratorioVirtual.ps1" %*
set CODIGO=%ERRORLEVEL%

if not "%1"=="" exit /b %CODIGO%

echo.
pause
exit /b %CODIGO%
