@echo off
REM ===========================================================================
REM PT-PT: Gera ficheiros de exemplo para experimentar a aplicacao - um
REM        formulario em papel e seis propostas de fornecedores ficticios.
REM        Assim nao e preciso arranjar documentos reais para testar, nem
REM        arriscar por propostas verdadeiras numa pasta de testes.
REM
REM EN-UK: Generates sample files to try the application - a paper form and six
REM        fictional vendor quotes.
REM
REM Created by Redfox using Claude
REM ===========================================================================

setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERRO] Ambiente nao preparado. Execute EXECUTAR.bat uma vez primeiro.
    pause
    exit /b 1
)

set PYTHONPATH=%~dp0src
".venv\Scripts\python.exe" tools\gerar_exemplos.py exemplos
echo.
pause

endlocal
