#!/usr/bin/env python3
"""
PT-PT: Gerador para switches Ubiquiti UniFi.

       Um switch UniFi corre a mesma CLI de um EdgeSwitch por baixo, e por isso
       este gerador herda daquele. O que muda não é a sintaxe — é a quem
       pertence a configuração.

       Num UniFi a configuração pertence ao controlador. O switch recebe-a no
       provisionamento e volta a recebê-la a cada alteração, a cada adopção e a
       cada reinício do controlador. Tudo o que for escrito por SSH desaparece
       nesse momento, sem aviso e sem registo.

       Portanto: o que este gerador produz é um remendo temporário, útil para
       um teste ou para desbloquear uma situação até o controlador ser
       corrigido. Não é uma configuração. O cabeçalho di-lo em cada ficheiro, o
       `write memory` não é escrito — daria a ideia errada de permanência — e
       a aplicação recusa-se a enviá-lo sem uma confirmação extra.

       O sítio certo para configurar um UniFi é o controlador.

EN-UK: Generator for Ubiquiti UniFi switches.

       A UniFi switch runs the same CLI as an EdgeSwitch underneath, which is
       why this generator inherits from it. What differs is not the syntax — it
       is who owns the configuration.

       On UniFi the configuration belongs to the controller. The switch
       receives it at provisioning and receives it again on every change, every
       adoption and every controller restart. Anything written over SSH
       disappears at that moment, without warning and without a log entry.

       So: what this generator produces is a temporary patch, useful for a test
       or to unblock a situation until the controller is fixed. It is not a
       configuration. The header says so in every file, `write memory` is not
       written — it would suggest a permanence that is not there — and the
       application refuses to push it without an extra confirmation.

       The right place to configure a UniFi is the controller.

Created by Redfox using Claude
"""

from __future__ import annotations

from typing import ClassVar

from ..models import DeviceSpec, Platform
from .ubiquiti_edgeswitch import UbiquitiEdgeSwitchGenerator


class UbiquitiUniFiGenerator(UbiquitiEdgeSwitchGenerator):
    """
    PT-PT: EdgeSwitch com um aviso à cabeça e sem gravação para arranque.
    EN-UK: EdgeSwitch with a warning up front and no save-to-startup.
    """

    platform: ClassVar[Platform] = Platform.UBIQUITI_UNIFI
    save_command: ClassVar[str] = ""

    def body(self, spec: DeviceSpec) -> list[str]:
        """
        PT-PT: Os comandos do EdgeSwitch, precedidos do aviso e sem `write`.
        EN-UK: The EdgeSwitch commands, preceded by the warning and with no
               `write`.
        """
        # PT-PT: A classe base fecha com o comando de gravação, que aqui é ""
        #        — o `generate` corta o vazio final.
        # EN-UK: The base class closes with the save command, empty here — the
        #        trailing blank is trimmed by `generate`.
        return self._transient_warning() + super().body(spec)

    def _transient_warning(self) -> list[str]:
        """
        PT-PT: O aviso, em comentário, para sobreviver a um copiar-colar.
        EN-UK: The warning, commented, so it survives a copy-paste.
        """
        rule = self.comment_prefix + " " + "*" * 72
        return [
            rule,
            self.comment("ATENCAO — CONFIGURACAO TEMPORARIA"),
            self.comment(),
            self.comment("Num switch UniFi a configuracao pertence ao controlador."),
            self.comment("Estas linhas desaparecem no provisionamento seguinte: uma"),
            self.comment("alteracao no controlador, uma readopcao ou um reinicio bastam."),
            self.comment(),
            self.comment("Use isto para um teste ou para desbloquear uma situacao."),
            self.comment("Para uma alteracao definitiva, configure no controlador."),
            self.comment(),
            self.comment("Acesso a CLI do switch: ssh <utilizador>@<ip> e depois"),
            self.comment("  telnet localhost   (nos modelos que nao dao CLI directa)"),
            rule,
            "",
        ]
