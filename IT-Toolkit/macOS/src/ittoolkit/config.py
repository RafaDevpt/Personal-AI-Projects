"""
PT-PT: Definicoes da aplicacao.

       A v1.0 gravava os relatorios numa pasta «Relatorios» ao lado do proprio
       ficheiro .py. Parecia pratico e trazia dois problemas: numa pasta em
       Program Files ou numa partilha de rede so de leitura a escrita falhava,
       e os relatorios — que contem nome da maquina, utilizador, numero de serie
       e mensagens de erro — ficavam dentro da arvore do repositorio, a um
       `git add .` de distancia de irem parar ao GitHub.

EN-UK: Application settings.

       v1.0 wrote reports into a folder beside the .py file itself. That looked
       convenient and caused two problems: writing failed in Program Files or on
       a read-only share, and the reports — which carry machine name, user,
       serial number and error messages — sat inside the repository tree, one
       `git add .` away from GitHub.

Created by Redfox using Claude
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

from . import platform_support

_log = logging.getLogger(__name__)

APP_FOLDER_NAME = "ITToolkit"

# PT-PT: Valores admissiveis, validados ao carregar.
# EN-UK: Permitted values, validated on load.
TEMAS: tuple[str, ...] = ("system", "light", "dark")

# PT-PT: Periodos oferecidos na analise de eventos, em horas.
# EN-UK: Periods offered in the event analysis, in hours.
PERIODOS: tuple[int, ...] = (24, 48, 168, 720)


def default_data_dir() -> Path:
    """
    PT-PT: Pasta de dados da aplicacao (configuracao e registo).
           Fica em `~/Library/Application Support/ITToolkit`, que e a
           convencao do macOS. Nunca escreve dentro da pasta do repositorio.

    EN-UK: Application data folder (configuration and log). It lives in
           `~/Library/Application Support/ITToolkit`, the macOS convention. It
           never writes inside the repository folder.
    """
    # PT-PT: A convencao desta pasta e a do sistema desta versao, e vive num
    #        sitio so — `platform_support`. Nao ha aqui ramificacao nenhuma:
    #        esta versao corre num sistema e sabe qual e.
    # EN-UK: This folder's convention is that of this version's system, and it
    #        lives in one place — `platform_support`. There is no branching
    #        here: this version runs on one system and knows which.
    return platform_support.app_data_dir(APP_FOLDER_NAME)


def default_reports_dir() -> Path:
    """
    PT-PT: Pasta dos relatorios, dentro dos Documentos do utilizador.
           E onde as pessoas procuram ficheiros — uma pasta em %APPDATA% seria
           mais arrumada e ninguem a encontraria.

    EN-UK: Reports folder, inside the user's Documents. It is where people look
           for files — a folder under %APPDATA% would be tidier and nobody would
           ever find it.
    """
    return Path.home() / "Documents" / "IT Toolkit" / "Relatorios"


@dataclass
class AppConfig:
    """
    PT-PT: Definicoes da aplicacao. Todos os campos tem valor por omissao, pelo
           que um ficheiro corrompido ou parcial nunca impede o arranque.

    EN-UK: Application settings. Every field has a default, so a corrupt or
           partial file can never prevent start-up.
    """

    # --- PT-PT: Saida / EN-UK: Output --------------------------------------
    reports_dir: Path = field(default_factory=default_reports_dir)

    # --- PT-PT: Analise de eventos / EN-UK: Event analysis -----------------
    periodo_horas: int = 24
    #: PT-PT: Incluir as mensagens `Default` alem dos erros e das falhas. Num
    #:        Mac isto multiplica o volume por dez, e por isso e uma opcao e nao
    #:        o comportamento normal.
    #: EN-UK: Include `Default` messages besides errors and faults. On a Mac this
    #:        multiplies the volume tenfold, hence an option rather than the norm.
    incluir_avisos: bool = True
    #: PT-PT: Ler tambem os relatorios de paragem em `DiagnosticReports`. E o que
    #:        permite ver um kernel panic de anteontem, que ja nao esta no diario
    #:        desta sessao. Precisa de Acesso Total ao Disco para os do sistema.
    #: EN-UK: Also read the crash reports in `DiagnosticReports`. It is what
    #:        surfaces a two-day-old kernel panic no longer in this session's log.
    #:        The system's need Full Disk Access.
    incluir_relatorios_paragem: bool = True
    #: PT-PT: Janela, em dias, dos relatorios de paragem. E mais larga do que a
    #:        do diario de proposito: uma paragem de ha uma semana continua a ser
    #:        a explicacao mais provavel para a queixa de hoje.
    #: EN-UK: Crash-report window in days. Deliberately wider than the log's: a
    #:        week-old crash is still the likeliest explanation for today's
    #:        complaint.
    dias_relatorios: int = 7

    # PT-PT: Tecto de eventos lidos por log. Sem tecto, uma maquina com o
    #        Application a rebentar em ciclo devolve centenas de milhares de
    #        linhas e a interface fica presa varios minutos. Quando o tecto e
    #        atingido, o relatorio di-lo em vez de fingir que leu tudo.
    # EN-UK: Ceiling on events read per log. Without one, a machine whose
    #        Application log is looping returns hundreds of thousands of lines
    #        and the interface locks up for minutes. When the ceiling is hit the
    #        report says so instead of pretending it read everything.
    max_eventos: int = 3000

    # --- PT-PT: Limites de alerta / EN-UK: Alert thresholds ----------------
    # PT-PT: Percentagem livre abaixo da qual um disco e assinalado.
    # EN-UK: Free percentage below which a disk is flagged.
    disco_percent_min: int = 10
    # PT-PT: E tambem um minimo absoluto. Num disco de 4 TB, 10% livres sao
    #        400 GB e nao ha problema nenhum; num SSD de 128 GB do sistema,
    #        12 GB livres ja impedem uma actualizacao do macOS, que precisa de
    #        bastante mais espaco do que o tamanho do ficheiro que descarrega.
    #        So a percentagem, como na v1.0, engana nos dois sentidos.
    # EN-UK: And an absolute floor too. On a 4 TB disk, 10% free is 400 GB and
    #        no problem at all; on a 128 GB MacBook, 12 GB free already blocks a
    #        macOS update. Percentage alone misleads both ways.
    disco_gb_min: int = 15
    # PT-PT: Dias de uptime a partir dos quais se sugere reiniciar.
    # EN-UK: Uptime days from which a restart is suggested.
    uptime_dias_max: int = 30
    ram_percent_max: int = 90
    cpu_percent_max: int = 90

    # --- PT-PT: Rede / EN-UK: Network --------------------------------------
    host_teste: str = "8.8.8.8"
    dominio_teste: str = "www.google.com"
    timeout_ping: int = 15
    timeout_porta: float = 1.5

    # --- PT-PT: Comportamento / EN-UK: Behaviour ---------------------------
    # PT-PT: Analisar assim que a janela abre. A v1.0 abria vazia e obrigava a
    #        carregar num botao para ver seja o que for.
    # EN-UK: Analyse as soon as the window opens. v1.0 opened empty and required
    #        a button press before showing anything at all.
    analisar_ao_arrancar: bool = True
    abrir_relatorio_apos_gerar: bool = True

    # --- PT-PT: Interface / EN-UK: Interface -------------------------------
    tema: str = "system"

    def __post_init__(self) -> None:
        """
        PT-PT: Normaliza tipos e limita os valores a intervalos sensatos,
               revertendo em silencio e deixando registo.
        EN-UK: Normalises types and clamps values to sensible ranges, falling
               back silently and recording it in the log.
        """
        self.reports_dir = Path(self.reports_dir).expanduser()

        if self.tema not in TEMAS:
            _log.warning("Tema inválido %r; a usar 'system'.", self.tema)
            self.tema = "system"

        if int(self.periodo_horas) not in PERIODOS:
            _log.warning("Período inválido %r; a usar 24h.", self.periodo_horas)
            self.periodo_horas = 24
        else:
            self.periodo_horas = int(self.periodo_horas)

        self.max_eventos = max(100, min(int(self.max_eventos), 50_000))
        self.disco_percent_min = max(1, min(int(self.disco_percent_min), 50))
        self.disco_gb_min = max(1, min(int(self.disco_gb_min), 500))
        self.uptime_dias_max = max(1, min(int(self.uptime_dias_max), 365))
        self.ram_percent_max = max(50, min(int(self.ram_percent_max), 99))
        self.cpu_percent_max = max(50, min(int(self.cpu_percent_max), 99))
        self.timeout_ping = max(3, min(int(self.timeout_ping), 120))
        self.timeout_porta = max(0.2, min(float(self.timeout_porta), 30.0))

    # -----------------------------------------------------------------------
    # PT-PT: Persistencia / EN-UK: Persistence
    # -----------------------------------------------------------------------

    @classmethod
    def config_path(cls) -> Path:
        """PT-PT: Caminho do ficheiro de configuracao.
        EN-UK: Path of the configuration file."""
        return default_data_dir() / "config.json"

    @classmethod
    def load(cls, path: Path | None = None) -> AppConfig:
        """
        PT-PT: Carrega a configuracao do disco. Qualquer falha resulta nos
               valores por omissao, nunca numa excecao.
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

        if not isinstance(raw, dict):
            _log.warning("Configuração não é um objecto JSON; a usar omissões.")
            return cls()

        conhecidos = {f.name for f in fields(cls)}
        desconhecidos = set(raw) - conhecidos
        if desconhecidos:
            _log.debug("Chaves ignoradas: %s", ", ".join(sorted(desconhecidos)))

        try:
            return cls(**{k: v for k, v in raw.items() if k in conhecidos})
        except (TypeError, ValueError) as exc:
            # PT-PT: Um tipo errado no JSON (uma string onde se espera um
            #        numero) nao deve impedir a aplicacao de abrir.
            # EN-UK: A wrong type in the JSON must not stop the app opening.
            _log.warning("Configuração com valores inválidos: %s", exc)
            return cls()

    def save(self, path: Path | None = None) -> bool:
        """
        PT-PT: Grava a configuracao em JSON.
        EN-UK: Writes the configuration as JSON.

        :return: PT-PT: True se gravou; False se falhou (a aplicacao continua).
                 EN-UK: True on success; False on failure (the app carries on).
        """
        path = path or self.config_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                k: (str(v) if isinstance(v, Path) else v) for k, v in asdict(self).items()
            }
            path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            return True
        except OSError as exc:
            _log.error("Não foi possível gravar a configuração: %s", exc)
            return False

    def ensure_directories(self) -> None:
        """
        PT-PT: Garante que a pasta de relatorios existe.
        EN-UK: Ensures the reports folder exists.
        """
        try:
            self.reports_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            _log.error("Não foi possível criar %s: %s", self.reports_dir, exc)

    @property
    def fontes_escolhidas(self) -> list[str]:
        """
        PT-PT: Que fontes de eventos ler, conforme as opcoes.

               Em Windows sao tres logs com nomes proprios. Num Mac ha um
               diario unico — nao ha nada para escolher dentro dele — mais os
               relatorios de paragem, que sao ficheiros e nao um log, e que
               sobrevivem ao reinicio que apagou o resto.

        EN-UK: Which event sources to read, according to the options.

               On Windows these are three named logs. On a Mac there is a single
               log — nothing to choose inside it — plus the crash reports, which
               are files rather than a log, and which survive the reboot that
               took the rest.
        """
        escolhidas = ["diário"]
        if self.incluir_relatorios_paragem:
            escolhidas.append("relatórios de paragem")
        return escolhidas
