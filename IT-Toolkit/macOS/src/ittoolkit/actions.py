#!/usr/bin/env python3
"""
PT-PT: Ferramentas rapidas — accoes pontuais de manutencao.

       Regra do modulo: nada aqui apaga dados do utilizador, e tudo o que tem
       impacto declara-o na sua descricao para a interface poder pedir
       confirmacao.

       Tres coisas sao especificas do macOS e moldaram este ficheiro.

       **A limpeza de DNS sao dois comandos, nao um.** O `dscacheutil
       -flushcache` esvazia a cache do Directory Service; o
       `killall -HUP mDNSResponder` obriga o resolvedor a reler a configuracao.
       Correr so o primeiro — que e o que a maioria dos artigos diz — nao
       resolve o caso mais comum, que e o de um servidor DNS que mudou e o
       mDNSResponder continuar a falar com o antigo.

       **O `open -a` e o equivalente das consolas MMC.** Um Mac nao tem
       `services.msc` nem `diskmgmt.msc`; tem aplicacoes em `/System/
       Applications/Utilities`, e o `open -a` abre-as pelo nome sem precisar de
       saber onde estao. As que existem sao sempre as mesmas, porque fazem parte
       do sistema — ao contrario do Linux, onde metade das ferramentas graficas
       podem nao estar instaladas.

       **A limpeza de temporarios nao toca no `/tmp`.** Num Mac, os temporarios
       de cada processo estao em `/private/var/folders`, numa arvore por
       utilizador que o sistema gere e limpa sozinho — e onde apagar coisas a
       mao parte sessoes a serio. O que se limpa aqui e o `~/Library/Caches`, que
       e o que ocupa espaco e o que e seguro apagar: as aplicacoes reconstroem-no.

EN-UK: Quick tools — one-off maintenance actions.

       Module rule: nothing here deletes user data, and anything with impact
       declares it so the interface can ask for confirmation.

       Three things are macOS-specific and shaped this file.

       **Flushing DNS is two commands, not one.** `dscacheutil -flushcache`
       empties the Directory Service cache; `killall -HUP mDNSResponder` makes
       the resolver reread its configuration. Running only the first — what most
       articles say — does not fix the commonest case.

       **`open -a` is the MMC-console equivalent.** A Mac has no `services.msc`;
       it has applications in `/System/Applications/Utilities`, and `open -a`
       opens them by name. They are always present, being part of the system —
       unlike Linux, where half the graphical tools may be missing.

       **Clearing temporaries does not touch `/tmp`.** On a Mac each process's
       temporaries live in `/private/var/folders`, a per-user tree the system
       manages and cleans itself, and where deleting by hand breaks live
       sessions. What is cleared here is `~/Library/Caches`, which is what takes
       up space and what is safe to delete: applications rebuild it.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from .shell import Resultado, abrir_ficheiro, e_root, executar

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Accao:
    """
    PT-PT: Descricao de uma accao para a interface construir os botoes sem
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
    #: PT-PT: True significa que abre uma janela propria e nao devolve saida.
    #: EN-UK: True means it opens its own window and returns no output.
    consola: bool = False
    #: PT-PT: True significa que so funciona como root.
    #: EN-UK: True means it only works as root.
    root: bool = False


ACCOES: tuple[Accao, ...] = (
    Accao("ip_config", "Ver configuração IP", "Mostra os endereços, as rotas e o DNS efectivo."),
    Accao("flush_dns", "Limpar cache DNS", "Esvazia a cache e reinicia o mDNSResponder.", root=True),
    Accao(
        "renovar_ip",
        "Renovar endereço IP",
        "Volta a pedir o endereço ao DHCP. A ligação cai por alguns segundos.",
        confirmar=True,
    ),
    Accao(
        "reiniciar_cups",
        "Reiniciar a impressão",
        "Para e volta a arrancar o CUPS. Os trabalhos em fila perdem-se.",
        confirmar=True,
        root=True,
    ),
    Accao(
        "limpar_caches",
        "Limpar caches do utilizador",
        "Apaga o ~/Library/Caches. As aplicações reconstroem-no; algumas abrem mais "
        "devagar da primeira vez.",
        confirmar=True,
    ),
    Accao(
        "limpar_snapshots",
        "Apagar snapshots locais",
        "Apaga os snapshots do Time Machine guardados no disco. Liberta espaço; a "
        "próxima cópia de segurança refá-los.",
        confirmar=True,
        root=True,
    ),
    Accao("sessoes", "Sessões abertas", "Lista as sessões de utilizador na máquina."),
    Accao("montagens", "Volumes montados", "Mostra o que está montado e o espaço de cada um."),
    Accao("snapshots", "Snapshots do Time Machine", "Lista os snapshots locais e o seu peso."),
    Accao("energia", "Estado da energia", "Bateria, adaptador e o que impede a suspensão."),
    Accao("hora", "Estado da hora", "Mostra a sincronização horária e o fuso configurado."),
    Accao(
        "primeira_ajuda",
        "Verificar o disco de arranque",
        "Corre a Primeira Ajuda em modo de verificação. Não altera nada.",
        confirmar=True,
    ),
    Accao("diario_seguir", "Seguir o diário", "Abre a Consola no diário em tempo real.", consola=True),
    Accao("processos", "Monitor de Actividade", "Abre o Monitor de Actividade.", consola=True),
)

