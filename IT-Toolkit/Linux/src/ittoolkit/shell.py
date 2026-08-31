#!/usr/bin/env python3
"""
PT-PT: Execucao de comandos externos em Linux.

       Quase todo o diagnostico depende de correr ferramentas do sistema e ler
       o que elas devolvem — e ler mal e a fonte mais comum de bugs silenciosos
       numa ferramenta destas.

       Tres decisoes que valem mais do que o codigo que as implementa.

       **Nunca `shell=True`.** Os comandos vao como lista de argumentos. Uma
       ferramenta de diagnostico corre com privilegios e recebe nomes de
       unidades e de dispositivos que vem do sistema; passa-los por uma shell
       seria dar-lhes poder de execucao que nao precisam de ter.

       **O ambiente e forcado a C.** Um `LANG=pt_PT.UTF-8` faz o `systemctl` e o
       `lsblk` traduzirem os cabecalhos e os estados, e um parser que procura
       "failed" deixa de encontrar "falhou". A versao anterior desta ferramenta
       em Windows aprendeu isto com as codepages; em Linux o problema e o mesmo
       com outro nome.

       **Um comando que nao existe nao e um erro.** Numa instalacao minima nao
       ha `smartctl`, nem `dmidecode`, nem `ss`. O `Resultado` distingue «correu
       e falhou» de «nem sequer esta instalado», porque a resposta a dar ao
       utilizador e diferente em cada caso.

EN-UK: External command execution on Linux.

       Nearly all diagnostics depend on running system tools and reading what
       they return — and reading it wrongly is the commonest source of silent
       bugs in a tool like this.

       Three decisions worth more than the code implementing them.

       **Never `shell=True`.** Commands go as argument lists. A diagnostic tool
       runs with privilege and handles unit and device names coming from the
       system; passing them through a shell would grant them execution power
       they do not need.

       **The environment is forced to C.** A `LANG=pt_PT.UTF-8` makes
       `systemctl` and `lsblk` translate their headers and states, and a parser
       looking for "failed" stops finding "falhou".

       **A missing command is not an error.** A minimal installation has no
       `smartctl`, no `dmidecode`, no `ss`. `Resultado` tells "ran and failed"
       from "is not even installed", because what to tell the user differs.

Created by Redfox using Claude
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)

# PT-PT: O ambiente com que todos os comandos correm. O `LC_ALL=C` garante
#        saidas em ingles e formatos numericos previsiveis; sem ele, uma maquina
#        configurada em portugues devolve "falhou" onde o parser espera "failed"
#        e virgulas onde ele espera pontos decimais.
# EN-UK: The environment every command runs with. `LC_ALL=C` guarantees English
#        output and predictable number formats; without it a Portuguese-
#        configured machine returns "falhou" where the parser expects "failed".
AMBIENTE_NEUTRO = {"LC_ALL": "C", "LANG": "C", "LANGUAGE": "C"}


@dataclass(slots=True)
class Resultado:
    """
    PT-PT: O resultado de um comando.

           `ausente` e o campo que distingue os dois tipos de falha. Um
           `smartctl` que devolve codigo 2 esta a dizer alguma coisa sobre o
           disco; um `smartctl` que nao existe nao esta a dizer nada sobre o
           disco nenhum — esta a dizer que falta um pacote. Apresentar os dois
           como «erro ao ler o disco» seria mandar alguem procurar uma avaria
           que nao existe.

    EN-UK: A command's result.

           `ausente` is the field telling the two kinds of failure apart. A
           `smartctl` returning code 2 is saying something about the disk; a
           `smartctl` that does not exist is saying nothing about any disk — it
           is saying a package is missing.
    """

    comando: str
    codigo: int
    saida: str = ""
    erro: str = ""
    ausente: bool = False
    expirou: bool = False

    @property
    def ok(self) -> bool:
        """PT-PT: Se correu e devolveu zero. / EN-UK: Whether it ran and returned zero."""
        return self.codigo == 0 and not self.ausente and not self.expirou

    @property
    def texto(self) -> str:
        """
        PT-PT: A saída se correu bem, a explicação da falha se não.

               É o que a interface mostra numa caixa de texto: quem está a olhar
               para o ecrã quer ver o resultado ou a razão de não haver
               resultado, e nunca uma caixa vazia.

        EN-UK: The output when it worked, the failure explanation when it did
               not. It is what the interface shows in a text box: whoever is
               looking at the screen wants the result, or the reason there is
               none, and never an empty box.
        """
        if self.ok:
            return self.saida.strip() or "(sem saída)"
        return self.explicacao() or (self.erro or self.saida).strip()

    @property
    def linhas(self) -> list[str]:
        """PT-PT: A saida em linhas, sem vazias. / EN-UK: Output as lines, blanks dropped."""
        return [linha for linha in self.saida.splitlines() if linha.strip()]

    def explicacao(self) -> str:
        """
        PT-PT: Uma frase que se pode mostrar ao utilizador quando falhou.
        EN-UK: A sentence that can be shown to the user when it failed.
        """
        if self.ausente:
            return f"O comando '{self.comando}' não está instalado nesta máquina."
        if self.expirou:
            return f"O comando '{self.comando}' não respondeu a tempo."
        if self.codigo != 0:
            detalhe = (self.erro or self.saida).strip().splitlines()
            return f"'{self.comando}' terminou com código {self.codigo}. {detalhe[0] if detalhe else ''}".strip()
        return ""


def disponivel(programa: str) -> bool:
    """
    PT-PT: Se um programa existe no PATH.

    EN-UK: Whether a program exists on the PATH.

    :param programa:
        PT-PT: Nome do executável. / EN-UK: The executable's name.
    """
    return shutil.which(programa) is not None


def executar(args: list[str], timeout: int = 60) -> Resultado:
    """
    PT-PT: Corre um comando e devolve o que ele disse.

           Nunca levanta excepção por o comando ter falhado: uma ferramenta de
           diagnóstico que rebenta porque um dos vinte comandos não correu é
           inútil. O que falha vira um `Resultado` com a razão, e o módulo que
           chamou decide o que fazer.

    EN-UK: Runs a command and returns what it said.

           It never raises because the command failed: a diagnostic tool that
           blows up because one of twenty commands did not run is useless.
           Whatever fails becomes a `Resultado` carrying the reason.

    :param args:
        PT-PT: Programa e argumentos, um por elemento.
        EN-UK: Program and arguments, one per element.
    :param timeout:
        PT-PT: Segundos até desistir. / EN-UK: Seconds before giving up.
    :return:
        PT-PT: O resultado, sempre. / EN-UK: The result, always.
    """
    if not args:
        return Resultado(comando="", codigo=-1, erro="Comando vazio.")

    nome = args[0]
    if not disponivel(nome):
        log.debug("Comando ausente: %s", nome)
        return Resultado(comando=nome, codigo=127, ausente=True)

    ambiente = {**os.environ, **AMBIENTE_NEUTRO}

    try:
        processo = subprocess.run(  # noqa: S603 - PT-PT: lista de argumentos, nunca shell
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=ambiente,
            check=False,
        )
    except subprocess.TimeoutExpired:
        log.warning("Expirou: %s", " ".join(args))
        return Resultado(comando=nome, codigo=-1, expirou=True)
    except OSError as exc:
        log.warning("Falha ao correr %s: %s", nome, exc)
        return Resultado(comando=nome, codigo=-1, erro=str(exc))

    return Resultado(
        comando=nome,
        codigo=processo.returncode,
        saida=processo.stdout or "",
        erro=processo.stderr or "",
    )


def executar_json(args: list[str], timeout: int = 60) -> Any:
    """
    PT-PT: Corre um comando que devolve JSON e interpreta-o.

           Cada vez mais ferramentas de Linux têm um `--json` ou um `-J`, e usá-
           -lo é sempre melhor do que ler colunas: o `lsblk` muda a largura das
           colunas com o nome dos discos, e um parser posicional parte-se na
           primeira máquina com nomes compridos.

    EN-UK: Runs a command returning JSON and parses it.

           More and more Linux tools have a `--json` or `-J`, and using it always
           beats reading columns: `lsblk` changes column widths with disk names,
           and a positional parser breaks on the first machine with long ones.

    :return:
        PT-PT: O que o JSON continha, ou None se não houver JSON válido.
        EN-UK: Whatever the JSON held, or None when there is no valid JSON.
    """
    resultado = executar(args, timeout=timeout)
    if not resultado.saida.strip():
        return None
    try:
        return json.loads(resultado.saida)
    except json.JSONDecodeError as exc:
        log.debug("Saída de %s não é JSON: %s", resultado.comando, exc)
        return None


def linhas_json(args: list[str], timeout: int = 60) -> list[dict]:
    """
    PT-PT: Corre um comando que devolve um objecto JSON por linha.

           É o formato do `journalctl -o json`, e não é um documento JSON: são
           milhares de objectos independentes, um por linha. Tentar interpretar
           tudo de uma vez falha sempre.

    EN-UK: Runs a command returning one JSON object per line.

           It is `journalctl -o json`'s format, and it is not a JSON document:
           it is thousands of independent objects, one per line. Parsing it all
           at once always fails.

    :return:
        PT-PT: Um dicionário por linha válida; as inválidas são saltadas.
        EN-UK: One dictionary per valid line; invalid ones are skipped.
    """
    resultado = executar(args, timeout=timeout)
    registos: list[dict] = []

    for linha in resultado.saida.splitlines():
        linha = linha.strip()
        if not linha:
            continue
        try:
            objecto = json.loads(linha)
        except json.JSONDecodeError:
            continue
        if isinstance(objecto, dict):
            registos.append(objecto)

    return registos


def ler_ficheiro(caminho: str) -> str:
    """
    PT-PT: Lê um ficheiro de `/proc` ou `/sys`, devolvendo "" se não der.

           Metade do inventário em Linux está nestes dois sistemas de ficheiros,
           e nenhum deles é garantido: `/sys/class/power_supply` não existe num
           servidor, e `/proc/pressure` não existe em kernels antigos.

    EN-UK: Reads a file from `/proc` or `/sys`, returning "" on failure.

           Half the inventory on Linux lives in those two filesystems, and
           neither is guaranteed.
    """
    try:
        with open(caminho, encoding="utf-8", errors="replace") as ficheiro:
            return ficheiro.read()
    except OSError:
        return ""


def e_root() -> bool:
    """
    PT-PT: Se estamos a correr como root.

           Interessa porque muda o que se consegue ler: o `dmidecode` precisa
           de root, e o `journalctl` sem root só mostra o que o utilizador tem
           permissão para ver — o que, num diagnóstico, é meia história.

    EN-UK: Whether we are running as root.

           It matters because it changes what can be read: `dmidecode` needs
           root, and `journalctl` without it only shows what the user may see —
           which, in a diagnostic, is half the story.
    """
    # PT-PT: O `geteuid` so existe em POSIX. O `getattr` mantem este modulo
    #        importavel e chamavel numa maquina de desenvolvimento que nao seja
    #        Linux, e e o que permite correr o `--cli` desta versao a partir de
    #        qualquer sitio para confirmar que a ligacao entre os modulos esta
    #        de pe. Numa maquina Linux — a unica onde isto e suposto correr a
    #        serio — o atributo existe sempre.
    # EN-UK: `geteuid` exists on POSIX only. The `getattr` keeps this module
    #        importable and callable on a non-Linux development machine, which
    #        is what allows running this version's `--cli` from anywhere to
    #        confirm the modules are wired together. On a Linux machine — the
    #        only place this is meant to run for real — the attribute is always
    #        there.
    obter = getattr(os, "geteuid", None)
    return obter() == 0 if obter else False


def no_grupo_systemd_journal() -> bool:
    """
    PT-PT: Se o utilizador pertence ao grupo que pode ler o diário completo.

           Sem root e sem este grupo, o `journalctl` mostra apenas as mensagens
           do próprio utilizador — e um diagnóstico feito sobre isso parece
           limpo mesmo numa máquina com problemas. Vale mais dizê-lo do que
           apresentar um relatório vazio como se fosse boa notícia.

    EN-UK: Whether the user belongs to the group that may read the full journal.

           Without root and without this group, `journalctl` shows only the
           user's own messages — and a diagnostic built on that looks clean even
           on a broken machine.
    """
    if e_root():
        return True
    try:
        import grp

        for nome in ("systemd-journal", "adm", "wheel"):
            try:
                grupo = grp.getgrnam(nome)
            except KeyError:
                continue
            if grupo.gr_gid in os.getgroups():
                return True
    except Exception:  # noqa: BLE001 - PT-PT: sem grp nao ha como saber
        log.debug("Não foi possível verificar os grupos", exc_info=True)
    return False


def abrir_ficheiro(caminho: str) -> Resultado:
    """
    PT-PT: Abre um ficheiro ou pasta no ambiente de trabalho.

           O `xdg-open` é o padrão, e é o que qualquer ambiente gráfico de Linux
           implementa. Numa sessão sem ecrã não existe, e o `Resultado` diz-o.

    EN-UK: Opens a file or folder in the desktop environment, via `xdg-open`.
    """
    return executar(["xdg-open", caminho], timeout=15)


@dataclass(slots=True)
class Ambiente:
    """
    PT-PT: O que se sabe sobre a máquina antes de começar a diagnosticar.

           É recolhido uma vez e passado adiante, para não haver vinte chamadas
           a perguntar a mesma coisa — e para o relatório poder dizer, à cabeça,
           em que condições foi produzido.

    EN-UK: What is known about the machine before diagnosing starts.

           Gathered once and passed along, so there are not twenty calls asking
           the same thing — and so the report can say up front under what
           conditions it was produced.
    """

    root: bool = False
    le_diario_completo: bool = False
    tem_systemd: bool = False
    ferramentas_em_falta: list[str] = field(default_factory=list)

    def limitacoes(self) -> list[str]:
        """
        PT-PT: O que este diagnóstico não vai conseguir ver, e porquê.

               Um relatório que não diz o que lhe faltou é pior do que nenhum:
               dá a impressão de ter olhado para tudo.

        EN-UK: What this diagnostic will not be able to see, and why.

               A report that does not say what it missed is worse than none: it
               gives the impression of having looked at everything.
        """
        avisos: list[str] = []

        if not self.tem_systemd:
            avisos.append(
                "Esta máquina não usa systemd: a análise de eventos e de serviços "
                "não está disponível. O resto do diagnóstico funciona."
            )
        elif not self.le_diario_completo:
            avisos.append(
                "Sem permissão para ler o diário completo: só aparecem as mensagens "
                "deste utilizador. Corra com sudo, ou junte o utilizador ao grupo "
                "'systemd-journal', para ver as do sistema."
            )

        if not self.root:
            avisos.append(
                "Sem privilégios de root: o inventário de hardware fica incompleto "
                "e o estado SMART dos discos não pode ser lido."
            )

        for ferramenta in self.ferramentas_em_falta:
            avisos.append(f"A ferramenta '{ferramenta}' não está instalada; a secção respectiva fica vazia.")

        return avisos


def detectar_ambiente() -> Ambiente:
    """
    PT-PT: Recolhe as condições em que este diagnóstico vai correr.
    EN-UK: Gathers the conditions this diagnostic will run under.
    """
    opcionais = ("smartctl", "dmidecode", "lsblk", "ss", "ip", "systemctl", "journalctl")
    return Ambiente(
        root=e_root(),
        le_diario_completo=no_grupo_systemd_journal(),
        tem_systemd=disponivel("systemctl") and os.path.isdir("/run/systemd/system"),
        ferramentas_em_falta=[nome for nome in opcionais if not disponivel(nome)],
    )
