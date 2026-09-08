#!/usr/bin/env python3
"""
PT-PT: Os ecrãs.

       Há três que valem uma explicação:

       **O ecrã de confiança** aparece antes de qualquer credencial ser enviada.
       Mostra a impressão digital do certificado e não tem nada preenchido por
       omissão — nem um botão "aceitar" em foco. Se aparecer, é para ser lido.

       **O ecrã de confirmação** é onde as operações destrutivas param. Não tem
       "Sim" e "Não": tem uma caixa onde é preciso escrever o nome do objecto.
       Um diálogo com um botão de confirmar ensina a carregar em confirmar; uma
       caixa onde é preciso escrever `SRV-DC01` obriga a ler que a máquina que
       está prestes a ser desligada se chama `SRV-DC01`.

       **O painel** actualiza sozinho, mas nunca enquanto um modal está aberto.
       Ver a lista mudar debaixo do cursor no momento em que se vai carregar em
       algo é como se perde a máquina errada.

EN-UK: The screens.

       The **trust screen** appears before any credential is sent, shows the
       certificate fingerprint and has nothing pre-filled — not even a focused
       accept button. If it appears, it is meant to be read.

       The **confirmation screen** is where destructive operations stop. It has
       no "Yes" and "No": it has a box where the object's name must be typed. A
       dialog with a confirm button teaches people to press confirm; a box
       needing `SRV-DC01` typed into it forces you to read that the machine
       about to be powered off is called `SRV-DC01`.

       The **dashboard** refreshes itself, but never while a modal is open:
       watching the list move under the cursor at the moment you press
       something is how the wrong machine gets stopped.

Created by Redfox using Claude
"""

from __future__ import annotations

from datetime import datetime, timezone

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    OptionList,
    Static,
    TabbedContent,
    TabPane,
)
from textual.widgets.option_list import Option

from .. import health
from ..actions import Guard
from ..config import Settings
from ..connection import TrustResult
from ..models import Fleet, Severity, format_bytes, format_uptime


