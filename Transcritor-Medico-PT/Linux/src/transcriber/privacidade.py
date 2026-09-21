#!/usr/bin/env python3
"""
PT-PT: Permissões dos ficheiros que contêm dados de doentes.

       **Porquê um módulo só para isto.** O que este programa grava não é texto
       qualquer: é a transcrição de uma consulta, a gravação áudio que lhe deu
       origem, e o dicionário de correcções, que acaba por acumular nomes e
       termos que aparecem nas consultas. Em Portugal isso é dado de saúde, e o
       RGPD trata-o como categoria especial.

       O programa já faz a parte difícil bem: a transcrição é local, com o
       faster-whisper, e não sai daqui nada para servidor nenhum. O que faltava
       era o passo pequeno — os ficheiros eram criados com a máscara por
       omissão, que na maioria das distribuições dá 0644 nos ficheiros e 0755
       nas pastas. Numa máquina partilhada, ou num posto com mais do que uma
       conta, qualquer outro utilizador lia as transcrições sem precisar de
       fazer nada de especial.

       Aqui os ficheiros passam a 0600 e as pastas a 0700: só o dono.

       **No Windows isto não faz nada**, e é esperado. O `os.chmod` do Windows
       só mexe no atributo de leitura e as permissões a sério são ACLs, que o
       Python não escreve. A protecção real aí é a pasta do perfil do
       utilizador, que já é restrita. Não se finge que foi aplicada uma coisa
       que não foi — por isso a função devolve se conseguiu ou não.

EN-UK: Permissions for the files that hold patient data.

       **Why a module just for this.** What this program writes is not ordinary
       text: it is the transcription of a consultation, the audio recording
       behind it, and the corrections dictionary, which accumulates names and
       terms appearing in consultations. That is health data, and the GDPR
       treats it as a special category.

       The program already gets the hard part right: transcription is local, via
       faster-whisper, and nothing leaves the machine. What was missing was the
       small step — files were created under the default umask, which on most
       distributions gives 0644 for files and 0755 for directories. On a shared
       machine, or a workstation with more than one account, any other user
       could read the transcriptions without having to do anything clever.

       Here files become 0600 and directories 0700: owner only.

       **On Windows this does nothing**, and that is expected. Windows `os.chmod`
       only touches the read-only attribute, and real permissions are ACLs, which
       Python does not write. The actual protection there is the user's profile
       folder, which is already restricted. Nothing pretends otherwise — the
       function reports whether it managed it.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

_log = logging.getLogger(__name__)

MODO_FICHEIRO = 0o600
MODO_PASTA = 0o700


def restringir_ao_dono(caminho: Path) -> bool:
    """
    PT-PT: Deixa o ficheiro ou a pasta acessível só ao dono.

    EN-UK: Leaves the file or directory accessible to its owner alone.

    :param caminho:
        PT-PT: Ficheiro ou pasta já existente.
        EN-UK: An existing file or directory.
    :return:
        PT-PT: True se as permissões foram mesmo aplicadas; False se o sistema
               não as suporta ou recusou. Nunca levanta excepção: apertar
               permissões não deve impedir a transcrição de ser gravada.
        EN-UK: True if the permissions were actually applied; False if the
               system does not support them or refused. Never raises: tightening
               permissions must not stop a transcription from being saved.
    """
    if os.name == "nt":
        return False
    try:
        modo = MODO_PASTA if caminho.is_dir() else MODO_FICHEIRO
        os.chmod(caminho, modo)
    except OSError as erro:
        _log.debug("Não foi possível restringir %s: %s", caminho, erro)
        return False
    return True


def criar_pasta_restrita(pasta: Path) -> None:
    """
    PT-PT: Cria a pasta, se faltar, e restringe-a ao dono.

           Substitui o `mkdir(parents=True, exist_ok=True)` que estava espalhado
           pelos módulos que gravam. Cada nível criado é restringido, e não só o
           último: uma pasta intermédia legível anula o trabalho da de baixo.

    EN-UK: Creates the directory if missing and restricts it to the owner.

           Replaces the `mkdir(parents=True, exist_ok=True)` that was scattered
           across the writing modules. Every level created is restricted, not
           just the last: a readable intermediate directory undoes the work of
           the one beneath it.

    :param pasta:
        PT-PT: Pasta a criar. / EN-UK: Directory to create.
    """
    if pasta.exists():
        restringir_ao_dono(pasta)
        return

    # PT-PT: Guardar os níveis que ainda não existem, para restringir só esses
    #        e não mexer em pastas do utilizador que já cá estavam.
    # EN-UK: Note which levels do not yet exist, so only those are restricted
    #        and pre-existing user directories are left alone.
    em_falta = []
    actual = pasta
    while not actual.exists() and actual != actual.parent:
        em_falta.append(actual)
        actual = actual.parent

    pasta.mkdir(parents=True, exist_ok=True)
    for nivel in em_falta:
        restringir_ao_dono(nivel)
