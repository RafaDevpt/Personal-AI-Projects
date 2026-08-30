"""
PT-PT: Ferramentas rapidas — accoes pontuais de manutencao.

       Regra do modulo: nada aqui apaga dados do utilizador, e tudo o que tem
       impacto declara-o na sua descricao para a interface poder pedir
       confirmacao. As accoes que exigem uma consola propria (SFC, DISM,
       chkdsk) sao lancadas numa janela separada em vez de capturadas — sao
       demoradas e mostram progresso, e capturar a saida deixava o operador a
       olhar para uma interface parada sem saber se estava a correr.

EN-UK: Quick tools — one-off maintenance actions.

       Module rule: nothing here deletes user data, and anything with impact
       declares it so the interface can ask for confirmation. Actions needing
       their own console (SFC, DISM, chkdsk) are launched in a separate window
       rather than captured — they are slow and show progress, and capturing
       their output left the operator staring at a frozen interface.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .shell import CREATE_NO_WINDOW, IS_WINDOWS, Resultado, abrir_ficheiro, executar, powershell

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Accao:
    """
    PT-PT: Descricao de uma accao para a interface construir os botoes sem
           saber nada sobre o que cada uma faz.
    EN-UK: Description of an action, so the interface can build buttons without
           knowing anything about what each one does.
    """

    chave: str
    etiqueta: str
    descricao: str
    #: PT-PT: True obriga a interface a confirmar antes de executar.
    #: EN-UK: True forces the interface to confirm before running.
    confirmar: bool = False
    #: PT-PT: True significa que abre uma consola propria e nao devolve saida.
    #: EN-UK: True means it opens its own console and returns no output.
    consola: bool = False


ACCOES: tuple[Accao, ...] = (
    Accao("ipconfig", "Ver configuração IP", "Mostra o ipconfig /all completo."),
    Accao("flush_dns", "Limpar cache DNS", "Esvazia a cache de resolução de nomes."),
    Accao(
        "renovar_ip",
        "Renovar endereço IP",
        "Liberta e volta a pedir o endereço ao DHCP. A ligação cai por alguns segundos.",
        confirmar=True,
    ),
    Accao(
        "reiniciar_spooler",
        "Reiniciar o spooler",
        "Para e volta a arrancar o serviço de impressão. Os trabalhos em fila perdem-se.",
        confirmar=True,
    ),
    Accao(
        "limpar_temp",
        "Limpar temporários",
        "Apaga o conteúdo da pasta TEMP do utilizador que puder ser apagado.",
        confirmar=True,
    ),
    Accao("gpupdate", "Actualizar políticas", "Corre gpupdate /force. Demora até um minuto."),
    Accao("sessoes", "Sessões abertas", "Lista as sessões de utilizador na máquina."),
    Accao("drives_rede", "Unidades de rede", "Mostra as unidades mapeadas."),
    Accao("resync_hora", "Sincronizar a hora", "Força a sincronização com o servidor de tempo."),
    Accao(
        "sfc",
        "Verificar ficheiros de sistema",
        "Abre uma consola com o sfc /scannow. Demora bastante.",
        confirmar=True,
        consola=True,
    ),
    Accao(
        "dism",
        "Reparar imagem do Windows",
        "Abre uma consola com o DISM /RestoreHealth. Demora bastante.",
        confirmar=True,
        consola=True,
    ),
)

# PT-PT: Consolas de gestao, para nao andar a escrever nomes no Executar.
# EN-UK: Management consoles, so nobody has to type names into Run.
CONSOLAS: tuple[tuple[str, str], ...] = (
    ("Gestor de Dispositivos", "devmgmt.msc"),
    ("Gestão de Discos", "diskmgmt.msc"),
    ("Serviços", "services.msc"),
    ("Visualizador de Eventos", "eventvwr.msc"),
    ("Gestão do Computador", "compmgmt.msc"),
    ("Monitor de Desempenho", "perfmon.msc"),
    ("Firewall Avançada", "wf.msc"),
    ("Utilizadores Locais", "lusrmgr.msc"),
    ("Agendador de Tarefas", "taskschd.msc"),
    ("Impressoras", "printmanagement.msc"),
)


def _abrir_consola(comando: str) -> Resultado:
    """
    PT-PT: Lanca um comando numa consola propria, sem esperar por ele.
    EN-UK: Launches a command in its own console, without waiting for it.
    """
    if not IS_WINDOWS:
        return Resultado(erro="Só disponível em Windows.", ok=False)
    try:
        subprocess.Popen(  # noqa: S603 — comando fixo, nunca vem do utilizador
            ["cmd.exe", "/c", "start", "", "cmd.exe", "/k", comando],
            creationflags=0,
        )
        return Resultado(
            saida="Abriu numa janela separada. Acompanhe o progresso por lá."
        )
    except OSError as exc:
        return Resultado(erro=f"Não foi possível abrir a consola: {exc}", ok=False)


def limpar_temp() -> Resultado:
    """
    PT-PT: Limpa a pasta de temporarios do utilizador.

           Conta o que apagou e o que nao conseguiu. Ficheiros em uso nao sao
           apagaveis e isso e normal, nao um erro — a v1.0 lancava a excepcao do
           primeiro ficheiro bloqueado e desistia do resto, o que na pratica
           significava que quase nunca limpava nada.

           Nunca sai da pasta TEMP e nunca apaga a propria pasta.

    EN-UK: Clears the user's temporary folder. Counts what it removed and what
           it could not. Files in use are not deletable and that is normal, not
           an error — v1.0 raised on the first locked file and gave up on the
           rest, so in practice it almost never cleaned anything.
    """
    pasta = Path(tempfile.gettempdir())
    if not pasta.is_dir():
        return Resultado(erro=f"Pasta temporária não encontrada: {pasta}", ok=False)

    apagados = 0
    bloqueados = 0
    libertado = 0

    for item in pasta.iterdir():
        try:
            if item.is_file() or item.is_symlink():
                tamanho = item.stat().st_size
                item.unlink()
                apagados += 1
                libertado += tamanho
            elif item.is_dir():
                tamanho = sum(
                    f.stat().st_size for f in item.rglob("*") if f.is_file()
                )
                shutil.rmtree(item)
                apagados += 1
                libertado += tamanho
        except (OSError, PermissionError):
            bloqueados += 1

    return Resultado(
        saida=(
            f"Apagados {apagados} item(ns), {libertado / 1024**2:.0f} MB libertados.\n"
            f"{bloqueados} em uso, deixados como estavam.\n"
            f"Pasta: {pasta}"
        )
    )


def executar_accao(chave: str) -> Resultado:
    """
    PT-PT: Corre a accao correspondente a chave.
    EN-UK: Runs the action matching the key.
    """
    if chave == "limpar_temp":
        return limpar_temp()

    if not IS_WINDOWS:
        return Resultado(erro="Só disponível em Windows.", ok=False)

    if chave == "ipconfig":
        return executar(["ipconfig", "/all"], timeout=30)
    if chave == "flush_dns":
        return executar(["ipconfig", "/flushdns"], timeout=30)
    if chave == "renovar_ip":
        libertar = executar(["ipconfig", "/release"], timeout=60)
        renovar = executar(["ipconfig", "/renew"], timeout=120)
        return Resultado(
            saida=f"{libertar.texto}\n{renovar.texto}",
            ok=renovar.ok,
            codigo=renovar.codigo,
        )
    if chave == "reiniciar_spooler":
        return powershell("Restart-Service -Name Spooler -Force; (Get-Service Spooler).Status")
    if chave == "gpupdate":
        return executar(["gpupdate", "/force"], timeout=180)
    if chave == "sessoes":
        return executar(["query", "user"], timeout=30)
    if chave == "drives_rede":
        return executar(["net", "use"], timeout=30)
    if chave == "resync_hora":
        return executar(["w32tm", "/resync"], timeout=60)
    if chave == "sfc":
        return _abrir_consola("sfc /scannow")
    if chave == "dism":
        return _abrir_consola("DISM /Online /Cleanup-Image /RestoreHealth")

    return Resultado(erro=f"Acção desconhecida: {chave}", ok=False)


def abrir_consola_mmc(ficheiro: str) -> Resultado:
    """
    PT-PT: Abre uma consola de gestao do Windows.
    EN-UK: Opens a Windows management console.
    """
    if not IS_WINDOWS:
        return Resultado(erro="Só disponível em Windows.", ok=False)
    try:
        subprocess.Popen(  # noqa: S603 — nome vem da lista fixa CONSOLAS
            ["cmd.exe", "/c", "start", "", ficheiro],
            creationflags=CREATE_NO_WINDOW,
        )
        return Resultado(saida=f"{ficheiro} aberto.")
    except OSError as exc:
        return Resultado(erro=f"Não foi possível abrir {ficheiro}: {exc}", ok=False)


def abrir_pasta(caminho: os.PathLike[str] | str) -> Resultado:
    """PT-PT: Abre uma pasta no Explorador. / EN-UK: Opens a folder in Explorer."""
    return abrir_ficheiro(str(caminho))