class ConnectScreen(Screen):
    """
    PT-PT: Onde se diz a que servidor ligar.

           A lista de servidores guardados existe para não se escrever o
           endereço todos os dias, mas **nunca** preenche a senha — não há senha
           guardada para preencher. O foco começa na senha quando já se sabe o
           endereço e o utilizador, que é o caso normal a partir da segunda vez.

    EN-UK: Where you say which server to connect to. The saved-server list
           exists so the address need not be retyped daily, but it **never**
           fills the password — there is no stored password to fill. Focus
           starts on the password when the address and username are already
           known, which is the normal case from the second time onwards.
    """

    BINDINGS = [
        Binding("escape", "app.quit", "Sair"),
        Binding("ctrl+d", "esquecer", "Esquecer servidor"),
    ]

    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self.settings = settings

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="caixa-ligacao"):
            yield Label("Ligar a um vCenter ou anfitrião ESXi", id="titulo-ligacao")
            if self.settings.servers:
                yield Label("Servidores conhecidos (Enter para escolher):")
                yield OptionList(
                    *[
                        Option(servidor.display, id=servidor.host)
                        for servidor in self.settings.servers
                    ],
                    id="servidores-guardados",
                )
            yield Input(placeholder="Endereço ou nome (ex.: vcenter.empresa.local)", id="campo-host")
            yield Input(
                placeholder="Utilizador (ex.: administrator@vsphere.local, ou root num ESXi)",
                id="campo-utilizador",
            )
            yield Input(placeholder="Senha", password=True, id="campo-senha")
            yield Static("", id="erro-ligacao")
            with Horizontal(id="botoes-modal"):
                yield Button("Sair", variant="default", id="botao-sair")
                yield Button("Ligar", variant="primary", id="botao-ligar")
        yield Footer()

    def on_mount(self) -> None:
        """PT-PT: Onde começa o cursor. / EN-UK: Where the cursor starts."""
        if self.settings.servers:
            primeiro = self.settings.servers[0]
            self.query_one("#campo-host", Input).value = primeiro.host
            self.query_one("#campo-utilizador", Input).value = primeiro.username
            self.query_one("#campo-senha", Input).focus()
        else:
            self.query_one("#campo-host", Input).focus()

    def on_option_list_option_selected(self, evento: OptionList.OptionSelected) -> None:
        """PT-PT: Escolher um servidor guardado. / EN-UK: Picking a saved server."""
        escolhido = self.settings.server_for(str(evento.option.id or ""))
        if escolhido is None:
            return
        self.query_one("#campo-host", Input).value = escolhido.host
        self.query_one("#campo-utilizador", Input).value = escolhido.username
        self.query_one("#campo-senha", Input).focus()

    def on_input_submitted(self, evento: Input.Submitted) -> None:
        """
        PT-PT: Enter na senha liga; Enter noutro campo passa ao seguinte. É o
               que qualquer pessoa espera de um formulário e evita a viagem ao
               rato para carregar num botão que está mesmo ali.
        EN-UK: Enter on the password connects; Enter elsewhere moves on. It is
               what anybody expects of a form.
        """
        if evento.input.id == "campo-senha":
            self._submeter()
        else:
            self.focus_next()

    def on_button_pressed(self, evento: Button.Pressed) -> None:
        if evento.button.id == "botao-ligar":
            self._submeter()
        elif evento.button.id == "botao-sair":
            self.app.exit()

    def action_esquecer(self) -> None:
        """PT-PT: Tira um servidor da lista. / EN-UK: Drops a server from the list."""
        endereco = self.query_one("#campo-host", Input).value.strip()
        if endereco and self.settings.forget(endereco):
            self.notify(f"{endereco} esquecido. A impressão digital também.")
            self.app.guardar_definicoes()  # type: ignore[attr-defined]

    def _submeter(self) -> None:
        anfitriao = self.query_one("#campo-host", Input).value.strip()
        utilizador = self.query_one("#campo-utilizador", Input).value.strip()
        senha = self.query_one("#campo-senha", Input).value

        erro = self.query_one("#erro-ligacao", Static)
        if not anfitriao:
            erro.update("Falta o endereço do servidor.")
            self.query_one("#campo-host", Input).focus()
            return
        if not utilizador:
            erro.update("Falta o utilizador.")
            self.query_one("#campo-utilizador", Input).focus()
            return
        if not senha:
            erro.update("Falta a senha.")
            self.query_one("#campo-senha", Input).focus()
            return

        erro.update("A ligar...")
        self.app.iniciar_ligacao(anfitriao, utilizador, senha)  # type: ignore[attr-defined]

    def mostrar_erro(self, texto: str) -> None:
        """PT-PT: Mostra um erro e devolve o foco à senha. / EN-UK: Shows an error."""
        self.query_one("#erro-ligacao", Static).update(texto)
        self.query_one("#campo-senha", Input).value = ""
        self.query_one("#campo-senha", Input).focus()


class TrustScreen(ModalScreen[bool]):
    """
    PT-PT: A decisão sobre o certificado.

           Nada aqui está pré-escolhido, e o botão em foco é o de recusar.
           Alguém que carregue em Enter por reflexo não aceita um certificado
           que não olhou — o comportamento por omissão é o seguro.

    EN-UK: The certificate decision. Nothing here is pre-chosen and the focused
           button is the refuse one: somebody hitting Enter by reflex does not
           accept a certificate they did not look at.
    """

    BINDINGS = [Binding("escape", "recusar", "Recusar")]

    def __init__(self, resultado: TrustResult, anfitriao: str) -> None:
        super().__init__()
        self.resultado = resultado
        self.anfitriao = anfitriao

    def compose(self) -> ComposeResult:
        certificado = self.resultado.certificate
        with Vertical(id="caixa-modal", classes="confianca"):
            yield Label(f"Certificado de {self.anfitriao}", id="titulo-modal")
            yield Static(self.resultado.message, id="texto-modal")
            yield Static(certificado.fingerprint_sha256 or "(sem certificado)", id="impressao-digital")
            yield Static(
                "Onde confirmar esta impressão digital:\n"
                "  ESXi    — na consola directa (DCUI), em View Support Information\n"
                "  vCenter — em Administration > Certificates > Machine SSL Certificate\n"
                "\n"
                f"Emitido para: {certificado.subject or 'desconhecido'}\n"
                f"Emitido por:  {certificado.issuer or 'desconhecido'}\n"
                f"Válido até:   {certificado.not_after or 'desconhecido'}",
                id="texto-modal",
            )
            with Horizontal(id="botoes-modal"):
                yield Button("Recusar", variant="primary", id="botao-recusar")
                yield Button("Aceitar e guardar", variant="warning", id="botao-aceitar")

    def on_mount(self) -> None:
        self.query_one("#botao-recusar", Button).focus()

    def on_button_pressed(self, evento: Button.Pressed) -> None:
        self.dismiss(evento.button.id == "botao-aceitar")

    def action_recusar(self) -> None:
        self.dismiss(False)


