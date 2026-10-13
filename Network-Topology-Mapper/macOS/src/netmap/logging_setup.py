#!/usr/bin/env python3
"""
PT-PT: Configuração do registo de eventos.

       Um ficheiro rotativo e um nível de detalhe controlável, em vez de
       print() disperso pelo código. Num mapeamento que percorre trinta
       switches sem ninguém a olhar, o registo é a única forma de saber
       depois porque é que faltam dois: a diferença entre "não respondeu"
       e "recusou a autenticação" decide se é um problema de rede ou de
       credenciais.

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
#
#        **Duas formas escapavam à versão anterior, e são as mais comuns.**
#
#        1. O algarismo do tipo de cifra. Num IOS o segredo quase nunca vem
#           logo a seguir à palavra-chave:
#
#               enable secret 5 $1$mERr$Xk3lQ...
#               username admin password 7 0822455D0A16
#
#           O padrão antigo, `(secret\s+)(\S+)`, apanhava o `5` e substituía-o,
#           deixando o resumo criptográfico escrito no registo. E o tipo 7 nem
#           resumo é: é reversível com uma linha de script. Agora o algarismo do
#           tipo é preservado — é útil e não é segredo — e o que vem a seguir é
#           que desaparece.
#
#        2. Separadores que não são espaço. `password: x`, `password=x` e
#           `"password": "x"` não têm espaço a seguir à palavra-chave, por isso
#           nenhum padrão pegava e a linha ia inteira para o disco.
#
#        Sobre-substituir num registo não faz mal; deixar passar faz.
#
# EN-UK: Configuration lines carrying secrets. What matters is whatever follows
#        the keyword, and that is what gets replaced.
#
#        **Two shapes escaped the previous version, and they are the common
#        ones.**
#
#        1. The encryption-type digit. On IOS the secret almost never comes
#           directly after the keyword:
#
#               enable secret 5 $1$mERr$Xk3lQ...
#               username admin password 7 0822455D0A16
#
#           The old pattern, `(secret\s+)(\S+)`, caught the `5` and replaced
#           that, leaving the hash written to the log. And type 7 is not even a
#           hash: it is reversible with a one-line script. The type digit is now
#           preserved — it is useful and it is not secret — and what follows it
#           is what disappears.
#
#        2. Separators that are not whitespace. `password: x`, `password=x` and
#           `"password": "x"` have no space after the keyword, so no pattern
#           matched and the whole line went to disk.
#
#        Over-redacting a log costs nothing; letting one through costs a lot.

# PT-PT: Palavras que, a seguir a `key`, não são segredo nenhum.
# EN-UK: Words that, following `key`, are not a secret at all.
_NAO_SEGREDO = r"(?!generate\b|chain\b|zeroize\b|config-key\b|mypubkey\b)"

_PALAVRAS = r"(?:password|passwd|pwd|secret|community|key-string|pre-shared-key|key)"

_SECRET_PATTERNS = [
    # PT-PT: palavra-chave [algarismo do tipo] <segredo>
    # EN-UK: keyword [encryption-type digit] <secret>
    re.compile(rf"\b({_PALAVRAS}\s+(?:\d+\s+)?){_NAO_SEGREDO}(\S+)", re.IGNORECASE),
    # PT-PT: palavra-chave: <segredo>   palavra-chave=<segredo>   "chave": "x"
    # EN-UK: keyword: <secret>          keyword=<secret>          "key": "x"
    re.compile(rf"\b({_PALAVRAS}\"?\s*[:=]\s*\"?)([^\s\"',}}\]]+)", re.IGNORECASE),
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
    log_file = log_dir / "netmap.log"

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
