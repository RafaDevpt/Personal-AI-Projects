@echo off
REM ===========================================================================
REM PT-PT: Diagnostico sem interface grafica, para o Agendador de Tarefas.
REM        Escreve o relatorio HTML e sai com um codigo conforme o que
REM        encontrou, para o agendador reagir sem ninguem ler o relatorio:
REM
REM          0  limpo
REM          1  problemas nao criticos
REM          2  problemas criticos
REM          3  falta a interface grafica (nao acontece neste modo)
REM          4  nao conseguiu gravar o relatorio
REM
REM        Para agendar: Agendador de Tarefas -> Criar Tarefa ->
REM        "Executar com privilegios mais elevados" ->
REM        Accao "Iniciar um programa" -> Programa: este ficheiro.
REM
REM EN-UK: Headless diagnostic, for Windows Task Scheduler. Writes the HTML
REM        report and exits with a code reflecting what it found.
REM
REM Created by Redfox using Claude
REM ===========================================================================

setlocal
cd /d "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
    echo [ERRO] Ambiente nao preparado. Execute EXECUTAR.bat uma vez primeiro.
    exit /b 1
)

set PYTHONPATH=%CD%\src
".venv\Scripts\python.exe" -m ittoolkit --cli %*

endlocal
