#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PT-PT: Configuração da aplicação.
       Tudo o que na versão anterior estava escrito dentro do código — limite de
       alerta, gama de endereços, pastas de saída, credenciais do EWS — vive
       agora aqui e é editável pela interface.

EN-UK: Application configuration.
       Everything the previous version had written inside the code — alert
       threshold, address range, output folders, EWS credentials — now lives
       here and is editable from the interface.

PT-PT: Nota sobre a password do EWS. Não é gravada neste ficheiro. É pedida na
       interface e mantida apenas em memória durante a sessão. Gravá-la em
       texto claro num JSON ao lado do executável seria cómodo e seria errado:
       a password de administrador das impressoras dá acesso à configuração de
       rede de todas elas.

EN-UK: A note on the EWS password. It is not written to this file. It is asked
       for in the interface and kept in memory for the session only. Storing it
       in clear text in a JSON beside the executable would be convenient and
       would be wrong: the printers' administrator password grants access to the
       network configuration of every one of them.

Created by Redfox using Claude
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

_log = logging.getLogger(__name__)

APP_FOLDER_NAME = "HPTonerMonitor"

# PT-PT: Valores admissíveis, validados ao carregar.
# EN-UK: Permitted values, validated on load.
THEMES: tuple[str, ...] = ("system", "light", "dark")


def default_data_dir() -> Path:
    """
    PT-PT: Pasta de dados da aplicação (configuração e registos).
           Em Windows usa %APPDATA%; nos restantes sistemas segue a norma XDG.
           Nunca escreve dentro da pasta do repositório, para que uma
           configuração local não seja submetida por engano para o Git.

    EN-UK: Application data folder (configuration and logs).
           On Windows it uses %APPDATA%; elsewhere it follows the XDG
           convention. It never writes inside the repository folder, so a local
           configuration cannot be committed to Git by accident.
    """
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / APP_FOLDER_NAME


def default_documents_dir() -> Path:
    """
    PT-PT: Pasta de trabalho por omissão, dentro dos Documentos do utilizador.
           Escolhida por ser onde as pessoas procuram ficheiros — uma pasta em
           %APPDATA% seria mais arrumada e ninguém a encontraria.

    EN-UK: Default working folder, inside the user's Documents.
           Chosen because it is where people look for files — a folder under
           %APPDATA% would be tidier and nobody would ever find it.
    """
    return Path.home() / "Documents" / "Monitor de Toners"


