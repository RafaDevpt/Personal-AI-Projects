#!/usr/bin/env python3
"""
PT-PT: Particularidades do Windows.

       Esta é a versão para Windows da VMware Fleet Console. Não há aqui nenhuma
       ramificação por sistema operativo: o código sabe onde está e diz apenas o
       que é verdade nesta máquina. As outras duas versões vivem nas pastas ao
       lado, cada uma com o seu equivalente deste ficheiro.

       O que existe aqui e nas outras não existe são três coisas que só em
       Windows dão problemas:

       **O `python.exe` da Microsoft Store.** Uma instalação limpa do Windows
       traz um `python.exe` no PATH que não é o Python: é um atalho que abre a
       loja. Quem o corre vê a Store abrir-se e não percebe porquê. Detecta-se
       pelo caminho (`WindowsApps`) e diz-se o que é, em vez de deixar alguém
       concluir que o programa está avariado.

       **O terminal.** O `cmd.exe` clássico não desenha uma TUI decentemente —
       tem 16 cores, não tem cor verdadeira, e a página de código por omissão
       (850 em Portugal) transforma os caracteres de desenho em símbolos
       aleatórios. O Windows Terminal e o PowerShell moderno tratam disto, e a
       aplicação diz qual está a ser usado antes de tentar desenhar.

       **A página de código.** É a causa número um de "sai tudo aos quadradinhos"
       em Windows. A 65001 é a UTF-8, e é a única em que os caracteres de
       desenho e os acentos saem certos.

EN-UK: Windows specifics.

       This is the Windows version. There is no operating-system branching here:
       the code knows where it is and states only what is true on this machine.

       Three things go wrong only on Windows. The Microsoft Store `python.exe` is
       a shim that opens the Store rather than running Python, and whoever runs
       it sees the Store open and does not understand why — it is detected by its
       path and named. The classic `cmd.exe` does not draw a TUI decently. And
       the code page is the number-one cause of "it all comes out as boxes":
       65001 is UTF-8, and the only one where the drawing characters and the
       accents come out right.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

_log = logging.getLogger(__name__)

SYSTEM_NAME = "Windows"


@dataclass(frozen=True)
class Requirement:
    """
    PT-PT: Um requisito de sistema e o seu estado.

           `essential` separa o que impede a aplicação de funcionar do que
           apenas desliga uma funcionalidade. Apresentar os dois com a mesma
           gravidade levaria alguém a instalar coisas de que não precisa — e,
           pior, a desistir por causa de um aviso que não importava.

    EN-UK: A system requirement and its state. `essential` separates what stops
           the application working from what merely switches a feature off.
    """

    name: str
    present: bool
    essential: bool
    detail: str
    command: str = ""

    def __str__(self) -> str:
        estado = "OK" if self.present else ("EM FALTA" if self.essential else "em falta (opcional)")
        linha = f"{self.name}: {estado}"
        if self.detail:
            linha += f"\n    {self.detail}"
        if not self.present and self.command:
            linha += f"\n    {self.command}"
        return linha


class Terminal(str, Enum):
    """
    PT-PT: Em que terminal isto está a correr.

           Decide se a interface vale a pena. O `cmd.exe` clássico consegue
           desenhá-la, mas com 16 cores e uma página de código que costuma estar
           errada — funciona, e fica feio. O Windows Terminal não tem nenhum dos
           dois problemas.

    EN-UK: Which terminal this is running in. It decides whether the interface is
           worth drawing. The classic `cmd.exe` can draw it, with sixteen colours
           and a code page that is usually wrong — it works and it looks bad.
    """

    WINDOWS_TERMINAL = "Windows Terminal"
    CONHOST = "Consola clássica (cmd.exe)"
    VSCODE = "Terminal do VS Code"
    UNKNOWN = "desconhecido"


def detect_terminal(environment: dict[str, str] | None = None) -> Terminal:
    """
    PT-PT: Qual é o terminal.

           O `WT_SESSION` é posto pelo Windows Terminal e é a forma documentada
           de o reconhecer. O `TERM_PROGRAM` cobre o do VS Code, que é o segundo
           sítio mais provável de alguém correr isto.

    EN-UK: Which terminal this is. `WT_SESSION` is set by Windows Terminal and is
           the documented way to recognise it. `TERM_PROGRAM` covers VS Code's,
           the second most likely place somebody runs this.

       Um ambiente vazio devolve `UNKNOWN` e nao `CONHOST`: em Windows a
       `ComSpec` esta sempre definida, portanto a sua ausencia nao significa
       "consola classica", significa que nao se esta a olhar para um ambiente
       de Windows verdadeiro. Adivinhar a consola classica ai daria um
       diagnostico com um aviso sobre um terminal que ninguem esta a usar.

    EN-UK (cont.): An empty environment returns `UNKNOWN`, not `CONHOST`: on
       Windows `ComSpec` is always set, so its absence does not mean "classic
       console", it means this is not a real Windows environment. Guessing
       CONHOST there would produce a diagnostic warning about a terminal nobody
       is using.

    >>> detect_terminal({"WT_SESSION": "abc"}) is Terminal.WINDOWS_TERMINAL
    True
    >>> detect_terminal({}) is Terminal.UNKNOWN
    True
    """
    ambiente = os.environ if environment is None else environment
    if ambiente.get("WT_SESSION"):
        return Terminal.WINDOWS_TERMINAL
    if ambiente.get("TERM_PROGRAM", "").lower() == "vscode":
        return Terminal.VSCODE
    if ambiente.get("SESSIONNAME") or ambiente.get("ComSpec"):
        return Terminal.CONHOST
    return Terminal.UNKNOWN


def is_store_python(executable: str | None = None) -> bool:
    """
    PT-PT: Se este Python é o atalho da Microsoft Store.

           Uma instalação limpa do Windows traz um `python.exe` no PATH que abre
           a loja em vez de correr Python. Quem o corre vê a Store abrir-se e não
           percebe o que aconteceu. Reconhece-se pelo caminho.

    EN-UK: Whether this Python is the Microsoft Store shim. A clean Windows
           carries a `python.exe` on the PATH that opens the Store instead of
           running Python. It is recognised by its path.

    >>> is_store_python(r"C:\\Users\\x\\AppData\\Local\\Microsoft\\WindowsApps\\python.exe")
    True
    >>> is_store_python(r"C:\\Python312\\python.exe")
    False
    """
    caminho = (executable if executable is not None else sys.executable).replace("/", "\\").lower()
    return "\\microsoft\\windowsapps\\" in caminho


def code_page() -> int:
    """
    PT-PT: A página de código activa da consola.

           A 65001 é a UTF-8. A 850 e a 1252 são as de omissão em Portugal, e são
           a causa número um de "sai tudo aos quadradinhos". Devolve 0 quando não
           se conseguiu saber, que é diferente de estar errada.

    EN-UK: The console's active code page. 65001 is UTF-8; 850 and 1252 are the
           usual defaults here and the number-one cause of box characters.
           Returns 0 when it could not be determined, which is different from
           being wrong.
    """
    try:
        saida = subprocess.run(  # noqa: S603
            ["chcp.com"], capture_output=True, text=True, timeout=5, check=False
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return 0
    digitos = "".join(c for c in saida if c.isdigit())
    try:
        return int(digitos)
    except ValueError:
        return 0


def app_data_dir(app_name: str) -> Path:
    """
    PT-PT: A pasta de dados, na convenção do Windows: `%APPDATA%`.

           Sem a variável, cai-se em `~/AppData/Roaming`, que é o que ela vale.
           A pasta itinerante e não a local de propósito: as definições e as
           impressões digitais dos certificados devem seguir o utilizador para
           outra máquina do domínio.

    EN-UK: The data folder, in the Windows convention: `%APPDATA%`. Roaming and
           not local on purpose — the settings and certificate fingerprints
           should follow the user to another machine on the domain.
    """
    base = os.environ.get("APPDATA", "")
    raiz = Path(base) if base else Path.home() / "AppData" / "Roaming"
    return raiz / app_name


def terminal_is_capable() -> bool:
    """
    PT-PT: Se este terminal aguenta a interface.

           A saída tem de ser um terminal (e não um `> ficheiro.txt`) e tem de
           haver largura. O `cmd.exe` clássico passa: fica feio, mas funciona, e
           recusar desenhar seria pior do que desenhar mal.

    EN-UK: Whether this terminal can carry the interface. Output has to be a
           terminal and there has to be width. The classic `cmd.exe` passes: it
           looks bad but works, and refusing to draw would be worse than drawing
           badly.
    """
    if not sys.stdout.isatty():
        return False
    return terminal_size()[0] >= 60


def terminal_size() -> tuple[int, int]:
    """
    PT-PT: Colunas e linhas, com omissões de 80x24.
    EN-UK: Columns and rows, defaulting to 80x24.
    """
    try:
        tamanho = shutil.get_terminal_size(fallback=(80, 24))
        return tamanho.columns, tamanho.lines
    except OSError:
        return 80, 24


def unicode_is_safe() -> bool:
    """
    PT-PT: Se dá para desenhar caixas sem sair uma sopa de caracteres.

           Verifica-se a codificação da saída, e não só a página de código: o
           Python moderno em Windows usa UTF-8 na saída mesmo com a consola numa
           página antiga, e nesse caso os caracteres saem bem.

    EN-UK: Whether box-drawing will render. The output encoding is checked rather
           than only the code page: modern Python on Windows uses UTF-8 on output
           even with the console on an old code page, and then the characters do
           come out right.
    """
    codificacao = (getattr(sys.stdout, "encoding", "") or "").lower().replace("-", "")
    return "utf8" in codificacao or code_page() == 65001


def python_is_recent() -> bool:
    """PT-PT: Se a versão do Python chega. / EN-UK: Whether the Python is recent enough."""
    return sys.version_info >= (3, 10)


def check_requirements() -> list[Requirement]:
    """
    PT-PT: O estado desta máquina para correr a aplicação.

           É o que sai em `--diagnostico`, e é a primeira coisa a pedir a alguém
           que diz que "não abre".

    EN-UK: This machine's state for running the application. It is what
           `--diagnostico` prints, and the first thing to ask for from somebody
           saying "it does not open".
    """
    requisitos: list[Requirement] = [
        Requirement(
            name="Python",
            present=python_is_recent(),
            essential=True,
            detail=f"encontrado {platform.python_version()}, é preciso 3.10 ou superior",
            command="instale de python.org e marque 'Add Python to PATH'",
        ),
        Requirement(
            name="Origem do Python",
            present=not is_store_python(),
            essential=True,
            detail=(
                "atalho da Microsoft Store — abre a loja em vez de correr Python"
                if is_store_python()
                else sys.executable
            ),
            command=(
                "instale de python.org, e em Definições > Aplicações > Aliases de execução "
                "desligue os do python.exe"
            ),
        ),
    ]

    try:
        import pyVmomi  # noqa: F401,PLC0415

        tem_pyvmomi = True
    except ImportError:
        tem_pyvmomi = False

    requisitos.append(
        Requirement(
            name="pyVmomi",
            present=tem_pyvmomi,
            essential=True,
            detail="a biblioteca da VMware: sem ela não há ligação nenhuma ao vSphere",
            command="pip install -r requirements.txt",
        )
    )

    try:
        import textual  # noqa: F401,PLC0415

        tem_textual = True
    except ImportError:
        tem_textual = False

    requisitos.append(
        Requirement(
            name="Textual",
            present=tem_textual,
            essential=False,
            detail="a interface de texto; sem ela resta o modo de linha de comandos",
            command="pip install -r requirements.txt",
        )
    )

    terminal = detect_terminal()
    colunas, linhas = terminal_size()
    requisitos.append(
        Requirement(
            name="Terminal",
            present=terminal is not Terminal.CONHOST and terminal_is_capable(),
            essential=False,
            detail=f"{terminal.value}, {colunas}x{linhas}",
            command=(
                "a consola clássica desenha a interface com 16 cores; "
                "o Windows Terminal fica bastante melhor"
            ),
        )
    )

    pagina = code_page()
    requisitos.append(
        Requirement(
            name="Codificação",
            present=unicode_is_safe(),
            essential=False,
            detail=f"página de código {pagina or 'desconhecida'}, stdout em "
            f"{getattr(sys.stdout, 'encoding', '(desconhecida)')}",
            command="chcp 65001   (põe a consola em UTF-8 nesta sessão)",
        )
    )

    return requisitos


def diagnostic_report() -> str:
    """
    PT-PT: O relatório de diagnóstico em texto.
    EN-UK: The diagnostic report as text.
    """
    linhas = [
        "VMware Fleet Console — diagnóstico",
        f"Sistema: {SYSTEM_NAME} {platform.release()} ({platform.version()})",
        f"Python:  {platform.python_version()} em {sys.executable}",
        f"Dados:   {app_data_dir('VMwareFleetConsole')}",
        "",
    ]
    linhas.extend(str(r) for r in check_requirements())
    em_falta = [r for r in check_requirements() if not r.present and r.essential]
    linhas.append("")
    linhas.append(
        "Falta o essencial — a aplicação não arranca assim."
        if em_falta
        else "Está tudo o que é essencial."
    )
    return "\n".join(linhas)


def missing_essentials() -> list[Requirement]:
    """PT-PT: Só o que impede. / EN-UK: Only what blocks."""
    return [r for r in check_requirements() if not r.present and r.essential]
