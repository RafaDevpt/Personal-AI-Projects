@echo off
REM ===========================================================================
REM PT-PT: Modo sem interface, para o Agendador de Tarefas.
REM
REM        O uso obvio e o backup nocturno de toda a rede:
REM
REM          CLI.bat backup --todos
REM
REM        As credenciais nao se passam por argumento - ficariam a vista na
REM        definicao da tarefa. Defina-as como variaveis de ambiente da tarefa:
REM
REM          NETCONFIG_UTILIZADOR
REM          NETCONFIG_PALAVRA_PASSE
REM
REM        Codigos de saida:
REM          0  correu e esta tudo bem
REM          1  correu e encontrou problemas (validacao, diferencas)
REM          2  nao conseguiu falar com o equipamento
REM          3  erro da aplicacao
REM
REM EN-UK: Headless mode, for Windows Task Scheduler. The obvious use is the
REM        nightly backup of the whole network. Credentials are not passed as
REM        arguments - they would sit in plain sight in the task definition.
REM
REM Created by Redfox using Claude
REM ===========================================================================

setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERRO] Ambiente nao preparado. Execute EXECUTAR.bat uma vez primeiro.
    exit /b 3
)

set PYTHONPATH=%~dp0src
".venv\Scripts\python.exe" -m netconfig %*

endlocal
