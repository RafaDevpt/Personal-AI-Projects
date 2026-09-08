#!/usr/bin/env python3
"""
PT-PT: A aplicação, e o que a mantém a responder.

       **O problema, que não é óbvio até acontecer.** O pyVmomi é síncrono: uma
       chamada ao vCenter bloqueia até o vCenter responder. Feita no fio da
       interface, o ecrã congela — nem redesenha, nem aceita teclas, nem mostra
       que está à espera. E não é uma questão de milissegundos: ler o inventário
       de um parque grande são segundos, e um vCenter atolado ou uma rede de
       gestão com problemas são dezenas. Uma aplicação que fica preta durante
       trinta segundos parece uma aplicação que rebentou, e a reacção normal é
       matá-la — a meio de uma operação.

       Por isso **todas** as chamadas ao vSphere correm em fios separados, com
       `@work(thread=True)`, e o resultado volta ao fio da interface por
       `call_from_thread`. É a única forma correcta de mexer nos widgets a
       partir de outro fio no Textual, e não é opcional: fazê-lo directamente
       resulta em corrupção de ecrã que aparece uma vez em vinte.

       **A actualização automática pára quando um modal está aberto.** Não é
       cortesia visual: é a diferença entre confirmar o desligar da máquina que
       está debaixo do cursor e confirmar o desligar da máquina que passou a
       estar debaixo do cursor quando a lista se reordenou.

EN-UK: The application, and what keeps it responding.

       pyVmomi is synchronous: a call to vCenter blocks until vCenter answers.
       Made on the interface thread, the screen freezes — no redraw, no keys, no
       sign that it is waiting. And this is not milliseconds: reading a large
       estate is seconds, and a struggling vCenter is tens of them. An
       application that goes black for thirty seconds looks like one that
       crashed, and the normal reaction is to kill it — mid-operation.

       So **every** vSphere call runs on a separate thread with
       `@work(thread=True)`, and results return to the interface thread through
       `call_from_thread`. That is the only correct way to touch widgets from
       another thread in Textual, and it is not optional: doing it directly
       gives screen corruption that shows up once in twenty runs.

       Automatic refresh stops while a modal is open. Not visual courtesy: it is
       the difference between confirming the shutdown of the machine under the
       cursor and confirming the shutdown of the machine that came to be under
       the cursor when the list re-sorted.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from textual import work
from textual.app import App

from .. import cli, collect, config, connection, health
from ..actions import (
    Action,
    OperationRefusedError,
    Operations,
    guard_host,
    guard_snapshot,
    guard_vm,
)
from ..config import Server, Settings
from ..connection import Endpoint, TrustDecision
from ..models import Fleet, HostInfo, SnapshotInfo, VMInfo
from .screens import ChoiceScreen, ConfirmScreen, ConnectScreen, DashboardScreen, TrustScreen
from .theme import CSS

logger = logging.getLogger(__name__)


class FleetConsole(App):
    """
    PT-PT: A aplicação.
    EN-UK: The application.
    """

    CSS = CSS
    TITLE = "VMware Fleet Console"
    SUB_TITLE = "vCenter e ESXi a partir do terminal"

    def __init__(self, definicoes: Settings | None = None) -> None:
        super().__init__()
        self.definicoes = definicoes or config.load_settings()
        self.sessao: connection.Session | None = None
        self.operacoes: Operations | None = None
        self.parque: Fleet | None = None
        self._credenciais: tuple[str, str, str] | None = None
        self._modal_aberto = False
        self._temporizador = None

    def on_mount(self) -> None:
        self.push_screen(ConnectScreen(self.definicoes))

    # -- PT-PT: Ligação. / EN-UK: Connection. -------------------------------

    def iniciar_ligacao(self, anfitriao: str, utilizador: str, senha: str) -> None:
        """
        PT-PT: Começa pela verificação do certificado, antes de a senha sair
               daqui. A senha fica guardada num atributo durante o tempo desta
               operação e é apagada assim que a sessão abre — não porque um
               atributo em memória seja perigoso por si, mas porque não há razão
               nenhuma para a manter depois de ter servido.
        EN-UK: Starts with the certificate check, before the password leaves
               here. It is held in an attribute for the length of this operation
               and cleared as soon as the session opens — not because an
               attribute in memory is dangerous in itself, but because there is
               no reason to keep it after it has done its job.
        """
        self._credenciais = (anfitriao, utilizador, senha)
        self._verificar_certificado(anfitriao)

    @work(thread=True, exclusive=True)
    def _verificar_certificado(self, anfitriao: str) -> None:
        guardado = self.definicoes.server_for(anfitriao)
        resultado = connection.evaluate_trust(
            anfitriao,
            port=guardado.port if guardado else connection.DEFAULT_PORT,
            pinned_fingerprint=guardado.fingerprint if guardado else "",
            timeout=float(self.definicoes.connect_timeout),
        )
        self.call_from_thread(self._certificado_avaliado, resultado, anfitriao)

    def _certificado_avaliado(self, resultado: connection.TrustResult, anfitriao: str) -> None:
        if resultado.decision is TrustDecision.UNREACHABLE:
            self._falha_de_ligacao(resultado.message)
            return

        if resultado.may_connect:
            impressao = (
                resultado.certificate.fingerprint_sha256
                if resultado.decision is TrustDecision.PINNED_MATCH
                else ""
            )
            self._abrir_sessao(impressao)
            return

        # PT-PT: Alguém tem de olhar. / EN-UK: Somebody has to look.
        self._modal_aberto = True

        def decidido(aceite: bool | None) -> None:
            self._modal_aberto = False
            if not aceite:
                self._falha_de_ligacao(
                    "Certificado recusado. Nenhuma credencial foi enviada para o servidor."
                )
                return
            impressao = resultado.certificate.fingerprint_sha256
            self._guardar_impressao(anfitriao, impressao)
            self._abrir_sessao(impressao)

        self.push_screen(TrustScreen(resultado, anfitriao), decidido)

    def _guardar_impressao(self, anfitriao: str, impressao: str) -> None:
        guardado = self.definicoes.server_for(anfitriao)
        self.definicoes.remember(
            Server(
                label=guardado.label if guardado else anfitriao,
                host=anfitriao,
                username=self._credenciais[1] if self._credenciais else "",
                port=guardado.port if guardado else connection.DEFAULT_PORT,
                fingerprint=impressao,
            )
        )
        self.guardar_definicoes()

    def _abrir_sessao(self, impressao: str) -> None:
        if self._credenciais is None:
            return
        self._ligar(impressao)

    @work(thread=True, exclusive=True)
    def _ligar(self, impressao: str) -> None:
        assert self._credenciais is not None
        anfitriao, utilizador, senha = self._credenciais
        guardado = self.definicoes.server_for(anfitriao)
        alvo = Endpoint(
            host=anfitriao,
            username=utilizador,
            port=guardado.port if guardado else connection.DEFAULT_PORT,
        )
        try:
            sessao = connection.connect(
                alvo, senha, impressao, timeout=float(self.definicoes.connect_timeout)
            )
            parque = collect.collect_fleet(sessao)
        except connection.VSphereConnectionError as erro:
            self.call_from_thread(self._falha_de_ligacao, str(erro))
            return
        except Exception as erro:  # noqa: BLE001
            logger.exception("Falha inesperada ao ligar")
            self.call_from_thread(self._falha_de_ligacao, f"Falha inesperada: {erro}")
            return

        self.call_from_thread(self._sessao_aberta, sessao, parque)

    def _sessao_aberta(self, sessao: connection.Session, parque: Fleet) -> None:
        # PT-PT: A senha já serviu. / EN-UK: The password has done its job.
        if self._credenciais:
            anfitriao, utilizador, _ = self._credenciais
            self._credenciais = None
            guardado = self.definicoes.server_for(anfitriao)
            self.definicoes.remember(
                Server(
                    label=guardado.label if guardado else anfitriao,
                    host=anfitriao,
                    username=utilizador,
                    port=guardado.port if guardado else connection.DEFAULT_PORT,
                    fingerprint=guardado.fingerprint if guardado else "",
                )
            )
            self.guardar_definicoes()

        self.sessao = sessao
        self.operacoes = Operations(sessao)
        self.parque = parque

        self.pop_screen()
        self.push_screen(DashboardScreen(parque, self.definicoes))

        if self.definicoes.refresh_seconds > 0:
            self._temporizador = self.set_interval(
                self.definicoes.refresh_seconds, self.actualizar_inventario
            )

        if parque.read_only_reason:
            self.notify(parque.read_only_reason, severity="warning", timeout=15)

    def _falha_de_ligacao(self, mensagem: str) -> None:
        self._credenciais = None
        ecra = self.screen
        if isinstance(ecra, ConnectScreen):
            ecra.mostrar_erro(mensagem)
        else:
            self.notify(mensagem, severity="error", timeout=15)

    # -- PT-PT: Actualização. / EN-UK: Refresh. -----------------------------

    def actualizar_inventario(self) -> None:
        """
        PT-PT: Relê o inventário, se não houver um modal aberto.
        EN-UK: Re-reads the inventory, unless a modal is open.
        """
        if self.sessao is None or self._modal_aberto:
            return
        self._recolher()

    @work(thread=True, exclusive=True)
    def _recolher(self) -> None:
        try:
            parque = collect.collect_fleet(self.sessao)
        except Exception as erro:  # noqa: BLE001
            logger.exception("Falha a actualizar o inventário")
            self.call_from_thread(
                self.notify,
                f"Não foi possível actualizar: {erro}",
                severity="error",
            )
            return
        self.call_from_thread(self._inventario_actualizado, parque)

    def _inventario_actualizado(self, parque: Fleet) -> None:
        self.parque = parque
        ecra = self.screen
        if isinstance(ecra, DashboardScreen):
            ecra.actualizar_vista(parque)

    # -- PT-PT: Operações. / EN-UK: Operations. -----------------------------

    def _painel(self) -> DashboardScreen | None:
        ecra = self.screen
        return ecra if isinstance(ecra, DashboardScreen) else None

    def accao_ligar(self) -> None:
        """PT-PT: Ligar a máquina sob o cursor. / EN-UK: Power on the selected machine."""
        painel = self._painel()
        if painel is None:
            return
        maquina = painel.maquina_seleccionada()
        if not isinstance(maquina, VMInfo):
            self.notify("Escolha uma máquina no separador Máquinas.", severity="warning")
            return
        guarda = guard_vm(Action.VM_POWER_ON, maquina, self.parque)
        if not guarda.allowed:
            self.notify(guarda.reason, severity="warning", timeout=10)
            return
        self._executar(lambda ops: ops.vm_power_on(maquina, self.parque))

    def accao_encerrar(self) -> None:
        """
        PT-PT: Encerrar — e a escolha entre encerrar e cortar a corrente.

               As duas opções aparecem sempre juntas, com o que cada uma faz
               escrito ao lado. É o momento em que a diferença importa, e é o
               único sítio onde ela cabe.

        EN-UK: Shut down — and the choice between shutting down and pulling the
               plug. Both options always appear together with what each does
               written beside it. That is the moment the difference matters.
        """
        painel = self._painel()
        if painel is None:
            return
        maquina = painel.maquina_seleccionada()
        if not isinstance(maquina, VMInfo):
            self.notify("Escolha uma máquina no separador Máquinas.", severity="warning")
            return

        limpo = guard_vm(Action.VM_GUEST_SHUTDOWN, maquina, self.parque)
        forcado = guard_vm(Action.VM_POWER_OFF, maquina, self.parque)

        opcoes: list[tuple[str, str]] = []
        if limpo.allowed:
            opcoes.append(("encerrar", "Encerrar pelo sistema convidado — limpo, pede às Tools"))
        else:
            opcoes.append(("indisponivel", f"Encerrar limpo indisponível: {limpo.reason}"))
        if forcado.allowed:
            opcoes.append(("forcar", "Desligar à força — equivale a cortar a corrente"))
        reiniciar = guard_vm(Action.VM_GUEST_RESTART, maquina, self.parque)
        if reiniciar.allowed:
            opcoes.append(("reiniciar", "Reiniciar pelo sistema convidado"))
        suspender = guard_vm(Action.VM_SUSPEND, maquina, self.parque)
        if suspender.allowed:
            opcoes.append(("suspender", "Suspender — guarda a memória em disco"))

        self._modal_aberto = True

        def escolhido(chave: str | None) -> None:
            self._modal_aberto = False
            if not chave or chave == "indisponivel":
                return
            if chave == "encerrar":
                self._executar(lambda ops: ops.vm_guest_shutdown(maquina, self.parque))
            elif chave == "reiniciar":
                self._executar(lambda ops: ops.vm_guest_restart(maquina, self.parque))
            elif chave == "suspender":
                self._executar(lambda ops: ops.vm_suspend(maquina, self.parque))
            elif chave == "forcar":
                self._confirmar_e_executar(
                    forcado,
                    maquina.name,
                    lambda ops, texto: ops.vm_power_off(maquina, texto, self.parque),
                )

        self.push_screen(ChoiceScreen(f"{maquina.name} — o que fazer", opcoes), escolhido)

    def accao_snapshot(self) -> None:
        """PT-PT: Criar, ou mexer no que está seleccionado. / EN-UK: Create, or act on the selection."""
        painel = self._painel()
        if painel is None:
            return

        if painel.aba_actual() == "aba-snapshots":
            par = painel.snapshot_seleccionado()
            if par is None:
                self.notify("Nenhum snapshot seleccionado.", severity="warning")
                return
            maquina, snapshot = par
            self._menu_de_snapshot(maquina, snapshot)  # type: ignore[arg-type]
            return

        maquina = painel.maquina_seleccionada()
        if not isinstance(maquina, VMInfo):
            self.notify(
                "Escolha uma máquina, ou vá ao separador Snapshots para mexer num existente.",
                severity="warning",
            )
            return
        nome = f"vfc {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        self._executar(
            lambda ops: ops.snapshot_create(
                maquina, nome, "Criado pela VMware Fleet Console", with_memory=False
            )
        )

    def _menu_de_snapshot(self, maquina: VMInfo, snapshot: SnapshotInfo) -> None:
        reverter = guard_snapshot(Action.SNAPSHOT_REVERT, maquina, snapshot)
        apagar = guard_snapshot(Action.SNAPSHOT_DELETE, maquina, snapshot)

        opcoes = [
            ("apagar", "Apagar — consolida as diferenças, perde o ponto de retorno"),
            ("reverter", "Reverter — DEITA FORA tudo o que mudou desde que foi tirado"),
        ]

        self._modal_aberto = True

        def escolhido(chave: str | None) -> None:
            self._modal_aberto = False
            if chave == "apagar":
                self._confirmar_e_executar(
                    apagar,
                    maquina.name,
                    lambda ops, texto: ops.snapshot_delete(maquina, snapshot, texto),
                )
            elif chave == "reverter":
                self._confirmar_e_executar(
                    reverter,
                    maquina.name,
                    lambda ops, texto: ops.snapshot_revert(maquina, snapshot, texto),
                )

        self.push_screen(
            ChoiceScreen(f"{maquina.name} — snapshot '{snapshot.name}'", opcoes), escolhido
        )

    def accao_manutencao(self) -> None:
        """PT-PT: Modo de manutenção e reinício do anfitrião. / EN-UK: Maintenance and host reboot."""
        painel = self._painel()
        if painel is None:
            return
        anfitriao = painel.anfitriao_seleccionado()
        if not isinstance(anfitriao, HostInfo):
            self.notify("Escolha um anfitrião no separador Anfitriões.", severity="warning")
            return

        entrar = guard_host(Action.HOST_MAINTENANCE_ENTER, anfitriao, self.parque)
        sair = guard_host(Action.HOST_MAINTENANCE_EXIT, anfitriao, self.parque)
        reiniciar = guard_host(Action.HOST_REBOOT, anfitriao, self.parque)
        desligar = guard_host(Action.HOST_SHUTDOWN, anfitriao, self.parque)

        opcoes: list[tuple[str, str]] = []
        if sair.allowed:
            opcoes.append(("sair", "Sair do modo de manutenção"))
        if entrar.allowed:
            opcoes.append(("entrar", "Entrar em modo de manutenção"))
        if reiniciar.allowed:
            opcoes.append(("reiniciar", "Reiniciar o anfitrião"))
        else:
            opcoes.append(("indisponivel", f"Reiniciar indisponível: {reiniciar.reason}"))
        if desligar.allowed:
            opcoes.append(("desligar", "Desligar o anfitrião"))

        self._modal_aberto = True

        def escolhido(chave: str | None) -> None:
            self._modal_aberto = False
            if not chave or chave == "indisponivel":
                return
            if chave == "sair":
                self._executar(lambda ops: ops.host_exit_maintenance(anfitriao, self.parque))
            elif chave == "entrar":
                self._confirmar_e_executar(
                    entrar,
                    anfitriao.name,
                    lambda ops, texto: ops.host_enter_maintenance(anfitriao, texto, self.parque),
                )
            elif chave == "reiniciar":
                self._confirmar_e_executar(
                    reiniciar,
                    anfitriao.name,
                    lambda ops, texto: ops.host_reboot(anfitriao, texto, self.parque),
                )
            elif chave == "desligar":
                self._confirmar_e_executar(
                    desligar,
                    anfitriao.name,
                    lambda ops, texto: ops.host_shutdown(anfitriao, texto, self.parque),
                )

        self.push_screen(ChoiceScreen(f"{anfitriao.name} — o que fazer", opcoes), escolhido)

    # -- PT-PT: Confirmar e correr. / EN-UK: Confirm and run. ---------------

    def _confirmar_e_executar(self, guarda: object, assunto: str, chamada: object) -> None:
        """
        PT-PT: Pede a confirmação por escrito e só depois executa.

               O texto escrito é entregue à operação, que o volta a passar pela
               guarda. Sim, é verificado duas vezes — e é de propósito: a
               verificação que conta é a que está em `actions.py`, onde nenhuma
               alteração à interface lhe pode passar por cima.

        EN-UK: Asks for the written confirmation and only then executes. The
               typed text is handed to the operation, which puts it through the
               guard again. Yes, it is checked twice, on purpose: the check that
               counts is the one in `actions.py`, where no interface change can
               get past it.
        """
        self._modal_aberto = True

        def confirmado(texto: str | None) -> None:
            self._modal_aberto = False
            if texto is None:
                return
            self._executar(lambda ops: chamada(ops, texto))  # type: ignore[operator]

        self.push_screen(ConfirmScreen(guarda, assunto), confirmado)  # type: ignore[arg-type]

    def _executar(self, chamada: object) -> None:
        if self.operacoes is None:
            return
        self._correr_operacao(chamada)

    @work(thread=True)
    def _correr_operacao(self, chamada: object) -> None:
        try:
            resultado = chamada(self.operacoes)  # type: ignore[operator]
        except OperationRefusedError as erro:
            self.call_from_thread(self.notify, str(erro), severity="warning", timeout=12)
            return
        except Exception as erro:  # noqa: BLE001
            logger.exception("Falha a executar a operação")
            self.call_from_thread(
                self.notify, self._traduzir_falha(erro), severity="error", timeout=15
            )
            return

        self.call_from_thread(self.notify, resultado.message, timeout=8)
        # PT-PT: Relê a seguir, para o ecrã mostrar o estado novo em vez de o
        #        antigo com uma notificação por cima a dizer o contrário.
        # EN-UK: Re-reads afterwards, so the screen shows the new state rather
        #        than the old one with a notification on top saying otherwise.
        self.call_from_thread(self.actualizar_inventario)

    @staticmethod
    def _traduzir_falha(erro: Exception) -> str:
        """
        PT-PT: A mensagem do vSphere, traduzida onde vale a pena.

               `RestrictedVersion` é a que mais confunde: aparece quando se
               tenta escrever num ESXi com licença gratuita, e o texto original
               não diz nada sobre licenças.

        EN-UK: vSphere's message, translated where it is worth it.
               `RestrictedVersion` is the confusing one: it appears when writing
               to a free-licensed ESXi, and the original text says nothing about
               licences.
        """
        texto = str(erro)
        nome = type(erro).__name__
        if "RestrictedVersion" in nome or "RestrictedVersion" in texto:
            return (
                "O servidor recusou a operação por causa do licenciamento. Num ESXi com a "
                "licença gratuita a API do vSphere é só de leitura: esta operação só é "
                "possível pelo cliente web do anfitrião ou com uma licença que a permita."
            )
        if "NoPermission" in nome:
            return "A conta não tem permissões para esta operação neste objecto."
        if "InvalidState" in nome:
            return (
                "O objecto já não está no estado em que estava quando a operação foi pedida. "
                "Actualize o inventário (r) e tente outra vez."
            )
        if "TaskInProgress" in nome:
            return "Já há uma tarefa a correr neste objecto. Espere que termine."
        return f"O servidor recusou a operação: {texto}"

    # -- PT-PT: Ficheiros e definições. / EN-UK: Files and settings. --------

    def gravar_relatorio(self) -> None:
        """
        PT-PT: Grava o estado actual em texto, para colar num email ou anexar a
               um ticket. Sai na pasta do utilizador, nunca na do programa.
        EN-UK: Writes the current state to text, to paste into an email or
               attach to a ticket. It goes to the user's folder, never the
               program's.
        """
        if self.parque is None:
            return
        achados = health.evaluate(self.parque, self.definicoes.thresholds())  # type: ignore[arg-type]
        texto = cli.render_report(self.parque, achados)

        pasta = (
            Path(self.definicoes.output_dir)
            if self.definicoes.output_dir
            else config.reports_dir()
        )
        carimbo = datetime.now().strftime("%Y%m%d-%H%M%S")
        destino = pasta / f"estado-{carimbo}.txt"
        try:
            pasta.mkdir(parents=True, exist_ok=True)
            destino.write_text(texto, encoding="utf-8")
        except OSError as erro:
            self.notify(f"Não foi possível gravar: {erro}", severity="error")
            return
        self.notify(f"Gravado em {destino}", timeout=10)

    def guardar_definicoes(self) -> None:
        config.save_settings(self.definicoes)

    def on_unmount(self) -> None:
        if self.sessao is not None:
            self.sessao.close()


def run(definicoes: Settings | None = None) -> int:
    """
    PT-PT: Arranca a aplicação e devolve o código de saída.
    EN-UK: Starts the application and returns the exit code.
    """
    FleetConsole(definicoes).run()
    return 0
