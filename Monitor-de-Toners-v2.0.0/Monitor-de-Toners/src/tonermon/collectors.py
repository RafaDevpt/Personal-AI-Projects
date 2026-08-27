#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PT-PT: Recolha dos níveis de consumíveis.

       Três estratégias em cascata, porque um parque de impressoras tem sempre
       várias gerações de firmware ao mesmo tempo:

         1. LEDM  — /DevMgmt/ConsumableConfigDyn.xml. Dá percentagem, cor,
                    referência do cartucho e número de série. É a melhor fonte
                    e responde nas HP FutureSmart e nas Pro recentes.
         2. SNMP  — Printer-MIB. Universal, mas não devolve a referência do
                    cartucho, que é justamente o que se precisa para encomendar.
         3. HTML  — leitura da página do EWS. Último recurso, frágil por
                    natureza, mas é o único que funciona em firmware antigo.

       A cascata pára na primeira estratégia que devolva pelo menos um
       consumível com percentagem conhecida. Esta condição é deliberada: sem
       ela, uma resposta SNMP com todos os níveis a "desconhecido" contaria como
       sucesso e impediria o recurso ao HTML — que era exactamente o defeito da
       versão anterior na HP M527.

EN-UK: Supply level collection.

       Three strategies in cascade, because a printer fleet always runs several
       firmware generations at once:

         1. LEDM  — /DevMgmt/ConsumableConfigDyn.xml. Gives percentage, colour,
                    cartridge part number and serial. It is the best source and
                    answers on HP FutureSmart and recent Pro units.
         2. SNMP  — Printer-MIB. Universal, but does not return the cartridge
                    part number, which is precisely what ordering requires.
         3. HTML  — scraping the EWS page. Last resort, fragile by nature, but
                    the only thing that works on old firmware.

       The cascade stops at the first strategy returning at least one supply
       with a known percentage. That condition is deliberate: without it, an
       SNMP reply with every level "unknown" would count as success and block
       the HTML fallback — which was exactly the previous version's failure on
       the HP M527.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
import re
import ssl
import urllib.error
import urllib.request
from datetime import datetime
from html.parser import HTMLParser
from xml.etree import ElementTree

from .config import AppConfig
from .models import Printer, Reachability, Supply, normalise_colour
from .snmp import (
    OID_SUPPLY_CURRENT,
    OID_SUPPLY_DESCRIPTION,
    OID_SUPPLY_MAX,
    SnmpClient,
    level_to_percent,
)

_log = logging.getLogger(__name__)

# PT-PT: Caminhos LEDM conhecidos, por ordem de preferência.
# EN-UK: Known LEDM paths, in order of preference.
LEDM_PATHS: tuple[str, ...] = (
    "/DevMgmt/ConsumableConfigDyn.xml",
    "/DevMgmt/ProductStatusDyn.xml",
)

# PT-PT: Páginas HTML onde os níveis costumam aparecer, por modelo e geração.
# EN-UK: HTML pages where the levels usually appear, by model and generation.
HTML_PATHS: tuple[str, ...] = (
    "/hp/device/InternalPages/Index?id=SuppliesStatus",
    "/hp/device/DeviceStatus/Index",
    "/SSI/index.htm",
    "/",
)


def _ssl_context() -> ssl.SSLContext:
    """
    PT-PT: Contexto TLS tolerante, obrigatório para falar com impressoras.

           As impressoras usam certificados auto-assinados que nunca vão
           validar, e o firmware mais antigo só suporta TLS 1.0. Recusar
           qualquer um dos dois significa não conseguir ler metade do parque.

           Este relaxamento é aceitável aqui e não seria aceitável na Internet:
           os pedidos vão para endereços da rede interna, e o que se lê são
           níveis de toner, não credenciais.

    EN-UK: Tolerant TLS context, unavoidable when talking to printers.

           Printers use self-signed certificates that will never validate, and
           older firmware supports only TLS 1.0. Refusing either means being
           unable to read half the fleet.

           This relaxation is acceptable here and would not be on the Internet:
           the requests go to internal addresses, and what is read is toner
           levels, not credentials.
    """
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    try:
        # PT-PT: Baixar o mínimo para TLS 1.0. Em Python recente o mínimo por
        #        omissão é 1.2, e as impressoras antigas não chegam lá.
        # EN-UK: Lower the minimum to TLS 1.0. Recent Python defaults to 1.2 as
        #        the minimum, and older printers never get there.
        context.minimum_version = ssl.TLSVersion.TLSv1
        context.set_ciphers("DEFAULT@SECLEVEL=1")
    except (ValueError, AttributeError) as exc:
        # PT-PT: Distribuições com OpenSSL endurecido recusam SECLEVEL=1. Nesse
        #        caso continuamos com o que houver, e as impressoras antigas
        #        recorrem ao http em vez do https.
        # EN-UK: Distributions with a hardened OpenSSL refuse SECLEVEL=1. In
        #        that case we carry on with whatever is available, and older
        #        printers fall back to http rather than https.
        _log.debug("Não foi possível relaxar o TLS: %s", exc)

    return context


