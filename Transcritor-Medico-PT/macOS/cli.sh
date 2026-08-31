#!/usr/bin/env bash
# ===========================================================================
# PT-PT: Modo sem interface, em macOS.
#
#          macOS/cli.sh --batch --audio-dir ~/Gravacoes --output-dir ~/Texto
#          macOS/cli.sh --diagnostico
#
#        Para agendar, o launchd e o caminho certo em macOS — nao o cron, que
#        ainda existe mas esta a prazo. Ha um exemplo de .plist no LEIA-ME
#        desta pasta.
#
#        Codigos de saida: 0 tudo bem, 1 houve falhas, 2 nada a fazer,
#        3 ambiente por preparar, 130 interrompido.
#
# EN-UK: Headless mode on macOS. For scheduling, launchd is the right path on
#        macOS — not cron, which still exists but is on borrowed time. There is
#        a .plist example in this folder's LEIA-ME.
#
# Created by Redfox using Claude
# ===========================================================================

set -euo pipefail

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECTO="$(dirname "$AQUI")"
cd "$PROJECTO"

# PT-PT: O launchd arranca com um PATH minimo que nao inclui o Homebrew, por
#        isso o FFmpeg tem de ser encontrado explicitamente. Sem esta linha, a
#        tarefa agendada falha todas as noites com "FFmpeg nao encontrado"
#        enquanto o mesmo comando funciona perfeitamente no Terminal.
# EN-UK: launchd starts with a minimal PATH that excludes Homebrew, so FFmpeg
#        has to be found explicitly. Without this line the scheduled job fails
#        every night with "FFmpeg not found" while the same command works
#        perfectly in Terminal.
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

if [ ! -x ".venv/bin/python" ]; then
    printf "[ERRO] Ambiente nao preparado. Execute macOS/executar.command uma vez primeiro.\n" >&2
    exit 3
fi

export PYTHONPATH="$PROJECTO/src"
exec .venv/bin/python -m transcriber "$@"
