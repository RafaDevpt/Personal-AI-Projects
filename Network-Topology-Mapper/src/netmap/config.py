#!/usr/bin/env python3
"""
PT-PT: Definições e onde tudo é guardado.

       Nada é escrito dentro da pasta do programa. Os relatórios vão para a
       pasta do utilizador por duas razões: a pasta do programa pode estar numa
       partilha só de leitura, e um mapa de rede não deve acabar dentro de um
       repositório por distracção — é a planta do edifício.

       Não há campo para credenciais, nem para o controlador nem para os
       switches. São pedidas a cada sessão e vivem em memória.

EN-UK: Settings and where everything is stored.

       Nothing is written inside the program's folder. Reports go to the user's
       folder for two reasons: the program folder may sit on a read-only share,
       and a network map should not end up inside a repository by accident — it
       is the building's floor plan.

       There is no field for credentials, neither the controller's nor the
       switches'. They are asked for each session and live in memory.

Created by Redfox using Claude
"""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

APP_FOLDER_NAME = "NetworkTopologyMapper"


def app_data_dir() -> Path:
    """
    PT-PT: Pasta de dados da aplicação, conforme o sistema.
    EN-UK: The application's data folder, per operating system.
    """
    if sys.platform == "win32":
        base = os.environ.get("APPDATA")
        if base:
            return Path(base) / APP_FOLDER_NAME
    return Path.home() / ".config" / APP_FOLDER_NAME


def documents_dir() -> Path:
    """
    PT-PT: Onde o utilizador espera encontrar os relatórios.
    EN-UK: Where the user expects to find the reports.
    """
    documentos = Path.home() / "Documents"
    if not documentos.exists():
        documentos = Path.home()
    return documentos / "Network Topology Mapper"


@dataclass
class Settings:
    """PT-PT: As definições. / EN-UK: The settings."""

    output_dir: str = ""

    # PT-PT: Sementes do crawl — os switches por onde começar. Um core chega.
    # EN-UK: Crawl seeds — the switches to start from. One core is enough.
    seeds: list[str] = field(default_factory=list)

    # PT-PT: Controlador UniFi. Opcional: sem ele o crawl começa nas sementes.
    # EN-UK: UniFi controller. Optional: without it the crawl starts at the seeds.
    unifi_url: str = ""
    unifi_site: str = "default"
    unifi_verify_tls: bool = True

    ssh_timeout: int = 30
    max_depth: int = 4
    max_devices: int = 150
    unifi_cli_hop: bool = False

    # PT-PT: Ficheiro do IEEE com os fabricantes, se tiver sido descarregado.
    # EN-UK: The IEEE manufacturer file, if it has been downloaded.
    oui_file: str = ""

    tema: str = "system"

    def __post_init__(self) -> None:
        if not self.output_dir:
            self.output_dir = str(documents_dir())

    @property
    def output_path(self) -> Path:
        """PT-PT: Pasta dos relatórios. / EN-UK: Reports folder."""
        return Path(self.output_dir)

    @property
    def oui_path(self) -> Path | None:
        """PT-PT: Ficheiro do IEEE, se estiver definido. / EN-UK: The IEEE file, if set."""
        return Path(self.oui_file) if self.oui_file.strip() else None


def settings_file() -> Path:
    """PT-PT: Caminho do ficheiro de definições. / EN-UK: Settings file path."""
    return app_data_dir() / "definicoes.json"


def load_settings() -> Settings:
    """
    PT-PT: Lê as definições. Um ficheiro em falta ou corrompido devolve os
           valores de omissão — a aplicação tem de abrir sempre.
    EN-UK: Reads the settings. A missing or corrupt file returns the defaults —
           the application must always open.
    """
    caminho = settings_file()
    if not caminho.exists():
        return Settings()

    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.warning("Definições ilegíveis em %s; a usar os valores de omissão.", caminho)
        return Settings()

    conhecidos = set(Settings().__dataclass_fields__)
    try:
        return Settings(**{k: v for k, v in dados.items() if k in conhecidos})
    except TypeError:
        logger.warning("Definições com campos inesperados; a usar os valores de omissão.")
        return Settings()


def save_settings(settings: Settings) -> Path:
    """
    PT-PT: Grava as definições.
    EN-UK: Writes the settings.
    """
    caminho = settings_file()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(
        json.dumps(asdict(settings), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return caminho
