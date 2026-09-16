"""
PT-PT: Execução de comandos externos (cmd.exe e PowerShell).

       Este módulo existe porque quase todo o diagnóstico depende de correr
       ferramentas do Windows e ler o que elas devolvem — e ler mal e a fonte
       mais comum de bugs silenciosos numa ferramenta destas.

EN-UK: External command execution (cmd.exe and PowerShell).

       This module exists because nearly all diagnostics depend on running
       Windows tools and reading what they return — and reading it wrongly is
       the commonest source of silent bugs in a tool like this.

Created by Redfox using Claude
"""

from __future__ import annotations

import ctypes
import json
import logging
import os
import subprocess
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)

# PT-PT: Impede que uma janela de consola pisque no ecrã a cada comando.
# EN-UK: Stops a console window flashing on screen for every command.
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

IS_WINDOWS = os.name == "nt"


@dataclass(slots=True)
class Resultado:
    """
    PT-PT: Resultado de um comando. A versão anterior devolvia apenas uma
           string e engolia todas as excepções, o que significava que uma falha
           de permissões e um comando que devolve texto vazio eram
           indistinguíveis. Aqui ficam separados: `ok` diz se correu, `erro`
           diz porque não.
    EN-UK: Result of a command. The previous version returned only a string and
           swallowed every exception, which meant a permissions failure and a
           command returning empty text were indistinguishable. Here they are
           separate: `ok` says whether it ran, `erro` says why not.
    """

    saida: str = ""
    erro: str = ""
    codigo: int = 0
    ok: bool = True

    @property
    def texto(self) -> str:
        """PT-PT: Saída útil, ou a mensagem de erro se não houver saída.
        EN-UK: Useful output, or the error message when there is none."""
        if self.saida:
            return self.saida
        return self.erro


def _codepage_oem() -> str:
    """
    PT-PT: Descobre a codificação que a consola do Windows usa realmente.

           A v1.0 assumia cp850 fixo, com o comentário «a consola PT usa
           cp850». Nem sempre: depende da versão do Windows, da região e de a
           opção «Beta: usar UTF-8 para suporte de idioma mundial» estar ou não
           ligada — nesse caso e cp65001. Assumir errado não rebenta nada, só
           enche os relatórios de acentos trocados, que é o tipo de bug que
           ninguém reporta e toda a gente nota.

    EN-UK: Works out which encoding the Windows console actually uses. Version
           1.0 assumed a fixed cp850; that depends on the Windows version,
           region and whether the UTF-8 beta option is enabled.
    """
    if not IS_WINDOWS:
        return "utf-8"
    try:
        codigo = ctypes.windll.kernel32.GetOEMCP()  # type: ignore[attr-defined]
        return f"cp{codigo}" if codigo != 65001 else "utf-8"
    except Exception:  # noqa: BLE001 — qualquer falha aqui cai no valor seguro
        return "cp850"


# PT-PT: Calculado uma vez; não muda durante a sessão.
# EN-UK: Computed once; does not change during the session.
CODEPAGE = _codepage_oem()


def executar(args: list[str], timeout: int = 60) -> Resultado:
    """
    PT-PT: Corre um comando de sistema e devolve a saída descodificada.
    EN-UK: Runs a system command and returns the decoded output.
    """
    log.debug("A executar: %s", " ".join(args))
    try:
        proc = subprocess.run(  # noqa: S603 — argumentos vem do codigo, nunca do utilizador
            args,
            capture_output=True,
            timeout=timeout,
            creationflags=CREATE_NO_WINDOW,
            check=False,
        )
    except FileNotFoundError:
        return Resultado(erro=f"Comando não encontrado: {args[0]}", ok=False, codigo=-1)
    except subprocess.TimeoutExpired:
        return Resultado(erro=f"O comando excedeu {timeout}s.", ok=False, codigo=-1)
    except OSError as exc:
        return Resultado(erro=f"Falha ao executar: {exc}", ok=False, codigo=-1)

    saida = proc.stdout.decode(CODEPAGE, errors="replace").strip()
    erro = proc.stderr.decode(CODEPAGE, errors="replace").strip()
    return Resultado(saida=saida, erro=erro, codigo=proc.returncode, ok=proc.returncode == 0)


def powershell(comando: str, timeout: int = 90) -> Resultado:
    """
    PT-PT: Corre um comando PowerShell e devolve a saída em UTF-8.

           O prefixo força a codificação de saída para UTF-8 antes de correr o
           comando, o que torna esta chamada independente da codepage da
           consola — ao contrário do `executar` acima, que tem de a adivinhar.

    EN-UK: Runs a PowerShell command and returns UTF-8 output. The prefix forces
           the output encoding to UTF-8, making this call independent of the
           console codepage.
    """
    prefixo = "$OutputEncoding=[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; "
    log.debug("PowerShell: %s", comando[:160])
    try:
        proc = subprocess.run(  # noqa: S603
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                prefixo + comando,
            ],
            capture_output=True,
            timeout=timeout,
            creationflags=CREATE_NO_WINDOW,
            check=False,
        )
    except FileNotFoundError:
        return Resultado(erro="PowerShell não encontrado nesta máquina.", ok=False, codigo=-1)
    except subprocess.TimeoutExpired:
        return Resultado(erro=f"O comando PowerShell excedeu {timeout}s.", ok=False, codigo=-1)
    except OSError as exc:
        return Resultado(erro=f"Falha ao executar PowerShell: {exc}", ok=False, codigo=-1)

    saida = proc.stdout.decode("utf-8", errors="replace").strip()
    erro = proc.stderr.decode("utf-8", errors="replace").strip()
    if erro:
        log.debug("PowerShell devolveu stderr: %s", erro[:400])
    return Resultado(saida=saida, erro=erro, codigo=proc.returncode, ok=proc.returncode == 0)


