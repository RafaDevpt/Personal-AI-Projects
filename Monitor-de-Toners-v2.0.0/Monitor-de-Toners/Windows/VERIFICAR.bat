@echo off
REM ===========================================================================
REM PT-PT: Verificacao sem interface grafica, para o Agendador de Tarefas.
REM        Gera os PDF e o rascunho de email se houver toners em alerta.
REM
REM        Para agendar: Agendador de Tarefas -> Criar Tarefa Basica ->
REM        Accao "Iniciar um programa" -> Programa: este ficheiro.
REM
REM EN-UK: Headless check, for Windows Task Scheduler.
REM        Produces the PDFs and the draft email if any toners are in alert.
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
".venv\Scripts\python.exe" -m tonermon --cli %*

endlocal