def _build_opener(bypass_proxy: bool) -> urllib.request.OpenerDirector:
    """
    PT-PT: Constrói o abridor HTTP usado em todos os pedidos.

           O ProxyHandler vazio é o detalhe que resolveu os timeouts nos
           primeiros testes: numa máquina de domínio, os pedidos para
           10.162.84.x eram encaminhados para o proxy corporativo, que os
           enviava para fora e os deixava morrer ao fim de 35 segundos. Um proxy
           vazio desliga esse encaminhamento por completo.

    EN-UK: Builds the HTTP opener used for every request.

           The empty ProxyHandler is the detail that fixed the timeouts in the
           first tests: on a domain machine, requests to 10.162.84.x were routed
           to the corporate proxy, which sent them outbound and let them die
           after 35 seconds. An empty proxy switches that routing off entirely.

    :param bypass_proxy:
        PT-PT: True ignora qualquer proxy configurado no sistema.
        EN-UK: True ignores any proxy configured on the system.
    """
    handlers: list[urllib.request.BaseHandler] = [
        urllib.request.HTTPSHandler(context=_ssl_context())
    ]
    if bypass_proxy:
        handlers.append(urllib.request.ProxyHandler({}))

    return urllib.request.build_opener(*handlers)


def _fetch(
    printer: Printer,
    path: str,
    config: AppConfig,
    password: str = "",
) -> str | None:
    """
    PT-PT: Descarrega uma página da impressora.

           Se o primeiro protocolo falhar, tenta o outro automaticamente: é
           comum o inventário dizer http e a impressora só responder em https
           depois de uma actualização de firmware, e obrigar o utilizador a
           corrigir 24 linhas de Excel por causa disso seria irritante.

    EN-UK: Downloads one page from the printer.

           If the first protocol fails, the other is tried automatically: it is
           common for the inventory to say http while the printer answers only
           over https after a firmware update, and making the user correct 24
           Excel rows because of that would be irritating.

    :param printer:
        PT-PT: Impressora alvo. / EN-UK: Target printer.
    :param path:
        PT-PT: Caminho a pedir. / EN-UK: Path to request.
    :param config:
        PT-PT: Configuração activa. / EN-UK: Active configuration.
    :param password:
        PT-PT: Password do EWS, se necessária.
        EN-UK: EWS password, if required.
    :return:
        PT-PT: Corpo da resposta, ou None se nenhum protocolo respondeu.
        EN-UK: Response body, or None if neither protocol answered.
    """
    opener = _build_opener(config.bypass_proxy)

    if password:
        # PT-PT: Basic e Digest, porque o firmware varia entre os dois.
        # EN-UK: Basic and Digest, because firmware varies between the two.
        manager = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        manager.add_password(
            None, f"{printer.scheme}://{printer.ip}/", config.ews_user, password
        )
        opener.add_handler(urllib.request.HTTPBasicAuthHandler(manager))
        opener.add_handler(urllib.request.HTTPDigestAuthHandler(manager))

    # PT-PT: Protocolo do inventário primeiro, o outro como recurso.
    # EN-UK: The inventory's protocol first, the other as a fallback.
    schemes = [printer.scheme, "https" if printer.scheme == "http" else "http"]

    for scheme in schemes:
        url = f"{scheme}://{printer.ip}{path}"
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "HP-Toner-Monitor/2.0",
                "Accept": "application/xml, text/html, */*",
            },
        )
        try:
            with opener.open(request, timeout=config.http_timeout) as response:
                body = response.read()

            if scheme != printer.scheme:
                # PT-PT: Lembrar a descoberta para os pedidos seguintes desta
                #        mesma leitura — poupa uma tentativa falhada por página.
                # EN-UK: Remember the discovery for the remaining requests of
                #        this reading — it saves one failed attempt per page.
                _log.info("%s responde em %s, não em %s.", printer.ip, scheme, printer.scheme)
                printer.scheme = scheme

            return body.decode("utf-8", errors="replace")

        except (urllib.error.URLError, OSError, ValueError) as exc:
            _log.debug("Falha ao obter %s: %s", url, exc)

    return None


