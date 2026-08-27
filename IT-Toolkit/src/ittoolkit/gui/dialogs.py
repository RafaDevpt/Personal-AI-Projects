# -*- coding: utf-8 -*-
"""
PT-PT: Janelas auxiliares — definicoes e testes de rede pontuais.

EN-UK: Auxiliary windows — settings and one-off network tests.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
import queue
import threading
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any, Callable

import customtkinter as ctk

from .. import __app_name__
from ..config import AppConfig
from . import theme

log = logging.getLogger(__name__)


class _JanelaBase(ctk.CTkToplevel):
    """
    PT-PT: Base comum das janelas auxiliares.

           O `grab_set` esta dentro de um `after` de 200 ms de proposito. Em
           Windows, chamado imediatamente a seguir ao construtor, o CustomTkinter
           ainda nao terminou de desenhar a janela e o pedido de foco falha em
           silencio — a janela abre atras da principal e o utilizador conclui
           que o botao nao fez nada.

    EN-UK: Common base for the auxiliary windows. The `grab_set` sits inside a
           200 ms `after` deliberately: on Windows, called straight after the
           constructor, CustomTkinter has not finished drawing and the focus
           request fails silently — the window opens behind the main one and the
           user concludes the button did nothing.
    """

    def __init__(self, pai: ctk.CTk, titulo: str, largura: int, altura: int) -> None:
        super().__init__(pai)
        self.pai = pai
        self.title(titulo)
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=theme.SURFACE)
        self.transient(pai)
        self.after(200, self._focar)

    def _focar(self) -> None:
        try:
            self.grab_set()
            self.lift()
            self.focus_force()
        except Exception as exc:  # noqa: BLE001
            log.debug("Não foi possível fixar o foco: %s", exc)


class JanelaDefinicoes(_JanelaBase):
    """
    PT-PT: Definicoes da aplicacao.
    EN-UK: Application settings.
    """

    def __init__(
        self, pai: ctk.CTk, config: AppConfig, ao_gravar: Callable[[], None]
    ) -> None:
        super().__init__(pai, f"{__app_name__} — Definições", 560, 620)
        self.config_app = config
        self.ao_gravar = ao_gravar
        self._construir()

    def _construir(self) -> None:
        corpo = ctk.CTkScrollableFrame(self, fg_color="transparent")
        corpo.pack(fill="both", expand=True, padx=theme.PAD_L, pady=theme.PAD_M)

        # --- Relatórios ---------------------------------------------------
        self._seccao(corpo, "Relatórios")
        linha = ctk.CTkFrame(corpo, fg_color="transparent")
        linha.pack(fill="x", pady=(0, theme.PAD_S))
        self.entrada_pasta = ctk.CTkEntry(linha, width=380)
        self.entrada_pasta.insert(0, str(self.config_app.reports_dir))
        self.entrada_pasta.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(
            linha, text="…", width=36, command=self._escolher_pasta,
            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
        ).pack(side="left", padx=(theme.PAD_XS, 0))

        self.var_abrir = ctk.BooleanVar(value=self.config_app.abrir_relatorio_apos_gerar)
        ctk.CTkCheckBox(
            corpo, text="Abrir o relatório no navegador depois de gerar",
            variable=self.var_abrir,
        ).pack(anchor="w", pady=theme.PAD_XS)

        # --- Event logs ---------------------------------------------------
        self._seccao(corpo, "Event logs")
        self.var_system = ctk.BooleanVar(value=self.config_app.incluir_system)
        self.var_app = ctk.BooleanVar(value=self.config_app.incluir_application)
        self.var_sec = ctk.BooleanVar(value=self.config_app.incluir_security)
        self.var_avisos = ctk.BooleanVar(value=self.config_app.incluir_avisos)

        ctk.CTkCheckBox(corpo, text="Log System", variable=self.var_system).pack(
            anchor="w", pady=theme.PAD_XS
        )
        ctk.CTkCheckBox(corpo, text="Log Application", variable=self.var_app).pack(
            anchor="w", pady=theme.PAD_XS
        )
        ctk.CTkCheckBox(
            corpo, text="Log Security (requer administrador)", variable=self.var_sec
        ).pack(anchor="w", pady=theme.PAD_XS)
        ctk.CTkCheckBox(corpo, text="Incluir avisos além dos erros", variable=self.var_avisos).pack(
            anchor="w", pady=theme.PAD_XS
        )

        self.max_eventos = self._campo_numero(
            corpo, "Máximo de eventos por log", self.config_app.max_eventos
        )

        # --- Limites ------------------------------------------------------
        self._seccao(corpo, "Limites de alerta")
        self.disco_percent = self._campo_numero(
            corpo, "Disco: alertar abaixo de (% livre)", self.config_app.disco_percent_min
        )
        self.disco_gb = self._campo_numero(
            corpo, "Disco: e também abaixo de (GB livres)", self.config_app.disco_gb_min
        )
        ctk.CTkLabel(
            corpo,
            text=(
                "As duas condições têm de se verificar em simultâneo. É o que evita "
                "alertar sobre 10% livres num disco de 4 TB e calar-se sobre 12 GB "
                "livres num SSD de sistema."
            ),
            font=ctk.CTkFont(size=theme.SIZE_SMALL),
            text_color=theme.TEXT_MUTED,
            wraplength=460,
            justify="left",
        ).pack(anchor="w", pady=(0, theme.PAD_S))

        self.uptime = self._campo_numero(
            corpo, "Sugerir reinício acima de (dias)", self.config_app.uptime_dias_max
        )
        self.ram = self._campo_numero(
            corpo, "Memória: alertar acima de (%)", self.config_app.ram_percent_max
        )

        # --- Rede ---------------------------------------------------------
        self._seccao(corpo, "Testes de rede")
        self.host = self._campo_texto(corpo, "Endereço de teste", self.config_app.host_teste)
        self.dominio = self._campo_texto(
            corpo, "Nome de teste (DNS)", self.config_app.dominio_teste
        )

        # --- Interface ----------------------------------------------------
        self._seccao(corpo, "Interface")
        self.tema = ctk.CTkComboBox(
            corpo, values=["system", "light", "dark"], state="readonly", width=180
        )
        self.tema.set(self.config_app.tema)
        self.tema.pack(anchor="w", pady=theme.PAD_XS)

        self.var_arranque = ctk.BooleanVar(value=self.config_app.analisar_ao_arrancar)
        ctk.CTkCheckBox(
            corpo, text="Analisar a máquina ao abrir a aplicação", variable=self.var_arranque
        ).pack(anchor="w", pady=theme.PAD_XS)

        # --- Botões -------------------------------------------------------
        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=theme.PAD_L, pady=(0, theme.PAD_M))
        ctk.CTkButton(
            rodape, text="Gravar", command=self._gravar,
            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
        ).pack(side="right")
        ctk.CTkButton(
            rodape, text="Cancelar", command=self.destroy,
            fg_color="transparent", text_color=theme.TEXT_PRIMARY,
            border_width=1, border_color=theme.BORDER, hover_color=theme.BORDER,
        ).pack(side="right", padx=(0, theme.PAD_S))

    def _seccao(self, pai: ctk.CTkFrame, texto: str) -> None:
        ctk.CTkLabel(
            pai, text=texto.upper(),
            font=ctk.CTkFont(size=theme.SIZE_SMALL, weight="bold"),
            text_color=theme.TEXT_MUTED,
        ).pack(anchor="w", pady=(theme.PAD_M, theme.PAD_XS))

    def _campo_texto(self, pai: ctk.CTkFrame, etiqueta: str, valor: str) -> ctk.CTkEntry:
        ctk.CTkLabel(pai, text=etiqueta, font=ctk.CTkFont(size=theme.SIZE_BODY)).pack(
            anchor="w", pady=(theme.PAD_XS, 0)
        )
        entrada = ctk.CTkEntry(pai, width=240)
        entrada.insert(0, str(valor))
        entrada.pack(anchor="w", pady=(0, theme.PAD_XS))
        return entrada

    def _campo_numero(self, pai: ctk.CTkFrame, etiqueta: str, valor: int) -> ctk.CTkEntry:
        return self._campo_texto(pai, etiqueta, str(valor))

    def _escolher_pasta(self) -> None:
        escolhida = filedialog.askdirectory(
            title="Pasta para os relatórios", initialdir=str(self.config_app.reports_dir)
        )
        if escolhida:
            self.entrada_pasta.delete(0, "end")
            self.entrada_pasta.insert(0, escolhida)

    def _inteiro(self, entrada: ctk.CTkEntry, actual: int, nome: str) -> int:
        """
        PT-PT: Le um inteiro de um campo, mantendo o valor actual se for invalido.

               Avisar e manter o valor anterior e melhor do que aceitar em
               silencio: a v1.0 convertia com um `int()` sem protecao e um campo
               vazio fechava a janela de definicoes com um ValueError, perdendo
               tudo o que tinha sido escrito nos outros campos.

        EN-UK: Reads an integer from a field, keeping the current value when
               invalid. v1.0 converted with a bare `int()` and an empty field
               closed the settings window with a ValueError, losing everything
               typed in the other fields.
        """
        texto = entrada.get().strip()
        try:
            return int(texto)
        except ValueError:
            messagebox.showwarning(
                __app_name__,
                f"«{nome}» tem de ser um número inteiro. Ficou {actual}.",
                parent=self,
            )
            return actual

    def _gravar(self) -> None:
        config = self.config_app
        config.reports_dir = Path(self.entrada_pasta.get().strip() or config.reports_dir)
        config.abrir_relatorio_apos_gerar = bool(self.var_abrir.get())

        config.incluir_system = bool(self.var_system.get())
        config.incluir_application = bool(self.var_app.get())
        config.incluir_security = bool(self.var_sec.get())
        config.incluir_avisos = bool(self.var_avisos.get())

        if not config.logs_escolhidos:
            # PT-PT: Sem nenhum log seleccionado a analise nao teria o que ler e
            #        devolveria «sem problemas», que e a conclusao errada.
            # EN-UK: With no log selected the analysis would have nothing to read
            #        and would return "no problems", which is the wrong answer.
            messagebox.showwarning(
                __app_name__,
                "Escolha pelo menos um log para analisar. O System foi reactivado.",
                parent=self,
            )
            config.incluir_system = True

        config.max_eventos = self._inteiro(
            self.max_eventos, config.max_eventos, "Máximo de eventos"
        )
        config.disco_percent_min = self._inteiro(
            self.disco_percent, config.disco_percent_min, "Disco (%)"
        )
        config.disco_gb_min = self._inteiro(self.disco_gb, config.disco_gb_min, "Disco (GB)")
        config.uptime_dias_max = self._inteiro(self.uptime, config.uptime_dias_max, "Dias")
        config.ram_percent_max = self._inteiro(self.ram, config.ram_percent_max, "Memória (%)")

        config.host_teste = self.host.get().strip() or config.host_teste
        config.dominio_teste = self.dominio.get().strip() or config.dominio_teste
        config.tema = self.tema.get()
        config.analisar_ao_arrancar = bool(self.var_arranque.get())

        # PT-PT: Volta a passar pela validacao do dataclass, que limita os
        #        valores aos intervalos admissiveis.
        # EN-UK: Runs the dataclass validation again, clamping to valid ranges.
        config.__post_init__()

        self.ao_gravar()
        self.destroy()


class JanelaTesteRede(_JanelaBase):
    """
    PT-PT: Testes de rede pontuais: ping, tracert e porta TCP.
    EN-UK: One-off network tests: ping, traceroute and TCP port.
    """

    def __init__(self, pai: ctk.CTk, config: AppConfig) -> None:
        super().__init__(pai, f"{__app_name__} — Testes de rede", 640, 520)
        self.config_app = config
        self._fila: queue.Queue[str] = queue.Queue()
        self._construir()
        self.after(120, self._pump)

    def _construir(self) -> None:
        topo = ctk.CTkFrame(self, fg_color="transparent")
        topo.pack(fill="x", padx=theme.PAD_L, pady=(theme.PAD_M, theme.PAD_S))

        ctk.CTkLabel(topo, text="Destino:").pack(side="left", padx=(0, theme.PAD_XS))
        self.destino = ctk.CTkEntry(topo, width=220, placeholder_text="IP ou nome")
        self.destino.insert(0, self.config_app.host_teste)
        self.destino.pack(side="left", padx=(0, theme.PAD_M))

        ctk.CTkLabel(topo, text="Porta:").pack(side="left", padx=(0, theme.PAD_XS))
        self.porta = ctk.CTkEntry(topo, width=70, placeholder_text="443")
        self.porta.pack(side="left")

        botoes = ctk.CTkFrame(self, fg_color="transparent")
        botoes.pack(fill="x", padx=theme.PAD_L, pady=(0, theme.PAD_S))
        for texto, comando in (
            ("Ping", self._ping),
            ("Tracert", self._tracert),
            ("Testar porta", self._porta),
            ("Resolver nome", self._resolver),
        ):
            ctk.CTkButton(
                botoes, text=texto, width=120, command=comando,
                fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
            ).pack(side="left", padx=(0, theme.PAD_S))

        familia = theme.resolve_font(theme.FONT_MONO, theme.FONT_MONO_FALLBACKS)
        self.saida = ctk.CTkTextbox(
            self,
            font=ctk.CTkFont(family=familia, size=theme.SIZE_SMALL),
            fg_color=theme.SURFACE_RAISED,
            border_width=1,
            border_color=theme.BORDER,
            wrap="none",
        )
        self.saida.pack(fill="both", expand=True, padx=theme.PAD_L, pady=(0, theme.PAD_M))
        self.saida.insert("end", "Escreva um destino e escolha um teste.\n")
        self.saida.configure(state="disabled")

    def _escrever(self, texto: str) -> None:
        self.saida.configure(state="normal")
        self.saida.delete("1.0", "end")
        self.saida.insert("end", texto)
        self.saida.configure(state="disabled")

    def _pump(self) -> None:
        """PT-PT: Le a fila no fio principal. / EN-UK: Reads the queue on the main thread."""
        try:
            while True:
                self._escrever(self._fila.get_nowait())
        except queue.Empty:
            pass
        try:
            self.after(120, self._pump)
        except Exception:  # noqa: BLE001 — a janela pode já ter sido fechada
            pass

    def _correr(self, funcao: Callable[[str], Any]) -> None:
        destino = self.destino.get().strip()
        if not destino:
            messagebox.showinfo(__app_name__, "Escreva um destino primeiro.", parent=self)
            return
        self._escrever("A correr…\n")

        def alvo() -> None:
            try:
                self._fila.put(str(funcao(destino)))
            except Exception as exc:  # noqa: BLE001
                self._fila.put(f"Falhou: {exc}\n")

        threading.Thread(target=alvo, daemon=True).start()

    def _ping(self) -> None:
        from ..network import ping

        self._correr(lambda d: ping(d, timeout=self.config_app.timeout_ping).texto)

    def _tracert(self) -> None:
        from ..network import tracert

        self._correr(lambda d: tracert(d).texto)

    def _resolver(self) -> None:
        from ..network import resolver

        def trabalho(destino: str) -> str:
            enderecos = resolver(destino)
            if not enderecos:
                return f"Não foi possível resolver {destino}.\n"
            return f"{destino} resolve para:\n" + "\n".join(f"  {e}" for e in enderecos)

        self._correr(trabalho)

    def _porta(self) -> None:
        from ..network import testar_porta

        texto = self.porta.get().strip()
        try:
            numero = int(texto)
            if not 1 <= numero <= 65535:
                raise ValueError
        except ValueError:
            messagebox.showinfo(
                __app_name__, "A porta tem de ser um número entre 1 e 65535.", parent=self
            )
            return

        def trabalho(destino: str) -> str:
            aberta = testar_porta(destino, numero, self.config_app.timeout_porta)
            estado = "aceita ligações" if aberta else "não responde"
            nota = (
                ""
                if aberta
                else (
                    "\n\nUma porta fechada pode ser a firewall, o serviço parado ou "
                    "a máquina inacessível. Um ping confirma qual dos três."
                )
            )
            return f"{destino}:{numero} — {estado}.{nota}\n"

        self._correr(trabalho)
