#!/usr/bin/env python3
"""
PT-PT: Servicos do launchd — listagem, deteccao dos que falharam e arranque
       manual.

       O launchd nao tem estado «failed». Isto e a diferenca de fundo em relacao
       ao systemd, e e o que molda este modulo inteiro.

       O que o `launchctl list` da sao tres colunas: o PID, o **ultimo codigo de
       saida** e a etiqueta. Um servico a correr tem PID e um traco na segunda
       coluna. Um servico que correu e saiu bem tem um traco no PID e um zero.
       Um servico que **falhou** tem um traco no PID e um numero diferente de
       zero — e nao ha mais nenhum sitio onde isso apareca. Ler mal esta coluna
       e nao ver falha nenhuma numa maquina cheia delas.

       A segunda particularidade sao os dois dominios. O `launchctl list` sem
       sudo mostra os servicos **do utilizador**; com sudo mostra os **do
       sistema**. Nao ha comando que mostre os dois, e sao populacoes
       completamente diferentes: as aplicacoes de arranque estao no primeiro, os
       daemons no segundo.

       A terceira e o vocabulario, que mudou. O `launchctl load` e o `start`
       estao obsoletos ha varias versoes do macOS; o que funciona hoje e o
       `bootstrap`, o `kickstart` e o `print`, sobre alvos com a forma
       `system/<etiqueta>` ou `gui/<uid>/<etiqueta>`. Um artigo de 2015 na
       Internet ensina o contrario, e por isso esta escrito aqui.

EN-UK: launchd services — listing, failure detection and manual start.

       launchd has no "failed" state. That is the fundamental difference from
       systemd and shapes this whole module.

       `launchctl list` gives three columns: the PID, the **last exit code** and
       the label. A running service has a PID and a dash. A service that ran and
       exited cleanly has a dash and a zero. A service that **failed** has a dash
       and a non-zero number — and there is nowhere else this shows. Misreading
       that column means seeing no failures on a machine full of them.

       Second quirk: two domains. `launchctl list` without sudo shows the
       **user's** services; with sudo, the **system's**. No command shows both,
       and they are completely different populations.

       Third: the vocabulary changed. `launchctl load` and `start` have been
       deprecated for several macOS versions; what works today is `bootstrap`,
       `kickstart` and `print`, over targets shaped `system/<label>` or
       `gui/<uid>/<label>`. A 2015 article teaches the opposite, which is why
       this is written down here.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
import os

from .models import Achado, Gravidade
from .shell import Resultado, e_root, executar

log = logging.getLogger(__name__)

#: PT-PT: Caracteres validos numa etiqueta de launchd. Sao nomes em notacao
#:        inversa de dominio — `com.apple.mDNSResponder`.
#: EN-UK: Valid characters in a launchd label. They are reverse-domain names.
_CARACTERES_ETIQUETA = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-."
)

# PT-PT: Servicos que saem com codigo diferente de zero por desenho, e nao por
#        avaria. Sao os que o sistema arranca a pedido, os que terminam quando
#        nao ha nada a fazer, e alguns que a Apple deixa a falhar em maquinas
#        onde a funcionalidade nao existe — o `com.apple.mbsystemadministration`
#        num Mac sem gestao, por exemplo.
#
#        Sem esta lista, um Mac saudavel apresentava vinte «servicos falhados» e
#        o operador aprendia a ignorar a seccao inteira.
# EN-UK: Services exiting non-zero by design rather than by failure: those the
#        system starts on demand, those ending when there is nothing to do, and
#        a few Apple leaves failing on machines where the feature does not exist.
#        Without this list a healthy Mac showed twenty "failed services".
RUIDO_CONHECIDO: frozenset[str] = frozenset(
    {
        "com.apple.mbsystemadministration",
        "com.apple.mbuseragent",
        "com.apple.familycontrols.useragent",
        "com.apple.SafariHistoryServiceAgent",
        "com.apple.photoanalysisd",
        "com.apple.mediaanalysisd",
        "com.apple.parentalcontrols.check",
        "com.apple.CommCenterRootHelper",
        "com.apple.systemstats.analysis",
        "com.apple.systemstats.daily",
        "com.apple.periodic-daily",
        "com.apple.periodic-weekly",
        "com.apple.periodic-monthly",
        "com.apple.speech.speechsynthesisd",
        "com.apple.mrt",
        "com.apple.MRTa",
    }
)

#: PT-PT: Quantos servicos listar no detalhe de um achado.
#: EN-UK: How many services to list in a finding's detail.
MAX_NO_DETALHE = 12


def _etiqueta_valida(nome: str) -> bool:
    """
    PT-PT: Se a etiqueta pode ser passada ao `launchctl`.

           Ao contrário da versão de Windows, isto **não** é uma fronteira de
           segurança: os comandos são executados com uma lista de argumentos e
           nunca por uma shell. A validação existe para dar uma mensagem útil em
           vez de um erro do launchctl, e para o teste poder confirmar que uma
           entrada absurda não chega a sair daqui.

    EN-UK: Whether the label can be handed to `launchctl`. Not a security
           boundary — commands run from an argument list, never through a shell.
    """
    return bool(nome) and all(c in _CARACTERES_ETIQUETA for c in nome)


def _ler_listagem(saida: str) -> list[dict]:
    """
    PT-PT: Lê a saída de três colunas do `launchctl list`.

           A primeira linha é o cabeçalho `PID Status Label` e é saltada. As
           colunas são separadas por tabulação, mas nem sempre — há versões que
           usam espaços — por isso a divisão é por espaço em branco, com um
           máximo de três campos: uma etiqueta nunca tem espaços.

    EN-UK: Reads `launchctl list`'s three-column output. The header line is
           skipped. Columns are tab-separated, but not always, so splitting is by
           whitespace with a three-field cap: a label never has spaces.

    :return:
        PT-PT: Um dicionário por serviço com `pid`, `codigo` e `etiqueta`.
        EN-UK: One dictionary per service with `pid`, `codigo` and `etiqueta`.
    """
    servicos: list[dict] = []
    for linha in saida.splitlines():
        campos = linha.split(None, 2)
        if len(campos) < 3 or campos[0] == "PID":
            continue
        pid, codigo, etiqueta = campos
        servicos.append(
            {
                "pid": pid.strip(),
                "codigo": codigo.strip(),
                "etiqueta": etiqueta.strip(),
            }
        )
    return servicos


def _numero(valor: str) -> int | None:
    """
    PT-PT: O código de saída como número, ou None quando é um traço.

           O traço significa «não há código», e não «código zero». A diferença
           importa: um serviço a correr tem traço na coluna do código, e
           tratá-lo como zero é dizer que terminou bem quando nem sequer
           terminou.

    EN-UK: The exit code as a number, or None when it is a dash.

           The dash means "no code", not "code zero". A running service has a
           dash there, and treating it as zero says it finished cleanly when it
           has not finished at all.
    """
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def listar(dominio: str = "utilizador") -> list[dict]:
    """
    PT-PT: Lista os serviços de um domínio do launchd.

           Ver o cabeçalho do módulo: os dois domínios são populações
           diferentes e não há comando que mostre os dois.

    EN-UK: Lists one launchd domain's services. See the module header: the two
           domains are different populations and no command shows both.

    :param dominio:
        PT-PT: `"utilizador"` ou `"sistema"`. O segundo exige root.
        EN-UK: `"utilizador"` or `"sistema"`. The latter needs root.
    :return:
        PT-PT: Um dicionário por serviço com `nome`, `descricao`, `estado`,
               `codigo_saida` e `dominio`.
        EN-UK: One dictionary per service.
    """
    if dominio == "sistema" and not e_root():
        log.debug("Domínio de sistema pedido sem root; devolvido vazio.")
        return []

    resultado = executar(["launchctl", "list"], timeout=60)
    if not resultado.ok:
        log.debug("launchctl list falhou: %s", resultado.explicacao())
        return []

    servicos: list[dict] = []
    for entrada in _ler_listagem(resultado.saida):
        codigo = _numero(entrada["codigo"])
        a_correr = entrada["pid"] not in {"-", ""}
        servicos.append(
            {
                "nome": entrada["etiqueta"],
                "descricao": f"PID {entrada['pid']}" if a_correr else "",
                "estado": "a correr" if a_correr else "parado",
                "codigo_saida": codigo,
                "dominio": dominio,
            }
        )
    return servicos


def falhadas() -> list[dict]:
    """
    PT-PT: Serviços cujo último código de saída não foi zero.

           É o equivalente mais próximo do `failed` do systemd que o launchd
           oferece, e a razão de ser deste módulo. Ver o cabeçalho.

           O ruído conhecido é excluído aqui, e não em `achados()`, para a
           listagem no ecrã e o relatório dizerem a mesma coisa.

    EN-UK: Services whose last exit code was not zero.

           The closest thing to systemd's `failed` that launchd offers, and this
           module's reason to exist. Known noise is excluded here rather than in
           `achados()`, so the on-screen listing and the report agree.
    """
    encontradas: list[dict] = []
    for servico in listar("sistema") + listar("utilizador"):
        codigo = servico.get("codigo_saida")
        if codigo in (None, 0):
            continue
        if servico["nome"] in RUIDO_CONHECIDO:
            continue
        servico["descricao"] = f"último código de saída: {codigo}"
        encontradas.append(servico)
    return encontradas


def registo(nome: str, linhas: int = 40) -> Resultado:
    """
    PT-PT: As últimas mensagens do diário relativas a um serviço.

           O launchd não tem um `journalctl -u`. O que há é o diário unificado
           com um predicado sobre o processo, e é isso que isto monta — a
           etiqueta `com.apple.exemplo` corresponde tipicamente a um processo
           chamado `exemplo`.

           A janela é de uma hora e não do dia inteiro: sem limite, este comando
           demora tanto quanto uma análise completa, e quem carrega no botão
           quer ver o que aconteceu agora.

    EN-UK: A service's last journal messages.

           launchd has no `journalctl -u`. What there is, is the unified log with
           a predicate on the process. The window is one hour, not the whole day:
           unbounded, this takes as long as a full analysis.
    """
    if not _etiqueta_valida(nome):
        return Resultado(comando="log", codigo=1, erro=f"Etiqueta inválida: {nome!r}")

    processo = nome.rsplit(".", 1)[-1]
    return executar(
        [
            "log", "show",
            "--last", "1h",
            "--style", "compact",
            "--predicate", f'process CONTAINS "{processo}"',
        ],
        timeout=180,
    )


def arrancar(nome: str) -> Resultado:
    """
    PT-PT: Arranca um serviço pela etiqueta.

           Usa o `kickstart`, e não o `start`, que está obsoleto — ver o
           cabeçalho do módulo. O alvo tem de incluir o domínio: `system/` para
           os daemons, `gui/<uid>/` para os agentes do utilizador. Passar a
           etiqueta sozinha devolve «Could not find service», que parece um
           serviço inexistente e é apenas um alvo incompleto.

           Não é destrutivo, mas tem impacto: quem chama deve confirmar com o
           operador antes.

    EN-UK: Starts a service by label.

           It uses `kickstart` rather than the deprecated `start` — see the
           module header. The target must include the domain: `system/` for
           daemons, `gui/<uid>/` for user agents. Passing the bare label returns
           "Could not find service", which looks like a missing service and is
           only an incomplete target.
    """
    if not _etiqueta_valida(nome):
        return Resultado(comando="launchctl", codigo=1, erro=f"Etiqueta inválida: {nome!r}")

    if e_root():
        alvo = f"system/{nome}"
    else:
        uid = os.getuid() if hasattr(os, "getuid") else 501
        alvo = f"gui/{uid}/{nome}"

    return executar(["launchctl", "kickstart", "-k", alvo], timeout=60)


def achados() -> list[Achado]:
    """
    PT-PT: Serviços do launchd com o último arranque falhado.
    EN-UK: launchd services whose last start failed.
    """
    lista = falhadas()
    if not lista:
        encontrados: list[Achado] = []
    else:
        nomes = [str(s.get("nome") or "?") for s in lista[:MAX_NO_DETALHE]]
        detalhe = ", ".join(nomes)
        if len(lista) > MAX_NO_DETALHE:
            detalhe += f" (e mais {len(lista) - MAX_NO_DETALHE})"
        encontrados = [
            Achado(
                modulo="Serviços",
                titulo=f"{len(lista)} serviço(s) do launchd com falha no último arranque",
                detalhe=detalhe,
                gravidade=Gravidade.MEDIA,
                solucao=(
                    "Ver o motivo no separador Serviços, com o botão de registo. Se o "
                    "serviço tiver KeepAlive no plist, o launchd volta a arrancá-lo em "
                    "ciclo — e nesse caso o processador e o diário mostram-no."
                ),
            )
        ]

    if not e_root():
        encontrados.append(
            Achado(
                modulo="Serviços",
                titulo="Serviços de sistema não verificados",
                detalhe=(
                    "Sem root, o 'launchctl list' mostra apenas os serviços deste "
                    "utilizador. Os daemons do sistema não foram lidos."
                ),
                gravidade=Gravidade.INFORMATIVA,
                solucao="Correr o diagnóstico com sudo: sudo ./cli.sh --cli",
            )
        )

    return encontrados
