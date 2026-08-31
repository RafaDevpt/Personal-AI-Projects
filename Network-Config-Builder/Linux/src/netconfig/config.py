#!/usr/bin/env python3
"""
PT-PT: Definições da aplicação e onde tudo é guardado.

       Nada é escrito dentro da pasta do programa. As configurações geradas, os
       backups e o registo vão para a pasta do utilizador, por duas razões: a
       pasta do programa pode estar numa partilha só de leitura, e uma
       configuração de switch não deve acabar dentro de um repositório por
       distracção.

       O ficheiro de definições também não guarda credenciais. Não há campo
       para isso e não vai haver — ver o cabeçalho de `inventory.py`.

EN-UK: Application settings and where everything is stored.

       Nothing is written inside the program's folder. Generated
       configurations, backups and the log go to the user's folder, for two
       reasons: the program folder may sit on a read-only share, and a switch
       configuration should not end up inside a repository by accident.

       The settings file holds no credentials either. There is no field for
       them and there will not be — see the header of `inventory.py`.

Created by Redfox using Claude
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import platform_support
from .models import Platform

logger = logging.getLogger(__name__)

APP_FOLDER_NAME = "NetworkConfigBuilder"


def app_data_dir() -> Path:
    """
    PT-PT: Pasta de dados da aplicação, conforme o sistema.

    EN-UK: The application's data folder, per operating system.

    :return:
        PT-PT: %APPDATA%\\NetworkConfigBuilder no Windows,
               ~/.config/NetworkConfigBuilder no resto.
        EN-UK: %APPDATA%\\NetworkConfigBuilder on Windows,
               ~/.config/NetworkConfigBuilder elsewhere.
    """
    # PT-PT: A convencao desta pasta e a do sistema desta versao, e vive num
    #        sitio so — `platform_support`. Nao ha aqui ramificacao nenhuma:
    #        esta versao corre num sistema e sabe qual e.
    # EN-UK: This folder's convention is that of this version's system, and it
    #        lives in one place — `platform_support`. There is no branching
    #        here: this version runs on one system and knows which.
    return platform_support.app_data_dir(APP_FOLDER_NAME)


def documents_dir() -> Path:
    """
    PT-PT: Pasta onde o utilizador espera encontrar o que a aplicação produz.
    EN-UK: The folder where the user expects to find what the application makes.
    """
    documentos = Path.home() / "Documents"
    if not documentos.exists():
        documentos = Path.home()
    return documentos / "Network Config Builder"


@dataclass
class Settings:
    """
    PT-PT: As definições, com valores de omissão que servem sem serem tocados.
    EN-UK: The settings, with defaults that work untouched.
    """

    # PT-PT: Onde ficam os ficheiros produzidos.
    # EN-UK: Where the produced files go.
    output_dir: str = ""
    backup_dir: str = ""
    inventory_path: str = ""

    # PT-PT: Valores iniciais do formulário, para não os reescrever a cada
    #        switch de uma mesma casa.
    # EN-UK: Initial form values, so they need not be retyped for every switch
    #        in the same property.
    default_platform: str = Platform.ARUBA_CX.value
    default_domain: str = ""
    default_ntp: list[str] = field(default_factory=list)
    default_syslog: list[str] = field(default_factory=list)
    default_timezone: str = "WET"

    # PT-PT: Rede.
    # EN-UK: Network.
    ssh_timeout: int = 30
    # PT-PT: A simulação por omissão não é configurável para False aqui de
    #        propósito: quem quer escrever tem de o dizer no momento, não uma
    #        vez numas definições que ninguém volta a ver.
    # EN-UK: Dry-run-by-default is deliberately not switchable to False here:
    #        whoever wants to write must say so at the time, not once in a
    #        settings file nobody looks at again.
    confirmar_envio: bool = True

    tema: str = "system"

    def __post_init__(self) -> None:
        if not self.output_dir:
            self.output_dir = str(documents_dir() / "Configuracoes")
        if not self.backup_dir:
            self.backup_dir = str(documents_dir() / "Backups")
        if not self.inventory_path:
            self.inventory_path = str(app_data_dir() / "inventario.json")

    @property
    def output_path(self) -> Path:
        """PT-PT: Pasta das configurações geradas. / EN-UK: Generated configurations folder."""
        return Path(self.output_dir)

    @property
    def backup_path(self) -> Path:
        """PT-PT: Pasta dos backups. / EN-UK: Backups folder."""
        return Path(self.backup_dir)

    @property
    def inventory_file(self) -> Path:
        """PT-PT: Ficheiro do inventário. / EN-UK: Inventory file."""
        return Path(self.inventory_path)

    @property
    def platform(self) -> Platform:
        """
        PT-PT: Plataforma inicial do formulário. Um valor inválido no ficheiro
               não impede a aplicação de abrir.
        EN-UK: The form's starting platform. An invalid value in the file does
               not stop the application from opening.
        """
        try:
            return Platform(self.default_platform)
        except ValueError:
            logger.warning("Plataforma desconhecida nas definições: %s", self.default_platform)
            return Platform.ARUBA_CX


def settings_file() -> Path:
    """PT-PT: Caminho do ficheiro de definições. / EN-UK: Settings file path."""
    return app_data_dir() / "definicoes.json"


def load_settings() -> Settings:
    """
    PT-PT: Lê as definições. Um ficheiro em falta ou corrompido devolve os
           valores de omissão — a aplicação tem de abrir sempre.

    EN-UK: Reads the settings. A missing or corrupt file returns the defaults —
           the application must always open.

    :return:
        PT-PT: As definições em vigor. / EN-UK: The settings in force.
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
    filtrados = {k: v for k, v in dados.items() if k in conhecidos}
    try:
        return Settings(**filtrados)
    except TypeError:
        logger.warning("Definições com campos inesperados; a usar os valores de omissão.")
        return Settings()


def save_settings(settings: Settings) -> Path:
    """
    PT-PT: Grava as definições.

    EN-UK: Writes the settings.

    :param settings:
        PT-PT: Definições a gravar. / EN-UK: Settings to save.
    :return:
        PT-PT: Caminho gravado. / EN-UK: Written path.
    """
    caminho = settings_file()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(
        json.dumps(asdict(settings), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return caminho
