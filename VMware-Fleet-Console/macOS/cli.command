#!/usr/bin/env bash
# ===========================================================================
# PT-PT: Modo de texto da VMware Fleet Console em macOS.
#
#        O mesmo programa, sem interface. Para terminais que nao aguentam uma
#        TUI, e para automacao: o codigo de saida diz o estado do parque sem
#        ninguem ler nada.
#
#            ./cli.command --servidor vcenter.empresa.local --utilizador admin@vsphere.local
#            ./cli.command --json --seccao estado
#
#        Codigos de saida: 0 tudo bem, 1 avisos, 2 criticos, 3 nao ligou.
#
#        Para correr num launchd sem ninguem a olhar, ponha a senha em
#        VFC_PASSWORD. Nao ha opcao de linha de comandos para ela de proposito:
#        um argumento fica visivel no `ps` para qualquer utilizador da maquina.
#
# EN-UK: VMware Fleet Console text mode on macOS. Exit codes: 0 well,
#        1 warnings, 2 critical, 3 could not connect. For an unattended launchd
#        job, put the password in VFC_PASSWORD — there is deliberately no
#        command-line option for it.
#
# Created by Redfox using Claude
# ===========================================================================

set -euo pipefail

PROJECTO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECTO"

if [ ! -x ".venv/bin/python" ]; then
    printf "Ambiente ainda nao preparado. Corra ./executar.command uma vez primeiro.\n" >&2
    exit 3
fi

export PYTHONPATH="$PROJECTO/src"
exec .venv/bin/python -m vfc --texto "$@"
