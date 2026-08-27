# -*- coding: utf-8 -*-
"""
PT-PT: Janelas auxiliares — definicoes e pesos dos criterios.

EN-UK: Auxiliary windows — settings and criterion weights.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Callable

import customtkinter as ctk

from .. import __app_name__
from ..config import AppConfig
from . import theme

log = logging.getLogger(__name__)


class _JanelaBase(ctk.CTkToplevel):
    """
    PT-PT: Base comum das janelas auxiliares. O `grab_set` esta num `after` de
           200 ms porque, chamado logo a seguir ao construtor, em Windows o
           CustomTkinter ainda nao terminou de desenhar e o pedido de foco falha
           em silencio.
    EN-UK: Common base for the auxiliary windows.
    """

    def __init__(self, pai, titulo: str, largura: int, altura: int) -> None:
        super().__init__(pai)
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

    def _seccao(self, pai, texto: str) -> None:
        ctk.CTkLabel(
            pai, text=texto.upper(),
            font=ctk.CTkFont(size=theme.SIZE_SMALL, weight="bold"),
            text_color=theme.TEXT_MUTED,
        ).pack(anchor="w", pady=(theme.PAD_M, theme.PAD_XS))

    def _campo(self, pai, etiqueta: str, valor, largura: int = 240) -> ctk.CTkEntry:
        ctk.CTkLabel(pai, text=etiqueta, font=ctk.CTkFont(size=theme.SIZE_BODY)).pack(
            anchor="w", pady=(theme.PAD_XS, 0)
        )
        entrada = ctk.CTkEntry(pai, width=largura)
        entrada.insert(0, str(valor))
        entrada.pack(anchor="w", pady=(0, theme.PAD_XS))
        return entrada

    def _numero(self, entrada: ctk.CTkEntry, actual: float, nome: str, inteiro: bool = False):
        """
        PT-PT: Le um numero de um campo, mantendo o valor actual se for invalido.

               Avisar e manter o anterior e melhor do que aceitar em silencio:
               um `float()` sem proteccao fecha a janela com um ValueError e
               perde tudo o que foi escrito nos outros campos.

        EN-UK: Reads a number from a field, keeping the current value when
               invalid. A bare `float()` closes the window with a ValueError and
               loses everything typed in the other fields.
        """
        texto = entrada.get().strip().replace(",", ".")
        try:
            return int(float(texto)) if inteiro else float(texto)
        except ValueError:
            messagebox.showwarning(
                __app_name__,
                f"«{nome}» tem de ser um número. Ficou {actual:g}.",
                parent=self,
            )
            return actual


class JanelaDefinicoes(_JanelaBase):
    """PT-PT: Definicoes da aplicacao. / EN-UK: Application settings."""

    def __init__(self, pai, config: AppConfig, ao_gravar: Callable[[], None]) -> None:
        super().__init__(pai, f"{__app_name__} — Definições", 580, 660)
        self.config_app = config
        self.ao_gravar = ao_gravar
        self._construir()

    def _construir(self) -> None:
        corpo = ctk.CTkScrollableFrame(self, fg_color="transparent")
        corpo.pack(fill="both", expand=True, padx=theme.PAD_L, pady=theme.PAD_M)

        # --- Saída --------------------------------------------------------
        self._seccao(corpo, "Pasta de saída")
        linha = ctk.CTkFrame(corpo, fg_color="transparent")
        linha.pack(fill="x", pady=(0, theme.PAD_S))
        self.entrada_pasta = ctk.CTkEntry(linha, width=400)
        self.entrada_pasta.insert(0, str(self.config_app.output_dir))
        self.entrada_pasta.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(
            linha, text="…", width=36, command=self._escolher_pasta,
            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
        ).pack(side="left", padx=(theme.PAD_XS, 0))

        self.var_abrir = ctk.BooleanVar(value=self.config_app.abrir_apos_gerar)
        ctk.CTkCheckBox(
            corpo, text="Abrir o ficheiro gerado no fim", variable=self.var_abrir
        ).pack(anchor="w", pady=theme.PAD_XS)

        # --- Formulários --------------------------------------------------
        self._seccao(corpo, "Detecção de campos")
        self.var_dois_pontos = ctk.BooleanVar(value=self.config_app.detectar_dois_pontos)
        ctk.CTkCheckBox(
            corpo,
            text="Detectar campos por etiquetas com dois pontos",
            variable=self.var_dois_pontos,
        ).pack(anchor="w", pady=theme.PAD_XS)
        ctk.CTkLabel(
            corpo,
            text=(
                "Apanha os formulários de Word que não desenham linha nenhuma, "
                "mas num documento em prosa gera campos a mais. Desligue se "
                "estiver a converter algo que não seja um formulário."
            ),
            font=ctk.CTkFont(size=theme.SIZE_SMALL),
            text_color=theme.TEXT_MUTED, wraplength=470, justify="left",
        ).pack(anchor="w", pady=(0, theme.PAD_S))

        self.confianca = self._campo(
            corpo, "Confiança mínima para marcar automaticamente (0 a 1)",
            self.config_app.confianca_minima, largura=110,
        )

        self.var_substituir = ctk.BooleanVar(
            value=self.config_app.substituir_campos_existentes
        )
        ctk.CTkCheckBox(
            corpo,
            text="Substituir campos que o PDF já tenha, em vez de acrescentar",
            variable=self.var_substituir,
        ).pack(anchor="w", pady=theme.PAD_XS)

        # --- Comparação ---------------------------------------------------
        self._seccao(corpo, "Comparação de propostas")
        self.iva = self._campo(
            corpo, "Taxa de IVA quando o documento não a declara (%)",
            f"{self.config_app.taxa_iva:g}", largura=110,
        )
        self.penalizacao = self._campo(
            corpo, "Penalizar dados em falta (0 = não, 1 = totalmente)",
            f"{self.config_app.penalizar_em_falta:g}", largura=110,
        )
        ctk.CTkLabel(
            corpo,
            text=(
                "Em 0, uma proposta que só declara os critérios onde é forte é "
                "comparada apenas nesses — e pode ganhar a outra que declarou "
                "tudo e perdeu num deles. Em 1, a pontuação desce na proporção "
                "do que ficou por declarar."
            ),
            font=ctk.CTkFont(size=theme.SIZE_SMALL),
            text_color=theme.TEXT_MUTED, wraplength=470, justify="left",
        ).pack(anchor="w", pady=(0, theme.PAD_S))

        self.frases = self._campo(
            corpo, "Frases por resumo", self.config_app.frases_resumo, largura=110
        )

        # --- Análise assistida --------------------------------------------
        self._seccao(corpo, "Análise assistida (opcional)")
        self.var_ia = ctk.BooleanVar(value=self.config_app.usar_ia)
        ctk.CTkCheckBox(
            corpo, text="Permitir análise assistida por modelo", variable=self.var_ia
        ).pack(anchor="w", pady=theme.PAD_XS)
        ctk.CTkLabel(
            corpo,
            text=(
                "Envia o texto dos documentos para a API da Anthropic. A "
                "aplicação avisa e pede confirmação antes de cada envio. A "
                "chave é lida da variável ANTHROPIC_API_KEY e nunca é gravada "
                "em disco. Tudo o resto funciona sem isto."
            ),
            font=ctk.CTkFont(size=theme.SIZE_SMALL),
            text_color=theme.TEXT_MUTED, wraplength=470, justify="left",
        ).pack(anchor="w", pady=(0, theme.PAD_S))

        # --- Interface ----------------------------------------------------
        self._seccao(corpo, "Interface")
        self.tema = ctk.CTkComboBox(
            corpo, values=["system", "light", "dark"], state="readonly", width=180
        )
        self.tema.set(self.config_app.tema)
        self.tema.pack(anchor="w", pady=theme.PAD_XS)

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

    def _escolher_pasta(self) -> None:
        escolhida = filedialog.askdirectory(
            title="Pasta de saída", initialdir=str(self.config_app.output_dir)
        )
        if escolhida:
            self.entrada_pasta.delete(0, "end")
            self.entrada_pasta.insert(0, escolhida)

    def _gravar(self) -> None:
        config = self.config_app
        config.output_dir = Path(self.entrada_pasta.get().strip() or config.output_dir)
        config.abrir_apos_gerar = bool(self.var_abrir.get())
        config.detectar_dois_pontos = bool(self.var_dois_pontos.get())
        config.substituir_campos_existentes = bool(self.var_substituir.get())
        config.usar_ia = bool(self.var_ia.get())
        config.tema = self.tema.get()

        config.confianca_minima = self._numero(
            self.confianca, config.confianca_minima, "Confiança mínima"
        )
        config.taxa_iva = self._numero(self.iva, config.taxa_iva, "Taxa de IVA")
        config.penalizar_em_falta = self._numero(
            self.penalizacao, config.penalizar_em_falta, "Penalização"
        )
        config.frases_resumo = self._numero(
            self.frases, config.frases_resumo, "Frases por resumo", inteiro=True
        )

        # PT-PT: Volta a passar pela validacao do dataclass, que limita tudo aos
        #        intervalos admissiveis.
        # EN-UK: Runs the dataclass validation again, clamping to valid ranges.
        config.__post_init__()

        self.ao_gravar()
        self.destroy()


class JanelaPesos(_JanelaBase):
    """
    PT-PT: Pesos dos criterios da comparacao.

           Os pesos sao apresentados com uma barra deslizante e o valor ao lado,
           e a soma aparece em baixo. A soma nao tem de dar 100 — a pontuacao e
           uma media pesada e normaliza sozinha — mas ve-la ajuda a perceber o
           peso relativo de cada criterio, que e o que importa decidir.

    EN-UK: The comparison's criterion weights. Shown as sliders with the value
           beside them and the sum below. The sum need not be 100 — the score is
           a weighted mean and normalises itself — but seeing it helps.
    """

    def __init__(self, pai, config: AppConfig, ao_gravar: Callable[[], None]) -> None:
        super().__init__(pai, f"{__app_name__} — Pesos dos critérios", 560, 480)
        self.config_app = config
        self.ao_gravar = ao_gravar
        self.controlos: dict[str, tuple] = {}
        self._construir()

    def _construir(self) -> None:
        corpo = ctk.CTkFrame(self, fg_color="transparent")
        corpo.pack(fill="both", expand=True, padx=theme.PAD_L, pady=theme.PAD_M)

        ctk.CTkLabel(
            corpo,
            text=(
                "Ajuste os pesos ao que está a comprar. Numa compra urgente, o "
                "prazo de entrega vale mais do que a garantia; numa "
                "infraestrutura que fica cinco anos no sítio, é ao contrário."
            ),
            font=ctk.CTkFont(size=theme.SIZE_SMALL),
            text_color=theme.TEXT_MUTED, wraplength=500, justify="left",
        ).pack(anchor="w", pady=(0, theme.PAD_M))

        for criterio in self.config_app.criterios():
            linha = ctk.CTkFrame(corpo, fg_color="transparent")
            linha.pack(fill="x", pady=theme.PAD_XS)

            ctk.CTkLabel(
                linha, text=criterio.etiqueta, width=150, anchor="w",
                font=ctk.CTkFont(size=theme.SIZE_BODY),
            ).pack(side="left")

            valor = ctk.CTkLabel(linha, text=f"{criterio.peso:g}", width=40, anchor="e")

            deslizante = ctk.CTkSlider(
                linha, from_=0, to=60, number_of_steps=60, width=250,
                button_color=theme.ACCENT, progress_color=theme.ACCENT,
                command=lambda v, c=criterio.chave: self._mudou(c, v),
            )
            deslizante.set(criterio.peso)
            deslizante.pack(side="left", padx=theme.PAD_S)
            valor.pack(side="left")

            direccao = "mais é melhor" if criterio.maior_melhor else "menos é melhor"
            ctk.CTkLabel(
                linha, text=direccao, font=ctk.CTkFont(size=theme.SIZE_SMALL),
                text_color=theme.TEXT_MUTED, anchor="w",
            ).pack(side="left", padx=(theme.PAD_S, 0))

            self.controlos[criterio.chave] = (deslizante, valor)

        self.lbl_soma = ctk.CTkLabel(
            corpo, text="", font=ctk.CTkFont(size=theme.SIZE_SMALL),
            text_color=theme.TEXT_MUTED,
        )
        self.lbl_soma.pack(anchor="w", pady=(theme.PAD_M, 0))
        self._actualizar_soma()

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=theme.PAD_L, pady=(0, theme.PAD_M))
        ctk.CTkButton(
            rodape, text="Aplicar", command=self._gravar,
            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
        ).pack(side="right")
        ctk.CTkButton(
            rodape, text="Repor omissões", command=self._repor,
            fg_color="transparent", text_color=theme.TEXT_PRIMARY,
            border_width=1, border_color=theme.BORDER, hover_color=theme.BORDER,
        ).pack(side="right", padx=(0, theme.PAD_S))

    def _mudou(self, chave: str, valor: float) -> None:
        self.controlos[chave][1].configure(text=f"{valor:.0f}")
        self._actualizar_soma()

    def _actualizar_soma(self) -> None:
        soma = sum(d.get() for d, _ in self.controlos.values())
        if soma <= 0:
            self.lbl_soma.configure(
                text="Todos os pesos a zero — nenhum critério seria usado."
            )
            return
        self.lbl_soma.configure(
            text=(
                f"Soma: {soma:.0f}. Não tem de dar 100 — o que conta é o peso de "
                "cada critério em relação aos outros."
            )
        )

    def _repor(self) -> None:
        from ..scoring import CRITERIOS_OMISSAO

        for criterio in CRITERIOS_OMISSAO:
            deslizante, etiqueta = self.controlos[criterio.chave]
            deslizante.set(criterio.peso)
            etiqueta.configure(text=f"{criterio.peso:g}")
        self._actualizar_soma()

    def _gravar(self) -> None:
        pesos = {chave: float(d.get()) for chave, (d, _) in self.controlos.items()}
        if sum(pesos.values()) <= 0:
            messagebox.showwarning(
                __app_name__,
                "Pelo menos um critério tem de ter peso maior do que zero.",
                parent=self,
            )
            return
        self.config_app.pesos = pesos
        self.config_app.__post_init__()
        self.ao_gravar()
        self.destroy()
