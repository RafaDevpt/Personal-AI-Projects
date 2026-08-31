#!/usr/bin/env python3
"""
PT-PT: Comparação entre a configuração que está no equipamento e a que se quer
       aplicar.

       Um diff em bruto entre estes dois textos não serve para nada: a
       configuração lida do switch traz o cabeçalho do firmware, contadores,
       certificados, a data de arranque e centenas de linhas de omissão que o
       equipamento escreve sozinho e que o ficheiro gerado nunca terá. Sem
       normalizar, tudo aparece como diferença e ninguém lê o resultado.

       Por isso a comparação é feita sobre uma versão normalizada — sem
       comentários, sem espaços a mais, sem as linhas que se sabe serem ruído —
       e o que se apresenta é a diferença dessa versão. O objectivo não é
       reproduzir o ficheiro do switch; é responder a uma pergunta concreta:
       *o que é que este envio vai mudar?*

EN-UK: Comparison between the configuration on the device and the one about to
       be applied.

       A raw diff between those two texts is worthless: the configuration read
       from the switch carries the firmware banner, counters, certificates, the
       boot date and hundreds of default lines the device writes by itself and
       the generated file will never have. Without normalising, everything
       shows as a difference and nobody reads the result.

       So the comparison runs over a normalised version — no comments, no extra
       whitespace, none of the lines known to be noise — and what is presented
       is that version's difference. The aim is not to reproduce the switch's
       file; it is to answer one concrete question: *what will this push
       change?*

Created by Redfox using Claude
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass

# PT-PT: Linhas que o equipamento escreve sozinho e que nunca serão iguais
#        entre uma leitura e um ficheiro gerado. Compará-las é ruído.
# EN-UK: Lines the device writes by itself, which will never match between a
#        read and a generated file. Comparing them is noise.
_NOISE_PATTERNS = [
    re.compile(r"^\s*!?\s*(Current|Startup) configuration", re.IGNORECASE),
    re.compile(r"^\s*!?\s*Last configuration change", re.IGNORECASE),
    re.compile(r"^\s*!?\s*NVRAM config last updated", re.IGNORECASE),
    re.compile(r"^\s*version\s", re.IGNORECASE),
    re.compile(r"^\s*Building configuration", re.IGNORECASE),
    re.compile(r"^\s*ntp clock-period", re.IGNORECASE),
    re.compile(r"^\s*crypto pki ", re.IGNORECASE),
    re.compile(r"^\s*certificate ", re.IGNORECASE),
    re.compile(r"^\s*[0-9A-F]{16,}\s*$"),
]


@dataclass(frozen=True)
class DiffSummary:
    """
    PT-PT: Contagem do que muda, para se poder decidir sem ler o diff todo.
           Um envio que acrescenta três linhas e não remove nenhuma é uma
           conversa diferente de um que remove quarenta.

    EN-UK: A count of what changes, so a decision can be made without reading
           the whole diff. A push that adds three lines and removes none is a
           different conversation from one that removes forty.
    """

    added: int
    removed: int

    @property
    def changed(self) -> bool:
        """PT-PT: Se há alguma diferença. / EN-UK: Whether anything differs."""
        return bool(self.added or self.removed)

    def __str__(self) -> str:
        if not self.changed:
            return "Sem diferenças."
        return f"{self.added} linhas a acrescentar, {self.removed} a remover."


def normalise(config_text: str) -> list[str]:
    """
    PT-PT: Reduz uma configuração ao que vale a pena comparar.

    EN-UK: Reduces a configuration to what is worth comparing.

    :param config_text:
        PT-PT: Texto original, lido ou gerado.
        EN-UK: Original text, read or generated.
    :return:
        PT-PT: Linhas úteis, sem comentários, sem vazios e sem espaços a mais.
        EN-UK: Useful lines, comment-free, blank-free and whitespace-collapsed.
    """
    linhas: list[str] = []
    for raw in config_text.splitlines():
        linha = raw.rstrip()
        if not linha.strip():
            continue
        if linha.strip().startswith("!") or linha.strip().startswith("#"):
            continue
        if any(pattern.match(linha) for pattern in _NOISE_PATTERNS):
            continue
        # PT-PT: A indentação varia entre fabricantes e entre firmwares; o que
        #        interessa é o comando, não quantos espaços o precedem.
        # EN-UK: Indentation varies between vendors and firmwares; what matters
        #        is the command, not how many spaces precede it.
        linhas.append(re.sub(r"\s+", " ", linha.strip()))
    return linhas


def unified(current: str, proposed: str, current_label: str = "no equipamento", proposed_label: str = "a aplicar") -> str:
    """
    PT-PT: Diff unificado entre as duas configurações, já normalizadas.

    EN-UK: Unified diff between the two configurations, already normalised.

    :param current:
        PT-PT: Configuração lida do equipamento.
        EN-UK: Configuration read from the device.
    :param proposed:
        PT-PT: Configuração gerada. / EN-UK: Generated configuration.
    :param current_label:
        PT-PT: Rótulo do lado esquerdo. / EN-UK: Left-hand label.
    :param proposed_label:
        PT-PT: Rótulo do lado direito. / EN-UK: Right-hand label.
    :return:
        PT-PT: O diff, ou "" se não houver diferenças.
        EN-UK: The diff, or "" when there is no difference.
    """
    linhas = list(
        difflib.unified_diff(
            normalise(current),
            normalise(proposed),
            fromfile=current_label,
            tofile=proposed_label,
            lineterm="",
            n=2,
        )
    )
    return "\n".join(linhas)


def summarise(current: str, proposed: str) -> DiffSummary:
    """
    PT-PT: Conta as linhas acrescentadas e removidas.

    EN-UK: Counts the added and removed lines.

    :param current:
        PT-PT: Configuração lida. / EN-UK: Configuration read.
    :param proposed:
        PT-PT: Configuração gerada. / EN-UK: Generated configuration.
    :return:
        PT-PT: A contagem. / EN-UK: The count.
    """
    added = removed = 0
    for linha in unified(current, proposed).splitlines():
        if linha.startswith("+++") or linha.startswith("---"):
            continue
        if linha.startswith("+"):
            added += 1
        elif linha.startswith("-"):
            removed += 1
    return DiffSummary(added=added, removed=removed)


def missing_lines(current: str, proposed: str) -> list[str]:
    """
    PT-PT: As linhas da configuração proposta que ainda não estão no
           equipamento — que é, na prática, o que o envio vai fazer.

           Não é o mesmo que o diff: aqui a ordem não conta e as linhas que só
           existem no equipamento são ignoradas. Um envio acrescenta e altera,
           não apaga o que já lá está.

    EN-UK: The lines of the proposed configuration that are not on the device
           yet — which is, in practice, what the push will do.

           Not the same as the diff: order does not count here and lines that
           exist only on the device are ignored. A push adds and changes; it
           does not delete what is already there.

    :param current:
        PT-PT: Configuração lida. / EN-UK: Configuration read.
    :param proposed:
        PT-PT: Configuração gerada. / EN-UK: Generated configuration.
    :return:
        PT-PT: Linhas em falta, pela ordem da configuração gerada.
        EN-UK: Missing lines, in the generated configuration's order.
    """
    existentes = set(normalise(current))
    return [linha for linha in normalise(proposed) if linha not in existentes]
