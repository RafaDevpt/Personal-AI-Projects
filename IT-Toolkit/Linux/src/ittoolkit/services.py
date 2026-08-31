#!/usr/bin/env python3
"""
PT-PT: Unidades do systemd — listagem, deteccao das que falharam e arranque
       manual.

       A diferenca em relacao ao Windows nao e so de vocabulario. Em Windows a
       pergunta util e «que servicos automaticos estao parados», porque parado e
       o unico sinal que ha. O systemd distingue tres coisas que o Windows junta
       numa so:

       - **failed** — a unidade tentou arrancar e nao conseguiu, ou morreu. E o
         sinal forte, e e o que aparece primeiro no relatorio.
       - **inactive mas enabled** — devia ter arrancado no boot e nao esta a
         correr. Merece atencao, mas nem sempre e avaria.
       - **inactive e oneshot** — correu, fez o que tinha a fazer e saiu. E o
         estado normal de metade das unidades de um sistema, e assinala-lo era o
         erro que enchia a lista de ruido.

       E por isso que este modulo cruza `list-units` com `list-unit-files`: uma
       so das duas nao chega para separar estes casos.

EN-UK: systemd units — listing, detection of failures and manual start.

       The difference from Windows is more than vocabulary. On Windows the
       useful question is "which automatic services are stopped", because
       stopped is the only signal there is. systemd distinguishes three things
       Windows merges into one:

       - **failed** — the unit tried to start and could not, or died. The strong
         signal, and what comes first in the report.
       - **inactive but enabled** — it should have started at boot and is not
         running. Worth attention, though not always a fault.
       - **inactive and oneshot** — it ran, did its job and exited. The normal
         state of half a system's units, and flagging it was the mistake that
         filled the list with noise.

       Hence this module crosses `list-units` with `list-unit-files`: either one
       alone cannot separate these cases.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging

from .models import Achado, Gravidade
from .shell import Resultado, executar

log = logging.getLogger(__name__)

#: PT-PT: Caracteres validos num nome de unidade. O `@` e das unidades de
#:        modelo (`getty@tty1.service`) e o `\` das que trazem um caminho
#:        codificado no nome (`home-user.mount`, `dev-disk\x2dby...`).
#: EN-UK: Valid characters in a unit name. `@` is for template units and `\`
#:        for those carrying an escaped path in the name.
_CARACTERES_UNIDADE = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.@\\:")

# PT-PT: Unidades activadas que estao inactivas por desenho, e nao por avaria.
#        Sao oneshot ou disparadas por temporizador: correm, saem, e o estado
#        «inactive (dead)» e o resultado de terem corrido bem.
#
#        A deteccao de `Type=oneshot` ja apanha a maioria destas, mas custa uma
#        chamada a `systemctl show` por unidade. Esta lista evita essa chamada
#        para as mais comuns, e cobre as que nao sao oneshot mas tambem nao sao
#        problema.
# EN-UK: Enabled units inactive by design rather than by failure. They are
#        oneshot or timer-driven: they run, exit, and "inactive (dead)" is the
#        result of having run correctly. The `Type=oneshot` detection catches
#        most of them, but costs one `systemctl show` per unit; this list avoids
#        that call for the commonest, and covers those that are not oneshot but
#        are not a problem either.
ARRANQUE_TARDIO: frozenset[str] = frozenset(
    {
        "systemd-fsck-root.service",
        "systemd-remount-fs.service",
        "systemd-random-seed.service",
        "systemd-update-utmp.service",
        "systemd-tmpfiles-setup.service",
        "systemd-tmpfiles-clean.service",
        "systemd-sysctl.service",
        "systemd-modules-load.service",
        "systemd-user-sessions.service",
        "systemd-journal-flush.service",
        "kmod-static-nodes.service",
        "apparmor.service",
        "e2scrub_reap.service",
        "man-db.service",
        "apt-daily.service",
        "apt-daily-upgrade.service",
        "dnf-makecache.service",
        "logrotate.service",
        "fstrim.service",
        "plymouth-quit.service",
        "plymouth-quit-wait.service",
        "plymouth-read-write.service",
        "grub-initrd-fallback.service",
        "console-setup.service",
        "keyboard-setup.service",
        "ldconfig.service",
        "setvtrgb.service",
    }
)

#: PT-PT: Quantas unidades listar no detalhe de um achado.
#: EN-UK: How many units to list in a finding's detail.
MAX_NO_DETALHE = 12


def _nome_valido(nome: str) -> bool:
    """
    PT-PT: Se o nome pode ser passado ao `systemctl`.

           Ao contrario da versao de Windows, aqui isto **nao e** uma fronteira
           de seguranca: os comandos sao executados com uma lista de argumentos
           e nunca por uma shell, portanto um ponto e virgula no nome nao
           executa coisa nenhuma. A validacao existe para dar uma mensagem util
           em vez de um erro do systemctl, e para o teste poder confirmar que
           uma entrada absurda nao chega a sair daqui.

    EN-UK: Whether the name can be handed to `systemctl`.

           Unlike the Windows version this is **not** a security boundary:
           commands run from an argument list and never through a shell, so a
           semicolon in the name executes nothing. The validation exists to give
           a useful message instead of a systemctl error, and so the test can
           confirm an absurd entry never leaves here.
    """
    return bool(nome) and all(c in _CARACTERES_UNIDADE for c in nome)


def _ler_tabela(saida: str, colunas: int) -> list[list[str]]:
    """
    PT-PT: Le a saida tabular do `systemctl --plain --no-legend`.

           Divide em `colunas` campos e deixa o resto na ultima — a descricao de
           uma unidade tem espacos, o nome nunca tem. Divide-se pela esquerda,
           que e o unico lado onde o numero de campos e conhecido.

           O primeiro campo pode vir com um marcador de estado a frente
           (bullet), que o `--plain` costuma tirar mas nem sempre; e retirado
           aqui por seguranca.

    EN-UK: Reads `systemctl --plain --no-legend` tabular output.

           Splits into `colunas` fields and leaves the rest in the last one — a
           unit's description has spaces, its name never does. Splitting is from
           the left, the only side where the field count is known.
    """
    linhas: list[list[str]] = []
    for linha in saida.splitlines():
        texto = linha.strip()
        if not texto:
            continue
        if texto[0] in "*●•":
            texto = texto[1:].strip()
        campos = texto.split(None, colunas - 1)
        if len(campos) < colunas:
            campos += [""] * (colunas - len(campos))
        linhas.append(campos)
    return linhas


def ficheiros_de_unidade() -> dict[str, str]:
    """
    PT-PT: O estado de activacao de cada unidade de servico.

    EN-UK: Each service unit's enablement state.

    :return:
        PT-PT: Nome da unidade → `enabled`, `disabled`, `static`, `masked`…
        EN-UK: Unit name → `enabled`, `disabled`, `static`, `masked`…
    """
    resultado = executar(
        ["systemctl", "list-unit-files", "--type=service", "--no-pager", "--plain", "--no-legend"],
        timeout=60,
    )
    if not resultado.ok:
        log.debug("list-unit-files falhou: %s", resultado.explicacao())
        return {}
    return {campos[0]: campos[1] for campos in _ler_tabela(resultado.saida, 2) if campos[0]}


def listar(apenas_activadas: bool = True) -> list[dict]:
    """
    PT-PT: Lista as unidades de servico e o seu estado.

    EN-UK: Lists the service units and their state.

    :param apenas_activadas:
        PT-PT: True devolve so as que estao `enabled` — as que o sistema promete
               arrancar no boot. False devolve tudo.
        EN-UK: True returns only the `enabled` ones — those the system promises
               to start at boot. False returns everything.
    :return:
        PT-PT: Um dicionario por unidade com `nome`, `descricao`, `estado`,
               `subestado` e `arranque`.
        EN-UK: One dictionary per unit with `nome`, `descricao`, `estado`,
               `subestado` and `arranque`.
    """
    resultado = executar(
        ["systemctl", "list-units", "--type=service", "--all", "--no-pager", "--plain", "--no-legend"],
        timeout=60,
    )
    if not resultado.ok:
        log.debug("list-units falhou: %s", resultado.explicacao())
        return []

    activacao = ficheiros_de_unidade()
    unidades: list[dict] = []

    # PT-PT: UNIT LOAD ACTIVE SUB DESCRIPTION — cinco campos, o ultimo com espaços.
    # EN-UK: UNIT LOAD ACTIVE SUB DESCRIPTION — five fields, the last with spaces.
    for nome, carga, activo, subestado, descricao in _ler_tabela(resultado.saida, 5):
        arranque = activacao.get(nome, "")
        if apenas_activadas and arranque != "enabled":
            continue
        unidades.append(
            {
                "nome": nome,
                "descricao": descricao,
                "estado": activo,
                "subestado": subestado,
                "carga": carga,
                "arranque": arranque or "?",
            }
        )
    return unidades


def falhadas() -> list[dict]:
    """
    PT-PT: Unidades em estado `failed`.

           E o sinal mais claro que o systemd da. Nao precisa de interpretacao,
           nao precisa de lista de excepcoes: se esta aqui, alguma coisa tentou
           arrancar e nao conseguiu.

    EN-UK: Units in `failed` state.

           The clearest signal systemd gives. It needs no interpretation and no
           exception list: if it is here, something tried to start and could not.
    """
    resultado = executar(
        ["systemctl", "list-units", "--type=service", "--state=failed",
         "--no-pager", "--plain", "--no-legend"],
        timeout=60,
    )
    if not resultado.ok:
        return []

    activacao = ficheiros_de_unidade()
    return [
        {
            "nome": nome,
            "descricao": descricao,
            "estado": activo,
            "subestado": subestado,
            "carga": carga,
            "arranque": activacao.get(nome, "?"),
        }
        for nome, carga, activo, subestado, descricao in _ler_tabela(resultado.saida, 5)
    ]


def e_oneshot(nome: str) -> bool:
    """
    PT-PT: Se a unidade e do tipo `oneshot`.

           Uma unidade oneshot inactiva correu e saiu — e o estado normal dela.
           Confundir isso com uma avaria era o que fazia a lista de «servicos
           parados» ter cinquenta entradas numa maquina saudavel.

    EN-UK: Whether the unit is of type `oneshot`.

           An inactive oneshot unit ran and exited — that is its normal state.
           Confusing it with a failure is what made the "stopped services" list
           show fifty entries on a healthy machine.
    """
    resultado = executar(["systemctl", "show", "-p", "Type", "--value", nome], timeout=15)
    return resultado.saida.strip() == "oneshot"


def paradas() -> list[dict]:
    """
    PT-PT: Unidades activadas que nao estao a correr, sem o ruido conhecido.

           Nao inclui as que falharam — essas tem funcao propria, `falhadas()`, e
           merecem um lugar separado no relatorio. Aqui ficam as que estao
           simplesmente inactivas quando deviam estar de pe.

    EN-UK: Enabled units not running, minus the known noise.

           It excludes the failed ones — those have their own function,
           `falhadas()`, and deserve a separate place in the report. What is left
           here are the ones simply inactive when they should be up.
    """
    encontradas: list[dict] = []
    for unidade in listar(apenas_activadas=True):
        nome = str(unidade.get("nome") or "")
        estado = str(unidade.get("estado") or "")

        if estado in {"active", "activating", "reloading", "failed"}:
            continue
        if nome in ARRANQUE_TARDIO:
            continue
        if e_oneshot(nome):
            continue
        encontradas.append(unidade)
    return encontradas


def registo(nome: str, linhas: int = 40) -> Resultado:
    """
    PT-PT: As ultimas linhas do diario de uma unidade.

           E o passo seguinte inevitavel depois de ver uma unidade falhada, e
           poupar o operador a escrever o comando a mao e metade do valor desta
           ferramenta.

    EN-UK: A unit's last journal lines. The inevitable next step after seeing a
           failed unit, and saving the operator from typing the command by hand
           is half this tool's value.
    """
    if not _nome_valido(nome):
        return Resultado(comando="journalctl", codigo=1, erro=f"Nome de unidade inválido: {nome!r}")
    return executar(
        ["journalctl", "--no-pager", "-u", nome, "-n", str(linhas), "--output", "short-iso"],
        timeout=60,
    )


def arrancar(nome: str) -> Resultado:
    """
    PT-PT: Arranca uma unidade pelo nome.

           Nao e destrutivo, mas tem impacto: quem chama deve confirmar com o
           operador antes.

           Sem root, o `systemctl start` de uma unidade de sistema falha com
           «Access denied» — ou, pior, fica a espera de uma autenticacao
           interactiva do polkit que nunca chega numa sessao sem ecra. O
           `--no-ask-password` corta isso: falha depressa e com uma mensagem que
           se pode mostrar.

    EN-UK: Starts a unit by name. Not destructive but not trivial; the caller
           should confirm with the operator first.

           Without root, `systemctl start` on a system unit fails with "Access
           denied" — or worse, waits for a polkit interactive authentication
           that never arrives in a headless session. `--no-ask-password` cuts
           that short: it fails fast, with a message that can be displayed.
    """
    if not _nome_valido(nome):
        return Resultado(comando="systemctl", codigo=1, erro=f"Nome de unidade inválido: {nome!r}")
    return executar(["systemctl", "--no-ask-password", "start", nome], timeout=60)


def achados() -> list[Achado]:
    """
    PT-PT: Unidades falhadas e unidades activadas que nao arrancaram.

    EN-UK: Failed units, and enabled units that did not start.
    """
    encontrados: list[Achado] = []

    lista_falhadas = falhadas()
    if lista_falhadas:
        nomes = [str(u.get("nome") or "?") for u in lista_falhadas[:MAX_NO_DETALHE]]
        detalhe = ", ".join(nomes)
        if len(lista_falhadas) > MAX_NO_DETALHE:
            detalhe += f" (e mais {len(lista_falhadas) - MAX_NO_DETALHE})"
        encontrados.append(
            Achado(
                modulo="Serviços",
                titulo=f"{len(lista_falhadas)} unidade(s) em estado 'failed'",
                detalhe=detalhe,
                gravidade=Gravidade.ALTA,
                solucao=(
                    "Ver o motivo com 'systemctl status <unidade>' e o registo com "
                    "'journalctl -u <unidade> -n 50' — a causa está quase sempre nas "
                    "últimas linhas antes da falha. No separador Serviços, o botão de "
                    "registo faz isso sem sair da aplicação."
                ),
            )
        )

    lista_paradas = paradas()
    if lista_paradas:
        nomes = [str(u.get("nome") or "?") for u in lista_paradas[:MAX_NO_DETALHE]]
        detalhe = ", ".join(nomes)
        if len(lista_paradas) > MAX_NO_DETALHE:
            detalhe += f" (e mais {len(lista_paradas) - MAX_NO_DETALHE})"
        encontrados.append(
            Achado(
                modulo="Serviços",
                titulo=f"{len(lista_paradas)} unidade(s) activada(s) mas parada(s)",
                detalhe=detalhe,
                gravidade=Gravidade.MEDIA,
                solucao=(
                    "Estas unidades estão 'enabled' e deviam ter arrancado no boot. "
                    "Arrancar no separador Serviços. Se uma delas voltar a parar "
                    "sozinha, o registo da unidade diz porquê."
                ),
            )
        )

    return encontrados
