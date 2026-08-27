# -*- coding: utf-8 -*-
"""
PT-PT: Janela principal do IT Toolkit.

       Estrutura: barra lateral com os modulos, area central com o conteudo de
       cada um, barra inferior com o estado.

PT-PT: REGRA DE OURO DA CONCORRENCIA. O Tkinter nao e seguro em multiplos fios.
       Tudo o que demora — ler event logs, contar pastas, correr o gpupdate —
       corre num fio secundario e comunica com a interface exclusivamente
       atraves de uma fila lida por `_pump()` no fio principal. Nenhuma funcao
       que corra num fio secundario pode tocar num widget.

       A v1.0 chamava `self.tb.insert(...)` de dentro dos fios de trabalho. Nao
       rebentava sempre, o que e a pior propriedade que um bug destes pode ter:
       falhava de vez em quando, com uma excecao do Tcl sem relacao aparente com
       o que estava a acontecer, e era impossivel de reproduzir a pedido.

EN-UK: Main window of the IT Toolkit.

       THE GOLDEN RULE OF CONCURRENCY. Tkinter is not thread-safe. Everything
       slow runs on a secondary thread and talks to the interface solely through
       a queue read by `_pump()` on the main thread. No function running on a
       secondary thread may touch a widget.

       v1.0 called `self.tb.insert(...)` from inside worker threads. It did not
       fail every time, which is the worst property such a bug can have.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
import queue
import threading
import webbrowser
from pathlib import Path
from tkinter import messagebox
from typing import Any, Callable

import customtkinter as ctk

from .. import __app_name__, __credit__, __version__
from ..config import AppConfig
from ..models import Achado, Gravidade
from ..shell import Ambiente
from . import theme
from .dialogs import JanelaDefinicoes, JanelaTesteRede

log = logging.getLogger(__name__)

# PT-PT: Modulos da barra lateral: (chave, etiqueta).
# EN-UK: Sidebar modules: (key, label).
MODULOS: tuple[tuple[str, str], ...] = (
    ("resumo", "Resumo"),
    ("eventos", "Event Logs"),
    ("rede", "Rede"),
    ("discos", "Discos"),
    ("servicos", "Serviços"),
    ("ferramentas", "Ferramentas"),
    ("inventario", "Inventário"),
    ("relatorios", "Relatórios"),
)


class ITToolkitApp(ctk.CTk):
    """
    PT-PT: Janela principal.
    EN-UK: Main window.
    """

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self.config_app = config
        self.ambiente = Ambiente()

        # PT-PT: Fila de mensagens dos fios de trabalho para a interface.
        # EN-UK: Message queue from worker threads to the interface.
        self._fila: queue.Queue[tuple[str, Any]] = queue.Queue()
        self._ocupado = False

        # PT-PT: Resultados guardados, para os relatorios os poderem usar sem
        #        voltar a recolher tudo.
        # EN-UK: Stored results, so reports can use them without recollecting.
        self._analise = None
        self._achados: list[Achado] = []

        self._fontes()
        self._janela()
        self._construir()

        self.after(100, self._pump)
        if self.config_app.analisar_ao_arrancar:
            # PT-PT: O `after` deixa a janela desenhar-se primeiro. Arrancar a
            #        analise directamente no __init__ mostrava uma janela cinzenta
            #        durante segundos antes de aparecer seja o que for.
            # EN-UK: The `after` lets the window draw first. Starting the
            #        analysis directly in __init__ showed a grey window for
            #        seconds before anything appeared.
            self.after(250, self.analisar_tudo)

    # ------------------------------------------------------------------
    # PT-PT: Construcao / EN-UK: Construction
    # ------------------------------------------------------------------

    def _fontes(self) -> None:
        """PT-PT: Resolve os tipos de letra uma vez. / EN-UK: Resolve fonts once."""
        familia = theme.resolve_font(theme.FONT_UI, theme.FONT_UI_FALLBACKS)
        mono = theme.resolve_font(theme.FONT_MONO, theme.FONT_MONO_FALLBACKS)
        self.f_titulo = ctk.CTkFont(family=familia, size=theme.SIZE_TITLE, weight="bold")
        self.f_seccao = ctk.CTkFont(family=familia, size=theme.SIZE_HEADING, weight="bold")
        self.f_corpo = ctk.CTkFont(family=familia, size=theme.SIZE_BODY)
        self.f_pequena = ctk.CTkFont(family=familia, size=theme.SIZE_SMALL)
        self.f_mono = ctk.CTkFont(family=mono, size=theme.SIZE_SMALL)

    def _janela(self) -> None:
        """PT-PT: Propriedades da janela. / EN-UK: Window properties."""
        ctk.set_appearance_mode(self.config_app.tema)
        ctk.set_default_color_theme("blue")

        self.title(f"{__app_name__} {__version__}")
        self.geometry(f"{theme.WINDOW_MIN_WIDTH}x{theme.WINDOW_MIN_HEIGHT}")
        self.minsize(theme.WINDOW_MIN_WIDTH - 160, theme.WINDOW_MIN_HEIGHT - 120)
        self.configure(fg_color=theme.SURFACE)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

    def _construir(self) -> None:
        """PT-PT: Monta barra lateral, paginas e rodape. / EN-UK: Builds the layout."""
        self._barra_lateral()

        self.area = ctk.CTkFrame(self, fg_color="transparent")
        self.area.grid(row=0, column=1, sticky="nsew", padx=theme.PAD_M, pady=(theme.PAD_M, 0))
        self.area.grid_columnconfigure(0, weight=1)
        self.area.grid_rowconfigure(0, weight=1)

        self.paginas: dict[str, ctk.CTkFrame] = {}
        self.saidas: dict[str, ctk.CTkTextbox] = {}
        for chave, etiqueta in MODULOS:
            pagina = ctk.CTkFrame(self.area, fg_color="transparent")
            pagina.grid(row=0, column=0, sticky="nsew")
            pagina.grid_columnconfigure(0, weight=1)
            pagina.grid_rowconfigure(2, weight=1)
            self.paginas[chave] = pagina
            construtor = getattr(self, f"_pagina_{chave}")
            construtor(pagina, etiqueta)

        self._rodape()
        self.mostrar("resumo")

        for limitacao in self.ambiente.limitacoes():
            self.escrever("resumo", f"⚠  {limitacao}\n", limpar=False)

    def _barra_lateral(self) -> None:
        """PT-PT: Barra de navegacao a esquerda. / EN-UK: Left navigation bar."""
        barra = ctk.CTkFrame(
            self, width=theme.SIDEBAR_WIDTH, corner_radius=0, fg_color=theme.SIDEBAR
        )
        barra.grid(row=0, column=0, sticky="nsw")
        barra.grid_propagate(False)

        cabecalho = ctk.CTkFrame(barra, fg_color="transparent")
        cabecalho.pack(fill="x", padx=theme.PAD_M, pady=(theme.PAD_L, theme.PAD_M))
        ctk.CTkLabel(
            cabecalho, text=__app_name__, font=self.f_titulo, text_color=theme.TEXT_PRIMARY
        ).pack(anchor="w")
        estado_admin = "administrador" if self.ambiente.administrador else "sem elevação"
        ctk.CTkLabel(
            cabecalho,
            text=f"v{__version__} · {estado_admin}",
            font=self.f_pequena,
            text_color=theme.TEXT_MUTED,
        ).pack(anchor="w")

        self.botoes_nav: dict[str, ctk.CTkButton] = {}
        for chave, etiqueta in MODULOS:
            botao = ctk.CTkButton(
                barra,
                text=etiqueta,
                anchor="w",
                height=34,
                corner_radius=theme.RADIUS,
                font=self.f_corpo,
                fg_color="transparent",
                text_color=theme.TEXT_PRIMARY,
                hover_color=theme.BORDER,
                command=lambda c=chave: self.mostrar(c),
            )
            botao.pack(fill="x", padx=theme.PAD_S, pady=2)
            self.botoes_nav[chave] = botao

        rodape = ctk.CTkFrame(barra, fg_color="transparent")
        rodape.pack(side="bottom", fill="x", padx=theme.PAD_S, pady=theme.PAD_M)
        ctk.CTkButton(
            rodape,
            text="Analisar tudo",
            height=34,
            font=self.f_corpo,
            fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_HOVER,
            command=self.analisar_tudo,
        ).pack(fill="x", pady=(0, theme.PAD_XS))
        ctk.CTkButton(
            rodape,
            text="Definições",
            height=30,
            font=self.f_pequena,
            fg_color="transparent",
            text_color=theme.TEXT_MUTED,
            hover_color=theme.BORDER,
            command=self.abrir_definicoes,
        ).pack(fill="x")

    def _rodape(self) -> None:
        """PT-PT: Barra de estado. / EN-UK: Status bar."""
        barra = ctk.CTkFrame(self, height=32, corner_radius=0, fg_color=theme.SIDEBAR)
        barra.grid(row=1, column=0, columnspan=2, sticky="ew")
        barra.grid_columnconfigure(0, weight=1)

        self.lbl_estado = ctk.CTkLabel(
            barra, text="Pronto.", font=self.f_pequena,
            text_color=theme.TEXT_MUTED, anchor="w",
        )
        self.lbl_estado.grid(row=0, column=0, sticky="w", padx=theme.PAD_M, pady=theme.PAD_XS)

        self.progresso = ctk.CTkProgressBar(barra, width=140, height=6, mode="indeterminate")
        self.progresso.grid(row=0, column=1, padx=theme.PAD_M)
        self.progresso.grid_remove()

        ctk.CTkLabel(
            barra, text=__credit__, font=self.f_pequena, text_color=theme.TEXT_MUTED
        ).grid(row=0, column=2, sticky="e", padx=theme.PAD_M)

    # ------------------------------------------------------------------
    # PT-PT: Pecas reutilizaveis / EN-UK: Reusable pieces
    # ------------------------------------------------------------------

    def _titulo(self, pagina: ctk.CTkFrame, texto: str, subtitulo: str) -> None:
        """PT-PT: Cabecalho de uma pagina. / EN-UK: Page heading."""
        caixa = ctk.CTkFrame(pagina, fg_color="transparent")
        caixa.grid(row=0, column=0, sticky="ew", pady=(0, theme.PAD_S))
        ctk.CTkLabel(
            caixa, text=texto, font=self.f_titulo, text_color=theme.TEXT_PRIMARY
        ).pack(anchor="w")
        ctk.CTkLabel(
            caixa, text=subtitulo, font=self.f_pequena, text_color=theme.TEXT_MUTED,
            justify="left", anchor="w",
        ).pack(anchor="w")

    def _barra_botoes(self, pagina: ctk.CTkFrame) -> ctk.CTkFrame:
        """PT-PT: Linha de botoes de uma pagina. / EN-UK: A page's button row."""
        caixa = ctk.CTkFrame(pagina, fg_color="transparent")
        caixa.grid(row=1, column=0, sticky="ew", pady=(0, theme.PAD_S))
        return caixa

    def _botao(
        self, pai: ctk.CTkFrame, texto: str, comando: Callable[[], None], principal: bool = False
    ) -> ctk.CTkButton:
        """PT-PT: Botao normalizado. / EN-UK: Standardised button."""
        botao = ctk.CTkButton(
            pai,
            text=texto,
            height=30,
            font=self.f_corpo,
            corner_radius=theme.RADIUS,
            fg_color=theme.ACCENT if principal else "transparent",
            text_color=theme.TEXT_ON_ACCENT if principal else theme.TEXT_PRIMARY,
            hover_color=theme.ACCENT_HOVER if principal else theme.BORDER,
            border_width=0 if principal else 1,
            border_color=theme.BORDER,
            command=comando,
        )
        botao.pack(side="left", padx=(0, theme.PAD_S))
        return botao

    def _saida(self, pagina: ctk.CTkFrame, chave: str) -> ctk.CTkTextbox:
        """PT-PT: Caixa de texto de resultados. / EN-UK: Results text box."""
        caixa = ctk.CTkTextbox(
            pagina,
            font=self.f_mono,
            corner_radius=theme.RADIUS,
            fg_color=theme.SURFACE_RAISED,
            text_color=theme.TEXT_PRIMARY,
            border_width=1,
            border_color=theme.BORDER,
            wrap="word",
        )
        caixa.grid(row=2, column=0, sticky="nsew", pady=(0, theme.PAD_M))
        caixa.configure(state="disabled")
        self.saidas[chave] = caixa
        return caixa

    # ------------------------------------------------------------------
    # PT-PT: Paginas / EN-UK: Pages
    # ------------------------------------------------------------------

    def _pagina_resumo(self, pagina: ctk.CTkFrame, etiqueta: str) -> None:
        self._titulo(
            pagina, "Resumo da máquina",
            "Estado geral, discos, rede e serviços numa única passagem.",
        )
        botoes = self._barra_botoes(pagina)
        self._botao(botoes, "Analisar tudo", self.analisar_tudo, principal=True)
        self._botao(botoes, "Gerar relatório de saúde", self.relatorio_saude)
        self._saida(pagina, "resumo")

    def _pagina_eventos(self, pagina: ctk.CTkFrame, etiqueta: str) -> None:
        self._titulo(
            pagina, "Análise de Event Logs",
            "Lê, agrupa e interpreta os eventos, com causa provável e o que verificar.",
        )
        botoes = self._barra_botoes(pagina)

        ctk.CTkLabel(botoes, text="Período:", font=self.f_corpo).pack(
            side="left", padx=(0, theme.PAD_XS)
        )
        self.cb_periodo = ctk.CTkComboBox(
            botoes,
            values=["Últimas 24h", "Últimas 48h", "Últimos 7 dias", "Últimos 30 dias"],
            width=150,
            state="readonly",
            font=self.f_corpo,
            command=self._mudar_periodo,
        )
        self.cb_periodo.set(self._etiqueta_periodo(self.config_app.periodo_horas))
        self.cb_periodo.pack(side="left", padx=(0, theme.PAD_M))

        self._botao(botoes, "Analisar", self.analisar_eventos, principal=True)
        self.btn_rel_eventos = self._botao(botoes, "Gerar relatório HTML", self.relatorio_eventos)
        self.btn_rel_eventos.configure(state="disabled")
        self._saida(pagina, "eventos")

    def _pagina_rede(self, pagina: ctk.CTkFrame, etiqueta: str) -> None:
        self._titulo(
            pagina, "Rede",
            "Configuração dos adaptadores, diagnóstico e testes pontuais.",
        )
        botoes = self._barra_botoes(pagina)
        self._botao(botoes, "Diagnosticar", self.diagnosticar_rede, principal=True)
        self._botao(botoes, "Ping / tracert / porta", self.abrir_teste_rede)
        self._botao(botoes, "Configuração IP", lambda: self.accao_rapida("ipconfig", "rede"))
        self._saida(pagina, "rede")

    def _pagina_discos(self, pagina: ctk.CTkFrame, etiqueta: str) -> None:
        self._titulo(
            pagina, "Discos",
            "Espaço por partição, estado dos discos físicos e as maiores pastas.",
        )
        botoes = self._barra_botoes(pagina)
        self._botao(botoes, "Verificar", self.verificar_discos, principal=True)
        self._botao(botoes, "Maiores pastas de C:", self.maiores_pastas)
        self._saida(pagina, "discos")

    def _pagina_servicos(self, pagina: ctk.CTkFrame, etiqueta: str) -> None:
        self._titulo(
            pagina, "Serviços",
            "Serviços com arranque automático que não estão a correr.",
        )
        botoes = self._barra_botoes(pagina)
        self._botao(botoes, "Listar parados", self.listar_servicos, principal=True)

        self.entrada_servico = ctk.CTkEntry(
            botoes, placeholder_text="Nome do serviço", width=200, font=self.f_corpo
        )
        self.entrada_servico.pack(side="left", padx=(theme.PAD_M, theme.PAD_S))
        self._botao(botoes, "Arrancar", self.arrancar_servico)
        self._saida(pagina, "servicos")

    def _pagina_ferramentas(self, pagina: ctk.CTkFrame, etiqueta: str) -> None:
        from ..actions import ACCOES, CONSOLAS

        self._titulo(
            pagina, "Ferramentas rápidas",
            "Acções pontuais de manutenção. As que têm impacto pedem confirmação.",
        )

        grelha = ctk.CTkScrollableFrame(pagina, fg_color="transparent", height=200)
        grelha.grid(row=1, column=0, sticky="ew", pady=(0, theme.PAD_S))
        for indice in range(3):
            grelha.grid_columnconfigure(indice, weight=1)

        for posicao, accao in enumerate(ACCOES):
            ctk.CTkButton(
                grelha,
                text=accao.etiqueta,
                height=32,
                font=self.f_corpo,
                anchor="w",
                corner_radius=theme.RADIUS,
                fg_color=theme.SURFACE_RAISED,
                text_color=theme.TEXT_PRIMARY,
                hover_color=theme.BORDER,
                border_width=1,
                border_color=theme.BORDER,
                command=lambda a=accao: self.executar_ferramenta(a),
            ).grid(
                row=posicao // 3, column=posicao % 3,
                sticky="ew", padx=theme.PAD_XS, pady=theme.PAD_XS,
            )

        base = len(ACCOES)
        ctk.CTkLabel(
            grelha, text="Consolas de gestão", font=self.f_seccao,
            text_color=theme.TEXT_MUTED, anchor="w",
        ).grid(
            row=base // 3 + 1, column=0, columnspan=3,
            sticky="w", padx=theme.PAD_XS, pady=(theme.PAD_M, theme.PAD_XS),
        )

        inicio = base // 3 + 2
        for posicao, (nome, ficheiro) in enumerate(CONSOLAS):
            ctk.CTkButton(
                grelha,
                text=nome,
                height=30,
                font=self.f_pequena,
                anchor="w",
                corner_radius=theme.RADIUS,
                fg_color="transparent",
                text_color=theme.TEXT_PRIMARY,
                hover_color=theme.BORDER,
                border_width=1,
                border_color=theme.BORDER,
                command=lambda f=ficheiro: self.abrir_consola(f),
            ).grid(
                row=inicio + posicao // 3, column=posicao % 3,
                sticky="ew", padx=theme.PAD_XS, pady=theme.PAD_XS,
            )

        self._saida(pagina, "ferramentas")

    def _pagina_inventario(self, pagina: ctk.CTkFrame, etiqueta: str) -> None:
        self._titulo(
            pagina, "Inventário",
            "Modelo, número de série, BIOS, actualizações e software instalado.",
        )
        botoes = self._barra_botoes(pagina)
        self._botao(botoes, "Recolher", self.recolher_inventario, principal=True)
        self.btn_rel_inv = self._botao(botoes, "Gerar relatório HTML", self.relatorio_inventario)
        self.btn_rel_inv.configure(state="disabled")
        self._saida(pagina, "inventario")

    def _pagina_relatorios(self, pagina: ctk.CTkFrame, etiqueta: str) -> None:
        self._titulo(
            pagina, "Relatórios",
            "Relatórios já gerados. Contêm dados da máquina — não os partilhe sem rever.",
        )
        botoes = self._barra_botoes(pagina)
        self._botao(botoes, "Actualizar lista", self.listar_relatorios, principal=True)
        self._botao(botoes, "Abrir pasta", self.abrir_pasta_relatorios)
        self._saida(pagina, "relatorios")
        self.after(400, self.listar_relatorios)

    # ------------------------------------------------------------------
    # PT-PT: Navegacao e escrita / EN-UK: Navigation and writing
    # ------------------------------------------------------------------

    def mostrar(self, chave: str) -> None:
        """PT-PT: Passa para um modulo. / EN-UK: Switches to a module."""
        self.paginas[chave].tkraise()
        for nome, botao in self.botoes_nav.items():
            activo = nome == chave
            botao.configure(
                fg_color=theme.ACCENT if activo else "transparent",
                text_color=theme.TEXT_ON_ACCENT if activo else theme.TEXT_PRIMARY,
            )

    def escrever(self, chave: str, texto: str, limpar: bool = True) -> None:
        """
        PT-PT: Escreve numa caixa de saida. So do fio principal.
        EN-UK: Writes to an output box. Main thread only.
        """
        caixa = self.saidas[chave]
        caixa.configure(state="normal")
        if limpar:
            caixa.delete("1.0", "end")
        caixa.insert("end", texto)
        caixa.see("end")
        caixa.configure(state="disabled")

    def estado(self, texto: str) -> None:
        """PT-PT: Actualiza a barra de estado. / EN-UK: Updates the status bar."""
        self.lbl_estado.configure(text=texto)

    # ------------------------------------------------------------------
    # PT-PT: Concorrencia / EN-UK: Concurrency
    # ------------------------------------------------------------------

    def _trabalhar(self, funcao: Callable[[], Any], destino: str, estado: str) -> None:
        """
        PT-PT: Corre `funcao` num fio e entrega o resultado a interface.

               Recusa arrancar se ja houver trabalho em curso. A v1.0 permitia
               carregar em «Analisar» dez vezes seguidas e lancava dez fios,
               todos a escrever na mesma caixa de texto ao mesmo tempo.

        EN-UK: Runs `funcao` on a thread and hands the result to the interface.
               Refuses to start when work is already in progress: v1.0 allowed
               pressing "Analyse" ten times and launched ten threads, all
               writing to the same text box at once.
        """
        if self._ocupado:
            self.estado("Já há uma operação em curso — aguarde que termine.")
            return

        self._ocupado = True
        self.estado(estado)
        self.progresso.grid()
        self.progresso.start()

        def alvo() -> None:
            try:
                resultado = funcao()
                self._fila.put(("resultado", (destino, resultado)))
            except Exception as exc:  # noqa: BLE001 — a mensagem tem de chegar ao operador
                log.exception("Falha em %s", destino)
                self._fila.put(("erro", (destino, str(exc))))

        threading.Thread(target=alvo, daemon=True).start()

    def _pump(self) -> None:
        """
        PT-PT: Le a fila e aplica na interface. So corre no fio principal.
        EN-UK: Reads the queue and applies to the interface. Main thread only.
        """
        try:
            while True:
                tipo, carga = self._fila.get_nowait()
                if tipo == "resultado":
                    destino, resultado = carga
                    self._terminar()
                    tratador = getattr(self, f"_receber_{destino}", None)
                    if tratador:
                        tratador(resultado)
                    else:
                        self.escrever(destino, str(resultado))
                elif tipo == "erro":
                    destino, mensagem = carga
                    self._terminar()
                    self.escrever(destino, f"Falhou: {mensagem}\n")
                    self.estado("Operação falhou — ver o registo com --verbose.")
                elif tipo == "texto":
                    destino, mensagem = carga
                    self.escrever(destino, mensagem, limpar=False)
        except queue.Empty:
            pass
        self.after(120, self._pump)

    def _terminar(self) -> None:
        """PT-PT: Fecha o estado de ocupado. / EN-UK: Clears the busy state."""
        self._ocupado = False
        self.progresso.stop()
        self.progresso.grid_remove()
        self.estado("Pronto.")

    # ------------------------------------------------------------------
    # PT-PT: Accoes / EN-UK: Actions
    # ------------------------------------------------------------------

    def _etiqueta_periodo(self, horas: int) -> str:
        return {
            24: "Últimas 24h", 48: "Últimas 48h",
            168: "Últimos 7 dias", 720: "Últimos 30 dias",
        }.get(horas, "Últimas 24h")

    def _mudar_periodo(self, escolha: str) -> None:
        self.config_app.periodo_horas = {
            "Últimas 24h": 24, "Últimas 48h": 48,
            "Últimos 7 dias": 168, "Últimos 30 dias": 720,
        }.get(escolha, 24)

    def analisar_tudo(self) -> None:
        """PT-PT: Diagnostico completo. / EN-UK: Full diagnostic."""
        self.mostrar("resumo")
        config = self.config_app

        def trabalho():
            from .. import disks, events, network, services, system

            achados: list[Achado] = []
            for nome, funcao in (
                ("sistema", lambda: system.achados(
                    config.uptime_dias_max, config.ram_percent_max, config.cpu_percent_max
                )),
                ("discos", lambda: disks.achados(config.disco_percent_min, config.disco_gb_min)),
                ("rede", lambda: network.achados(config.host_teste, config.dominio_teste)),
                ("serviços", services.achados),
            ):
                try:
                    achados.extend(funcao())
                except Exception as exc:  # noqa: BLE001
                    log.error("Módulo %s falhou: %s", nome, exc, exc_info=True)
                    achados.append(
                        Achado(
                            modulo=nome.capitalize(),
                            titulo="Verificação não concluída",
                            detalhe=str(exc),
                            gravidade=Gravidade.BAIXA,
                            solucao="Correr com --verbose e consultar o registo.",
                        )
                    )

            analise = None
            try:
                analise = events.analisar_maquina(
                    config.logs_escolhidos, config.periodo_horas,
                    config.incluir_avisos, config.max_eventos,
                )
            except Exception as exc:  # noqa: BLE001
                log.error("Eventos: %s", exc, exc_info=True)

            return achados, analise, system.identificacao(), system.carga(), system.uptime_dias()

        self._trabalhar(trabalho, "resumo", "A analisar a máquina…")

    def _receber_resumo(self, resultado) -> None:
        achados, analise, identificacao, carga, dias = resultado
        self._achados = achados
        self._analise = analise
        if analise is not None:
            self.btn_rel_eventos.configure(state="normal")

        linhas = []
        for chave, valor in identificacao.items():
            linhas.append(f"{chave:<16}{valor}")
        if carga:
            linhas.append(
                f"{'Processador':<16}{carga['cpu']:.0f}%   "
                f"Memória {carga['ram']:.0f}% "
                f"({carga['ram_usada_gb']:.1f}/{carga['ram_total_gb']:.1f} GB)"
            )
        if dias is not None:
            linhas.append(f"{'Ligada há':<16}{dias:.1f} dias")
        linhas.append("")

        if not achados:
            linhas.append("Nenhum problema identificado nas verificações efectuadas.")
        else:
            criticos = sum(1 for a in achados if a.gravidade is Gravidade.CRITICA)
            linhas.append(
                f"{len(achados)} verificação(ões) com problema"
                + (f", {criticos} crítica(s)." if criticos else ".")
            )
            linhas.append("")
            for achado in sorted(achados, key=lambda a: a.gravidade.value):
                linhas.append(f"[{achado.gravidade.etiqueta:>12}]  {achado.titulo}")
                linhas.append(f"{'':>15}{achado.modulo} · {achado.detalhe}")
                if achado.solucao:
                    linhas.append(f"{'':>15}→ {achado.solucao}")
                linhas.append("")

        if analise is not None:
            linhas.append("─" * 68)
            linhas.append(f"Event logs · {analise.veredicto}")
            linhas.append(
                f"{analise.total} evento(s) lido(s) nas últimas {analise.horas}h. "
                "Ver o separador Event Logs para o detalhe."
            )

        self.escrever("resumo", "\n".join(linhas))
        self.escrever("eventos", self._texto_eventos(analise) if analise else "")

    def analisar_eventos(self) -> None:
        """PT-PT: So os event logs. / EN-UK: Event logs only."""
        config = self.config_app

        def trabalho():
            from .. import events

            return events.analisar_maquina(
                config.logs_escolhidos, config.periodo_horas,
                config.incluir_avisos, config.max_eventos,
            )

        self._trabalhar(trabalho, "eventos", "A ler os event logs…")

    def _texto_eventos(self, analise) -> str:
        """PT-PT: Analise em texto para o ecra. / EN-UK: Analysis as screen text."""
        linhas = [
            f"Período: últimas {analise.horas}h · {analise.total} evento(s) lido(s)",
            analise.veredicto,
            "",
        ]
        for aviso in analise.avisos:
            linhas.append(f"⚠  {aviso}")
        if analise.avisos:
            linhas.append("")

        if analise.problemas:
            for grupo in analise.problemas:
                titulo = grupo.regra.titulo if grupo.regra else "Evento sem entrada na base"
                linhas.append(f"[{grupo.gravidade.etiqueta:>12}]  {titulo}")
                marca = " · recorrente" if grupo.recorrente else ""
                linhas.append(
                    f"{'':>15}ID {grupo.event_id} · {grupo.provider} · {grupo.log} · "
                    f"{grupo.contagem}×{marca}"
                )
                if grupo.regra:
                    linhas.append(f"{'':>15}Causa: {grupo.regra.causa}")
                    linhas.append(f"{'':>15}→ {grupo.regra.solucao}")
                if grupo.exemplo:
                    linhas.append(f"{'':>15}« {grupo.exemplo[:220]} »")
                linhas.append("")

        if analise.outros:
            linhas.append("─" * 68)
            linhas.append(f"Outros {len(analise.outros)} tipo(s) de evento registados:")
            for grupo in analise.outros[:25]:
                linhas.append(
                    f"  {grupo.event_id:<7}{grupo.nivel_texto:<9}{grupo.contagem:>4}×  "
                    f"{grupo.provider}"
                )
        return "\n".join(linhas)

    def _receber_eventos(self, analise) -> None:
        self._analise = analise
        self.btn_rel_eventos.configure(state="normal")
        self.escrever("eventos", self._texto_eventos(analise))

    def diagnosticar_rede(self) -> None:
        config = self.config_app

        def trabalho():
            from .. import network

            return network.adaptadores(), network.achados(
                config.host_teste, config.dominio_teste
            )

        self._trabalhar(trabalho, "rede", "A diagnosticar a rede…")

    def _receber_rede(self, resultado) -> None:
        adaptadores, achados = resultado
        linhas = []
        for adaptador in adaptadores:
            linhas.append(str(adaptador.get("InterfaceAlias") or "?"))
            linhas.append(f"  Descrição   {adaptador.get('InterfaceDescription') or '?'}")
            linhas.append(
                f"  IPv4        {adaptador.get('IPv4') or '?'}"
                f"/{adaptador.get('Mascara') or '?'}"
            )
            linhas.append(f"  Gateway     {adaptador.get('Gateway') or '—'}")
            linhas.append(f"  DNS         {adaptador.get('DNS') or '—'}")
            linhas.append("")
        if not adaptadores:
            linhas.append("Nenhum adaptador com endereço IPv4.\n")

        if achados:
            linhas.append("─" * 68)
            for achado in sorted(achados, key=lambda a: a.gravidade.value):
                linhas.append(f"[{achado.gravidade.etiqueta:>12}]  {achado.titulo}")
                linhas.append(f"{'':>15}{achado.detalhe}")
                if achado.solucao:
                    linhas.append(f"{'':>15}→ {achado.solucao}")
                linhas.append("")
        else:
            linhas.append("Nenhum problema de rede identificado.")

        self.escrever("rede", "\n".join(linhas))

    def verificar_discos(self) -> None:
        config = self.config_app

        def trabalho():
            from .. import disks

            return (
                disks.particoes(),
                disks.smart(),
                disks.achados(config.disco_percent_min, config.disco_gb_min),
            )

        self._trabalhar(trabalho, "discos", "A verificar os discos…")

    def _receber_discos(self, resultado) -> None:
        particoes, fisicos, achados = resultado
        linhas = ["PARTIÇÕES", ""]
        for parte in particoes:
            linhas.append(
                f"  {parte.montagem:<8}{parte.sistema:<8}"
                f"{parte.livre_gb:>8.1f} GB livres de {parte.total_gb:>8.1f} GB"
                f"   ({parte.percent_livre:.0f}% livre)"
            )
        if not particoes:
            linhas.append("  Sem dados (o psutil não está instalado?).")

        linhas.extend(["", "DISCOS FÍSICOS", ""])
        for disco in fisicos:
            linhas.append(
                f"  {str(disco.get('FriendlyName') or '?'):<34}"
                f"{str(disco.get('MediaType') or '?'):<10}"
                f"{str(disco.get('TamanhoGB') or '?'):>8} GB   "
                f"{disco.get('HealthStatus') or 'desconhecido'}"
            )
        if not fisicos:
            linhas.append("  Sem dados. Requer Windows e privilégios de administrador.")

        if achados:
            linhas.extend(["", "─" * 68])
            for achado in sorted(achados, key=lambda a: a.gravidade.value):
                linhas.append(f"[{achado.gravidade.etiqueta:>12}]  {achado.titulo}")
                linhas.append(f"{'':>15}{achado.detalhe}")
                if achado.solucao:
                    linhas.append(f"{'':>15}→ {achado.solucao}")

        self.escrever("discos", "\n".join(linhas))

    def maiores_pastas(self) -> None:
        def trabalho():
            from .. import disks

            raiz = "C:\\" if self.ambiente.windows else "/"
            return disks.pastas_maiores(raiz)

        self._trabalhar(trabalho, "discos", "A medir as pastas — pode demorar…")

    def _receber_servicos(self, lista) -> None:
        if not lista:
            self.escrever("servicos", "Nenhum serviço automático parado.")
            return
        linhas = [f"{len(lista)} serviço(s) automático(s) parado(s):", ""]
        for servico in lista:
            linhas.append(
                f"  {str(servico.get('Name') or '?'):<28}"
                f"{str(servico.get('DisplayName') or '')}"
            )
        linhas.extend(["", "Escreva o nome (coluna da esquerda) e carregue em Arrancar."])
        self.escrever("servicos", "\n".join(linhas))

    def listar_servicos(self) -> None:
        def trabalho():
            from .. import services

            return services.parados()

        self._trabalhar(trabalho, "servicos", "A ler os serviços…")

    def arrancar_servico(self) -> None:
        nome = self.entrada_servico.get().strip()
        if not nome:
            messagebox.showinfo(__app_name__, "Escreva o nome do serviço primeiro.")
            return
        if not messagebox.askyesno(__app_name__, f"Arrancar o serviço «{nome}»?"):
            return

        def trabalho():
            from .. import services

            resultado = services.arrancar(nome)
            return [{"Name": nome, "DisplayName": resultado.texto}]

        self._trabalhar(trabalho, "servicos", f"A arrancar {nome}…")

    def executar_ferramenta(self, accao) -> None:
        """PT-PT: Corre uma ferramenta rapida. / EN-UK: Runs a quick tool."""
        if accao.confirmar and not messagebox.askyesno(
            __app_name__, f"{accao.etiqueta}\n\n{accao.descricao}\n\nContinuar?"
        ):
            return
        self.mostrar("ferramentas")
        self.accao_rapida(accao.chave, "ferramentas")

    def accao_rapida(self, chave: str, destino: str) -> None:
        def trabalho():
            from ..actions import executar_accao

            return executar_accao(chave).texto

        self._trabalhar(trabalho, destino, "A executar…")

    def _receber_ferramentas(self, texto) -> None:
        self.escrever("ferramentas", str(texto))

    def abrir_consola(self, ficheiro: str) -> None:
        from ..actions import abrir_consola_mmc

        resultado = abrir_consola_mmc(ficheiro)
        self.escrever("ferramentas", resultado.texto)

    def recolher_inventario(self) -> None:
        def trabalho():
            from .. import inventory

            return (
                inventory.hardware(),
                inventory.sistema(),
                inventory.software(),
                inventory.actualizacoes(),
            )

        self._trabalhar(trabalho, "inventario", "A recolher o inventário…")

    def _receber_inventario(self, resultado) -> None:
        self._inventario = resultado
        self.btn_rel_inv.configure(state="normal")
        hardware, sistema, software, actualizacoes = resultado

        linhas = ["HARDWARE", ""]
        linhas.extend(f"  {k:<24}{v}" for k, v in hardware.items())
        linhas.extend(["", "SISTEMA OPERATIVO", ""])
        linhas.extend(f"  {k:<24}{v}" for k, v in sistema.items())

        if actualizacoes:
            linhas.extend(["", "ÚLTIMAS ACTUALIZAÇÕES", ""])
            for item in actualizacoes:
                linhas.append(
                    f"  {str(item.get('HotFixID') or '?'):<14}"
                    f"{str(item.get('Quando') or ''):<12}"
                    f"{item.get('Description') or ''}"
                )

        linhas.extend(["", f"SOFTWARE INSTALADO ({len(software)})", ""])
        for item in software:
            linhas.append(
                f"  {str(item.get('DisplayName') or '')[:52]:<54}"
                f"{str(item.get('DisplayVersion') or '')}"
            )
        if not hardware and not software:
            linhas.append("  Sem dados. Este módulo requer Windows.")

        self.escrever("inventario", "\n".join(linhas))

    # ------------------------------------------------------------------
    # PT-PT: Relatorios / EN-UK: Reports
    # ------------------------------------------------------------------

    def _gravar_relatorio(self, html: str, prefixo: str) -> None:
        """PT-PT: Grava e opcionalmente abre. / EN-UK: Saves and optionally opens."""
        from ..reports import gravar

        try:
            destino = gravar(html, self.config_app.reports_dir, prefixo)
        except OSError as exc:
            messagebox.showerror(
                __app_name__,
                f"Não foi possível gravar o relatório:\n{exc}\n\n"
                "Verifique a pasta configurada nas Definições.",
            )
            return

        self.estado(f"Relatório gravado: {destino.name}")
        self.listar_relatorios()
        if self.config_app.abrir_relatorio_apos_gerar:
            webbrowser.open(destino.as_uri())

    def relatorio_eventos(self) -> None:
        if self._analise is None:
            messagebox.showinfo(__app_name__, "Analise os eventos primeiro.")
            return
        from .. import system
        from ..reports import relatorio_eventos

        self._gravar_relatorio(
            relatorio_eventos(self._analise, system.identificacao()), "eventos"
        )

    def relatorio_saude(self) -> None:
        if not self._achados and self._analise is None:
            messagebox.showinfo(__app_name__, "Carregue em «Analisar tudo» primeiro.")
            return
        from .. import system
        from ..reports import relatorio_saude

        self._gravar_relatorio(
            relatorio_saude(self._achados, system.identificacao(), self._analise), "saude"
        )

    def relatorio_inventario(self) -> None:
        dados = getattr(self, "_inventario", None)
        if not dados:
            messagebox.showinfo(__app_name__, "Recolha o inventário primeiro.")
            return
        from .. import system
        from ..reports import relatorio_inventario

        hardware, sistema, software, actualizacoes = dados
        self._gravar_relatorio(
            relatorio_inventario(
                hardware, sistema, software, actualizacoes, system.identificacao()
            ),
            "inventario",
        )

    def listar_relatorios(self) -> None:
        from ..reports import listar_relatorios

        ficheiros = listar_relatorios(self.config_app.reports_dir)
        if not ficheiros:
            self.escrever(
                "relatorios",
                f"Sem relatórios em:\n{self.config_app.reports_dir}\n\n"
                "Gere um a partir de qualquer módulo.",
            )
            return

        import datetime as dt

        linhas = [f"Pasta: {self.config_app.reports_dir}", ""]
        for ficheiro in ficheiros[:40]:
            quando = dt.datetime.fromtimestamp(ficheiro.stat().st_mtime)
            linhas.append(
                f"  {quando.strftime('%Y-%m-%d %H:%M')}   "
                f"{ficheiro.stat().st_size / 1024:>7.0f} KB   {ficheiro.name}"
            )
        linhas.extend(["", "Abrir pasta para consultar. Contêm dados desta máquina."])
        self.escrever("relatorios", "\n".join(linhas))

    def abrir_pasta_relatorios(self) -> None:
        from ..actions import abrir_pasta

        self.config_app.ensure_directories()
        resultado = abrir_pasta(self.config_app.reports_dir)
        if not resultado.ok:
            messagebox.showerror(__app_name__, resultado.erro)

    # ------------------------------------------------------------------
    # PT-PT: Janelas auxiliares / EN-UK: Auxiliary windows
    # ------------------------------------------------------------------

    def abrir_definicoes(self) -> None:
        JanelaDefinicoes(self, self.config_app, ao_gravar=self._aplicar_definicoes)

    def _aplicar_definicoes(self) -> None:
        ctk.set_appearance_mode(self.config_app.tema)
        self.config_app.ensure_directories()
        self.config_app.save()
        self.cb_periodo.set(self._etiqueta_periodo(self.config_app.periodo_horas))
        self.estado("Definições gravadas.")

    def abrir_teste_rede(self) -> None:
        JanelaTesteRede(self, self.config_app)


def correr(config: AppConfig) -> None:
    """
    PT-PT: Abre a janela e entra no ciclo de eventos.
    EN-UK: Opens the window and enters the event loop.
    """
    app = ITToolkitApp(config)
    app.mainloop()