# PT-PT: Aplicacoes de gestao do macOS. Ao contrario das ferramentas graficas
#        de Linux, estas fazem parte do sistema e estao sempre la — o `open -a`
#        encontra-as pelo nome sem precisar do caminho.
# EN-UK: macOS management applications. Unlike Linux's graphical tools these are
#        part of the system and always present — `open -a` finds them by name.
FERRAMENTAS: tuple[tuple[str, str], ...] = (
    ("Utilitário de Disco", "Disk Utility"),
    ("Monitor de Actividade", "Activity Monitor"),
    ("Consola", "Console"),
    ("Informações do Sistema", "System Information"),
    ("Utilitário de Rede", "Network Utility"),
    ("Acesso a Chaves", "Keychain Access"),
    ("Terminal", "Terminal"),
)


def ferramenta_disponivel(nome: str) -> bool:
    """
    PT-PT: Se a aplicação existe nesta máquina.

           Todas as da lista fazem parte do macOS, mas nem todas sobrevivem a
           todas as versões: o Utilitário de Rede foi removido no macOS 11.
           Verificar antes de mostrar o botão evita oferecer uma coisa que não
           abre.

    EN-UK: Whether the application exists on this machine.

           All of the listed ones ship with macOS, but not all survive every
           version: Network Utility was removed in macOS 11.
    """
    for base in ("/System/Applications/Utilities", "/Applications/Utilities", "/System/Applications"):
        if Path(base, f"{nome}.app").exists():
            return True
    return False


def _abrir_aplicacao(nome: str) -> Resultado:
    """
    PT-PT: Abre uma aplicação pelo nome, sem esperar por ela.
    EN-UK: Opens an application by name, without waiting for it.
    """
    if not ferramenta_disponivel(nome):
        return Resultado(
            comando="open",
            codigo=1,
            ausente=True,
            erro=f"A aplicação '{nome}' não existe nesta versão do macOS.",
        )
    return executar(["open", "-a", nome], timeout=30)


def limpar_caches() -> Resultado:
    """
    PT-PT: Limpa a pasta de caches do utilizador.

           Conta o que apagou e o que não conseguiu. Ficheiros em uso não são
           apagáveis e isso é normal, não um erro — a v1.0 lançava a excepção do
           primeiro ficheiro bloqueado e desistia do resto, o que na prática
           significava que quase nunca limpava nada.

           **Só toca no `~/Library/Caches`.** Ver o cabeçalho do módulo: o
           `/private/var/folders` é gerido pelo sistema e apagar coisas lá
           dentro parte sessões a sério. E o `/Library/Caches`, de sistema, é
           partilhado por todos os utilizadores e não é desta ferramenta.

    EN-UK: Clears the user's cache folder.

           It counts what it removed and what it could not. Files in use are not
           deletable and that is normal.

           **It touches only `~/Library/Caches`.** See the module header.
    """
    cache = Path.home() / "Library" / "Caches"
    if not cache.is_dir():
        return Resultado(comando="limpar_caches", codigo=1, erro=f"Não encontrei {cache}.")

    apagados = 0
    bloqueados = 0
    libertado = 0

    try:
        itens = list(cache.iterdir())
    except (OSError, PermissionError) as exc:
        return Resultado(comando="limpar_caches", codigo=1, erro=f"Não foi possível ler {cache}: {exc}")

    for item in itens:
        try:
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
        comando="limpar_caches",
        codigo=0,
        saida=(
            f"Apagados {apagados} item(ns), {libertado / 1024**2:.0f} MB libertados.\n"
            f"{bloqueados} em uso, deixados como estavam.\n"
            f"Pasta: {cache}"
        ),
    )


def _apagar_snapshots() -> Resultado:
    """
    PT-PT: Apaga os snapshots locais do Time Machine.

           É a forma mais rápida de libertar espaço num Mac, e é reversível: a
           próxima cópia de segurança volta a criá-los. O `tmutil
           deletelocalsnapshots` recebe uma data ou um volume; passar-lhe o `/`
           apaga todos os do volume de arranque, que é o que interessa.

           Exige root. Sem ele o comando corre, devolve erro por snapshot, e
           deixa tudo como estava — que é pior do que recusar já.

    EN-UK: Deletes Time Machine's local snapshots.

           The fastest way to free space on a Mac, and reversible: the next
           backup recreates them. It needs root; without it the command runs,
           errors per snapshot and changes nothing.
    """
    if not e_root():
        return Resultado(
            comando="tmutil",
            codigo=1,
            erro=(
                "Apagar snapshots exige root. Correr o diagnóstico com sudo, ou "
                "executar à mão: sudo tmutil deletelocalsnapshots /"
            ),
        )
    return executar(["tmutil", "deletelocalsnapshots", "/"], timeout=300)


