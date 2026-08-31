#!/usr/bin/env python3
"""
PT-PT: Sessão SSH com o equipamento.

       Este módulo é o único que fala com a rede, e é o único onde uma
       distracção deixa um piso sem serviço. Daí as três regras que o governam:

       1. **Ler antes de escrever.** Nenhum envio acontece sem que a
          configuração actual tenha sido lida e gravada primeiro. Se a leitura
          falhar, o envio não se faz — não há pressa que justifique não ter
          para onde voltar.
       2. **Simular por omissão.** `push()` nasce em `dry_run=True`. Quem quer
          escrever a sério tem de o dizer explicitamente.
       3. **Nunca registar segredos.** As credenciais não aparecem no registo
          nem em `repr`, e o filtro do módulo de registo apanha o que escapar.

       O Netmiko é importado dentro das funções, e não no topo. A geração de
       ficheiros — que é a parte que a maioria das pessoas usa — não deve
       exigir a instalação de uma biblioteca de SSH.

EN-UK: SSH session with the device.

       This module is the only one that talks to the network, and the only one
       where a lapse takes a floor out of service. Hence the three rules that
       govern it:

       1. **Read before writing.** No push happens unless the current
          configuration has been read and saved first. If the read fails, the
          push does not happen — no urgency justifies having nowhere to go back
          to.
       2. **Simulate by default.** `push()` starts at `dry_run=True`. Anyone
          wanting to write for real has to say so explicitly.
       3. **Never log secrets.** Credentials appear neither in the log nor in
          `repr`, and the logging module's filter catches whatever escapes.

       Netmiko is imported inside the functions, not at the top. Generating
       files — the part most people use — must not require an SSH library to be
       installed.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
import socket
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import Credentials, Device, Platform

logger = logging.getLogger(__name__)

# PT-PT: O que cada plataforma responde a "mostra-me a configuração".
#        Coincidem hoje, mas ter a tabela evita a suposição de que coincidem
#        sempre — o AOS-CX já teve `show running-config current-context`.
# EN-UK: What each platform answers to "show me the configuration". They match
#        today, but keeping the table avoids assuming they always will —
#        AOS-CX has had `show running-config current-context`.
_SHOW_RUNNING: dict[Platform, str] = {
    Platform.ARUBA_CX: "show running-config",
    Platform.CISCO_IOS: "show running-config",
    Platform.UBIQUITI_EDGESWITCH: "show running-config",
    Platform.UBIQUITI_UNIFI: "show running-config",
}

# PT-PT: Linhas que embrulham a configuração e que o Netmiko já trata sozinho.
# EN-UK: Lines that wrap the configuration and that Netmiko already handles.
_WRAPPER_COMMANDS = {"configure terminal", "configure", "conf t", "end", "exit", "write memory"}


class TransportError(RuntimeError):
    """
    PT-PT: Falha ao falar com o equipamento, com a razão em português.
    EN-UK: Failure talking to the device, with the reason in Portuguese.
    """


def netmiko_available() -> bool:
    """
    PT-PT: Se o Netmiko está instalado. A interface pergunta isto antes de
           mostrar as abas que precisam de rede, para explicar em vez de falhar.
    EN-UK: Whether Netmiko is installed. The interface asks this before showing
           the tabs that need the network, so it can explain rather than fail.
    """
    try:
        import netmiko  # noqa: F401
    except ImportError:
        return False
    return True


def reachable(host: str, port: int = 22, timeout: float = 3.0) -> bool:
    """
    PT-PT: Se a porta de SSH aceita ligação. É um teste de TCP, não de
           autenticação: responde depressa e não precisa de credenciais, o que
           o torna útil para varrer um inventário inteiro antes de começar.

    EN-UK: Whether the SSH port accepts a connection. This is a TCP test, not
           an authentication one: it answers quickly and needs no credentials,
           which makes it useful for sweeping a whole inventory before starting.

    :param host:
        PT-PT: Endereço ou nome. / EN-UK: Address or name.
    :param port:
        PT-PT: Porta de TCP. / EN-UK: TCP port.
    :param timeout:
        PT-PT: Segundos a esperar. / EN-UK: Seconds to wait.
    :return:
        PT-PT: True se a porta respondeu. / EN-UK: True if the port answered.
    """
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def commands_for_push(config_text: str) -> list[str]:
    """
    PT-PT: Reduz um ficheiro gerado à lista de comandos a enviar.

           Tira os comentários, as linhas vazias e o embrulho de entrada e
           saída do modo de configuração, que o Netmiko põe por si. Os `exit`
           que fecham blocos de interface no EdgeSwitch ficam — só os do fim é
           que são retirados.

    EN-UK: Reduces a generated file to the list of commands to send.

           Strips comments, blank lines and the configuration-mode wrapper,
           which Netmiko supplies itself. The `exit` lines closing EdgeSwitch
           interface blocks stay — only the trailing ones are removed.

    :param config_text:
        PT-PT: Ficheiro gerado. / EN-UK: Generated file.
    :return:
        PT-PT: Comandos, pela ordem em que devem ser enviados.
        EN-UK: Commands, in the order they must be sent.
    """
    linhas = [
        line.rstrip()
        for line in config_text.splitlines()
        if line.strip() and not line.strip().startswith("!")
    ]

    if linhas and linhas[0].strip().lower() in _WRAPPER_COMMANDS:
        linhas = linhas[1:]

    while linhas and linhas[-1].strip().lower() in _WRAPPER_COMMANDS:
        linhas.pop()

    return linhas


@dataclass
class PushResult:
    """
    PT-PT: O que aconteceu num envio, para poder ser mostrado e arquivado.
    EN-UK: What happened during a push, so it can be shown and filed.
    """

    device: str
    dry_run: bool
    commands: list[str] = field(default_factory=list)
    backup_path: Path | None = None
    output: str = ""
    saved: bool = False

    @property
    def summary(self) -> str:
        """PT-PT: Uma linha para o registo. / EN-UK: A single line for the log."""
        modo = "simulacao" if self.dry_run else "envio"
        return f"{self.device}: {modo}, {len(self.commands)} comandos"


class SwitchSession:
    """
    PT-PT: Uma sessão SSH aberta com um equipamento.

           Usar como gestor de contexto — a ligação fecha-se sozinha, inclusive
           se rebentar a meio:

               with SwitchSession(device, creds) as sessao:
                   actual = sessao.read_running_config()

    EN-UK: An open SSH session with a device.

           Use as a context manager — the connection closes itself, including
           on the way out of an exception:

               with SwitchSession(device, creds) as session:
                   current = session.read_running_config()
    """

    def __init__(self, device: Device, credentials: Credentials, timeout: int = 30) -> None:
        """
        :param device:
            PT-PT: Equipamento a contactar. / EN-UK: Device to contact.
        :param credentials:
            PT-PT: Credenciais da sessão. / EN-UK: Session credentials.
        :param timeout:
            PT-PT: Segundos até desistir da ligação.
            EN-UK: Seconds before giving up on the connection.
        """
        self.device = device
        self._credentials = credentials
        self._timeout = timeout
        self._connection: Any = None

    def __enter__(self) -> SwitchSession:
        self.connect()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def connect(self) -> None:
        """
        PT-PT: Abre a ligação.

        EN-UK: Opens the connection.

        :raises TransportError:
            PT-PT: Se o Netmiko faltar, ou o equipamento não responder, ou
                   recusar as credenciais.
            EN-UK: If Netmiko is missing, or the device does not answer, or
                   refuses the credentials.
        """
        try:
            from netmiko import ConnectHandler
            from netmiko.exceptions import NetmikoAuthenticationException, NetmikoTimeoutException
        except ImportError as exc:
            raise TransportError(
                "O netmiko não está instalado. Instale com: pip install netmiko"
            ) from exc

        logger.info("A ligar a %s (%s)", self.device.name, self.device.host)
        try:
            self._connection = ConnectHandler(
                device_type=self.device.platform.netmiko_device_type,
                host=self.device.host,
                port=self.device.port,
                username=self._credentials.username,
                password=self._credentials.password,
                secret=self._credentials.enable_password or self._credentials.password,
                conn_timeout=self._timeout,
                fast_cli=False,
            )
        except NetmikoAuthenticationException as exc:
            raise TransportError(f"{self.device.name}: credenciais recusadas.") from exc
        except NetmikoTimeoutException as exc:
            raise TransportError(
                f"{self.device.name}: sem resposta em {self._timeout}s ({self.device.host})."
            ) from exc
        except Exception as exc:  # noqa: BLE001 - PT-PT: o Netmiko lança de tudo / EN-UK: Netmiko raises anything
            raise TransportError(f"{self.device.name}: {exc}") from exc

    def close(self) -> None:
        """PT-PT: Fecha a ligação, se estiver aberta. / EN-UK: Closes the connection, if open."""
        if self._connection is not None:
            try:
                self._connection.disconnect()
            except Exception:  # noqa: BLE001 - PT-PT: fechar nunca deve rebentar / EN-UK: closing must never blow up
                logger.debug("Falha ao fechar a ligação a %s", self.device.name, exc_info=True)
            self._connection = None

    def _require_connection(self) -> Any:
        if self._connection is None:
            raise TransportError("A sessão não está aberta.")
        return self._connection

    def read_running_config(self) -> str:
        """
        PT-PT: Lê a configuração que está a correr.

        EN-UK: Reads the running configuration.

        :return:
            PT-PT: O texto tal como o equipamento o devolveu.
            EN-UK: The text exactly as the device returned it.
        """
        connection = self._require_connection()
        comando = _SHOW_RUNNING[self.device.platform]
        logger.info("A ler a configuração de %s", self.device.name)
        return str(connection.send_command(comando, read_timeout=90))

    def backup(self, folder: Path, moment: datetime | None = None) -> Path:
        """
        PT-PT: Lê a configuração e grava-a com data no nome.

               O nome leva a data até ao segundo por uma razão prática: numa
               intervenção fazem-se vários backups do mesmo switch em poucos
               minutos, e sobrepor o anterior seria perder exactamente o que
               interessa.

        EN-UK: Reads the configuration and saves it with the date in the name.

               The name carries the date down to the second for a practical
               reason: during one intervention several backups of the same
               switch happen within minutes, and overwriting the previous one
               would lose exactly what matters.

        :param folder:
            PT-PT: Pasta de destino, criada se faltar.
            EN-UK: Destination folder, created when missing.
        :param moment:
            PT-PT: Data a usar no nome. Serve para os testes.
            EN-UK: Date to use in the name. Useful for tests.
        :return:
            PT-PT: Caminho do ficheiro gravado. / EN-UK: Path of the saved file.
        """
        conteudo = self.read_running_config()
        folder.mkdir(parents=True, exist_ok=True)
        carimbo = (moment or datetime.now()).strftime("%Y%m%d-%H%M%S")
        destino = folder / f"{_safe_filename(self.device.name)}-{carimbo}.cfg"
        destino.write_text(conteudo, encoding="utf-8")
        logger.info("Configuração de %s guardada em %s", self.device.name, destino)
        return destino

    def push(
        self,
        config_text: str,
        backup_folder: Path,
        dry_run: bool = True,
        save: bool = True,
    ) -> PushResult:
        """
        PT-PT: Envia a configuração para o equipamento.

               Faz sempre o backup primeiro, mesmo em simulação — é durante a
               simulação que se quer ter o antes guardado, para o comparar.

        EN-UK: Pushes the configuration to the device.

               It always takes the backup first, even in simulation — the
               simulation is exactly when you want the "before" on disk, to
               compare against.

        :param config_text:
            PT-PT: Ficheiro gerado. / EN-UK: Generated file.
        :param backup_folder:
            PT-PT: Onde gravar o estado anterior.
            EN-UK: Where to save the previous state.
        :param dry_run:
            PT-PT: True (omissão) não escreve nada; devolve os comandos que
                   teriam sido enviados.
            EN-UK: True (default) writes nothing; returns the commands that
                   would have been sent.
        :param save:
            PT-PT: Gravar para arranque no fim. Ignorado em simulação e nas
                   plataformas sem comando de gravação.
            EN-UK: Save to startup at the end. Ignored in simulation and on
                   platforms with no save command.
        :return:
            PT-PT: O que foi feito. / EN-UK: What was done.
        :raises TransportError:
            PT-PT: Se a leitura de segurança falhar — nesse caso não se escreve.
            EN-UK: If the safety read fails — in which case nothing is written.
        """
        comandos = commands_for_push(config_text)
        if not comandos:
            raise TransportError("A configuração não tem nenhum comando a enviar.")

        # PT-PT: O backup é a condição de entrada, não um extra.
        # EN-UK: The backup is the entry condition, not an extra.
        caminho_backup = self.backup(backup_folder)

        resultado = PushResult(
            device=self.device.name,
            dry_run=dry_run,
            commands=comandos,
            backup_path=caminho_backup,
        )

        if dry_run:
            resultado.output = "\n".join(comandos)
            logger.info("Simulação em %s: %d comandos", self.device.name, len(comandos))
            return resultado

        connection = self._require_connection()
        logger.warning("A enviar %d comandos para %s", len(comandos), self.device.name)
        resultado.output = str(connection.send_config_set(comandos, read_timeout=120))

        if save and self.device.platform.writable:
            connection.save_config()
            resultado.saved = True

        return resultado


def _safe_filename(name: str) -> str:
    """
    PT-PT: Nome de equipamento utilizável como nome de ficheiro no Windows.
    EN-UK: A device name usable as a Windows filename.
    """
    proibidos = '<>:"/\\|?*'
    limpo = "".join("-" if c in proibidos else c for c in name).strip(" .")
    return limpo or "equipamento"