# ---------------------------------------------------------------------------
# PT-PT: Estratégia 1 — LEDM / EN-UK: Strategy 1 — LEDM
# ---------------------------------------------------------------------------


def _strip_namespace(tag: str) -> str:
    """
    PT-PT: Remove o espaço de nomes de uma etiqueta XML.
           O LEDM usa vários espaços de nomes que mudam entre versões de
           firmware, e procurar pelo nome simples é muito mais robusto do que
           tentar acompanhá-los.

    EN-UK: Strips the namespace from an XML tag.
           LEDM uses several namespaces that change between firmware versions,
           and matching on the bare name is far more robust than trying to keep
           up with them.
    """
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def collect_ledm(printer: Printer, config: AppConfig, password: str = "") -> list[Supply]:
    """
    PT-PT: Lê os consumíveis pelo XML de gestão do dispositivo (LEDM).

    EN-UK: Reads the supplies from the device management XML (LEDM).

    :return:
        PT-PT: Consumíveis encontrados; lista vazia se a estratégia falhar.
        EN-UK: Supplies found; an empty list if the strategy fails.
    """
    for path in LEDM_PATHS:
        body = _fetch(printer, path, config, password)
        if not body or "<" not in body:
            continue

        try:
            root = ElementTree.fromstring(body)
        except ElementTree.ParseError as exc:
            _log.debug("XML inválido em %s%s: %s", printer.ip, path, exc)
            continue

        supplies: list[Supply] = []

        for node in root.iter():
            if _strip_namespace(node.tag) not in ("ConsumableInfo", "SupplyInfo"):
                continue

            values: dict[str, str] = {}
            for child in node.iter():
                name = _strip_namespace(child.tag)
                if child.text and child.text.strip():
                    values[name] = child.text.strip()

            percent_text = (
                values.get("ConsumablePercentageLevelRemaining")
                or values.get("PercentageLevelRemaining")
                or values.get("PercentLifeRemaining")
            )
            percent: int | None = None
            if percent_text and percent_text.lstrip("-").isdigit():
                candidate = int(percent_text)
                if 0 <= candidate <= 100:
                    percent = candidate

            colour = normalise_colour(
                values.get("ConsumableLabelCode")
                or values.get("MarkerColor")
                or values.get("ConsumableSelectibilityNumber")
                or values.get("Color")
            )

            part = (
                values.get("ConsumableSelectibilityNumber")
                or values.get("ProductNumber")
                or values.get("ConsumableTypeEnum")
                or ""
            )

            # PT-PT: Ignorar entradas sem qualquer informação útil — o LEDM
            #        inclui nós de manutenção que não são consumíveis.
            # EN-UK: Skip entries with no useful information — LEDM includes
            #        maintenance nodes that are not supplies.
            if percent is None and not part:
                continue

            supplies.append(
                Supply(
                    colour=colour,
                    percent=percent,
                    part_number=part,
                    serial=values.get("SerialNumber", ""),
                    description=values.get("ConsumableLabelCode", ""),
                )
            )

        if any(supply.percent is not None for supply in supplies):
            return supplies

    return []


# ---------------------------------------------------------------------------
# PT-PT: Estratégia 2 — SNMP / EN-UK: Strategy 2 — SNMP
# ---------------------------------------------------------------------------


