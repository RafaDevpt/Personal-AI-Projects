#!/usr/bin/env python3
"""
PT-PT: O registo, e o que nunca pode aparecer nele.

       Um registo desta aplicação vai conter endereços de servidores de
       virtualização, nomes de utilizador e nomes de todas as máquinas do
       parque. É material sensível por si só, e é por isso que vive na pasta do
       utilizador e não na do programa.

       O que **nunca** entra é a senha. Não há aqui um filtro esperto a tentar
       apanhá-la depois de ela ter sido escrita — a senha simplesmente nunca é
       passada a nenhuma função de registo. O filtro que existe é a segunda
       linha de defesa, para o dia em que alguém acrescente um `logger.debug`
       com o dicionário de parâmetros todo lá dentro.

       A rotação também não é arrumação: uma TUI que actualiza de minuto a
       minuto durante um mês escreve muito, e um ficheiro de registo que enche a
       partição do utilizador é uma avaria causada pela ferramenta que devia
       ajudar a evitá-las.

EN-UK: The log, and what may never appear in it.

       A log from this application will contain virtualisation server addresses,
       usernames and the names of every machine on the estate. That is sensitive
       on its own, which is why it lives in the user's folder and not the
       program's.

       What **never** enters is the password. There is no clever filter trying
       to catch it after it was written — the password is simply never passed to
       any logging call. The filter that does exist is the second line of
       defence, for the day somebody adds a `logger.debug` with the whole
       parameter dictionary in it.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
import logging.handlers
import re
from pathlib import Path

from . import config

MAX_BYTES = 2 * 1024 * 1024
BACKUP_COUNT = 3

# PT-PT: Padrões que nunca devem sair num registo. Procuram-se por nome do
#        campo, e não por valor — não se pode procurar por um valor que não se
#        conhece, e tentar adivinhar o que "parece uma senha" apanha nomes de
#        máquinas e falha senhas.
# EN-UK: Patterns that must never leave in a log. They are matched by field
#        name, not by value: you cannot search for a value you do not know, and
#        guessing what "looks like a password" catches machine names and misses
#        passwords.
_SENSITIVE = re.compile(
    r"(?i)\b(pwd|password|senha|pass|secret|token|sessionid|vmware_soap_session)\b\s*[=:]\s*\S+"
)


class RedactingFilter(logging.Filter):
    """
    PT-PT: Corta o que parecer um campo de senha antes de ser escrito.

           É deliberadamente cego: se apanhar um nome de máquina que por acaso
           se chame `token=...`, corta-o na mesma. Um registo com uma linha a
           menos é melhor do que um registo com uma senha a mais.

    EN-UK: Cuts anything that looks like a password field before it is written.
           Deliberately blunt: if it catches a machine name that happens to read
           `token=...`, it cuts that too. A log missing one line beats a log
           carrying one password.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            mensagem = record.getMessage()
        except Exception:  # noqa: BLE001
            return True
        limpa = _SENSITIVE.sub(lambda m: m.group(0).split("=")[0].split(":")[0] + "=[cortado]", mensagem)
        if limpa != mensagem:
            record.msg = limpa
            record.args = ()
        return True


def setup(verbose: bool = False, to_file: bool = True) -> Path | None:
    """
    PT-PT: Prepara o registo e devolve o caminho do ficheiro, se houver.

           A consola fica no nível de aviso mesmo em modo detalhado. Numa TUI, o
           que se escrever na saída padrão passa por cima do desenho do ecrã, e
           uma aplicação cujo painel fica riscado de linhas de `DEBUG` é
           inutilizável. O detalhe vai todo para o ficheiro, que é onde serve.

    EN-UK: Sets the logging up and returns the file's path, if there is one.
           The console stays at warning level even in verbose mode: in a TUI,
           anything written to standard output paints over the screen, and a
           panel scratched through with `DEBUG` lines is unusable. The detail
           all goes to the file, which is where it is any use.
    """
    raiz = logging.getLogger()
    raiz.setLevel(logging.DEBUG if verbose else logging.INFO)

    for anterior in list(raiz.handlers):
        raiz.removeHandler(anterior)

    filtro = RedactingFilter()

    consola = logging.StreamHandler()
    consola.setLevel(logging.WARNING)
    consola.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    consola.addFilter(filtro)
    raiz.addHandler(consola)

    if not to_file:
        return None

    try:
        pasta = config.log_dir()
        pasta.mkdir(parents=True, exist_ok=True)
        ficheiro = pasta / "consola.log"
        rotativo = logging.handlers.RotatingFileHandler(
            ficheiro, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
        )
        rotativo.setLevel(logging.DEBUG if verbose else logging.INFO)
        rotativo.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s")
        )
        rotativo.addFilter(filtro)
        raiz.addHandler(rotativo)
        return ficheiro
    except OSError as erro:
        # PT-PT: Sem sítio para escrever, continua-se sem ficheiro. Não ter
        #        registo é um incómodo; não arrancar por causa disso é uma avaria.
        # EN-UK: With nowhere to write, it carries on without a file. Having no
        #        log is an inconvenience; failing to start over it is a fault.
        raiz.warning("Sem registo em ficheiro: %s", erro)
        return None
