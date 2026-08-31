#!/usr/bin/env python3
"""
PT-PT: Execucao de comandos externos em macOS.

       Quase todo o diagnostico depende de correr ferramentas do sistema e ler
       o que elas devolvem — e ler mal e a fonte mais comum de bugs silenciosos
       numa ferramenta destas.

       Quatro decisoes que valem mais do que o codigo que as implementa.

       **Nunca `shell=True`.** Os comandos vao como lista de argumentos. Uma
       ferramenta de diagnostico corre com privilegios e recebe nomes de
       dispositivos e de servicos que vem do sistema; passa-los por uma shell
       seria dar-lhes poder de execucao que nao precisam de ter.

       **O ambiente e forcado a C.** Um `LANG=pt_PT.UTF-8` faz o `diskutil` e o
       `system_profiler` traduzirem os cabecalhos, e um parser que procura
       "Verified" deixa de encontrar "Verificado".

       **Meia dozena de ferramentas do macOS so falam plist** — o
       `diskutil -plist`, o `defaults`, os `Info.plist` das aplicacoes. O plist
       nao e JSON e nao se interpreta como tal: tentar faze-lo devolve None e o
       modulo que chamou conclui, erradamente, que o comando nao respondeu. O
       `plistlib` da biblioteca padrao le as duas formas — XML e binaria — e e
       por ai que este modulo os le, sem pipes e sem ficheiros temporarios.

       **Um comando lento nao e um comando parado.** O `log show` de um Mac com
       um mes de historico demora minutos, e o `system_profiler
       SPApplicationsDataType` demora ainda mais. Os timeouts aqui sao mais
       generosos do que na versao de Linux de proposito, e o codigo que os usa
       limita sempre a janela em vez de esperar mais.

EN-UK: External command execution on macOS.

       Nearly all diagnostics depend on running system tools and reading what
       they return — and reading it wrongly is the commonest source of silent
       bugs in a tool like this.

       Four decisions worth more than the code implementing them.

       **Never `shell=True`.** Commands go as argument lists.

       **The environment is forced to C**, so `diskutil` and `system_profiler`
       do not translate their headers.

       **Half a dozen macOS tools speak only plist** — `diskutil -plist`,
       `defaults`, applications' `Info.plist`. A plist is not JSON and must not
       be parsed as one: trying returns None, and the calling module wrongly
       concludes the command did not answer. The standard library's `plistlib`
       reads both forms — XML and binary — and that is how this module reads
       them, with no pipes and no temporary files.

       **A slow command is not a stuck command.** `log show` on a Mac with a
       month of history takes minutes. The timeouts here are more generous than
       the Linux version's, deliberately, and the code using them always narrows
       the window rather than waiting longer.

Created by Redfox using Claude
"""

from __future__ import annotations

import json
import logging
import os
import plistlib
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any
from xml.parsers.expat import ExpatError

log = logging.getLogger(__name__)

# PT-PT: O ambiente com que todos os comandos correm. O `LC_ALL=C` garante
#        saidas em ingles e formatos numericos previsiveis.
# EN-UK: The environment every command runs with. `LC_ALL=C` guarantees English
#        output and predictable number formats.
AMBIENTE_NEUTRO = {"LC_ALL": "C", "LANG": "C", "LANGUAGE": "C"}

#: PT-PT: Timeout por omissao. E maior do que o da versao de Linux porque as
#:        ferramentas do macOS sao genuinamente mais lentas — o `diskutil list`
#:        acorda discos externos, o `log show` percorre um arquivo comprimido.
#: EN-UK: Default timeout. Larger than the Linux version's because macOS tools
#:        are genuinely slower — `diskutil list` spins up external disks and
#:        `log show` walks a compressed archive.
TIMEOUT_NORMAL = 90


