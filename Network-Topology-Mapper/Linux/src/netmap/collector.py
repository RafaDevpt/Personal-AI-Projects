#!/usr/bin/env python3
"""
PT-PT: Recolha por SSH.

       Este módulo é o único que abre ligações, e tem uma propriedade que vale
       a pena garantir por código e não por boa vontade: **só corre comandos de
       leitura**. Antes de enviar qualquer coisa, o comando é verificado contra
       uma lista de verbos permitidos. Um `show`, um `display`, um
       `telnet localhost` para chegar à CLI de um UniFi — mais nada.

       Não é paranóia. É que um programa de mapeamento entra em toda a
       infra-estrutura de uma casa, muitas vezes com credenciais de
       administrador e fora de horas, sem ninguém a olhar. A garantia de que
       não escreve não pode depender de nenhum programador se lembrar: tem de
       estar no caminho de execução.

EN-UK: SSH collection.

       This is the only module that opens connections, and it has a property
       worth guaranteeing in code rather than in good intentions: **it only
       runs read commands**. Before anything is sent, the command is checked
       against a list of allowed verbs. A `show`, a `display`, a
       `telnet localhost` to reach a UniFi's CLI — nothing else.

       This is not paranoia. A mapping program enters an entire property's
       infrastructure, often with administrative credentials and out of hours,
       with nobody watching. The guarantee that it does not write cannot depend
       on a programmer remembering: it has to sit in the execution path.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .models import Credentials, DeviceFacts, NetworkDevice, Platform
from .parsers import detect_platform, get_parser

logger = logging.getLogger(__name__)

# PT-PT: Os únicos verbos que este programa pode enviar. Tudo o resto é recusado
#        antes de chegar à rede.
# EN-UK: The only verbs this program may send. Anything else is refused before
#        it reaches the network.
READ_ONLY_VERBS = ("show", "display", "get", "dir", "more", "telnet localhost")

# PT-PT: Comando para descobrir com o que se está a falar, quando não se sabe.
#        O `show version` existe nas três plataformas.
# EN-UK: Command to find out what we are talking to, when it is not known.
#        `show version` exists on all three platforms.
PROBE_COMMAND = "show version"


class CollectorError(RuntimeError):
    """PT-PT: Falha na recolha, com a razão em português. / EN-UK: Collection failure."""


class UnsafeCommandError(CollectorError):
    """
    PT-PT: Alguém tentou correr um comando que não é de leitura. É um erro de
           programação, não de rede, e por isso rebenta em vez de avisar.
    EN-UK: Somebody tried to run a command that is not a read. It is a
           programming error, not a network one, so it raises rather than warns.
    """


def is_read_only(command: str) -> bool:
    """
    PT-PT: Se o comando é seguro de correr num equipamento de produção.

    EN-UK: Whether the command is safe to run on a production device.

    :param command:
        PT-PT: O comando tal como seria enviado. / EN-UK: The command as it would be sent.
    :return:
        PT-PT: True se começar por um verbo de leitura.
        EN-UK: True when it starts with a read verb.
    """
    limpo = command.strip().lower()
    if not limpo:
        return False
    # PT-PT: Um `|` pode encadear qualquer coisa a seguir a um `show`.
    # EN-UK: A `|` can chain anything after a `show`.
    if any(simbolo in limpo for simbolo in (";", "&&", "||")):
        return False
    return limpo.startswith(READ_ONLY_VERBS)


def assert_read_only(commands: dict[str, str]) -> None:
    """
    PT-PT: Verifica todos os comandos antes de abrir a ligação.

    EN-UK: Checks every command before the connection is opened.

    :raises UnsafeCommandError:
        PT-PT: Ao primeiro comando que não seja de leitura.
        EN-UK: On the first command that is not a read.
    """
    for chave, comando in commands.items():
        if not is_read_only(comando):
            raise UnsafeCommandError(
                f"O comando de '{chave}' não é de leitura e foi recusado: {comando!r}"
            )


def netmiko_available() -> bool:
    """PT-PT: Se o Netmiko está instalado. / EN-UK: Whether Netmiko is installed."""
    try:
        import netmiko  # noqa: F401
    except ImportError:
        return False
    return True


@dataclass
class CollectionResult:
    """
    PT-PT: O que uma sessão produziu, incluindo os comandos que falharam.

           Guardar as falhas por comando importa: um switch que respondeu a
           tudo menos ao PoE não é o mesmo que um switch que não respondeu a
           nada, e o relatório tem de conseguir dizer a diferença.

    EN-UK: What one session produced, failed commands included.

           Recording per-command failures matters: a switch that answered
           everything but PoE is not the same as one that answered nothing, and
           the report has to be able to tell the difference.
    """

    facts: DeviceFacts
    platform: Platform
    failed_commands: list[str]
    raw: dict[str, str]


def collect(
    device: NetworkDevice,
    credentials: Credentials,
    timeout: int = 30,
    unifi_cli_hop: bool = False,
) -> CollectionResult:
    """
    PT-PT: Abre uma sessão, corre os comandos de leitura e interpreta o que vem.

    EN-UK: Opens a session, runs the read commands and interprets what comes
           back.

    :param device:
        PT-PT: Equipamento a contactar. Se a plataforma for desconhecida, é
               descoberta antes de mais nada.
        EN-UK: Device to contact. If the platform is unknown, it is discovered
               first.
    :param credentials:
        PT-PT: Credenciais da sessão. / EN-UK: Session credentials.
    :param timeout:
        PT-PT: Segundos até desistir da ligação. / EN-UK: Seconds before giving up.
    :param unifi_cli_hop:
        PT-PT: Nalguns modelos UniFi a CLI do switch só se alcança com
               `telnet localhost` depois do SSH. Isto activa esse salto.
        EN-UK: On some UniFi models the switch CLI is only reachable via
               `telnet localhost` after SSH. This enables that hop.
    :return:
        PT-PT: Os factos lidos e o que falhou. / EN-UK: The facts read and what failed.
    :raises CollectorError:
        PT-PT: Se não conseguir ligar-se ou autenticar-se.
        EN-UK: If it cannot connect or authenticate.
    """
    conexao = _connect(device, credentials, timeout)
    try:
        if unifi_cli_hop:
            _hop_to_unifi_cli(conexao)

        plataforma = device.platform
        bruto: dict[str, str] = {}

        if plataforma is Platform.UNKNOWN:
            plataforma, banner = _probe(conexao)
            bruto["version"] = banner
            if plataforma is Platform.UNKNOWN:
                raise CollectorError(
                    f"{device.label}: respondeu, mas não reconheci a plataforma. "
                    "Indique-a no inventário."
                )

        leitor = get_parser(plataforma)
        assert_read_only(leitor.commands)

        falhados: list[str] = []
        for chave, comando in leitor.commands.items():
            if chave in bruto:
                continue
            try:
                bruto[chave] = str(conexao.send_command(comando, read_timeout=90))
            except Exception as exc:  # noqa: BLE001 - PT-PT: um comando falhado não pára a recolha
                logger.warning("%s: '%s' falhou (%s)", device.label, comando, exc)
                falhados.append(comando)
                bruto[chave] = ""

        return CollectionResult(
            facts=leitor.parse(bruto),
            platform=plataforma,
            failed_commands=falhados,
            raw=bruto,
        )
    finally:
        _close(conexao, device.label)


def _connect(device: NetworkDevice, credentials: Credentials, timeout: int) -> Any:
    """PT-PT: Abre a sessão SSH. / EN-UK: Opens the SSH session."""
    try:
        from netmiko import ConnectHandler
        from netmiko.exceptions import NetmikoAuthenticationException, NetmikoTimeoutException
    except ImportError as exc:
        raise CollectorError(
            "O netmiko não está instalado. Instale com: pip install netmiko"
        ) from exc

    # PT-PT: Com plataforma desconhecida usa-se o dialecto genérico do Cisco,
    #        que é o que dá menos problemas a chegar a uma prompt e a correr um
    #        `show version`. Depois disso já se sabe com quem se está a falar.
    # EN-UK: With an unknown platform the generic Cisco dialect is used, being
    #        the one that most reliably reaches a prompt and runs a
    #        `show version`. After that we know who we are talking to.
    tipo = (
        device.platform.netmiko_device_type
        if device.platform is not Platform.UNKNOWN
        else "cisco_ios"
    )

    logger.info("A ligar a %s (%s)", device.label, device.host)
    try:
        return ConnectHandler(
            device_type=tipo,
            host=device.host,
            username=credentials.username,
            password=credentials.password,
            secret=credentials.enable_password or credentials.password,
            conn_timeout=timeout,
            fast_cli=False,
        )
    except NetmikoAuthenticationException as exc:
        raise CollectorError(f"{device.label}: credenciais recusadas.") from exc
    except NetmikoTimeoutException as exc:
        raise CollectorError(f"{device.label}: sem resposta em {timeout}s ({device.host}).") from exc
    except Exception as exc:  # noqa: BLE001 - PT-PT: o Netmiko lança de tudo
        raise CollectorError(f"{device.label}: {exc}") from exc


def _probe(connection: Any) -> tuple[Platform, str]:
    """
    PT-PT: Descobre a plataforma perguntando a versão.
    EN-UK: Discovers the platform by asking for the version.
    """
    try:
        banner = str(connection.send_command(PROBE_COMMAND, read_timeout=45))
    except Exception as exc:  # noqa: BLE001
        raise CollectorError(f"Não respondeu a '{PROBE_COMMAND}': {exc}") from exc
    return detect_platform(banner), banner


def _hop_to_unifi_cli(connection: Any) -> None:
    """
    PT-PT: Salta para a CLI do switch num UniFi.

           Nos modelos em que o SSH cai numa shell do Linux, a CLI de comutação
           está atrás de um `telnet localhost`. Se falhar, não é fatal: pode
           ser um modelo que já dá a CLI directamente.

    EN-UK: Hops to the switch CLI on a UniFi.

           On models where SSH lands in a Linux shell, the switching CLI sits
           behind a `telnet localhost`. Failing is not fatal: it may be a model
           that gives the CLI directly.
    """
    try:
        connection.write_channel("telnet localhost\n")
        connection.read_until_pattern(pattern=r"[>#]", read_timeout=20)
    except Exception:  # noqa: BLE001 - PT-PT: nem todos os modelos precisam
        logger.debug("O salto para a CLI do UniFi não foi necessário ou falhou", exc_info=True)


def _close(connection: Any, label: str) -> None:
    """PT-PT: Fecha a sessão. / EN-UK: Closes the session."""
    try:
        connection.disconnect()
    except Exception:  # noqa: BLE001 - PT-PT: fechar nunca deve rebentar
        logger.debug("Falha ao fechar a ligação a %s", label, exc_info=True)