@dataclass
class AppConfig:
    """
    PT-PT: Definições da aplicação. Todos os campos têm valor por omissão, pelo
           que um ficheiro corrompido ou parcial nunca impede o arranque.

    EN-UK: Application settings. Every field has a default, so a corrupt or
           partial file can never prevent start-up.
    """

    # --- PT-PT: Inventário / EN-UK: Inventory ------------------------------
    # PT-PT: Ficheiro Excel com as impressoras. Criado automaticamente no
    #        primeiro arranque se ainda não existir.
    # EN-UK: Excel file holding the printers. Created automatically on first run
    #        if it does not exist yet.
    inventory_path: Path = field(
        default_factory=lambda: default_documents_dir() / "Impressoras.xlsx"
    )

    # --- PT-PT: Saída / EN-UK: Output --------------------------------------
    output_dir: Path = field(default_factory=lambda: default_documents_dir() / "Relatorios")

    # --- PT-PT: Alertas / EN-UK: Alerts ------------------------------------
    # PT-PT: Limite abaixo do qual um toner é assinalado. 15% é o valor pedido
    #        originalmente e continua a ser um bom compromisso: dá tempo para
    #        encomendar sem acumular stock.
    # EN-UK: Threshold below which a toner is flagged. 15% was the value
    #        originally asked for and remains a sound compromise: enough time to
    #        order without building up stock.
    alert_threshold: int = 15

    # --- PT-PT: Rede / EN-UK: Network --------------------------------------
    # PT-PT: Gama a varrer na descoberta. Vazio obriga o utilizador a indicá-la,
    #        o que é intencional: varrer uma gama adivinhada numa rede alheia é
    #        má prática e pode disparar alertas de segurança.
    # EN-UK: Range to sweep during discovery. Empty forces the user to state it,
    #        which is intentional: sweeping a guessed range on somebody else's
    #        network is bad practice and may trigger security alerts.
    scan_range: str = ""

    snmp_community: str = "public"
    use_snmp: bool = True
    tcp_timeout: float = 0.4
    snmp_timeout: float = 1.5
    http_timeout: float = 6.0
    scan_workers: int = 64
    poll_workers: int = 8

    # PT-PT: Utilizador do EWS. A password NÃO é gravada — ver o cabeçalho.
    # EN-UK: EWS user name. The password is NOT stored — see the header.
    ews_user: str = "admin"

    # PT-PT: O proxy corporativo foi a causa dos timeouts nos primeiros testes:
    #        pedidos para 10.162.84.x eram encaminhados para fora e morriam. A
    #        aplicação ignora o proxy por omissão para endereços locais.
    # EN-UK: The corporate proxy caused the timeouts in the first tests:
    #        requests to 10.162.84.x were routed outbound and died. The
    #        application bypasses the proxy for local addresses by default.
    bypass_proxy: bool = True

    # --- PT-PT: Automatização / EN-UK: Automation --------------------------
    auto_refresh: bool = False
    refresh_minutes: int = 60

    # PT-PT: Gerar o PDF da página de utilização quando há alerta.
    # EN-UK: Generate the usage page PDF when there is an alert.
    pdf_on_alert: bool = True

    # PT-PT: Destinatário do rascunho de email com o pedido de toners.
    # EN-UK: Recipient of the draft email carrying the toner order.
    order_email_to: str = ""

    # --- PT-PT: Interface / EN-UK: Interface -------------------------------
    theme: str = "system"

    def __post_init__(self) -> None:
        """
        PT-PT: Normaliza tipos e limita os valores numéricos a intervalos
               sensatos, revertendo em silêncio e deixando registo. Um valor
               inválido não deve derrubar a aplicação.

        EN-UK: Normalises types and clamps the numeric values to sensible
               ranges, falling back silently and recording it in the log. An
               invalid value should not bring the application down.
        """
        self.inventory_path = Path(self.inventory_path).expanduser()
        self.output_dir = Path(self.output_dir).expanduser()

        if self.theme not in THEMES:
            _log.warning("Tema inválido %r; a usar 'system'.", self.theme)
            self.theme = "system"

        # PT-PT: Um limite de 0 desligaria os alertas sem o utilizador perceber;
        #        acima de 100 assinalaria tudo. Ambos são erros de escrita.
        # EN-UK: A threshold of 0 would silently disable alerts; above 100 would
        #        flag everything. Both are typing mistakes.
        self.alert_threshold = max(1, min(int(self.alert_threshold), 99))

        self.refresh_minutes = max(5, min(int(self.refresh_minutes), 1440))
        self.scan_workers = max(1, min(int(self.scan_workers), 256))
        self.poll_workers = max(1, min(int(self.poll_workers), 32))
        self.tcp_timeout = max(0.1, min(float(self.tcp_timeout), 10.0))
        self.snmp_timeout = max(0.2, min(float(self.snmp_timeout), 15.0))
        self.http_timeout = max(1.0, min(float(self.http_timeout), 60.0))

    # -----------------------------------------------------------------------
    # PT-PT: Persistência / EN-UK: Persistence
    # -----------------------------------------------------------------------

    @classmethod
    def config_path(cls) -> Path:
        """
        PT-PT: Caminho do ficheiro de configuração.
        EN-UK: Path of the configuration file.
        """
        return default_data_dir() / "config.json"

    @classmethod
    def load(cls, path: Path | None = None) -> "AppConfig":
        """
        PT-PT: Carrega a configuração do disco. Qualquer falha resulta nos
               valores por omissão, nunca numa excepção.

        EN-UK: Loads the configuration from disk. Any failure yields the
               defaults, never an exception.
        """
        path = path or cls.config_path()
        if not path.is_file():
            _log.info("Sem configuração em %s; a usar valores por omissão.", path)
            return cls()

        try:
            raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            _log.warning("Configuração ilegível (%s): %s", path, exc)
            return cls()

        known = {f.name for f in fields(cls)}
        unknown = set(raw) - known
        if unknown:
            _log.debug("Chaves ignoradas: %s", ", ".join(sorted(unknown)))

        return cls(**{key: value for key, value in raw.items() if key in known})

    def save(self, path: Path | None = None) -> bool:
        """
        PT-PT: Grava a configuração em JSON.

        EN-UK: Writes the configuration as JSON.

        :return:
            PT-PT: True se gravou; False se falhou (a aplicação continua).
            EN-UK: True on success; False on failure (the application carries on).
        """
        path = path or self.config_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                key: (str(value) if isinstance(value, Path) else value)
                for key, value in asdict(self).items()
            }
            path.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            return True
        except OSError as exc:
            _log.error("Não foi possível gravar a configuração: %s", exc)
            return False

    def ensure_directories(self) -> None:
        """
        PT-PT: Garante que as pastas de saída e do inventário existem.
        EN-UK: Ensures the output and inventory folders exist.
        """
        for directory in (self.output_dir, self.inventory_path.parent):
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                _log.error("Não foi possível criar %s: %s", directory, exc)
