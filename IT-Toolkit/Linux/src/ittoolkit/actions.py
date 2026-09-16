#!/usr/bin/env python3
"""
PT-PT: Ferramentas rápidas — acções pontuais de manutenção.

       Regra do módulo: nada aqui apaga dados do utilizador, e tudo o que tem
       impacto declara-o na sua descrição para a interface poder pedir
       confirmação.

       Duas coisas são específicas do Linux e moldaram este ficheiro:

       1. **Não há um `cmd /c start`.** Para abrir uma consola própria é preciso
          um emulador de terminal, e não há nenhum que exista em todo o lado: uma
          máquina com GNOME tem `gnome-terminal`, uma com KDE tem `konsole`, um
          servidor sem ambiente gráfico não tem nenhum. A lista `TERMINAIS` e
          percorrida por ordem e, se não houver nenhum, a acção diz o comando
          para o operador o correr onde quiser — que é melhor do que falhar em
          silêncio.

       2. **O `/tmp` e partilhado.** Em Windows, a pasta TEMP e do utilizador e
          limpa-la é seguro. Em Linux o `/tmp` e de toda a gente, e tem o sticky
          bit precisamente para impedir que um utilizador apague ficheiros de
          outro. Esta limpeza toca apenas no que pertence a quem esta a correr a
          aplicação, e na cache pessoal — nunca no `/tmp` inteiro.

EN-UK: Quick tools — one-off maintenance actions.

       Module rule: nothing here deletes user data, and anything with impact
       declares it so the interface can ask for confirmation.

       Two things are Linux-specific and shaped this file:

       1. **There is no `cmd /c start`.** Opening a console of its own needs a
          terminal emulator, and none exists everywhere: a GNOME machine has
          `gnome-terminal`, a KDE one `konsole`, a headless server neither. The
          `TERMINAIS` list is walked in order and, when none is present, the
          action states the command for the operator to run wherever they like —
          better than failing silently.

       2. **`/tmp` is shared.** On Windows the TEMP folder belongs to the user
          and clearing it is safe. On Linux `/tmp` belongs to everybody, and has
          the sticky bit precisely to stop one user deleting another's files.
          This cleanup touches only what belongs to whoever is running the
          application, plus their own cache — never the whole of `/tmp`.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .shell import Resultado, abrir_ficheiro, disponivel, executar

log = logging.getLogger(__name__)

#: PT-PT: Emuladores de terminal, por ordem de preferência. O
#:        `x-terminal-emulator` vem primeiro porque e o mecanismo das famílias
#:        Debian para dizer «o terminal que este utilizador escolheu».
#: EN-UK: Terminal emulators, in order of preference. `x-terminal-emulator`
#:        comes first because it is the Debian families' way of saying "the
#:        terminal this user chose".
TERMINAIS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("x-terminal-emulator", ("-e",)),
    ("gnome-terminal", ("--",)),
    ("konsole", ("-e",)),
    ("xfce4-terminal", ("-e",)),
    ("mate-terminal", ("-e",)),
    ("tilix", ("-e",)),
    ("alacritty", ("-e",)),
    ("kitty", ()),
    ("xterm", ("-e",)),
)


@dataclass(frozen=True, slots=True)
class Accao:
    """
    PT-PT: Descrição de uma acção para a interface construir os botões sem
           saber nada sobre o que cada uma faz.
    EN-UK: Description of an action, so the interface can build buttons without
           knowing anything about what each one does.
    """

    chave: str
    etiqueta: str
    descricao: str
    #: PT-PT: True obriga a interface a confirmar antes de executar.
    #: EN-UK: True forces the interface to confirm before running.
    confirmar: bool = False
    #: PT-PT: True significa que abre uma consola própria e não devolve saída.
    #: EN-UK: True means it opens its own console and returns no output.
    consola: bool = False
    #: PT-PT: True significa que só funciona como root.
    #: EN-UK: True means it only works as root.
    root: bool = False


ACCOES: tuple[Accao, ...] = (
    Accao("ip_config", "Ver configuração IP", "Mostra os endereços, as rotas e o DNS."),
    Accao("flush_dns", "Limpar cache DNS", "Esvazia a cache do systemd-resolved."),
    Accao(
        "renovar_ip",
        "Renovar endereço IP",
        "Volta a aplicar a configuração da ligação. A ligação cai por alguns segundos.",
        confirmar=True,
        root=True,
    ),
    Accao(
        "reiniciar_cups",
        "Reiniciar a impressão",
        "Para e volta a arrancar o CUPS. Os trabalhos em fila perdem-se.",
        confirmar=True,
        root=True,
    ),
    Accao(
        "limpar_temp",
        "Limpar temporários e cache",
        "Apaga os temporários deste utilizador e a cache pessoal. Não toca no /tmp dos outros.",
        confirmar=True,
    ),
    Accao(
        "limpar_diario",
        "Reduzir o diário",
        "Apaga as entradas do diário com mais de 7 dias. Liberta espaço em /var/log.",
        confirmar=True,
        root=True,
    ),
    Accao(
        "limpar_pacotes",
        "Limpar cache de pacotes",
        "Apaga os pacotes descarregados que já foram instalados.",
        confirmar=True,
        root=True,
    ),
    Accao("sessoes", "Sessões abertas", "Lista as sessões de utilizador na máquina."),
    Accao("montagens", "Sistemas de ficheiros", "Mostra o que está montado e onde."),
    Accao("falhadas", "Unidades falhadas", "Lista as unidades do systemd em estado failed."),
    Accao("hora", "Estado da hora", "Mostra a sincronização horária e o fuso configurado."),
    Accao(
        "diario_seguir",
        "Seguir o diário",
        "Abre uma consola com o diário em tempo real.",
        consola=True,
    ),
    Accao(
        "processos",
        "Monitor de processos",
        "Abre uma consola com o top.",
        consola=True,
    ),
)

# PT-PT: Ferramentas gráficas de gestão, para não andar a procura-las no menu.
#        Ao contrário das consolas MMC do Windows, estas podem não estar
#        instaladas — a interface deve verificar com `ferramenta_disponivel`
#        antes de mostrar o botão.
# EN-UK: Graphical management tools, so nobody hunts for them in the menu.
#        Unlike Windows MMC consoles these may not be installed — the interface
#        should check with `ferramenta_disponivel` before showing the button.
FERRAMENTAS: tuple[tuple[str, str], ...] = (
    ("Discos", "gnome-disks"),
    ("Monitor do Sistema", "gnome-system-monitor"),
    ("Ligações de Rede", "nm-connection-editor"),
    ("Registos do Sistema", "gnome-logs"),
    ("Utilizadores", "gnome-control-center"),
    ("Gestor de Ficheiros", "xdg-open"),
)


def ferramenta_disponivel(comando: str) -> bool:
    """PT-PT: Se a ferramenta existe. / EN-UK: Whether the tool exists."""
    return disponivel(comando)


def _abrir_consola(comando: list[str]) -> Resultado:
    """
    PT-PT: Lança um comando numa consola própria, sem esperar por ele.

           Ver o cabeçalho do módulo para o porque de haver uma lista de
           terminais em vez de um só.

    EN-UK: Launches a command in its own console, without waiting for it. See
           the module header for why there is a list of terminals rather than one.
    """
    for terminal, prefixo in TERMINAIS:
        if not disponivel(terminal):
            continue
        try:
            subprocess.Popen(  # noqa: S603 — comando fixo, nunca vem do utilizador
                [terminal, *prefixo, *comando],
                start_new_session=True,
            )
        except OSError as exc:
            log.debug("Terminal %s falhou: %s", terminal, exc)
            continue
        return Resultado(
            comando=terminal,
            codigo=0,
            saida="Abriu numa janela separada. Acompanhe o progresso por lá.",
        )

    return Resultado(
        comando="terminal",
        codigo=1,
        erro=(
            "Não há nenhum emulador de terminal instalado nesta máquina. "
            "Corra à mão: " + " ".join(comando)
        ),
    )


def limpar_temp() -> Resultado:
    """
    PT-PT: Limpa os temporários deste utilizador e a cache pessoal.

           Conta o que apagou e o que não conseguiu. Ficheiros em uso, ou de
           outro utilizador, não são apagáveis e isso é normal, não um erro — a
           v1.0 lançava a excepção do primeiro ficheiro bloqueado e desistia do
           resto, o que na prática significava que quase nunca limpava nada.

           **Só toca no que pertence a quem esta a correr a aplicação.** O `/tmp`
           de um Linux tem ficheiros de todos os utilizadores e de vários
           serviços; apagar o que é de outro não só falha por causa do sticky
           bit como, se corresse como root, partia sessões alheias.

    EN-UK: Clears this user's temporary files and personal cache.

           It counts what it removed and what it could not. Files in use, or
           belonging to another user, are not deletable and that is normal, not
           an error.

           **It touches only what belongs to whoever is running the
           application.** A Linux `/tmp` holds files from every user and several
           services; deleting another's not only fails because of the sticky bit
           but, running as root, would break other people's sessions.
    """
    meu_uid = os.getuid() if hasattr(os, "getuid") else -1
    cache = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    pastas = [Path(tempfile.gettempdir()), cache]

    apagados = 0
    bloqueados = 0
    alheios = 0
    libertado = 0

    for pasta in pastas:
        if not pasta.is_dir():
            continue
        try:
            itens = list(pasta.iterdir())
        except (OSError, PermissionError):
            continue

        for item in itens:
            try:
                if meu_uid >= 0 and item.lstat().st_uid != meu_uid:
                    alheios += 1
                    continue
                if item.is_file() or item.is_symlink():
                    tamanho = item.stat().st_size
                    item.unlink()
                    apagados += 1
                    libertado += tamanho
                elif item.is_dir():
                    tamanho = sum(f.stat().st_size for f in item.rglob("*") if f.is_file())
                    shutil.rmtree(item)
                    apagados += 1
                    libertado += tamanho
            except (OSError, PermissionError):
                bloqueados += 1

    return Resultado(
        comando="limpar_temp",
        codigo=0,
        saida=(
            f"Apagados {apagados} item(ns), {libertado / 1024**2:.0f} MB libertados.\n"
            f"{bloqueados} em uso, deixados como estavam.\n"
            f"{alheios} de outros utilizadores, não tocados.\n"
            f"Pastas: {', '.join(str(p) for p in pastas)}"
        ),
    )


def _limpar_pacotes() -> Resultado:
    """
    PT-PT: Limpa a cache de pacotes descarregados, conforme o gestor.

           O comando muda com a distribuição; a escolha vem do
           `platform_support` e não de adivinhação pelo que existe no PATH — uma
           máquina pode ter o `apt` instalado sem ser uma Debian.

    EN-UK: Clears the downloaded-package cache, per manager. The command changes
           with the distribution; the choice comes from `platform_support` rather
           than from guessing by what is on the PATH.
    """
    from .platform_support import package_manager

    comandos = {
        "apt": ["apt-get", "clean"],
        "dnf": ["dnf", "clean", "all"],
        "pacman": ["pacman", "-Sc", "--noconfirm"],
        "zypper": ["zypper", "clean", "--all"],
        "apk": ["apk", "cache", "clean"],
    }
    gestor = package_manager()
    if gestor not in comandos:
        return Resultado(
            comando="limpar_pacotes",
            codigo=1,
            erro="Gestor de pacotes não reconhecido nesta distribuição.",
        )
    return executar(comandos[gestor], timeout=180)


def executar_accao(chave: str) -> Resultado:
    """
    PT-PT: Corre a acção correspondente a chave.
    EN-UK: Runs the action matching the key.
    """
    if chave == "limpar_temp":
        return limpar_temp()

    if chave == "ip_config":
        enderecos = executar(["ip", "-o", "addr", "show"], timeout=30)
        rotas = executar(["ip", "route", "show"], timeout=30)
        dns = executar(["resolvectl", "status"], timeout=30)
        partes = [
            "== Endereços ==", enderecos.saida or enderecos.explicacao(),
            "", "== Rotas ==", rotas.saida or rotas.explicacao(),
            "", "== DNS ==", dns.saida or dns.explicacao(),
        ]
        return Resultado(comando="ip", codigo=enderecos.codigo, saida="\n".join(partes))

    if chave == "flush_dns":
        if not disponivel("resolvectl"):
            return Resultado(
                comando="resolvectl",
                codigo=1,
                ausente=True,
                erro=(
                    "Esta máquina não usa o systemd-resolved; não há cache central "
                    "de DNS para limpar."
                ),
            )
        return executar(["resolvectl", "flush-caches"], timeout=30)

    if chave == "renovar_ip":
        if disponivel("nmcli"):
            # PT-PT: O `networking off/on` do nmcli renova sem precisar de saber
            #        o nome da ligação, que muda de máquina para máquina.
            # EN-UK: nmcli's `networking off/on` renews without needing the
            #        connection name, which differs from machine to machine.
            desligar = executar(["nmcli", "networking", "off"], timeout=60)
            ligar = executar(["nmcli", "networking", "on"], timeout=120)
            return Resultado(
                comando="nmcli",
                codigo=ligar.codigo,
                saida=f"{desligar.saida}\n{ligar.saida}".strip() or "Rede reiniciada.",
                erro=ligar.erro,
            )
        if disponivel("dhclient"):
            executar(["dhclient", "-r"], timeout=60)
            return executar(["dhclient"], timeout=120)
        return Resultado(
            comando="renovar_ip",
            codigo=1,
            ausente=True,
            erro="Nem o nmcli nem o dhclient estão disponíveis nesta máquina.",
        )

    if chave == "reiniciar_cups":
        return executar(["systemctl", "--no-ask-password", "restart", "cups"], timeout=60)

    if chave == "limpar_diario":
        return executar(["journalctl", "--vacuum-time=7d"], timeout=180)

    if chave == "limpar_pacotes":
        return _limpar_pacotes()

    if chave == "sessoes":
        if disponivel("loginctl"):
            return executar(["loginctl", "list-sessions"], timeout=30)
        return executar(["who", "-a"], timeout=30)

    if chave == "montagens":
        if disponivel("findmnt"):
            return executar(["findmnt", "--real", "-o", "TARGET,SOURCE,FSTYPE,SIZE,USE%"], timeout=30)
        return executar(["df", "-h"], timeout=30)

    if chave == "falhadas":
        return executar(
            ["systemctl", "--failed", "--no-pager", "--plain"], timeout=60
        )

    if chave == "hora":
        return executar(["timedatectl", "status"], timeout=30)

    if chave == "diario_seguir":
        return _abrir_consola(["journalctl", "-f", "-p", "warning"])

    if chave == "processos":
        return _abrir_consola(["top"])

    return Resultado(comando="accao", codigo=1, erro=f"Acção desconhecida: {chave}")


def abrir_ferramenta(comando: str) -> Resultado:
    """
    PT-PT: Abre uma ferramenta gráfica de gestão.

    EN-UK: Opens a graphical management tool.
    """
    if not disponivel(comando):
        return Resultado(
            comando=comando,
            codigo=1,
            ausente=True,
            erro=f"A ferramenta '{comando}' não está instalada nesta máquina.",
        )
    try:
        subprocess.Popen([comando], start_new_session=True)  # noqa: S603 — vem da lista fixa
    except OSError as exc:
        return Resultado(comando=comando, codigo=1, erro=f"Não foi possível abrir {comando}: {exc}")
    return Resultado(comando=comando, codigo=0, saida=f"{comando} aberto.")


def abrir_pasta(caminho: os.PathLike[str] | str) -> Resultado:
    """PT-PT: Abre uma pasta no ambiente gráfico. / EN-UK: Opens a folder in the desktop."""
    return abrir_ficheiro(str(caminho))
