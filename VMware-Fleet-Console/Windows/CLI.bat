@echo off
REM ===========================================================================
REM PT-PT: Modo de texto da VMware Fleet Console em Windows.
REM
REM        O mesmo programa, sem interface. Para consolas que nao aguentam uma
REM        TUI, e para automacao — o codigo de saida diz o estado do parque sem
REM        ninguem ler nada.
REM
REM            CLI.bat --servidor vcenter.empresa.local --utilizador admin@vsphere.local
REM            CLI.bat --json --seccao estado
REM
REM        Codigos de saida: 0 tudo bem, 1 avisos, 2 criticos, 3 nao ligou.
REM
REM        Para correr numa tarefa agendada, ponha a senha em VFC_PASSWORD. Nao
REM        ha opcao de linha de comandos para ela de proposito: um argumento
REM        fica visivel na lista de processos e no historico.
REM
REM EN-UK: VMware Fleet Console text mode on Windows. Exit codes: 0 well,
REM        1 warnings, 2 critical, 3 could not connect. For a scheduled task,
REM        put the password in VFC_PASSWORD — there is deliberately no
REM        command-line option for it.
REM
REM Created by Redfox using Claude
REM ===========================================================================

chcp 65001 >nul 2>&1
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Ambiente ainda nao preparado. Corra EXECUTAR.bat uma vez primeiro. 1>&2
    exit /b 3
)

set "PYTHONPATH=%~dp0src"
set "PYTHONIOENCODING=utf-8"
.venv\Scripts\python.exe -m vfc --texto %*
exit /b %errorlevel%
