#!/usr/bin/env python3
"""
PT-PT: Configuração do registo de eventos.

       Um ficheiro rotativo e um nível de detalhe controlável, em vez de
       print() disperso pelo código. Numa ferramenta que fala com equipamento
       de rede o registo não é um luxo: quando um switch não responde, a
       diferença entre "não deu" e "recusou a autenticação ao fim de 30
       segundos" está toda aqui.

       O filtro de segredos é a parte que não se pode esquecer. O Netmiko,
       em modo de depuração, escreve no registo tudo o que envia — palavra-passe
       incluída. Aqui isso é apanhado antes de chegar ao disco.

EN-UK: Event logging setup.

       A rotating file and a controllable level of detail, rather than print()
       scattered through the code. In a tool that talks to network equipment
       logging is not a luxury: when a switch does not answer, the difference
       between "it failed" and "it refused the credentials after 30 seconds"
       lives here.

       The secret filter is the part that must not be forgotten. Netmiko, in
       debug mode, writes everything it sends to the log — password included.
       Here that is caught before it reaches the disk.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
import re
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# PT-PT: 2 MB por ficheiro, 3 gerações. Chega para várias semanas de uso.
# EN-UK: 2 MB per file, 3 generations. Enough for several weeks of use.
_MAX_BYTES = 2 * 1024 * 1024
_BACKUP_COUNT = 3

# PT-PT: Linhas de configuração que carregam segredos. O que interessa é o que
#        vem depois da palavra-chave, e é isso que é substituído.
# EN-UK: Configuration lines carrying secrets. What matters is whatever follows
#        the keyword, and that is what gets replaced.
_SECRET_PATTERNS = [
    re.compile(r"(password\s+)(\S+)", re.IGNORECASE),
    re.compile(r"(secret\s+)(\S+)", re.IGNORECASE),
    re.compile(r"(community\s+)(\S+)", re.IGNORECASE),
    re.compile(r"(key\s+\d?\s*)(\S+)", re.IGNORECASE),
]

REDACTED = "***"


class SecretFilter(logging.Filter):
    """
    PT-PT: Substitui segredos no texto das mensagens antes de serem escritas.

           Actua sobre a mensagem já formatada, e não sobre os argumentos, para
           apanhar também o que venha de bibliotecas de terceiros.

    EN-UK: Replaces secrets in message text before it is written.

           It works on the formatted message rather than the arguments, so it
           also catches whatever comes from third-party libraries.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """PT-PT: Sempre True; o que muda é a mensagem. / EN-UK: Always True; the message changes."""
        try:
            message = record.getMessage()
        except Exception:  # noqa: BLE001 - PT-PT: registo nunca deve rebentar / EN-UK: logging must never blow up
            return True

        cleaned = redact(message)
        if cleaned != message:
            record.msg = cleaned
            record.args = ()
        return True


def redact(text: str) -> str:
    """
    PT-PT: Devolve o texto com as palavras-passe e comunidades substituídas.
           Também é usado antes de mostrar uma configuração na interface.

    EN-UK: Returns the text with passwords and communities replaced. Also used
           before showing a configuration in the interface.

    :param text:
        PT-PT: Texto original. / EN-UK: Original text.
    :return:
        PT-PT: Texto sem segredos legíveis. / EN-UK: Text with no readable secrets.
    """
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub(lambda m: f"{m.group(1)}{REDACTED}", text)
    return text


def setup_logging(log_dir: Path, verbose: bool = False) -> Path:
    """
    PT-PT: Instala os destinos de registo (consola e ficheiro rotativo).

    EN-UK: Installs the logging destinations (console and rotating file).

    :param log_dir:
        PT-PT: Pasta onde gravar o registo. / EN-UK: Folder for the log file.
    :param verbose:
        PT-PT: True activa DEBUG; False mantém INFO.
        EN-UK: True enables DEBUG; False keeps INFO.
    :return:
        PT-PT: Caminho do ficheiro de registo.
        EN-UK: Path of the log file.
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "netconfig.log"

    root = logging.getLogger()
    root.setLevel(logging.DEBUG if verbose else logging.INFO)
    for handler in list(root.handlers):
        root.removeHandler(handler)

    formatter = logging.Formatter(_FORMAT, datefmt=_DATE_FORMAT)
    secret_filter = SecretFilter()

    file_handler = RotatingFileHandler(
        log_file, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(secret_filter)
    root.addHandler(file_handler)

    console = logging.StreamHandler(sys.stderr)
    console.setLevel(logging.DEBUG if verbose else logging.WARNING)
    console.setFormatter(formatter)
    console.addFilter(secret_filter)
    root.addHandler(console)

    # PT-PT: O Paramiko é falador ao nível INFO e não acrescenta nada útil.
    # EN-UK: Paramiko is chatty at INFO level and adds nothing useful.
    logging.getLogger("paramiko").setLevel(logging.WARNING)

    return log_file