@dataclass(slots=True)
class Resultado:
    """
    PT-PT: O resultado de um comando.

           `ausente` e o campo que distingue os dois tipos de falha. Um
           `smartctl` que devolve codigo 2 esta a dizer alguma coisa sobre o
           disco; um `smartctl` que nao existe nao esta a dizer nada sobre disco
           nenhum — esta a dizer que falta uma formula do Homebrew. Apresentar
           os dois como «erro ao ler o disco» seria mandar alguem procurar uma
           avaria que nao existe.

           `sem_permissao` e proprio do macOS e nao existe na versao de Linux.
           O TCC bloqueia leituras com «Operation not permitted» mesmo ao root,
           e essa mensagem, apresentada em bruto, manda o operador procurar um
           problema de permissoes de ficheiro que nao ha: o que falta e uma
           autorizacao nas Definicoes do Sistema.

    EN-UK: A command's result.

           `ausente` tells the two kinds of failure apart: a `smartctl`
           returning code 2 says something about the disk; a missing `smartctl`
           says a Homebrew formula is missing.

           `sem_permissao` is macOS-specific and has no Linux counterpart. TCC
           blocks reads with "Operation not permitted" even for root, and that
           message shown raw sends the operator hunting a file-permission
           problem that does not exist: what is missing is an authorisation in
           System Settings.
    """

    comando: str
    codigo: int
    saida: str = ""
    erro: str = ""
    ausente: bool = False
    expirou: bool = False
    sem_permissao: bool = False

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
               not.
        """
        if self.ok:
            return self.saida.strip() or "(sem saída)"
        return self.explicacao() or (self.erro or self.saida).strip()

    @property
    def linhas(self) -> list[str]:
        """PT-PT: A saída em linhas, sem vazias. / EN-UK: Output as lines, blanks dropped."""
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
        if self.sem_permissao:
            return (
                f"O sistema recusou o acesso a '{self.comando}'. Isto é o TCC, não são "
                "permissões de ficheiro: dê Acesso Total ao Disco ao Terminal em "
                "Definições do Sistema › Privacidade e Segurança."
            )
        if self.codigo != 0:
            detalhe = (self.erro or self.saida).strip().splitlines()
            return (
                f"'{self.comando}' terminou com código {self.codigo}. "
                f"{detalhe[0] if detalhe else ''}"
            ).strip()
        return ""


def disponivel(programa: str) -> bool:
    """
    PT-PT: Se um programa existe no PATH.

           Em macOS isto não é tão directo como parece: um processo lançado pelo
           Finder ou pelo `launchd` não herda o PATH da shell, e o Homebrew
           instala fora do PATH mínimo. Por isso os prefixos do Homebrew são
           procurados também.

    EN-UK: Whether a program exists on the PATH.

           On macOS this is less direct than it sounds: a process launched by
           Finder or `launchd` does not inherit the shell's PATH, and Homebrew
           installs outside the minimal PATH. Hence Homebrew's prefixes are
           searched too.

    :param programa:
        PT-PT: Nome do executável. / EN-UK: The executable's name.
    """
    if shutil.which(programa):
        return True
    from .platform_support import BREW_PREFIXES

    return any((prefixo / "bin" / programa).exists() for prefixo in BREW_PREFIXES)


def caminho_de(programa: str) -> str:
    """
    PT-PT: O caminho completo de um programa, incluindo os do Homebrew.

    EN-UK: A program's full path, Homebrew's included.

    :return:
        PT-PT: O caminho, ou o nome tal como veio se não for encontrado.
        EN-UK: The path, or the name as given when not found.
    """
    encontrado = shutil.which(programa)
    if encontrado:
        return encontrado

    from .platform_support import BREW_PREFIXES

    for prefixo in BREW_PREFIXES:
        candidato = prefixo / "bin" / programa
        if candidato.exists():
            return str(candidato)
    return programa


def executar(args: list[str], timeout: int = TIMEOUT_NORMAL) -> Resultado:
    """
    PT-PT: Corre um comando e devolve o que ele disse.

           Nunca levanta excepção por o comando ter falhado: uma ferramenta de
           diagnóstico que rebenta porque um dos vinte comandos não correu é
           inútil. O que falha vira um `Resultado` com a razão, e o módulo que
           chamou decide o que fazer.

    EN-UK: Runs a command and returns what it said. It never raises because the
           command failed.

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
    completo = [caminho_de(nome), *args[1:]]

    try:
        processo = subprocess.run(  # noqa: S603 - PT-PT: lista de argumentos, nunca shell
            completo,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=ambiente,
            check=False,
        )
    except subprocess.TimeoutExpired:
        log.warning("Expirou: %s", " ".join(args))
        return Resultado(comando=nome, codigo=-1, expirou=True)
    except PermissionError:
        return Resultado(comando=nome, codigo=-1, sem_permissao=True)
    except OSError as exc:
        log.debug("Falha ao correr %s: %s", nome, exc)
        return Resultado(comando=nome, codigo=-1, erro=str(exc))

    erro = processo.stderr or ""
    return Resultado(
        comando=nome,
        codigo=processo.returncode,
        saida=processo.stdout or "",
        erro=erro,
        # PT-PT: O TCC nao devolve um codigo de saida proprio; devolve esta
        #        frase. E feia de detectar assim, mas a alternativa e apresentar
        #        «operation not permitted» ao operador e deixa-lo procurar um
        #        chmod que nao resolve nada.
        # EN-UK: TCC returns no exit code of its own; it returns this sentence.
        #        Detecting it this way is ugly, but the alternative is showing
        #        "operation not permitted" and letting the operator hunt for a
        #        chmod that fixes nothing.
        sem_permissao="operation not permitted" in erro.lower(),
    )