def executar_accao(chave: str) -> Resultado:
    """
    PT-PT: Corre a accao correspondente a chave.
    EN-UK: Runs the action matching the key.
    """
    if chave == "limpar_caches":
        return limpar_caches()

    if chave == "ip_config":
        enderecos = executar(["ifconfig", "-a"], timeout=30)
        rotas = executar(["netstat", "-rn", "-f", "inet"], timeout=30)
        dns = executar(["scutil", "--dns"], timeout=30)
        partes = [
            "== Interfaces ==", enderecos.saida or enderecos.explicacao(),
            "", "== Rotas ==", rotas.saida or rotas.explicacao(),
            "", "== DNS efectivo ==", dns.saida or dns.explicacao(),
        ]
        return Resultado(comando="ifconfig", codigo=enderecos.codigo, saida="\n".join(partes))

    if chave == "flush_dns":
        # PT-PT: Os dois comandos, sempre. Ver o cabecalho do modulo.
        # EN-UK: Both commands, always. See the module header.
        cache = executar(["dscacheutil", "-flushcache"], timeout=30)
        resolvedor = executar(["killall", "-HUP", "mDNSResponder"], timeout=30)
        if not resolvedor.ok and not e_root():
            return Resultado(
                comando="killall",
                codigo=1,
                erro=(
                    "A cache foi esvaziada, mas reiniciar o mDNSResponder exige root — e "
                    "é esse o passo que faz efeito quando o servidor DNS mudou. Correr "
                    "com sudo."
                ),
            )
        return Resultado(
            comando="dscacheutil",
            codigo=cache.codigo,
            saida="Cache de DNS esvaziada e mDNSResponder reiniciado.",
        )

    if chave == "renovar_ip":
        # PT-PT: A interface por onde sai o trafego e a que interessa renovar.
        #        Renovar todas de uma vez derruba a VPN e as pontes de
        #        virtualizacao sem necessidade nenhuma.
        # EN-UK: The outbound interface is the one worth renewing. Renewing all
        #        at once needlessly drops the VPN and virtualisation bridges.
        from .network import _interface_de_saida

        interface = _interface_de_saida()
        if not interface:
            return Resultado(
                comando="ipconfig",
                codigo=1,
                erro="Não há rota por omissão: não sei que interface renovar.",
            )
        return executar(["ipconfig", "set", interface, "DHCP"], timeout=60)

    if chave == "reiniciar_cups":
        return executar(
            ["launchctl", "kickstart", "-k", "system/org.cups.cupsd"], timeout=60
        )

    if chave == "limpar_snapshots":
        return _apagar_snapshots()

    if chave == "sessoes":
        return executar(["who", "-a"], timeout=30)

    if chave == "montagens":
        return executar(["df", "-h"], timeout=30)

    if chave == "snapshots":
        return executar(["tmutil", "listlocalsnapshots", "/"], timeout=60)

    if chave == "energia":
        estado = executar(["pmset", "-g", "batt"], timeout=30)
        travoes = executar(["pmset", "-g", "assertions"], timeout=30)
        return Resultado(
            comando="pmset",
            codigo=estado.codigo,
            saida=(
                f"== Energia ==\n{estado.saida or estado.explicacao()}\n\n"
                f"== O que impede a suspensão ==\n{travoes.saida or travoes.explicacao()}"
            ),
        )

    if chave == "hora":
        return executar(["systemsetup", "-getusingnetworktime"], timeout=30)

    if chave == "primeira_ajuda":
        # PT-PT: `verifyVolume` e so de leitura. O `repairVolume` alteraria o
        #        disco e nao pertence a uma ferramenta de diagnostico: quem
        #        precisar de reparar deve faze-lo pelo Utilitario de Disco, a
        #        ver o que esta a acontecer.
        # EN-UK: `verifyVolume` is read-only. `repairVolume` would alter the disk
        #        and does not belong in a diagnostic tool.
        return executar(["diskutil", "verifyVolume", "/"], timeout=600)

    if chave == "diario_seguir":
        return _abrir_aplicacao("Console")

    if chave == "processos":
        return _abrir_aplicacao("Activity Monitor")

    return Resultado(comando="accao", codigo=1, erro=f"Acção desconhecida: {chave}")


def abrir_ferramenta(nome: str) -> Resultado:
    """
    PT-PT: Abre uma aplicação de gestão do sistema.
    EN-UK: Opens a system management application.
    """
    return _abrir_aplicacao(nome)


def abrir_pasta(caminho: os.PathLike[str] | str) -> Resultado:
    """PT-PT: Abre uma pasta no Finder. / EN-UK: Opens a folder in Finder."""
    return abrir_ficheiro(str(caminho))