class ConfirmScreen(ModalScreen[str | None]):
    """
    PT-PT: A confirmação por escrito.

           Devolve o texto escrito, ou `None` se foi cancelado. Quem chamou
           passa esse texto à guarda, que o compara. Este ecrã **não** decide se
           está certo — só recolhe. A decisão é sempre da guarda, num sítio só.

    EN-UK: The written confirmation. Returns what was typed, or `None` if
           cancelled. The caller hands that text to the guard, which compares
           it. This screen does **not** decide whether it is right — it only
           collects. The decision is always the guard's, in one place.
    """

    BINDINGS = [Binding("escape", "cancelar", "Cancelar")]

    def __init__(self, guarda: Guard, assunto: str) -> None:
        super().__init__()
        self.guarda = guarda
        self.assunto = assunto

    def compose(self) -> ComposeResult:
        with Vertical(id="caixa-modal"):
            yield Label(f"{self.guarda.action.label} — {self.assunto}", id="titulo-modal")
            if self.guarda.warning:
                yield Static(self.guarda.warning, id="texto-modal")
            yield Static(
                f"Para continuar, escreva o nome exacto:  {self.guarda.confirmation}",
                id="texto-modal",
            )
            yield Input(placeholder=self.guarda.confirmation, id="campo-confirmacao")
            with Horizontal(id="botoes-modal"):
                yield Button("Cancelar", variant="primary", id="botao-cancelar")
                yield Button("Confirmar", variant="error", id="botao-confirmar")

    def on_mount(self) -> None:
        self.query_one("#campo-confirmacao", Input).focus()

    def on_input_submitted(self) -> None:
        self._confirmar()

    def on_button_pressed(self, evento: Button.Pressed) -> None:
        if evento.button.id == "botao-confirmar":
            self._confirmar()
        else:
            self.dismiss(None)

    def action_cancelar(self) -> None:
        self.dismiss(None)

    def _confirmar(self) -> None:
        self.dismiss(self.query_one("#campo-confirmacao", Input).value)


class ChoiceScreen(ModalScreen[str | None]):
    """
    PT-PT: Uma escolha entre operações, para as teclas que têm mais do que uma
           leitura — desligar uma máquina pode querer dizer duas coisas muito
           diferentes, e a diferença tem de estar escrita.
    EN-UK: A choice between operations, for the keys with more than one reading:
           powering off a machine can mean two very different things, and the
           difference has to be written down.
    """

    BINDINGS = [Binding("escape", "cancelar", "Cancelar")]

    def __init__(self, titulo: str, opcoes: list[tuple[str, str]]) -> None:
        super().__init__()
        self.titulo = titulo
        self.opcoes = opcoes

    def compose(self) -> ComposeResult:
        with Vertical(id="caixa-modal", classes="confianca"):
            yield Label(self.titulo, id="titulo-modal")
            yield OptionList(
                *[Option(rotulo, id=chave) for chave, rotulo in self.opcoes],
                id="lista-opcoes",
            )
            with Horizontal(id="botoes-modal"):
                yield Button("Cancelar", variant="primary", id="botao-cancelar")

    def on_mount(self) -> None:
        self.query_one("#lista-opcoes", OptionList).focus()

    def on_option_list_option_selected(self, evento: OptionList.OptionSelected) -> None:
        self.dismiss(str(evento.option.id or ""))

    def on_button_pressed(self) -> None:
        self.dismiss(None)

    def action_cancelar(self) -> None:
        self.dismiss(None)


