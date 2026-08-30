#!/usr/bin/env python3
"""
PT-PT: A janela principal.

       Cinco separadores, pela ordem do trabalho: prepara-se o mapeamento,
       corre-se, olha-se para a topologia, procura-se um equipamento na lista, e
       vê-se o que ficou assinalado.

       Duas decisões de construção que valem a pena explicar.

       **As listas são `ttk.Treeview` e não widgets do customtkinter.** Uma rede
       de hotel dá facilmente dois mil pontos finais, e desenhar dois mil
       conjuntos de etiquetas em Tk demora dezenas de segundos e come memória. O
       `Treeview` desenha só as linhas visíveis. É mais feio; é utilizável.

       **O mapeamento corre noutra linha de execução, e vai escrevendo.** Um
       crawl de trinta switches demora minutos. Uma janela congelada durante
       minutos é uma janela que alguém fecha a meio — daí o registo ao vivo, que
       além de tranquilizar mostra exactamente onde é que parou quando pára.

EN-UK: The main window.

       Five tabs, in work order: prepare the mapping, run it, look at the
       topology, find a device in the list, and see what got flagged.

       Two construction decisions worth explaining.

       **The lists are `ttk.Treeview`, not customtkinter widgets.** A hotel
       network easily yields two thousand endpoints, and drawing two thousand
       sets of labels in Tk takes tens of seconds and eats memory. `Treeview`
       draws only the visible rows. It is uglier; it is usable.

       **The mapping runs on another thread, and reports as it goes.** A
       thirty-switch crawl takes minutes. A window frozen for minutes is a
       window somebody closes halfway — hence the live log, which besides
       reassuring shows exactly where it stopped when it stops.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, ttk
from typing import Any

import customtkinter as ctk

from .. import __app_name__, __version__, reports
from .. import topology as topo
from ..config import Settings, save_settings
from ..crawler import CrawlOptions, CrawlResult, crawl, seeds_from_unifi
from ..models import Credentials, NetworkDevice, Topology
from ..unifi import UnifiClient, UnifiController, UnifiDevice, UnifiError
from . import theme
from .dialogs import CredentialsDialog
from .widgets import Card, Field, MonoView, SwitchField, primary_button, quiet_button

logger = logging.getLogger(__name__)


class App(ctk.CTk):
    """
    PT-PT: A aplicação. Guarda as definições, o mapa da última corrida e as
           credenciais da sessão.
    EN-UK: The application. It holds the settings, the last run's map and the
           session credentials.
    """

    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self.settings = settings
        self.topology: Topology | None = None
        self.started: datetime | None = None
        self.credentials: Credentials | None = None
        self.unifi_credentials: Credentials | None = None
        self._running = False

        ctk.set_appearance_mode(settings.tema)
        ctk.set_default_color_theme("blue")

        self.title(f"{__app_name__} {__version__}")
        self.minsize(theme.WINDOW_MIN_WIDTH, theme.WINDOW_MIN_HEIGHT)
        self.geometry(f"{theme.WINDOW_MIN_WIDTH}x{theme.WINDOW_MIN_HEIGHT}")
        self.configure(fg_color=theme.SURFACE)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._style_tables()
        self._build_header()
        self._build_tabs()
        self._build_status_bar()

    # -----------------------------------------------------------------------
    # PT-PT: Estrutura.
    # EN-UK: Structure.
    # -----------------------------------------------------------------------

    def _style_tables(self) -> None:
        """
        PT-PT: Põe o `Treeview` do Tk parecido com o resto da janela.

               O `Treeview` não conhece o modo escuro do customtkinter, por isso
               as cores são escolhidas aqui conforme o modo activo. Sem isto,
               uma aplicação em modo escuro tem quatro tabelas brancas a
               brilhar no meio.

        EN-UK: Makes Tk's `Treeview` look like the rest of the window.

               `Treeview` knows nothing of customtkinter's dark mode, so the
               colours are picked here according to the active mode. Without
               this, a dark-mode application has four white tables glaring in
               the middle of it.
        """
        escuro = ctk.get_appearance_mode() == "Dark"
        indice = 1 if escuro else 0

        estilo = ttk.Style()
        try:
            estilo.theme_use("clam")
        except Exception:  # noqa: BLE001 - PT-PT: tema indisponível neste sistema
            logger.debug("Tema 'clam' indisponível", exc_info=True)

        fundo = theme.SURFACE_RAISED[indice]
        texto = theme.TEXT_PRIMARY[indice]
        cabecalho = theme.SIDEBAR[indice]

        estilo.configure(
            "Netmap.Treeview",
            background=fundo,
            fieldbackground=fundo,
            foreground=texto,
            rowheight=24,
            borderwidth=0,
            font=(theme.resolve_font(theme.FONT_UI, theme.FONT_UI_FALLBACKS), 9),
        )
        estilo.configure(
            "Netmap.Treeview.Heading",
            background=cabecalho,
            foreground=texto,
            relief="flat",
            font=(theme.resolve_font(theme.FONT_UI, theme.FONT_UI_FALLBACKS), 9, "bold"),
        )
        estilo.map(
            "Netmap.Treeview",
            background=[("selected", theme.ACCENT[indice])],
            foreground=[("selected", "#FFFFFF")],
        )

    def _build_header(self) -> None:
        cabecalho = ctk.CTkFrame(self, fg_color=theme.SIDEBAR, corner_radius=0, height=64)
        cabecalho.grid(row=0, column=0, sticky="ew")
        cabecalho.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            cabecalho,
            text=__app_name__,
            font=ctk.CTkFont(size=theme.SIZE_TITLE, weight="bold"),
            text_color=theme.TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w", padx=theme.PAD_L, pady=theme.PAD_M)

        ctk.CTkLabel(
            cabecalho,
            text="Do controlador ao equipamento final · só leitura",
            font=ctk.CTkFont(size=theme.SIZE_SMALL),
            text_color=theme.TEXT_MUTED,
        ).grid(row=0, column=1, sticky="w", padx=theme.PAD_S)

        self._export = ctk.CTkFrame(cabecalho, fg_color="transparent")
        self._export.grid(row=0, column=2, sticky="e", padx=theme.PAD_L)
        quiet_button(self._export, "Guardar Excel", self._save_excel, width=130).pack(
            side="left", padx=theme.PAD_XS
        )
        quiet_button(self._export, "Guardar PDF", self._save_pdf, width=120).pack(
            side="left", padx=theme.PAD_XS
        )

    def _build_tabs(self) -> None:
        self.tabs = ctk.CTkTabview(
            self,
            fg_color=theme.SURFACE,
            segmented_button_selected_color=theme.ACCENT,
            segmented_button_selected_hover_color=theme.ACCENT_HOVER,
            text_color=theme.TEXT_PRIMARY,
        )
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=theme.PAD_M, pady=theme.PAD_S)

        for nome in ["Mapeamento", "Topologia", "Pontos finais", "Problemas", "Definições"]:
            self.tabs.add(nome)
            self.tabs.tab(nome).grid_columnconfigure(0, weight=1)
            self.tabs.tab(nome).grid_rowconfigure(0, weight=1)

        self._build_run_tab(self.tabs.tab("Mapeamento"))
        self._build_topology_tab(self.tabs.tab("Topologia"))
        self._build_endpoints_tab(self.tabs.tab("Pontos finais"))
        self._build_issues_tab(self.tabs.tab("Problemas"))
        self._build_settings_tab(self.tabs.tab("Definições"))

    def _build_status_bar(self) -> None:
        barra = ctk.CTkFrame(self, fg_color=theme.SIDEBAR, corner_radius=0, height=30)
        barra.grid(row=2, column=0, sticky="ew")
        barra.grid_columnconfigure(0, weight=1)

        self._status = ctk.CTkLabel(
            barra,
            text="Pronto. Nenhum mapeamento feito nesta sessão.",
            font=ctk.CTkFont(size=theme.SIZE_SMALL),
            text_color=theme.TEXT_MUTED,
            anchor="w",
        )
        self._status.grid(row=0, column=0, sticky="w", padx=theme.PAD_M, pady=theme.PAD_XS)

    def status(self, message: str, tone: str = "info") -> None:
        """PT-PT: Escreve na barra de estado. / EN-UK: Writes to the status bar."""
        cores = {
            "info": theme.TEXT_MUTED,
            "ok": theme.OK,
            "aviso": theme.WARNING,
            "erro": theme.DANGER,
        }
        self._status.configure(text=message, text_color=cores.get(tone, theme.TEXT_MUTED))

    # -----------------------------------------------------------------------
    # PT-PT: Separador do mapeamento.
    # EN-UK: Mapping tab.
    # -----------------------------------------------------------------------

    def _build_run_tab(self, parent: Any) -> None:
        parent.grid_columnconfigure(0, weight=2)
        parent.grid_columnconfigure(1, weight=3)

        formulario = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        formulario.grid(row=0, column=0, sticky="nsew", padx=(0, theme.PAD_S))
        formulario.grid_columnconfigure(0, weight=1)

        cartao = Card(
            formulario,
            "Por onde começar",
            "Um switch de core chega: o resto vem pelo LLDP. Vários endereços, um por linha.",
        )
        cartao.grid(row=0, column=0, sticky="ew", pady=(0, theme.PAD_S))
        self._seeds = ctk.CTkTextbox(
            cartao.body,
            height=90,
            border_width=1,
            border_color=theme.BORDER,
            fg_color=theme.SURFACE,
        )
        self._seeds.grid(row=cartao.next_row(), column=0, columnspan=2, sticky="ew")
        self._seeds.insert("1.0", "\n".join(self.settings.seeds))

        cartao = Card(
            formulario,
            "Controlador UniFi",
            "Opcional. Serve para semear o mapa e para saber em que porta estão os clientes "
            "que ele conhece. Deixe vazio se não houver.",
        )
        cartao.grid(row=1, column=0, sticky="ew", pady=theme.PAD_S)
        self.f_unifi = Field(cartao, "Endereço", self.settings.unifi_url, "https://10.0.10.5:8443")
        self.f_site = Field(cartao, "Sítio", self.settings.unifi_site, "default")
        self.f_verificar = SwitchField(
            cartao,
            "Verificar o certificado",
            self.settings.unifi_verify_tls,
            "Os controladores UniFi usam certificados auto-assinados. Desligar isto mantém a "
            "ligação cifrada mas deixa de haver garantia de que o controlador é quem diz ser.",
        )

        cartao = Card(formulario, "Limites")
        cartao.grid(row=2, column=0, sticky="ew", pady=theme.PAD_S)
        self.f_profundidade = Field(cartao, "Saltos máximos", str(self.settings.max_depth))
        self.f_max = Field(cartao, "Equipamentos máximos", str(self.settings.max_devices))
        self.f_hop = SwitchField(
            cartao,
            "Salto para a CLI nos UniFi",
            self.settings.unifi_cli_hop,
            "Alguns modelos UniFi só dão a CLI de comutação depois de um `telnet localhost`.",
        )

        acoes = ctk.CTkFrame(formulario, fg_color="transparent")
        acoes.grid(row=3, column=0, sticky="ew", pady=theme.PAD_M)
        self._run_button = primary_button(acoes, "Mapear a rede", self._start, width=160)
        self._run_button.pack(side="left", padx=(0, theme.PAD_S))
        ctk.CTkLabel(
            acoes,
            text="Só são enviados comandos de leitura.",
            font=ctk.CTkFont(size=theme.SIZE_SMALL),
            text_color=theme.TEXT_MUTED,
        ).pack(side="left")

        direita = ctk.CTkFrame(parent, fg_color="transparent")
        direita.grid(row=0, column=1, sticky="nsew")
        direita.grid_columnconfigure(0, weight=1)
        direita.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            direita,
            text="Registo do mapeamento",
            font=ctk.CTkFont(size=theme.SIZE_HEADING, weight="bold"),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", pady=(0, theme.PAD_XS))

        self._log = MonoView(direita)
        self._log.grid(row=1, column=0, sticky="nsew")

    def _log_line(self, text: str) -> None:
        """PT-PT: Acrescenta uma linha ao registo. / EN-UK: Appends a line to the log."""
        actual = self._log.get_text()
        self._log.set_text(f"{actual}\n{text}" if actual else text)
        self._log.see("end")

    # -----------------------------------------------------------------------
    # PT-PT: Separadores de resultado.
    # EN-UK: Result tabs.
    # -----------------------------------------------------------------------

    def _table(self, parent: Any, columns: list[tuple[str, int]]) -> ttk.Treeview:
        """
        PT-PT: Uma tabela com barra de deslocamento.

        EN-UK: A table with a scrollbar.

        :param parent:
            PT-PT: Onde a pôr. / EN-UK: Where to put it.
        :param columns:
            PT-PT: Pares (título, largura). / EN-UK: (heading, width) pairs.
        :return:
            PT-PT: A tabela, pronta a receber linhas.
            EN-UK: The table, ready to take rows.
        """
        quadro = ctk.CTkFrame(parent, fg_color="transparent")
        quadro.grid(row=0, column=0, sticky="nsew")
        quadro.grid_columnconfigure(0, weight=1)
        quadro.grid_rowconfigure(0, weight=1)

        tabela = ttk.Treeview(
            quadro,
            columns=[titulo for titulo, _ in columns],
            show="headings",
            style="Netmap.Treeview",
        )
        for titulo, largura in columns:
            tabela.heading(titulo, text=titulo)
            tabela.column(titulo, width=largura, anchor="w", stretch=False)
        tabela.grid(row=0, column=0, sticky="nsew")

        barra = ttk.Scrollbar(quadro, orient="vertical", command=tabela.yview)
        barra.grid(row=0, column=1, sticky="ns")
        tabela.configure(yscrollcommand=barra.set)

        horizontal = ttk.Scrollbar(quadro, orient="horizontal", command=tabela.xview)
        horizontal.grid(row=1, column=0, sticky="ew")
        tabela.configure(xscrollcommand=horizontal.set)

        return tabela

    def _build_topology_tab(self, parent: Any) -> None:
        parent.grid_rowconfigure(0, weight=3)
        parent.grid_rowconfigure(2, weight=2)

        superior = ctk.CTkFrame(parent, fg_color="transparent")
        superior.grid(row=0, column=0, sticky="nsew")
        superior.grid_columnconfigure(0, weight=1)
        superior.grid_rowconfigure(0, weight=1)
        self._devices_table = self._table(
            superior,
            [
                ("Equipamento", 190),
                ("Endereço", 120),
                ("Plataforma", 170),
                ("Modelo", 240),
                ("Estado", 110),
                ("Saltos", 60),
                ("Ligados", 70),
            ],
        )

        ctk.CTkLabel(
            parent,
            text="Ligações",
            font=ctk.CTkFont(size=theme.SIZE_HEADING, weight="bold"),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", pady=(theme.PAD_M, theme.PAD_XS))

        inferior = ctk.CTkFrame(parent, fg_color="transparent")
        inferior.grid(row=2, column=0, sticky="nsew")
        inferior.grid_columnconfigure(0, weight=1)
        inferior.grid_rowconfigure(0, weight=1)
        self._links_table = self._table(
            inferior,
            [
                ("Equipamento A", 200),
                ("Porta A", 140),
                ("Equipamento B", 200),
                ("Porta B", 140),
                ("Descoberta por", 130),
            ],
        )

    def _build_endpoints_tab(self, parent: Any) -> None:
        parent.grid_rowconfigure(1, weight=1)

        topo_barra = ctk.CTkFrame(parent, fg_color="transparent")
        topo_barra.grid(row=0, column=0, sticky="ew", pady=(0, theme.PAD_S))
        topo_barra.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(topo_barra, text="Procurar", text_color=theme.TEXT_PRIMARY).grid(
            row=0, column=0, padx=(0, theme.PAD_S)
        )
        self._filter = ctk.StringVar()
        entrada = ctk.CTkEntry(
            topo_barra,
            textvariable=self._filter,
            placeholder_text="MAC, IP, nome, porta, tipo — qualquer coisa",
            border_color=theme.BORDER,
        )
        entrada.grid(row=0, column=1, sticky="ew")
        self._filter.trace_add("write", lambda *_: self._refresh_endpoints())

        quadro = ctk.CTkFrame(parent, fg_color="transparent")
        quadro.grid(row=1, column=0, sticky="nsew")
        quadro.grid_columnconfigure(0, weight=1)
        quadro.grid_rowconfigure(0, weight=1)
        self._endpoints_table = self._table(
            quadro,
            [
                ("Equipamento", 150),
                ("Porta", 110),
                ("Etiqueta", 150),
                ("VLAN", 55),
                ("Tipo", 140),
                ("Confiança", 80),
                ("MAC", 140),
                ("IP", 110),
                ("Nome", 170),
                ("Fabricante", 160),
                ("PoE", 55),
                ("Notas", 320),
            ],
        )

    def _build_issues_tab(self, parent: Any) -> None:
        parent.grid_rowconfigure(0, weight=1)
        quadro = ctk.CTkFrame(parent, fg_color="transparent")
        quadro.grid(row=0, column=0, sticky="nsew")
        quadro.grid_columnconfigure(0, weight=1)
        quadro.grid_rowconfigure(0, weight=1)
        self._issues_table = self._table(
            quadro, [("Gravidade", 90), ("Onde", 220), ("O que se passa", 900)]
        )

    def _build_settings_tab(self, parent: Any) -> None:
        quadro = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        quadro.grid(row=0, column=0, sticky="nsew")
        quadro.grid_columnconfigure(0, weight=1)

        cartao = Card(quadro, "Pastas", "Nada é escrito dentro da pasta do programa.")
        cartao.grid(row=0, column=0, sticky="ew", pady=(0, theme.PAD_S))
        self.s_output = Field(cartao, "Relatórios", self.settings.output_dir, width=420)

        cartao = Card(
            quadro,
            "Fabricantes",
            "A tabela embutida cobre os fabricantes habituais. Para a lista completa, "
            "descarregue standards-oui.ieee.org/oui/oui.csv e indique o ficheiro aqui.",
        )
        cartao.grid(row=1, column=0, sticky="ew", pady=theme.PAD_S)
        self.s_oui = Field(cartao, "Ficheiro do IEEE", self.settings.oui_file, width=420)

        cartao = Card(quadro, "Rede e aparência")
        cartao.grid(row=2, column=0, sticky="ew", pady=theme.PAD_S)
        self.s_timeout = Field(cartao, "Tempo limite SSH (s)", str(self.settings.ssh_timeout))
        self.s_theme = Field(cartao, "Tema (system/light/dark)", self.settings.tema)

        primary_button(quadro, "Guardar definições", self._save_settings, width=180).grid(
            row=3, column=0, sticky="w", pady=theme.PAD_M
        )

    def _save_settings(self) -> None:
        self.settings.output_dir = self.s_output.get()
        self.settings.oui_file = self.s_oui.get()
        self.settings.tema = self.s_theme.get() or "system"
        timeout = self.s_timeout.get()
        self.settings.ssh_timeout = int(timeout) if timeout.isdigit() else 30

        self.settings.seeds = _lines(self._seeds.get("1.0", "end"))
        self.settings.unifi_url = self.f_unifi.get()
        self.settings.unifi_site = self.f_site.get() or "default"
        self.settings.unifi_verify_tls = self.f_verificar.get()
        self.settings.unifi_cli_hop = self.f_hop.get()
        self.settings.max_depth = _as_int(self.f_profundidade.get(), 4)
        self.settings.max_devices = _as_int(self.f_max.get(), 150)

        caminho = save_settings(self.settings)
        ctk.set_appearance_mode(self.settings.tema)
        self._style_tables()
        self.status(f"Definições gravadas em {caminho}", "ok")

    # -----------------------------------------------------------------------
    # PT-PT: A corrida.
    # EN-UK: The run.
    # -----------------------------------------------------------------------

    def _start(self) -> None:
        """PT-PT: Arranca o mapeamento. / EN-UK: Starts the mapping."""
        if self._running:
            return

        sementes_texto = _lines(self._seeds.get("1.0", "end"))
        url_unifi = self.f_unifi.get()

        if not sementes_texto and not url_unifi:
            self.status(
                "Indique pelo menos um switch por onde começar, ou um controlador UniFi.",
                "aviso",
            )
            return

        credenciais = self._ask_credentials(
            "Credenciais dos switches",
            "Um utilizador com permissão de leitura chega. Nada é escrito em equipamento nenhum.",
        )
        if credenciais is None:
            return

        credenciais_unifi = None
        if url_unifi:
            credenciais_unifi = self._ask_credentials(
                "Credenciais do controlador UniFi",
                "Um utilizador só de leitura do controlador.",
                unifi=True,
            )
            if credenciais_unifi is None:
                return

        opcoes = CrawlOptions(
            max_depth=_as_int(self.f_profundidade.get(), 4),
            max_devices=_as_int(self.f_max.get(), 150),
            timeout=self.settings.ssh_timeout,
            unifi_cli_hop=self.f_hop.get(),
        )
        sitio = self.f_site.get() or "default"
        verificar = self.f_verificar.get()

        self._running = True
        self._run_button.configure(state="disabled", text="A mapear...")
        self._log.set_text("")
        self.started = datetime.now()
        self.status("A percorrer a rede...")

        def trabalho() -> Topology:
            equipamentos: list[UnifiDevice] = []
            clientes: list[UnifiClient] = []

            if url_unifi and credenciais_unifi is not None:
                self._say("A perguntar ao controlador UniFi...")
                try:
                    with UnifiController(url_unifi, sitio, verify_tls=verificar) as controlador:
                        controlador.login(
                            credenciais_unifi.username, credenciais_unifi.password
                        )
                        equipamentos = controlador.devices()
                        clientes = controlador.clients()
                    self._say(
                        f"  {len(equipamentos)} equipamentos e {len(clientes)} clientes conhecidos."
                    )
                except UnifiError as exc:
                    # PT-PT: O controlador é uma ajuda, não uma dependência.
                    # EN-UK: The controller is a help, not a dependency.
                    self._say(f"  [aviso] {exc}")
                    self._say("  A continuar a partir das sementes.")

            sementes = [NetworkDevice(host=endereco) for endereco in sementes_texto]
            vistos = {s.host for s in sementes}
            for semente in seeds_from_unifi(equipamentos):
                if semente.host not in vistos:
                    sementes.append(semente)
                    vistos.add(semente.host)

            self._say(f"A percorrer a rede a partir de {len(sementes)} ponto(s)...")
            resultado: CrawlResult = crawl(
                sementes,
                credenciais,
                opcoes,
                progress=lambda nome, feitos, fila: self._say(
                    f"  [{feitos}] {nome}" + (f"  (+{fila} em fila)" if fila else "")
                ),
            )

            mapa = topo.build(resultado.devices, equipamentos, clientes)
            mapa.issues = resultado.issues + mapa.issues
            return mapa

        def concluido(mapa: Topology) -> None:
            self.topology = mapa
            self._refresh_all()
            self._say("")
            self._say(mapa.summary())
            tom = "aviso" if any(i.severity in {"ERRO", "AVISO"} for i in mapa.issues) else "ok"
            self.status(mapa.summary(), tom)
            self._finish()

        self._run_async(trabalho, concluido)

    def _say(self, text: str) -> None:
        """
        PT-PT: Escreve no registo a partir da linha de trabalho.

               O Tk não é seguro fora da sua própria linha de execução, por isso
               a escrita é agendada e não feita ali.
        EN-UK: Writes to the log from the worker thread.

               Tk is not safe outside its own thread, so the write is scheduled
               rather than done there.
        """
        self.after(0, lambda: self._log_line(text))

    def _finish(self) -> None:
        """PT-PT: Volta a activar o botão. / EN-UK: Re-enables the button."""
        self._running = False
        self._run_button.configure(state="normal", text="Mapear a rede")

    def _ask_credentials(
        self, title: str, hint: str, unifi: bool = False
    ) -> Credentials | None:
        """PT-PT: Pede credenciais, uma vez por sessão. / EN-UK: Asks once per session."""
        guardadas = self.unifi_credentials if unifi else self.credentials
        if guardadas is not None:
            return guardadas

        obtidas = CredentialsDialog(self, title, hint).show()
        if obtidas is None:
            self.status("Sem credenciais não é possível mapear.", "aviso")
            return None

        if unifi:
            self.unifi_credentials = obtidas
        else:
            self.credentials = obtidas
        return obtidas

    # -----------------------------------------------------------------------
    # PT-PT: Mostrar o resultado.
    # EN-UK: Showing the result.
    # -----------------------------------------------------------------------

    def _refresh_all(self) -> None:
        self._refresh_devices()
        self._refresh_links()
        self._refresh_endpoints()
        self._refresh_issues()

    def _refresh_devices(self) -> None:
        _clear(self._devices_table)
        if self.topology is None:
            return

        contagem: dict[str, int] = {}
        for ponto in self.topology.endpoints:
            if ponto.located:
                contagem[ponto.switch] = contagem.get(ponto.switch, 0) + 1

        for dispositivo in sorted(self.topology.devices.values(), key=lambda d: d.label.lower()):
            self._devices_table.insert(
                "",
                "end",
                values=(
                    dispositivo.label,
                    dispositivo.host,
                    dispositivo.platform.label,
                    dispositivo.model,
                    "alcançado" if dispositivo.reached else "sem resposta",
                    dispositivo.depth,
                    contagem.get(dispositivo.label, 0) if dispositivo.reached else "—",
                ),
            )

    def _refresh_links(self) -> None:
        _clear(self._links_table)
        if self.topology is None:
            return
        for ligacao in self.topology.links:
            self._links_table.insert(
                "",
                "end",
                values=(
                    ligacao.a_device,
                    ligacao.a_port,
                    ligacao.b_device,
                    ligacao.b_port,
                    ligacao.source.value,
                ),
            )

    def _refresh_endpoints(self) -> None:
        _clear(self._endpoints_table)
        if self.topology is None:
            return

        procura = self._filter.get().strip().lower()
        mostrados = 0

        for ponto in sorted(
            self.topology.endpoints,
            key=lambda p: (p.switch.lower(), _port_key(p.port), p.mac),
        ):
            linha = (
                ponto.switch,
                ponto.port,
                ponto.port_description,
                ponto.vlan if ponto.vlan is not None else "",
                ponto.role.value,
                ponto.confidence.value,
                ponto.mac,
                ponto.ip,
                ponto.hostname,
                ponto.vendor,
                f"{ponto.poe_watts:.1f}" if ponto.poe_watts else "",
                ponto.note,
            )
            if procura and not any(procura in str(valor).lower() for valor in linha):
                continue
            self._endpoints_table.insert("", "end", values=linha)
            mostrados += 1

        if procura:
            self.status(f"{mostrados} de {len(self.topology.endpoints)} pontos finais mostrados.")

    def _refresh_issues(self) -> None:
        _clear(self._issues_table)
        if self.topology is None:
            return
        ordem = {"ERRO": 0, "AVISO": 1, "INFO": 2}
        for problema in sorted(
            self.topology.issues, key=lambda i: (ordem.get(i.severity, 3), i.subject)
        ):
            self._issues_table.insert(
                "", "end", values=(problema.severity, problema.subject, problema.message)
            )

    # -----------------------------------------------------------------------
    # PT-PT: Exportação.
    # EN-UK: Export.
    # -----------------------------------------------------------------------

    def _save_excel(self) -> None:
        self._save(reports.write_excel, ".xlsx", "Excel", [("Excel", "*.xlsx")])

    def _save_pdf(self) -> None:
        self._save(reports.write_pdf, ".pdf", "PDF", [("PDF", "*.pdf")])

    def _save(
        self,
        writer: Callable[..., Path],
        suffix: str,
        label: str,
        filetypes: list[tuple[str, str]],
    ) -> None:
        """PT-PT: Grava um relatório. / EN-UK: Saves a report."""
        if self.topology is None:
            self.status("Não há nada para exportar: faça primeiro um mapeamento.", "aviso")
            return

        carimbo = (self.started or datetime.now()).strftime("%Y%m%d-%H%M")
        caminho = filedialog.asksaveasfilename(
            title=f"Guardar {label}",
            initialdir=str(self.settings.output_path),
            initialfile=f"mapa-rede-{carimbo}{suffix}",
            defaultextension=suffix,
            filetypes=filetypes,
        )
        if not caminho:
            return

        try:
            escrito = writer(self.topology, Path(caminho), self.started)
        except reports.ReportError as exc:
            self.status(str(exc), "erro")
            return
        self.status(f"{label} escrito em {escrito}", "ok")

    # -----------------------------------------------------------------------

    def _run_async(self, work: Callable[[], Any], on_done: Callable[[Any], None]) -> None:
        """
        PT-PT: Corre `work` noutra linha de execução e entrega o resultado a
               `on_done` já na linha da interface.
        EN-UK: Runs `work` on another thread and hands the result to `on_done`
               back on the interface thread.
        """

        def envolver() -> None:
            # PT-PT: A mensagem é lida já: o Python apaga o nome da excepção no
            #        fim do `except`, e o lambda só corre depois.
            # EN-UK: The message is read now: Python deletes the exception name
            #        at the end of the `except`, and the lambda runs later.
            try:
                resultado = work()
            except Exception as exc:  # noqa: BLE001 - PT-PT: a thread não deve morrer em silêncio
                logger.exception("Falha no mapeamento")
                mensagem = f"Falhou: {exc}"
                self.after(0, lambda: self.status(mensagem, "erro"))
                self.after(0, self._finish)
                return
            self.after(0, lambda: on_done(resultado))

        threading.Thread(target=envolver, daemon=True).start()


def _clear(table: ttk.Treeview) -> None:
    """PT-PT: Esvazia uma tabela. / EN-UK: Empties a table."""
    table.delete(*table.get_children())


def _lines(text: str) -> list[str]:
    """PT-PT: Linhas não vazias de uma caixa de texto. / EN-UK: A text box's non-empty lines."""
    return [linha.strip() for linha in text.splitlines() if linha.strip()]


def _as_int(text: str, fallback: int) -> int:
    """PT-PT: Um número, ou o valor de omissão. / EN-UK: A number, or the default."""
    return int(text) if text.strip().isdigit() else fallback


def _port_key(port: str) -> tuple[int, ...]:
    """PT-PT: Ordem numérica das portas. / EN-UK: Numeric port ordering."""
    import re

    numeros = tuple(int(parte) for parte in re.findall(r"\d+", port))
    return numeros or (0,)


def run(settings: Settings) -> None:
    """
    PT-PT: Abre a janela e entrega o controlo ao Tk.

    EN-UK: Opens the window and hands control to Tk.

    :param settings:
        PT-PT: Definições em vigor. / EN-UK: The settings in force.
    """
    app = App(settings)
    app.mainloop()
