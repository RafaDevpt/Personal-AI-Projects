@echo off
REM ===========================================================================
REM PT-PT: Linha de comandos do Transcritor Medico PT, sem abrir a interface grafica.
REM
REM        Reencaminha todos os argumentos para o modulo. Serve para agendar
REM        trabalho no Agendador de Tarefas e para correr lotes sem ninguem a
REM        olhar para o ecra.
REM
REM        Exemplos:
REM          CLI.bat --help
REM
REM          CLI.bat consulta.wav --formato docx
REM          CLI.bat gravacoes\ --modelo medium
REM
REM EN-UK: Command line for Transcritor Medico PT, without opening the graphical interface.
REM
REM        Forwards every argument to the module. Meant for scheduling work in
REM        Task Scheduler and for running batches with nobody watching.
REM
REM Created by Redfox using Claude
REM ===========================================================================

setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERRO] Ambiente nao preparado. Execute EXECUTAR.bat uma vez primeiro.
    echo [ERROR] Environment not ready. Run EXECUTAR.bat once first.
    exit /b 1
)

set PYTHONPATH=%~dp0src
".venv\Scripts\python.exe" -m transcriber %*

endlocal