def collect_snmp(printer: Printer, config: AppConfig) -> list[Supply]:
    """
    PT-PT: Lê os consumíveis pela Printer-MIB.

           Não devolve a referência do cartucho — a Printer-MIB não a define —
           por isso a descrição textual é guardada, que é onde a HP costuma
           incluir algo como "Black Cartridge HP W1470X".

    EN-UK: Reads the supplies from the Printer-MIB.

           It does not return the cartridge part number — the Printer-MIB does
           not define one — so the textual description is kept, which is where
           HP usually embeds something like "Black Cartridge HP W1470X".

    :return:
        PT-PT: Consumíveis encontrados; lista vazia se falhar.
        EN-UK: Supplies found; an empty list on failure.
    """
    if not config.use_snmp:
        return []

    client = SnmpClient(
        printer.ip, community=config.snmp_community, timeout=config.snmp_timeout
    )

    descriptions = client.walk_column(OID_SUPPLY_DESCRIPTION)
    if not descriptions:
        return []

    maxima = client.walk_column(OID_SUPPLY_MAX)
    currents = client.walk_column(OID_SUPPLY_CURRENT)

    supplies: list[Supply] = []
    for index, description in enumerate(descriptions):
        text = str(description or "")

        maximum = maxima[index] if index < len(maxima) else None
        current = currents[index] if index < len(currents) else None

        percent = level_to_percent(
            current if isinstance(current, int) else None,
            maximum if isinstance(maximum, int) else None,
        )

        # PT-PT: Extrair a referência da descrição, quando lá estiver. As
        #        referências HP modernas seguem o padrão letra + 4 a 6 dígitos
        #        + letras opcionais (W1470X, CF287A, W9004MC).
        # EN-UK: Pull the part number out of the description when it is there.
        #        Modern HP part numbers follow letter + 4 to 6 digits + optional
        #        letters (W1470X, CF287A, W9004MC).
        match = re.search(r"\b([A-Z]{1,2}\d{3,6}[A-Z]{0,2})\b", text)

        supplies.append(
            Supply(
                colour=normalise_colour(text),
                percent=percent,
                part_number=match.group(1) if match else "",
                description=text,
            )
        )

    return supplies


# ---------------------------------------------------------------------------
# PT-PT: Estratégia 3 — HTML / EN-UK: Strategy 3 — HTML
# ---------------------------------------------------------------------------


