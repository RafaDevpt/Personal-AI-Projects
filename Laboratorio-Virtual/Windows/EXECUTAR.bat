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

REM PT-PT: Uma janela que se fecha com um erro la dentro e um erro que ninguem
REM        consegue comunicar. Se o programa falhou, para-se **sempre**, mesmo
REM        quando foram passados argumentos -- porque foi assim que se perdeu
REM        um erro que fazia falta ver.
REM
REM        Quando corre bem e foram passados argumentos, sai sem parar: nesse
REM        caso quem chamou foi um script, e um script nao carrega em teclas.
REM EN-UK: A window that closes with an error inside it is an error nobody can
REM        report. On failure it **always** stops, even when arguments were
REM        passed. On success with arguments it exits without pausing: the
REM        caller was a script, and scripts do not press keys.
if not "%CODIGO%"=="0" (
    echo.
    echo   O programa terminou com erro. O registo desta sessao esta em:
    echo     %LOCALAPPDATA%\LaboratorioVirtual
    echo.
    pause
    exit /b %CODIGO%
)

if not "%1"=="" exit /b %CODIGO%

echo.
pause
exit /b %CODIGO%
