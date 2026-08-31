#!/usr/bin/env python3
"""
PT-PT: Base comum aos geradores de configuração.

       Cada fabricante escreve a mesma ideia de maneira diferente, mas a
       estrutura do ficheiro é sempre a mesma: cabeçalho, identidade, VLANs,
       interface de gestão, portas, serviços, segurança, gravação. Essa ordem
       está fixada aqui e não em cada gerador, porque a ordem importa — criar
       uma VLAN depois de a referenciar numa porta falha em todos eles.

       O cabeçalho é comentário em todas as plataformas suportadas, por isso
       pode ser colado na CLI tal como está. Leva sempre a data, a versão da
       ferramenta e os avisos da validação: daqui a um ano, quem abrir o
       ficheiro sabe de onde veio e o que estava por resolver.

EN-UK: Common base for the configuration generators.

       Each vendor writes the same idea differently, but the file's structure
       is always the same: header, identity, VLANs, management interface,
       ports, services, security, save. That order is fixed here rather than in
       each generator, because order matters — creating a VLAN after
       referencing it on a port fails on all of them.

       The header is a comment on every supported platform, so it can be
       pasted into the CLI as it stands. It always carries the date, the tool's
       version and the validation warnings: a year from now, whoever opens the
       file knows where it came from and what was left unresolved.

Created by Redfox using Claude
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import ClassVar

from .. import __app_name__, __version__
from ..models import DeviceSpec, Issue, Platform, Severity


class VendorGenerator(ABC):
    """
    PT-PT: Contrato de um gerador. Uma subclasse precisa de declarar a
           plataforma, o prefixo de comentário e de implementar as secções.

    EN-UK: A generator's contract. A subclass must declare the platform, the
           comment prefix and implement the sections.
    """

    platform: ClassVar[Platform]
    comment_prefix: ClassVar[str] = "!"

    # PT-PT: Linha que grava a configuração para arranque. Vazia se a
    #        plataforma gravar sozinha.
    # EN-UK: Line that writes the configuration to startup. Empty when the
    #        platform saves on its own.
    save_command: ClassVar[str] = ""

    def generate(
        self,
        spec: DeviceSpec,
        issues: list[Issue] | None = None,
        generated_at: datetime | None = None,
        include_header: bool = True,
    ) -> str:
        """
        PT-PT: Produz o ficheiro de configuração completo.

        EN-UK: Produces the complete configuration file.

        :param spec:
            PT-PT: Configuração a traduzir. / EN-UK: Configuration to translate.
        :param issues:
            PT-PT: Avisos da validação, para ficarem registados no cabeçalho.
            EN-UK: Validation warnings, to be recorded in the header.
        :param generated_at:
            PT-PT: Data a inscrever. Serve para os testes fixarem o resultado.
            EN-UK: Date to stamp. Lets the tests pin the output.
        :param include_header:
            PT-PT: False produz só os comandos, sem cabeçalho.
            EN-UK: False produces the commands alone, with no header.
        :return:
            PT-PT: Texto pronto a gravar ou a colar na CLI.
            EN-UK: Text ready to save or paste into the CLI.
        """
        lines: list[str] = []
        if include_header:
            lines += self._header(spec, issues or [], generated_at or datetime.now())
        lines += self.body(spec)
        return "\n".join(lines).rstrip() + "\n"

    @abstractmethod
    def body(self, spec: DeviceSpec) -> list[str]:
        """
        PT-PT: Os comandos, sem cabeçalho. Implementado por cada fabricante.
        EN-UK: The commands, headerless. Implemented per vendor.
        """

    # -----------------------------------------------------------------------
    # PT-PT: Auxiliares à disposição das subclasses.
    # EN-UK: Helpers available to subclasses.
    # -----------------------------------------------------------------------

    def comment(self, text: str = "") -> str:
        """
        PT-PT: Escreve uma linha de comentário na sintaxe da plataforma.
        EN-UK: Writes a comment line in the platform's syntax.
        """
        return f"{self.comment_prefix} {text}".rstrip()

    def _header(self, spec: DeviceSpec, issues: list[Issue], moment: datetime) -> list[str]:
        """
        PT-PT: Cabeçalho comentado, igual em todas as plataformas.
        EN-UK: Commented header, identical across platforms.
        """
        rule = self.comment_prefix + " " + "=" * 72
        lines = [
            rule,
            self.comment(f"{spec.management.hostname or 'sem-nome'} — {self.platform.label}"),
            self.comment(),
            self.comment(f"Gerado por {__app_name__} {__version__}"),
            self.comment(f"Data: {moment.strftime('%Y-%m-%d %H:%M')}"),
        ]

        if spec.notes.strip():
            lines.append(self.comment())
            for line in spec.notes.strip().splitlines():
                lines.append(self.comment(line))

        avisos = [i for i in issues if i.severity is Severity.WARNING]
        if avisos:
            lines.append(self.comment())
            lines.append(self.comment("Avisos por resolver:"))
            for issue in avisos:
                lines.append(self.comment(f"  - {issue.field_name}: {issue.message}"))

        lines += [
            self.comment(),
            self.comment("Reveja antes de aplicar. As palavras-passe estao por definir."),
            rule,
            "",
        ]
        return lines

    def section(self, title: str) -> list[str]:
        """
        PT-PT: Separador de secção, para o ficheiro se ler de cima a baixo.
        EN-UK: Section separator, so the file reads top to bottom.
        """
        return ["", self.comment("-" * 68), self.comment(title), self.comment("-" * 68)]