class _TextExtractor(HTMLParser):
    """
    PT-PT: Extrai o texto visível de uma página HTML.

           Usa o analisador da biblioteca padrão em vez de expressões regulares
           sobre HTML, que se partem à primeira mudança de firmware. O conteúdo
           de script e style é descartado porque contém números que passariam
           por percentagens.

    EN-UK: Extracts the visible text from an HTML page.

           It uses the standard library parser rather than regular expressions
           over HTML, which break at the first firmware change. Script and style
           contents are discarded because they hold numbers that would pass for
           percentages.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.chunks: list[str] = []
        self._skip = False

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        if tag in ("script", "style"):
            self._skip = True

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style"):
            self._skip = False

    def handle_data(self, data: str) -> None:
        if not self._skip and data.strip():
            self.chunks.append(data.strip())

    @property
    def text(self) -> str:
        """
        PT-PT: Texto recolhido, separado por barras verticais para preservar a
               fronteira entre células de tabela.
        EN-UK: Collected text, separated by pipes to preserve the boundary
               between table cells.
        """
        return " | ".join(self.chunks)


def collect_html(printer: Printer, config: AppConfig, password: str = "") -> list[Supply]:
    """
    PT-PT: Lê os consumíveis raspando a página do EWS.

           Frágil por natureza: depende da apresentação, que muda com o
           firmware e com o idioma configurado na impressora. Só é usada quando
           as outras duas falharam.

    EN-UK: Reads the supplies by scraping the EWS page.

           Fragile by nature: it depends on the presentation, which changes with
           firmware and with the language configured on the printer. It is used
           only when the other two have failed.

    :return:
        PT-PT: Consumíveis encontrados; lista vazia se falhar.
        EN-UK: Supplies found; an empty list on failure.
    """
    for path in HTML_PATHS:
        body = _fetch(printer, path, config, password)
        if not body:
            continue

        parser = _TextExtractor()
        try:
            parser.feed(body)
        except (AssertionError, ValueError) as exc:
            _log.debug("HTML ilegível em %s%s: %s", printer.ip, path, exc)
            continue

        text = parser.text
        supplies: list[Supply] = []
        seen: set[str] = set()

        # PT-PT: Procurar "cor ... número%" numa janela curta de caracteres. A
        #        janela evita associar uma cor a uma percentagem que aparece
        #        muito mais à frente e não tem nada a ver com ela.
        # EN-UK: Look for "colour ... number%" within a short character window.
        #        The window stops a colour being paired with a percentage that
        #        appears far later and has nothing to do with it.
        pattern = re.compile(
            r"\b(preto|black|ciano|cyan|magenta|amarelo|yellow)\b.{0,60}?(\d{1,3})\s*%",
            re.IGNORECASE | re.DOTALL,
        )

        for match in pattern.finditer(text):
            colour = normalise_colour(match.group(1))
            percent = int(match.group(2))

            if percent > 100 or colour in seen:
                continue
            seen.add(colour)

            # PT-PT: Procurar uma referência de cartucho perto da percentagem.
            # EN-UK: Look for a cartridge part number near the percentage.
            window = text[match.start():match.end() + 80]
            part = re.search(r"\b([A-Z]{1,2}\d{3,6}[A-Z]{0,2})\b", window)

            supplies.append(
                Supply(
                    colour=colour,
                    percent=percent,
                    part_number=part.group(1) if part else "",
                    description=match.group(0)[:80],
                )
            )

        if supplies:
            return supplies

    return []


# ---------------------------------------------------------------------------
# PT-PT: Cascata / EN-UK: Cascade
# ---------------------------------------------------------------------------


def _has_usable_data(supplies: list[Supply]) -> bool:
    """
    PT-PT: Indica se uma estratégia produziu dados aproveitáveis.

           Exigir pelo menos uma percentagem conhecida é a condição que impede
           uma resposta vazia de contar como sucesso e bloquear as estratégias
           seguintes.

    EN-UK: Says whether a strategy produced usable data.

           Requiring at least one known percentage is the condition that stops
           an empty reply counting as success and blocking the later strategies.
    """
    return any(supply.percent is not None for supply in supplies)


def read_printer(printer: Printer, config: AppConfig, password: str = "") -> Printer:
    """
    PT-PT: Lê uma impressora, percorrendo as estratégias até uma resultar.

           Modifica e devolve o mesmo objecto, para que a interface possa
           manter a sua referência na tabela em vez de reconstruir as linhas.

    EN-UK: Reads one printer, walking the strategies until one succeeds.

           It mutates and returns the same object, so the interface can keep its
           reference in the table rather than rebuilding the rows.

    :param printer:
        PT-PT: Impressora a ler. / EN-UK: Printer to read.
    :param config:
        PT-PT: Configuração activa. / EN-UK: Active configuration.
    :param password:
        PT-PT: Password do EWS, se necessária.
        EN-UK: EWS password, if required.
    :return:
        PT-PT: A mesma impressora, com o estado actualizado.
        EN-UK: The same printer, with its state updated.
    """
    printer.reset_reading()
    printer.last_checked = datetime.now()

    strategies: tuple[tuple[str, object], ...] = (
        ("LEDM", lambda: collect_ledm(printer, config, password)),
        ("SNMP", lambda: collect_snmp(printer, config)),
        ("HTML", lambda: collect_html(printer, config, password)),
    )

    for name, run in strategies:
        try:
            supplies = run()  # type: ignore[operator]
        except Exception as exc:  # noqa: BLE001
            # PT-PT: Uma estratégia que rebente não pode impedir as seguintes.
            # EN-UK: A strategy that blows up must not block the others.
            _log.debug("Estratégia %s falhou em %s: %s", name, printer.ip, exc)
            continue

        if _has_usable_data(supplies):
            printer.supplies = supplies
            printer.method = name
            printer.reachability = Reachability.ONLINE
            _log.info(
                "%s lida por %s: %d consumíveis.",
                printer.display_name, name, len(supplies),
            )
            return printer

    # PT-PT: Nenhuma estratégia deu níveis. Distinguir "não responde" de
    #        "responde mas não dá dados" poupa horas de diagnóstico.
    # EN-UK: No strategy returned levels. Telling "does not answer" from
    #        "answers but gives no data" saves hours of diagnosis.
    from .discovery import PORT_HTTP, PORT_HTTPS, PORT_RAW, probe_port

    alive = any(
        probe_port(printer.ip, port, config.tcp_timeout)
        for port in (PORT_RAW, PORT_HTTPS, PORT_HTTP)
    )

    if alive:
        printer.reachability = Reachability.NO_DATA
        printer.message = (
            "Responde na rede mas não devolveu níveis. "
            "Verifique se o EWS pede autenticação ou se o SNMP está desligado."
        )
    else:
        printer.reachability = Reachability.OFFLINE
        printer.message = (
            "Sem resposta na rede. Confirme o IP, a VLAN e se está ligada."
        )

    _log.warning("%s: %s", printer.display_name, printer.message)
    return printer