def executar_json(args: list[str], timeout: int = TIMEOUT_NORMAL) -> Any:
    """
    PT-PT: Corre um comando que devolve JSON e interpreta-o.

           O `system_profiler -json`, o `log show --style json` e o `plutil
           -convert json` respondem todos assim, e é sempre melhor do que ler
           colunas: o `diskutil list` alinha as colunas ao nome do disco, e um
           parser posicional parte-se no primeiro disco externo com nome
           comprido.

    EN-UK: Runs a command returning JSON and parses it.

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


def linhas_json(args: list[str], timeout: int = TIMEOUT_NORMAL) -> list[dict]:
    """
    PT-PT: Corre um comando que devolve um objecto JSON por linha.

           É o formato do `log show --style ndjson`, e não é um documento JSON:
           são milhares de objectos independentes, um por linha. Tentar
           interpretar tudo de uma vez falha sempre.

    EN-UK: Runs a command returning one JSON object per line — `log show
           --style ndjson`'s format.

    :return:
        PT-PT: Um dicionário por linha válida; as inválidas são saltadas.
        EN-UK: One dictionary per valid line; invalid ones are skipped.
    """
    resultado = executar(args, timeout=timeout)
    registos: list[dict] = []

    for bruta in resultado.saida.splitlines():
        linha = bruta.strip().rstrip(",")
        if not linha or linha in {"[", "]"}:
            continue
        try:
            objecto = json.loads(linha)
        except json.JSONDecodeError:
            continue
        if isinstance(objecto, dict):
            registos.append(objecto)

    return registos


def executar_plist(args: list[str], timeout: int = TIMEOUT_NORMAL) -> dict:
    """
    PT-PT: Corre um comando que devolve um plist e interpreta-o.

           É o formato do `diskutil list -plist`, do `diskutil info -plist` e do
           `system_profiler -xml`. **Não é JSON**, e passá-lo por um leitor de
           JSON devolve nada — foi exactamente esse o erro que fazia o
           agrupamento de volumes por contentor desligar-se em silêncio e o
           relatório repetir o mesmo espaço livre quatro vezes.

    EN-UK: Runs a command returning a plist and parses it.

           It is `diskutil list -plist`'s format, and `system_profiler -xml`'s.
           **It is not JSON**, and passing it to a JSON parser returns nothing —
           precisely the bug that made volume-by-container grouping switch itself
           off silently and the report repeat the same free space four times.

    :return:
        PT-PT: O conteúdo, ou {} se não for legível.
        EN-UK: The contents, or {} when unreadable.
    """
    resultado = executar(args, timeout=timeout)
    if not resultado.saida.strip():
        return {}
    try:
        dados = plistlib.loads(resultado.saida.encode("utf-8"))
    except (plistlib.InvalidFileException, ValueError, ExpatError) as exc:
        log.debug("Saída de %s não é um plist: %s", resultado.comando, exc)
        return {}
    return dados if isinstance(dados, dict) else {}


def ler_plist(caminho: str) -> dict:
    """
    PT-PT: Lê um ficheiro plist, seja ele XML ou binário.

           Metade dos plists de um Mac estão em formato binário — os
           `Info.plist` das aplicações, por exemplo, quase sempre. O `plistlib`
           reconhece o formato pelos primeiros bytes e trata dos dois sem lhe
           dizerem qual é.

    EN-UK: Reads a plist file, XML or binary.

           Half a Mac's plists are binary — applications' `Info.plist` almost
           always. `plistlib` recognises the format from the first bytes and
           handles both without being told which.

    :param caminho:
        PT-PT: Caminho do ficheiro. / EN-UK: The file's path.
    :return:
        PT-PT: O conteúdo, ou {} se não for legível.
        EN-UK: The contents, or {} when unreadable.
    """
    try:
        with open(caminho, "rb") as ficheiro:
            dados = plistlib.load(ficheiro)
    except (OSError, plistlib.InvalidFileException, ValueError, ExpatError) as exc:
        log.debug("Plist ilegível em %s: %s", caminho, exc)
        return {}
    return dados if isinstance(dados, dict) else {}


def e_root() -> bool:
    """
    PT-PT: Se estamos a correr como root.

           Num Mac esta é **metade** da resposta à pergunta «consigo ler tudo?».
           A outra metade é o Acesso Total ao Disco, que é uma autorização
           separada, vive nas Definições do Sistema e que o `sudo` não dá.

    EN-UK: Whether we are running as root.

           On a Mac this is **half** the answer to "can I read everything?". The
           other half is Full Disk Access, a separate authorisation living in
           System Settings that `sudo` does not grant.
    """
    obter = getattr(os, "geteuid", None)
    return obter() == 0 if obter else False


def abrir_ficheiro(caminho: str) -> Resultado:
    """
    PT-PT: Abre um ficheiro ou pasta no Finder, pelo `open`.

           O `open` faz parte do macOS e respeita a aplicação por omissão do
           utilizador — um relatório HTML abre no navegador dele, e não num que
           esta ferramenta tenha escolhido.

    EN-UK: Opens a file or folder in Finder, via `open`. It ships with macOS and
           honours the user's default application.
    """
    return executar(["open", caminho], timeout=15)


@dataclass(slots=True)
class Ambiente:
    """
    PT-PT: O que se sabe sobre a máquina antes de começar a diagnosticar.

           É recolhido uma vez e passado adiante, para não haver vinte chamadas
           a perguntar a mesma coisa — e para o relatório poder dizer, à cabeça,
           em que condições foi produzido.

    EN-UK: What is known about the machine before diagnosing starts.
    """

    root: bool = False
    acesso_total_ao_disco: bool = False
    apple_silicon: bool = False
    sip: bool = True
    ferramentas_em_falta: list[str] = field(default_factory=list)

    def limitacoes(self) -> list[str]:
        """
        PT-PT: O que este diagnóstico não vai conseguir ver, e porquê.

               Um relatório que não diz o que lhe faltou é pior do que nenhum:
               dá a impressão de ter olhado para tudo. Em macOS isto é mais
               importante do que em qualquer outro sistema, porque o TCC esconde
               sem dar erro — o comando corre, devolve zero e mostra menos.

        EN-UK: What this diagnostic will not be able to see, and why.

               On macOS this matters more than anywhere else, because TCC hides
               without erroring — the command runs, returns zero and shows less.
        """
        avisos: list[str] = []

        if not self.acesso_total_ao_disco:
            avisos.append(
                "Sem Acesso Total ao Disco: os relatórios de paragem do sistema e "
                "parte do diário não são visíveis, e o sistema não dá erro ao "
                "escondê-los. Dê a permissão ao Terminal em Definições do Sistema › "
                "Privacidade e Segurança. O sudo não substitui isto."
            )

        if not self.root:
            avisos.append(
                "Sem privilégios de root: os serviços de sistema do launchd e parte do "
                "inventário de hardware ficam por ler."
            )

        if not self.sip:
            avisos.append(
                "A Protecção de Integridade do Sistema (SIP) está desactivada. Não "
                "afecta este diagnóstico, mas é uma máquina fora da configuração "
                "normal e vale a pena saber porquê."
            )

        for ferramenta in self.ferramentas_em_falta:
            avisos.append(
                f"A ferramenta '{ferramenta}' não está instalada; a secção respectiva "
                "fica vazia."
            )

        return avisos


def detectar_ambiente() -> Ambiente:
    """
    PT-PT: Recolhe as condições em que este diagnóstico vai correr.
    EN-UK: Gathers the conditions this diagnostic will run under.
    """
    from . import platform_support

    opcionais = ("smartctl",)
    return Ambiente(
        root=e_root(),
        acesso_total_ao_disco=platform_support.full_disk_access(),
        apple_silicon=platform_support.apple_silicon(),
        sip=platform_support.sip_activo(),
        ferramentas_em_falta=[nome for nome in opcionais if not disponivel(nome)],
    )