def normalizar_json(dados: Any) -> list[dict]:
    """
    PT-PT: Transforma o que o ConvertTo-Json devolveu numa lista de dicionários.

           São três casos, e a v1.0 só tratava dois. Uma lista fica como esta;
           um objecto único e embrulhado numa lista — o PowerShell desenrola
           arrays de um elemento e devolve o objecto directamente. O terceiro
           caso e o que faltava: quando o comando devolve valores simples (uma
           lista de strings, tipicamente `Select-Object -ExpandProperty`), o
           JSON e uma string ou um número. Era exactamente o que acontecia com
           um único servidor DNS configurado, e o resultado era a lista de DNS
           aparecer vazia no diagnóstico sem qualquer erro.

    EN-UK: Turns whatever ConvertTo-Json returned into a list of dictionaries.
           Three cases; v1.0 handled only two. The missing one was scalar
           output — which is what a single configured DNS server produced,
           silently emptying the DNS list in the diagnostics.
    """
    if dados is None:
        return []
    if isinstance(dados, dict):
        return [dados]
    if isinstance(dados, list):
        return [d if isinstance(d, dict) else {"valor": d} for d in dados]
    return [{"valor": dados}]


def powershell_json(comando: str, timeout: int = 90) -> list[dict]:
    """
    PT-PT: Corre PowerShell que termina em ConvertTo-Json e devolve dicionários.
    EN-UK: Runs PowerShell ending in ConvertTo-Json and returns dictionaries.
    """
    res = powershell(comando, timeout)
    if not res.saida:
        return []
    try:
        return normalizar_json(json.loads(res.saida))
    except json.JSONDecodeError:
        log.warning("Resposta do PowerShell não é JSON válido: %s", res.saida[:200])
        return []


def valores_json(comando: str, timeout: int = 90) -> list[str]:
    """
    PT-PT: Igual ao anterior, mas para comandos que devolvem valores simples
           (uma lista de endereços, por exemplo).
    EN-UK: As above, but for commands returning plain scalars.
    """
    saida = []
    for item in powershell_json(comando, timeout):
        valor = item.get("valor")
        if isinstance(valor, str) and valor.strip():
            saida.append(valor.strip())
    return saida


def e_administrador() -> bool:
    """
    PT-PT: Diz se o processo esta elevado.

           Importa saber: sem elevação, o log Security fica inacessível, o SMART
           não devolve nada e os serviços não arrancam. A v1.0 não verificava, e
           esses módulos limitavam-se a devolver vazio — o operador ficava a
           pensar que a máquina estava limpa quando na verdade não tinha lido
           nada.

    EN-UK: Reports whether the process is elevated. Without elevation the
           Security log is inaccessible, SMART returns nothing and services will
           not start. v1.0 did not check, and those modules simply returned
           empty — leaving the operator thinking the machine was clean.
    """
    if not IS_WINDOWS:
        return os.geteuid() == 0 if hasattr(os, "geteuid") else False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        return False


def abrir_ficheiro(caminho: str) -> Resultado:
    """
    PT-PT: Abre um ficheiro ou consola do Windows com a aplicação associada.
    EN-UK: Opens a file or Windows console with its associated application.
    """
    if not IS_WINDOWS:
        return Resultado(erro="Só disponível em Windows.", ok=False)
    try:
        os.startfile(caminho)  # type: ignore[attr-defined]  # noqa: S606
        return Resultado(saida=f"{caminho} aberto.")
    except OSError as exc:
        return Resultado(erro=f"Não foi possível abrir {caminho}: {exc}", ok=False)


@dataclass(slots=True)
class Ambiente:
    """
    PT-PT: Retrato do ambiente onde a aplicação esta a correr, para os módulos
           poderem explicar o que não vão conseguir fazer em vez de falharem em
           silêncio.
    EN-UK: Snapshot of the running environment, so modules can explain what they
           will not be able to do instead of failing silently.
    """

    windows: bool = field(default_factory=lambda: IS_WINDOWS)
    administrador: bool = field(default_factory=e_administrador)
    codepage: str = field(default_factory=lambda: CODEPAGE)

    def limitacoes(self) -> list[str]:
        """PT-PT: Lista o que não vai funcionar e porque.
        EN-UK: Lists what will not work, and why."""
        avisos = []
        if not self.windows:
            avisos.append(
                "Não está a correr em Windows: os módulos de eventos, discos, "
                "serviços e inventário não têm dados para ler."
            )
        elif not self.administrador:
            avisos.append(
                "Sem privilégios de administrador: o log de Segurança, o estado "
                "SMART dos discos e o arranque de serviços não vão funcionar."
            )
        return avisos
