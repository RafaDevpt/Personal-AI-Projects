#!/usr/bin/env python3
"""
PT-PT: Definições, servidores conhecidos e onde tudo é guardado.

       **O que este ficheiro nunca guarda: senhas.** Não há campo para elas, não
       há opção para as guardar, e não há um "lembrar-me" desligado por omissão
       que alguém possa ligar. A senha é pedida a cada sessão e vive em memória
       enquanto a aplicação estiver aberta.

       A razão é o que a senha abre. Uma senha de administrador do vCenter dá
       acesso a todas as máquinas do parque — os controladores de domínio, as
       bases de dados, as cópias de segurança. Guardá-la num ficheiro de
       configuração na pasta do utilizador significa que qualquer coisa que
       consiga ler ficheiros nessa conta fica com o parque inteiro. Uma cifra
       feita com uma chave que também está na máquina não resolve isto: adia-o.

       O que **é** guardado é o que não tem valor sozinho: o endereço, o nome de
       utilizador (para não o escrever todos os dias) e a impressão digital do
       certificado aceite. Esta última é a que faz o trabalho de segurança —
       ver `connection.py`.

       Nada é escrito dentro da pasta do programa. Pode estar numa partilha só
       de leitura, e um ficheiro com a lista dos servidores de virtualização não
       deve acabar dentro de um repositório por distracção.

EN-UK: Settings, known servers, and where everything is stored.

       **What this file never stores: passwords.** There is no field for them,
       no option to store them, and no "remember me" switched off by default
       that somebody could switch on. The password is asked for each session and
       lives in memory while the application is open.

       The reason is what the password opens: a vCenter administrator password
       reaches every machine on the estate — domain controllers, databases,
       backups. Keeping it in a config file in the user's folder means anything
       that can read files as that account owns the whole estate. Encrypting it
       with a key that also sits on the machine does not fix this; it postpones it.

       What **is** stored is what has no value alone: the address, the username
       (so it need not be retyped daily) and the accepted certificate
       fingerprint. That last one does the security work — see `connection.py`.

Created by Redfox using Claude
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import platform_support

logger = logging.getLogger(__name__)

APP_FOLDER_NAME = "VMwareFleetConsole"
SETTINGS_FILE = "definicoes.json"


def app_data_dir() -> Path:
    """
    PT-PT: Pasta de dados da aplicação, na convenção deste sistema.
    EN-UK: The application's data folder, in this system's convention.
    """
    # PT-PT: A convenção é a do sistema desta versão e vive num sítio só —
    #        `platform_support`. Não há aqui ramificação nenhuma: esta versão
    #        corre num sistema e sabe qual é.
    # EN-UK: The convention is this version's system's, and it lives in one
    #        place — `platform_support`. No branching here: this version runs on
    #        one system and knows which.
    return platform_support.app_data_dir(APP_FOLDER_NAME)


def log_dir() -> Path:
    """PT-PT: Onde ficam os registos. / EN-UK: Where the logs go."""
    return app_data_dir() / "registos"


def reports_dir() -> Path:
    """PT-PT: Onde o utilizador espera os relatórios. / EN-UK: Where reports go."""
    documentos = Path.home() / "Documents"
    if not documentos.exists():
        documentos = Path.home()
    return documentos / "VMware Fleet Console"


@dataclass
class Server:
    """
    PT-PT: Um servidor conhecido.

           `fingerprint` é a impressão digital SHA-256 do certificado que alguém
           já viu e aceitou. Vazia significa "nunca ligámos a este servidor, ou
           o certificado dele valida sozinho" — e nos dois casos o comportamento
           certo é o de `connection.evaluate_trust`.

    EN-UK: A known server. `fingerprint` is the SHA-256 of a certificate
           somebody has already seen and accepted. Empty means "never connected,
           or its certificate validates on its own" — and in both cases the
           right behaviour is `connection.evaluate_trust`'s.
    """

    label: str = ""
    host: str = ""
    username: str = ""
    port: int = 443
    fingerprint: str = ""

    @property
    def display(self) -> str:
        """PT-PT: Como aparece na lista. / EN-UK: How it appears in the list."""
        if self.label and self.label != self.host:
            return f"{self.label} ({self.host})"
        return self.host or "(sem endereço)"


@dataclass
class Settings:
    """
    PT-PT: As definições.

           `refresh_seconds` a zero desliga a actualização automática. Não é um
           caso à parte: um parque grande demora a ler, e quem está a fazer uma
           intervenção quer o ecrã quieto enquanto trabalha.

    EN-UK: The settings. `refresh_seconds` at zero switches automatic refresh
           off — not a special case: a large estate takes time to read, and
           somebody in the middle of an intervention wants the screen still.
    """

    servers: list[Server] = field(default_factory=list)
    refresh_seconds: int = 60
    connect_timeout: int = 30
    theme: str = "escuro"
    confirm_destructive: bool = True
    output_dir: str = ""

    # -- PT-PT: Limiares editáveis. / EN-UK: Editable thresholds. -----------
    datastore_free_warning_pct: float = 20.0
    datastore_free_critical_pct: float = 10.0
    snapshot_age_warning_days: int = 3
    snapshot_age_critical_days: int = 30

    def server_for(self, host: str) -> Server | None:
        """PT-PT: O servidor guardado com este endereço. / EN-UK: The stored server."""
        alvo = (host or "").strip().casefold()
        return next((s for s in self.servers if s.host.strip().casefold() == alvo), None)

    def remember(self, server: Server) -> None:
        """
        PT-PT: Guarda ou actualiza um servidor.

               Uma impressão digital nova **substitui** a antiga, mas só chega
               aqui depois de alguém a ter aceite explicitamente em
               `connection.evaluate_trust`. Este método não decide nada sobre
               confiança: regista o que já foi decidido.

        EN-UK: Stores or updates a server. A new fingerprint **replaces** the
               old one, but only reaches here after somebody explicitly accepted
               it in `connection.evaluate_trust`. This method decides nothing
               about trust: it records what was already decided.
        """
        existente = self.server_for(server.host)
        if existente is None:
            self.servers.append(server)
            return
        existente.label = server.label or existente.label
        existente.username = server.username or existente.username
        existente.port = server.port or existente.port
        if server.fingerprint:
            existente.fingerprint = server.fingerprint

    def forget(self, host: str) -> bool:
        """PT-PT: Esquece um servidor. / EN-UK: Forgets a server."""
        antes = len(self.servers)
        alvo = (host or "").strip().casefold()
        self.servers = [s for s in self.servers if s.host.strip().casefold() != alvo]
        return len(self.servers) != antes

    def thresholds(self) -> object:
        """
        PT-PT: Os limiares editáveis, no formato que `health` espera.
        EN-UK: The editable thresholds in the shape `health` expects.
        """
        from .health import Thresholds  # noqa: PLC0415

        return Thresholds(
            datastore_free_critical_pct=self.datastore_free_critical_pct,
            datastore_free_warning_pct=self.datastore_free_warning_pct,
            snapshot_age_warning_days=self.snapshot_age_warning_days,
            snapshot_age_critical_days=self.snapshot_age_critical_days,
        )


def settings_path() -> Path:
    return app_data_dir() / SETTINGS_FILE


def load_settings(path: Path | None = None) -> Settings:
    """
    PT-PT: Lê as definições, e nunca falha por causa delas.

           Um ficheiro corrompido — meio escrito porque a máquina desligou, ou
           editado à mão com uma vírgula a mais — devolve as definições por
           omissão e um aviso no registo. Recusar arrancar por causa de uma
           preferência de tema seria desproporcionado.

           Se o ficheiro trouxer uma senha (porque alguém a lá pôs à mão), ela é
           **ignorada e não é reescrita**. Não há caminho nenhum no programa que
           leia uma senha de um ficheiro.

    EN-UK: Reads the settings, and never fails because of them. A corrupt file —
           half written because the machine went down, or hand-edited with one
           comma too many — returns the defaults and a line in the log. Refusing
           to start over a theme preference would be out of proportion.

           If the file carries a password because somebody put one there by
           hand, it is **ignored and not written back**. No path in the program
           reads a password from a file.
    """
    destino = path or settings_path()
    if not destino.exists():
        return Settings()

    try:
        dados = json.loads(destino.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as erro:
        logger.warning("Definições ilegíveis (%s). A usar as de omissão.", erro)
        return Settings()

    if not isinstance(dados, dict):
        logger.warning("Definições com formato inesperado. A usar as de omissão.")
        return Settings()

    servidores: list[Server] = []
    for bruto in dados.get("servers", []) or []:
        if not isinstance(bruto, dict):
            continue
        servidores.append(
            Server(
                label=str(bruto.get("label", "") or ""),
                host=str(bruto.get("host", "") or ""),
                username=str(bruto.get("username", "") or ""),
                port=int(bruto.get("port", 443) or 443),
                fingerprint=str(bruto.get("fingerprint", "") or "").upper(),
            )
        )

    definicoes = Settings(servers=[s for s in servidores if s.host])
    for campo in (
        "refresh_seconds",
        "connect_timeout",
        "snapshot_age_warning_days",
        "snapshot_age_critical_days",
    ):
        if campo in dados:
            try:
                setattr(definicoes, campo, int(dados[campo]))
            except (TypeError, ValueError):
                logger.warning("Valor inválido em '%s'. A manter o de omissão.", campo)

    for campo in ("datastore_free_warning_pct", "datastore_free_critical_pct"):
        if campo in dados:
            try:
                setattr(definicoes, campo, float(dados[campo]))
            except (TypeError, ValueError):
                logger.warning("Valor inválido em '%s'. A manter o de omissão.", campo)

    if isinstance(dados.get("theme"), str):
        definicoes.theme = dados["theme"]
    if isinstance(dados.get("output_dir"), str):
        definicoes.output_dir = dados["output_dir"]
    if isinstance(dados.get("confirm_destructive"), bool):
        definicoes.confirm_destructive = dados["confirm_destructive"]

    return definicoes


def save_settings(settings: Settings, path: Path | None = None) -> bool:
    """
    PT-PT: Escreve as definições. Devolve se conseguiu.

           Uma falha a escrever não pára nada — a aplicação continua a funcionar
           com o que tem em memória. O que se perde é a memória entre sessões, e
           isso não justifica interromper quem está a trabalhar.

    EN-UK: Writes the settings, returning whether it managed to. A write failure
           stops nothing: the application carries on with what it has in memory.
           What is lost is memory between sessions, which does not justify
           interrupting somebody mid-task.
    """
    destino = path or settings_path()
    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        dados = asdict(settings)
        destino.write_text(
            json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return True
    except OSError as erro:
        logger.warning("Não foi possível gravar as definições: %s", erro)
        return False
