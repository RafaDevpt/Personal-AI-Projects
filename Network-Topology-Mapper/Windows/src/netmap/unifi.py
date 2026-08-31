#!/usr/bin/env python3
"""
PT-PT: Cliente do controlador UniFi.

       O controlador é o melhor ponto de partida que existe, quando existe. Ele
       já sabe o que adoptou, já sabe o endereço de cada equipamento, e — o que
       poupa mais trabalho — já sabe em que switch e em que porta está cada
       cliente com fios. É informação que de outra forma se obtém cruzando
       tabelas MAC de meia dúzia de switches.

       O que ele **não** sabe é o que não é UniFi. Numa rede com Aruba e Cisco
       pelo meio, o controlador vê o seu próprio mundo e mais nada. Daí o
       desenho: pergunta-se-lhe primeiro para semear o mapa, e a partir daí é o
       LLDP que leva o resto do caminho.

       Sobre o certificado: praticamente todos os controladores UniFi usam um
       certificado auto-assinado, e a verificação de TLS falha contra eles. A
       opção de desligar a verificação existe, mas está desligada por omissão e
       a mensagem de erro explica o que se perde ao usá-la. O contrário — não
       verificar por omissão porque é mais cómodo — é como estas coisas
       normalmente acabam.

EN-UK: UniFi controller client.

       The controller is the best starting point there is, when there is one. It
       already knows what it adopted, already knows every device's address and —
       the biggest saving — already knows which switch and which port every
       wired client sits on. That is information otherwise obtained by crossing
       the MAC tables of half a dozen switches.

       What it does **not** know is anything that is not UniFi. On a network
       with Aruba and Cisco in the mix, the controller sees its own world and
       nothing else. Hence the design: it is asked first to seed the map, and
       from there LLDP carries the rest of the way.

       On the certificate: virtually every UniFi controller uses a self-signed
       certificate, and TLS verification fails against them. The option to turn
       verification off exists, but it is off by default and the error message
       explains what is given up by using it. The opposite — not verifying by
       default because it is more convenient — is how these things usually end
       up.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from .models import normalise_mac

logger = logging.getLogger(__name__)

DEFAULT_SITE = "default"


class UnifiError(RuntimeError):
    """PT-PT: Falha a falar com o controlador. / EN-UK: Failure talking to the controller."""


@dataclass
class UnifiDevice:
    """
    PT-PT: Um equipamento adoptado pelo controlador.
    EN-UK: A device adopted by the controller.
    """

    mac: str
    name: str = ""
    ip: str = ""
    model: str = ""
    kind: str = ""
    version: str = ""
    uplink_mac: str = ""
    uplink_port: str = ""
    poe_by_port: dict[str, float] = field(default_factory=dict)

    @property
    def is_switch(self) -> bool:
        """PT-PT: Se é um switch. / EN-UK: Whether it is a switch."""
        return self.kind == "usw"

    @property
    def is_access_point(self) -> bool:
        """PT-PT: Se é um ponto de acesso. / EN-UK: Whether it is an access point."""
        return self.kind == "uap"


@dataclass
class UnifiClient:
    """
    PT-PT: Um cliente que o controlador conhece.

           Para os clientes com fios, o `switch_mac` e o `switch_port` são a
           resposta directa à pergunta deste programa — sem cruzar nada.

    EN-UK: A client the controller knows about.

           For wired clients, `switch_mac` and `switch_port` are the direct
           answer to this program's question — with nothing to cross-reference.
    """

    mac: str
    ip: str = ""
    hostname: str = ""
    wired: bool = True
    switch_mac: str = ""
    switch_port: str = ""
    access_point_mac: str = ""
    vlan: int | None = None


class UnifiController:
    """
    PT-PT: Sessão com um controlador UniFi.

           Fala os dois dialectos: o controlador clássico (porta 8443,
           `/api/login`) e o UniFi OS das UDM e CloudKey de segunda geração
           (porta 443, `/api/auth/login`, com tudo por baixo de
           `/proxy/network`). Tenta o UniFi OS primeiro porque é o que existe
           em equipamento novo, e recai no clássico.

    EN-UK: A session with a UniFi controller.

           It speaks both dialects: the classic controller (port 8443,
           `/api/login`) and the UniFi OS of UDMs and second-generation
           CloudKeys (port 443, `/api/auth/login`, everything under
           `/proxy/network`). UniFi OS is tried first because it is what new
           equipment runs, falling back to classic.
    """

    def __init__(
        self,
        base_url: str,
        site: str = DEFAULT_SITE,
        verify_tls: bool = True,
        timeout: int = 20,
    ) -> None:
        """
        :param base_url:
            PT-PT: Endereço do controlador, com esquema e porta.
            EN-UK: Controller address, with scheme and port.
        :param site:
            PT-PT: Nome interno do sítio. Quase sempre `default`, mesmo quando
                   na interface tem outro nome.
            EN-UK: The site's internal name. Nearly always `default`, even when
                   the interface shows another name.
        :param verify_tls:
            PT-PT: Verificar o certificado. Ver o cabeçalho do módulo.
            EN-UK: Verify the certificate. See the module header.
        :param timeout:
            PT-PT: Segundos por pedido. / EN-UK: Seconds per request.
        """
        self.base_url = base_url.rstrip("/")
        self.site = site or DEFAULT_SITE
        self.verify_tls = verify_tls
        self.timeout = timeout
        self._session: Any = None
        self._prefix = ""

    # -----------------------------------------------------------------------

    def login(self, username: str, password: str) -> None:
        """
        PT-PT: Autentica-se no controlador.

        EN-UK: Authenticates against the controller.

        :param username:
            PT-PT: Utilizador com permissão de leitura.
            EN-UK: A user with read permission.
        :param password:
            PT-PT: Palavra-passe. / EN-UK: Password.
        :raises UnifiError:
            PT-PT: Se o controlador não responder, recusar as credenciais, ou o
                   certificado não for de confiança.
            EN-UK: If the controller does not answer, refuses the credentials,
                   or the certificate is not trusted.
        """
        try:
            import requests
        except ImportError as exc:
            raise UnifiError(
                "O requests não está instalado. Instale com: pip install requests"
            ) from exc

        if not self.verify_tls:
            logger.warning(
                "Verificação de certificado desligada para %s: a ligação está cifrada mas "
                "não há garantia de que o controlador seja quem diz ser.",
                self.base_url,
            )

        self._session = requests.Session()
        self._session.verify = self.verify_tls

        credenciais = {"username": username, "password": password}

        # PT-PT: UniFi OS primeiro; se não existir, o clássico.
        # EN-UK: UniFi OS first; if absent, the classic one.
        for caminho, prefixo in (("/api/auth/login", "/proxy/network"), ("/api/login", "")):
            try:
                resposta = self._session.post(
                    f"{self.base_url}{caminho}", json=credenciais, timeout=self.timeout
                )
            except requests.exceptions.SSLError as exc:
                raise UnifiError(
                    f"O certificado de {self.base_url} não é de confiança. "
                    "Os controladores UniFi usam certificados auto-assinados: instale o "
                    "certificado do controlador na máquina, ou desligue a verificação nas "
                    "definições sabendo que deixa de haver garantia de identidade."
                ) from exc
            except requests.exceptions.RequestException as exc:
                raise UnifiError(f"Não consegui falar com {self.base_url}: {exc}") from exc

            if resposta.status_code == 404:
                continue
            if resposta.status_code in (401, 403):
                raise UnifiError("O controlador recusou as credenciais.")
            if not resposta.ok:
                raise UnifiError(f"O controlador respondeu {resposta.status_code}.")

            self._prefix = prefixo
            logger.info("Autenticado em %s (%s)", self.base_url, prefixo or "clássico")
            return

        raise UnifiError(
            f"{self.base_url} respondeu, mas não parece um controlador UniFi "
            "(nem /api/auth/login nem /api/login existem)."
        )

    def close(self) -> None:
        """PT-PT: Fecha a sessão. / EN-UK: Closes the session."""
        if self._session is not None:
            try:
                self._session.close()
            except Exception:  # noqa: BLE001 - PT-PT: fechar nunca deve rebentar
                logger.debug("Falha ao fechar a sessão do controlador", exc_info=True)
            self._session = None

    def __enter__(self) -> UnifiController:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    # -----------------------------------------------------------------------

    def devices(self) -> list[UnifiDevice]:
        """
        PT-PT: Os equipamentos adoptados.

        EN-UK: The adopted devices.

        :return:
            PT-PT: Switches, pontos de acesso e gateways.
            EN-UK: Switches, access points and gateways.
        """
        return [_device_from(entrada) for entrada in self._get(f"/api/s/{self.site}/stat/device")]

    def clients(self) -> list[UnifiClient]:
        """
        PT-PT: Os clientes activos, com e sem fios.

        EN-UK: The active clients, wired and wireless.

        :return:
            PT-PT: Clientes, já com o switch e a porta quando são com fios.
            EN-UK: Clients, with switch and port already filled for wired ones.
        """
        return [_client_from(entrada) for entrada in self._get(f"/api/s/{self.site}/stat/sta")]

    def _get(self, path: str) -> list[dict[str, Any]]:
        """
        PT-PT: Um GET à API, já com o prefixo do dialecto certo.
        EN-UK: A GET to the API, with the right dialect's prefix applied.
        """
        if self._session is None:
            raise UnifiError("Não há sessão aberta com o controlador.")

        import requests

        url = f"{self.base_url}{self._prefix}{path}"
        try:
            resposta = self._session.get(url, timeout=self.timeout)
        except requests.exceptions.RequestException as exc:
            raise UnifiError(f"Falha em {path}: {exc}") from exc

        if resposta.status_code in (401, 403):
            raise UnifiError("A sessão com o controlador expirou ou não tem permissão.")
        if not resposta.ok:
            raise UnifiError(f"O controlador respondeu {resposta.status_code} em {path}.")

        try:
            corpo = resposta.json()
        except ValueError as exc:
            raise UnifiError(f"O controlador devolveu algo que não é JSON em {path}.") from exc

        dados = corpo.get("data") if isinstance(corpo, dict) else None
        return dados if isinstance(dados, list) else []


# ---------------------------------------------------------------------------
# PT-PT: Conversão do JSON do controlador para os modelos.
# EN-UK: Converting the controller's JSON into the models.
# ---------------------------------------------------------------------------


def _device_from(entry: dict[str, Any]) -> UnifiDevice:
    """PT-PT: Um equipamento. / EN-UK: One device."""
    uplink = entry.get("uplink") or {}
    return UnifiDevice(
        mac=normalise_mac(str(entry.get("mac", ""))),
        name=str(entry.get("name") or ""),
        ip=str(entry.get("ip") or ""),
        model=str(entry.get("model") or ""),
        kind=str(entry.get("type") or ""),
        version=str(entry.get("version") or ""),
        uplink_mac=normalise_mac(str(uplink.get("uplink_mac", ""))),
        uplink_port=_port_text(uplink.get("uplink_remote_port")),
        poe_by_port=_poe_from_ports(entry.get("port_table")),
    )


def _client_from(entry: dict[str, Any]) -> UnifiClient:
    """PT-PT: Um cliente. / EN-UK: One client."""
    # PT-PT: O controlador usa `is_wired`; quando falta, a presença de `ap_mac`
    #        diz que é sem fios.
    # EN-UK: The controller uses `is_wired`; when absent, an `ap_mac` says it is
    #        wireless.
    com_fios = entry.get("is_wired")
    if com_fios is None:
        com_fios = not entry.get("ap_mac")

    return UnifiClient(
        mac=normalise_mac(str(entry.get("mac", ""))),
        ip=str(entry.get("ip") or ""),
        hostname=str(entry.get("hostname") or entry.get("name") or ""),
        wired=bool(com_fios),
        switch_mac=normalise_mac(str(entry.get("sw_mac", ""))),
        switch_port=_port_text(entry.get("sw_port")),
        access_point_mac=normalise_mac(str(entry.get("ap_mac", ""))),
        vlan=_as_vlan(entry.get("vlan")),
    )


def _poe_from_ports(port_table: Any) -> dict[str, float]:
    """
    PT-PT: O consumo de PoE por porta, tal como o controlador o reporta.
           A chave é o número da porta em texto, porque é assim que ele aparece
           nos clientes (`sw_port`).
    EN-UK: PoE draw per port, as the controller reports it. The key is the port
           number as text, because that is how it appears on clients
           (`sw_port`).
    """
    if not isinstance(port_table, list):
        return {}

    consumo: dict[str, float] = {}
    for porta in port_table:
        if not isinstance(porta, dict):
            continue
        indice = _port_text(porta.get("port_idx"))
        watts = porta.get("poe_power")
        if not indice or watts in (None, ""):
            continue
        try:
            consumo[indice] = float(watts)
        except (TypeError, ValueError):
            continue
    return consumo


def _port_text(value: Any) -> str:
    """PT-PT: O número da porta como texto. / EN-UK: The port number as text."""
    if value in (None, ""):
        return ""
    return str(value).strip()


def _as_vlan(value: Any) -> int | None:
    """PT-PT: A VLAN, se for um número plausível. / EN-UK: The VLAN, if a plausible number."""
    try:
        numero = int(value)
    except (TypeError, ValueError):
        return None
    return numero if 1 <= numero <= 4094 else None
