@echo off
REM ===========================================================================
REM PT-PT: Modo sem interface, para o Agendador de Tarefas.
REM
REM        O uso obvio e um mapeamento mensal, para haver historico de como a
REM        rede foi mudando:
REM
REM          CLI.bat mapear --semente 10.0.10.1
REM
REM        As credenciais nao se passam por argumento - ficariam a vista na
REM        definicao da tarefa. Defina-as como variaveis de ambiente da tarefa:
REM
REM          NETMAP_UTILIZADOR
REM          NETMAP_PALAVRA_PASSE
REM          NETMAP_UNIFI_UTILIZADOR      (so se usar o controlador)
REM          NETMAP_UNIFI_PALAVRA_PASSE
REM
REM        Codigos de saida:
REM          0  correu e nao encontrou nada de estranho
REM          1  correu e assinalou problemas (o normal numa rede real)
REM          2  nao alcancou nenhum equipamento
REM          3  erro da aplicacao
REM
REM EN-UK: Headless mode, for Windows Task Scheduler. Credentials go in
REM        environment variables, never in arguments.
REM
REM Created by Redfox using Claude
REM ===========================================================================

setlocal
cd /d "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
    echo [ERRO] Ambiente nao preparado. Execute EXECUTAR.bat uma vez primeiro.
    exit /b 3
)

set PYTHONPATH=%CD%\src
".venv\Scripts\python.exe" -m netmap %*

endlocal