class DashboardScreen(Screen):
    """
    PT-PT: O painel.

           Cinco separadores, e o primeiro é o dos achados — porque a pergunta
           que traz alguém aqui é "está tudo bem?", e não "quantas máquinas há".
           As tabelas vêm a seguir para quem já sabe o que quer ver.

           As teclas de operação só existem nos separadores onde fazem sentido,
           e a barra de baixo muda com o separador. Uma tecla que faça uma coisa
           num ecrã e nada noutro é pior do que uma tecla que não existe.

    EN-UK: The dashboard. Five tabs, and the first is the findings — because the
           question that brings somebody here is "is everything all right?", not
           "how many machines are there". The operation keys only exist on the
           tabs where they mean something, and the bottom bar changes with the
           tab: a key that does one thing on one screen and nothing on another
           is worse than a key that does not exist.
    """

    BINDINGS = [
        Binding("r", "actualizar", "Actualizar"),
        Binding("l", "ligar_vm", "Ligar"),
        Binding("e", "encerrar_vm", "Encerrar"),
        Binding("s", "snapshot", "Snapshot"),
        Binding("m", "manutencao", "Manutenção"),
        Binding("t", "texto", "Copiar em texto"),
        Binding("q", "app.quit", "Sair"),
    ]

    def __init__(self, parque: Fleet, definicoes: Settings) -> None:
        super().__init__()
        self.parque = parque
        self.definicoes = definicoes
        self.achados: list = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("", id="cabecalho-parque")
        with TabbedContent(initial="aba-estado"):
            with TabPane("Estado", id="aba-estado"):
                yield VerticalScroll(Static("", id="lista-achados"))
            with TabPane("Anfitriões", id="aba-anfitrioes"):
                yield DataTable(id="tabela-anfitrioes", cursor_type="row")
            with TabPane("Máquinas", id="aba-maquinas"):
                yield DataTable(id="tabela-maquinas", cursor_type="row")
            with TabPane("Datastores", id="aba-datastores"):
                yield DataTable(id="tabela-datastores", cursor_type="row")
            with TabPane("Snapshots", id="aba-snapshots"):
                yield DataTable(id="tabela-snapshots", cursor_type="row")
        yield Static("", id="linha-estado")
        yield Footer()

    def on_mount(self) -> None:
        self._preparar_colunas()
        self.actualizar_vista(self.parque)

    def _preparar_colunas(self) -> None:
        anfitrioes = self.query_one("#tabela-anfitrioes", DataTable)
        anfitrioes.add_columns("Anfitrião", "Estado", "CPU", "Memória", "VMs", "Uptime", "Versão")

        maquinas = self.query_one("#tabela-maquinas", DataTable)
        maquinas.add_columns(
            "", "Máquina", "Estado", "vCPU", "Memória", "Tools", "Snap", "Endereço", "Anfitrião"
        )

        datastores = self.query_one("#tabela-datastores", DataTable)
        datastores.add_columns("Datastore", "Tipo", "Capacidade", "Livre", "Livre %", "Estado")

        snapshots = self.query_one("#tabela-snapshots", DataTable)
        snapshots.add_columns("Máquina", "Snapshot", "Idade", "Nível", "Descrição")

    # -- PT-PT: Desenhar. / EN-UK: Drawing. ---------------------------------

    def actualizar_vista(self, parque: Fleet) -> None:
        """
        PT-PT: Redesenha tudo com um inventário novo.

               Guarda-se a linha onde o cursor estava e repõe-se depois. Sem
               isso, cada actualização automática atirava o cursor para o topo —
               e alguém a meio de olhar para a máquina número quarenta perdia-a
               de minuto a minuto.

        EN-UK: Redraws everything with a fresh inventory. The cursor row is
               saved and restored: without that, every automatic refresh threw
               the cursor back to the top, and somebody halfway down a list lost
               their place every minute.
        """
        self.parque = parque
        self.achados = health.evaluate(parque, self.definicoes.thresholds())  # type: ignore[arg-type]

        self._desenhar_cabecalho()
        self._desenhar_achados()

        for identificador, desenhar in (
            ("#tabela-anfitrioes", self._desenhar_anfitrioes),
            ("#tabela-maquinas", self._desenhar_maquinas),
            ("#tabela-datastores", self._desenhar_datastores),
            ("#tabela-snapshots", self._desenhar_snapshots),
        ):
            tabela = self.query_one(identificador, DataTable)
            linha = tabela.cursor_row
            tabela.clear()
            desenhar(tabela)
            if 0 <= linha < tabela.row_count:
                tabela.move_cursor(row=linha)

        recolhido = parque.collected_at.astimezone().strftime("%H:%M:%S")
        self.query_one("#linha-estado", Static).update(
            f" Actualizado às {recolhido} · r actualiza · setas movem · Enter mostra detalhe"
        )

    def _desenhar_cabecalho(self) -> None:
        totais = health.fleet_totals(self.parque)
        contagem = health.summarise(self.achados)
        pior = health.worst(self.achados)

        veredicto = {
            Severity.CRITICAL: "[b]HÁ PROBLEMAS CRÍTICOS[/b]",
            Severity.WARNING: "[b]HÁ AVISOS[/b]",
            Severity.INFO: "[b]SEM NADA A APONTAR[/b]",
        }[pior]

        tipo = "vCenter" if self.parque.is_vcenter else "ESXi"
        linhas = [
            f"[b]{self.parque.endpoint}[/b]  ·  {tipo}  ·  {self.parque.product_name}",
            f"{totais['anfitrioes_ligados']}/{totais['anfitrioes']} anfitriões  ·  "
            f"{totais['maquinas_ligadas']}/{totais['maquinas']} máquinas ligadas  ·  "
            f"{totais['datastores']} datastores  ·  {totais['snapshots']} snapshots  ·  "
            f"{totais['alarmes']} alarmes",
            f"{veredicto}  —  {contagem[Severity.CRITICAL]} críticos, "
            f"{contagem[Severity.WARNING]} avisos, {contagem[Severity.INFO]} informativos",
        ]
        if self.parque.read_only_reason:
            linhas.append(f"[b]LICENÇA:[/b] {self.parque.read_only_reason}")
        self.query_one("#cabecalho-parque", Static).update("\n".join(linhas))

    def _desenhar_achados(self) -> None:
        alvo = self.query_one("#lista-achados", Static)
        if not self.achados:
            alvo.update(
                "\n  Nada a apontar.\n\n"
                "  Nenhuma das regras disparou neste parque: sem datastores apertados,\n"
                "  sem snapshots esquecidos, sem anfitriões em falta e sem alarmes por\n"
                "  reconhecer.\n"
            )
            return

        estilos = {Severity.CRITICAL: "critico", Severity.WARNING: "aviso", Severity.INFO: "info"}
        partes: list[str] = []
        gravidade = None
        for achado in self.achados:
            if achado.severity is not gravidade:
                gravidade = achado.severity
                partes.append(f"\n[b]{achado.severity.label.upper()}[/b]")
            classe = estilos[achado.severity]
            partes.append(
                f"  [{classe}]{achado.severity.tag}[/{classe}] "
                f"[b]{achado.subject}[/b]: {achado.message}"
            )
            if achado.remedy:
                partes.append(f"          {achado.remedy}")
        alvo.update("\n".join(partes))

    def _desenhar_anfitrioes(self, tabela: DataTable) -> None:
        for anfitriao in sorted(self.parque.hosts, key=lambda h: h.name.lower()):
            estado = anfitriao.connection_state.label
            if anfitriao.in_maintenance_mode:
                estado = "Manutenção"
            cpu = anfitriao.cpu_used_percent
            memoria = anfitriao.memory_used_percent
            tabela.add_row(
                anfitriao.name,
                estado,
                f"{cpu:.0f}%" if cpu is not None else "--",
                f"{memoria:.0f}%" if memoria is not None else "--",
                f"{anfitriao.running_vm_count}/{anfitriao.vm_count}",
                format_uptime(anfitriao.uptime_seconds),
                anfitriao.version or "--",
                key=anfitriao.moid,
            )

    def _desenhar_maquinas(self, tabela: DataTable) -> None:
        maquinas = [vm for vm in self.parque.vms if not vm.is_template]
        for vm in sorted(maquinas, key=lambda v: v.name.lower()):
            tabela.add_row(
                vm.power_state.symbol,
                vm.name,
                vm.power_state.label,
                str(vm.cpu_count),
                format_bytes(vm.memory_bytes),
                vm.tools_status.label,
                str(vm.snapshot_count) if vm.snapshot_count else "",
                vm.ip_address or "--",
                vm.host_name or "--",
                key=vm.moid,
            )

    def _desenhar_datastores(self, tabela: DataTable) -> None:
        # PT-PT: Ordenado pelo que tem menos espaço livre. A informação que se
        #        procura numa lista de datastores está sempre no fundo da lista
        #        ordenada por nome.
        # EN-UK: Sorted by least free space. What you look for in a datastore
        #        list is always at the bottom of one sorted by name.
        for datastore in sorted(self.parque.datastores, key=lambda d: d.free_percent or 0):
            livre = datastore.free_percent
            tabela.add_row(
                datastore.name,
                datastore.kind or "--",
                format_bytes(datastore.capacity_bytes),
                format_bytes(datastore.free_bytes),
                f"{livre:.0f}%" if livre is not None else "--",
                "Inacessível" if not datastore.accessible else datastore.overall_status.label,
                key=datastore.moid,
            )

    def _desenhar_snapshots(self, tabela: DataTable) -> None:
        agora = datetime.now(timezone.utc)
        entradas = [(vm, s) for vm in self.parque.vms for s in vm.snapshots]
        entradas.sort(key=lambda par: par[1].age_days(agora) or 0, reverse=True)
        for vm, snapshot in entradas:
            idade = snapshot.age_days(agora)
            tabela.add_row(
                vm.name,
                snapshot.name,
                f"{idade} d" if idade is not None else "--",
                str(snapshot.depth),
                snapshot.description or "",
                key=f"{vm.moid}:{snapshot.identifier}",
            )

    # -- PT-PT: O que está seleccionado. / EN-UK: What is selected. ---------

    def aba_actual(self) -> str:
        return str(self.query_one(TabbedContent).active)

    def maquina_seleccionada(self) -> object | None:
        """PT-PT: A máquina sob o cursor. / EN-UK: The machine under the cursor."""
        return self._sob_cursor("#tabela-maquinas", self.parque.vm_by_moid)

    def anfitriao_seleccionado(self) -> object | None:
        """PT-PT: O anfitrião sob o cursor. / EN-UK: The host under the cursor."""
        return self._sob_cursor("#tabela-anfitrioes", self.parque.host_by_moid)

    def snapshot_seleccionado(self) -> tuple[object, object] | None:
        """PT-PT: O par máquina/snapshot sob o cursor. / EN-UK: The pair under the cursor."""
        chave = self._chave_sob_cursor("#tabela-snapshots")
        if not chave or ":" not in chave:
            return None
        moid, _, identificador = chave.partition(":")
        maquina = self.parque.vm_by_moid(moid)
        if maquina is None:
            return None
        snapshot = next(
            (s for s in maquina.snapshots if str(s.identifier) == identificador), None
        )
        return (maquina, snapshot) if snapshot else None

    def _chave_sob_cursor(self, identificador: str) -> str:
        tabela = self.query_one(identificador, DataTable)
        if tabela.row_count == 0:
            return ""
        try:
            return str(tabela.coordinate_to_cell_key(tabela.cursor_coordinate).row_key.value or "")
        except Exception:  # noqa: BLE001
            return ""

    def _sob_cursor(self, identificador: str, procurar: object) -> object | None:
        chave = self._chave_sob_cursor(identificador)
        return procurar(chave) if chave else None  # type: ignore[operator]

    # -- PT-PT: As teclas. / EN-UK: The keys. -------------------------------

    def action_actualizar(self) -> None:
        self.app.actualizar_inventario()  # type: ignore[attr-defined]

    def action_ligar_vm(self) -> None:
        self.app.accao_ligar()  # type: ignore[attr-defined]

    def action_encerrar_vm(self) -> None:
        self.app.accao_encerrar()  # type: ignore[attr-defined]

    def action_snapshot(self) -> None:
        self.app.accao_snapshot()  # type: ignore[attr-defined]

    def action_manutencao(self) -> None:
        self.app.accao_manutencao()  # type: ignore[attr-defined]

    def action_texto(self) -> None:
        self.app.gravar_relatorio()  # type: ignore[attr-defined]
