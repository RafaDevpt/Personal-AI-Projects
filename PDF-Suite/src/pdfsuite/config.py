"""
PT-PT: Definicoes da aplicacao.

       Nota sobre a chave da API. Nao e gravada neste ficheiro nem em nenhum
       outro. E lida da variavel de ambiente `ANTHROPIC_API_KEY` ou escrita na
       interface e mantida so em memoria durante a sessao. Uma chave em texto
       claro num JSON ao lado do executavel e comoda e e um problema: quem
       tiver acesso a pasta tem acesso a conta, e um `git add .` distraido
       publica-a. As chaves publicadas em repositorios sao varridas
       automaticamente por quem as procura, e o custo cai em quem a deixou la.

EN-UK: Application settings.

       A note on the API key. It is not written to this file or any other. It is
       read from the `ANTHROPIC_API_KEY` environment variable, or typed in the
       interface and kept in memory for the session only. A key in clear text in
       a JSON beside the executable is convenient and is a problem: anyone with
       access to the folder has access to the account, and one careless
       `git add .` publishes it.

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

APP_FOLDER_NAME = "PDFSuite"

TEMAS: tuple[str, ...] = ("system", "light", "dark")


def default_data_dir() -> Path:
    """
    PT-PT: Pasta de dados da aplicacao (configuracao e registo).
    EN-UK: Application data folder (configuration and log).
    """
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / APP_FOLDER_NAME


def default_output_dir() -> Path:
    """
    PT-PT: Pasta de saida, dentro dos Documentos do utilizador. E onde as
           pessoas procuram ficheiros.
    EN-UK: Output folder, inside the user's Documents. It is where people look.
    """
    return Path.home() / "Documents" / "PDF Suite"


@dataclass
class AppConfig:
    """
    PT-PT: Definicoes. Todos os campos tem valor por omissao, pelo que um
           ficheiro corrompido nunca impede o arranque.
    EN-UK: Settings. Every field has a default, so a corrupt file can never
           prevent start-up.
    """

    # --- PT-PT: Saida / EN-UK: Output --------------------------------------
    output_dir: Path = field(default_factory=default_output_dir)
    abrir_apos_gerar: bool = True

    # --- PT-PT: Formularios / EN-UK: Forms ---------------------------------
    #: PT-PT: Incluir a estrategia dos dois pontos, menos fiavel.
    #: EN-UK: Include the colon strategy, the least reliable one.
    detectar_dois_pontos: bool = True
    #: PT-PT: Abaixo desta confianca, o campo entra desmarcado na lista de
    #:        revisao. E o compromisso entre apanhar tudo e nao inundar o
    #:        utilizador com campos inventados.
    #: EN-UK: Below this confidence a field arrives unticked in the review list.
    confianca_minima: float = 0.5
    substituir_campos_existentes: bool = False

    # --- PT-PT: Comparacao / EN-UK: Comparison -----------------------------
    taxa_iva: float = 23.0
    #: PT-PT: Pesos dos criterios, por chave. Vazio usa os valores por omissao
    #:        do modulo de pontuacao.
    #: EN-UK: Criterion weights by key. Empty uses the scoring module defaults.
    pesos: dict[str, float] = field(default_factory=dict)
    penalizar_em_falta: float = 0.0

    # --- PT-PT: Resumo / EN-UK: Summary ------------------------------------
    frases_resumo: int = 6

    # --- PT-PT: Analise assistida / EN-UK: Assisted analysis ---------------
    #: PT-PT: A chave NAO e gravada — ver o cabecalho deste ficheiro.
    #: EN-UK: The key is NOT stored — see this file's header.
    usar_ia: bool = False
    modelo_ia: str = "claude-sonnet-4-6"

    # --- PT-PT: Interface / EN-UK: Interface -------------------------------
    tema: str = "system"

    def __post_init__(self) -> None:
        """
        PT-PT: Normaliza tipos e limita os valores a intervalos sensatos.
        EN-UK: Normalises types and clamps values to sensible ranges.
        """
        self.output_dir = Path(self.output_dir).expanduser()

        if self.tema not in TEMAS:
            _log.warning("Tema inválido %r; a usar 'system'.", self.tema)
            self.tema = "system"

        # PT-PT: Uma taxa de 0 daria totais sem IVA a quem nao o declara, o que
        #        e exactamente o erro que a ferramenta existe para evitar.
        # EN-UK: A rate of 0 would give VAT-free totals to whoever does not
        #        state it, which is the very error the tool exists to prevent.
        self.taxa_iva = max(0.0, min(float(self.taxa_iva), 40.0))
        self.confianca_minima = max(0.0, min(float(self.confianca_minima), 1.0))
        self.penalizar_em_falta = max(0.0, min(float(self.penalizar_em_falta), 1.0))
        self.frases_resumo = max(2, min(int(self.frases_resumo), 30))

        if not isinstance(self.pesos, dict):
            _log.warning("Pesos inválidos; a usar os valores por omissão.")
            self.pesos = {}
        else:
            limpos: dict[str, float] = {}
            for chave, peso in self.pesos.items():
                try:
                    limpos[str(chave)] = max(0.0, min(float(peso), 100.0))
                except (TypeError, ValueError):
                    _log.warning("Peso inválido para %r; ignorado.", chave)
            self.pesos = limpos

    # -----------------------------------------------------------------------
    # PT-PT: Persistencia / EN-UK: Persistence
    # -----------------------------------------------------------------------

    @classmethod
    def config_path(cls) -> Path:
        return default_data_dir() / "config.json"

    @classmethod
    def load(cls, path: Path | None = None) -> AppConfig:
        """
        PT-PT: Carrega do disco. Qualquer falha resulta nos valores por
               omissao, nunca numa excecao.
        EN-UK: Loads from disk. Any failure yields the defaults, never an
               exception.
        """
        path = path or cls.config_path()
        if not path.is_file():
            _log.info("Sem configuração em %s; a usar valores por omissão.", path)
            return cls()

        try:
            raw: Any = json.loads(path.read_text(encoding="utf-8"))
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
            _log.warning("Configuração com valores inválidos: %s", exc)
            return cls()

    def save(self, path: Path | None = None) -> bool:
        """
        PT-PT: Grava em JSON. Devolve False em vez de levantar.
        EN-UK: Writes as JSON. Returns False rather than raising.
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
        """PT-PT: Garante a pasta de saida. / EN-UK: Ensures the output folder."""
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            _log.error("Não foi possível criar %s: %s", self.output_dir, exc)

    def criterios(self):
        """
        PT-PT: Criterios com os pesos configurados aplicados.
        EN-UK: Criteria with the configured weights applied.
        """
        from .models import Criterio
        from .scoring import CRITERIOS_OMISSAO

        return [
            Criterio(
                chave=c.chave,
                etiqueta=c.etiqueta,
                peso=self.pesos.get(c.chave, c.peso),
                maior_melhor=c.maior_melhor,
                unidade=c.unidade,
            )
            for c in CRITERIOS_OMISSAO
        ]
