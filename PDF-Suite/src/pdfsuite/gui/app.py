"""
PT-PT: Janela principal do PDF Suite.

       Tres separadores, um por tarefa: transformar um PDF em preenchivel,
       comparar propostas, resumir documentos.

PT-PT: REGRA DE OURO DA CONCORRENCIA. O Tkinter nao e seguro em multiplos fios.
       Ler seis PDF demora segundos, e faze-lo no fio da interface deixa a
       janela marcada como bloqueada pelo Windows. Tudo o que demora corre num
       fio secundario e comunica com a interface exclusivamente atraves de uma
       fila lida por `_pump()` no fio principal. Nenhuma funcao que corra num
       fio secundario pode tocar num widget.

EN-UK: Main window of PDF Suite.

       Three tabs, one per task: turn a PDF into a fillable one, compare
       proposals, summarise documents.

       THE GOLDEN RULE OF CONCURRENCY. Tkinter is not thread-safe. Reading six
       PDFs takes seconds, and doing it on the interface thread gets the window
       marked as hung by Windows. Everything slow runs on a secondary thread and
       talks to the interface solely through a queue read by `_pump()` on the
       main thread.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
import queue
import threading
import webbrowser
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any

import customtkinter as ctk

from .. import __app_name__, __credit__, __version__
from ..config import AppConfig
from ..extract import EXTENSOES, formatos_suportados
from ..models import Campo, Comparacao, Resumo
from . import theme
from .dialogs import JanelaDefinicoes, JanelaPesos
from .editor import EditorCampos

log = logging.getLogger(__name__)

SEPARADORES: tuple[tuple[str, str], ...] = (
    ("formularios", "Formulários"),
    ("comparar", "Comparar propostas"),
    ("resumir", "Resumir documentos"),
)


class PDFSuiteApp(ctk.CTk):
    """PT-PT: Janela principal. / EN-UK: Main window."""

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self.config_app = config

        self._fila: queue.Queue[tuple[str, Any]] = queue.Queue()
        self._ocupado = False

        # PT-PT: Estado de cada separador. Guardado para os botoes de gerar
        #        relatorio nao terem de repetir o trabalho todo.
        # EN-UK: Each tab's state, kept so the report buttons need not redo the
        #        whole job.
        self.pdf_formulario: Path | None = None
        self.campos: list[Campo] = []
        self.avisos_deteccao: list[str] = []

        self.ficheiros_comparar: list[Path] = []
        self.comparacao: Comparacao | None = None

        self.ficheiros_resumir: list[Path] = []
        self.resumos: list[Resumo] = []
        self.termos: dict | None = None

        # PT-PT: Chave da API so em memoria — nunca vai para o disco.
        # EN-UK: API key in memory only — it never reaches disk.
        self.chave_ia: str = ""

        self._fontes()
        self._janela()
        self._construir()
        self.after(100, self._pump)

    # ------------------------------------------------------------------
    # PT-PT: Construcao / EN-UK: Construction
    # ------------------------------------------------------------------

    def _fontes(self) -> None:
        familia = theme.resolve_font(theme.FONT_UI, theme.FONT_UI_FALLBACKS)
        mono = theme.resolve_font(theme.FONT_MONO, theme.FONT_MONO_FALLBACKS)
        self.f_titulo = ctk.CTkFont(family=familia, size=theme.SIZE_TITLE, weight="bold")
        self.f_seccao = ctk.CTkFont(family=familia, size=theme.SIZE_HEADING, weight="bold")
        self.f_corpo = ctk.CTkFont(family=familia, size=theme.SIZE_BODY)
        self.f_pequena = ctk.CTkFont(family=familia, size=theme.SIZE_SMALL)
        self.f_mono = ctk.CTkFont(family=mono, size=theme.SIZE_SMALL)

    def _janela(self) -> None:
        ctk.set_appearance_mode(self.config_app.tema)
        ctk.set_default_color_theme("blue")

        self.title(f"{__app_name__} {__version__}")
        self.geometry(f"{theme.WINDOW_MIN_WIDTH}x{theme.WINDOW_MIN_HEIGHT}")
        self.minsize(theme.WINDOW_MIN_WIDTH - 180, theme.WINDOW_MIN_HEIGHT - 130)
        self.configure(fg_color=theme.SURFACE)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

    def _construir(self) -> None:
        self._barra_lateral()

        self.area = ctk.CTkFrame(self, fg_color="transparent")
        self.area.grid(row=0, column=1, sticky="nsew", padx=theme.PAD_M, pady=(theme.PAD_M, 0))
        self.area.grid_columnconfigure(0, weight=1)
        self.area.grid_rowconfigure(0, weight=1)

        self.paginas: dict[str, ctk.CTkFrame] = {}
        self.saidas: dict[str, ctk.CTkTextbox] = {}

        for chave, _ in SEPARADORES:
            pagina = ctk.CTkFrame(self.area, fg_color="transparent")
            pagina.grid(row=0, column=0, sticky="nsew")
            pagina.grid_columnconfigure(0, weight=1)
            pagina.grid_rowconfigure(3, weight=1)
            self.paginas[chave] = pagina
            getattr(self, f"_pagina_{chave}")(pagina)

        self._rodape()
        self.mostrar("formularios")

    def _barra_lateral(self) -> None:
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
        ctk.CTkLabel(
            cabecalho, text=f"v{__version__}", font=self.f_pequena,
            text_color=theme.TEXT_MUTED,
        ).pack(anchor="w")

        self.botoes_nav: dict[str, ctk.CTkButton] = {}
        for chave, etiqueta in SEPARADORES:
            botao = ctk.CTkButton(
                barra, text=etiqueta, anchor="w", height=36,
                corner_radius=theme.RADIUS, font=self.f_corpo,
                fg_color="transparent", text_color=theme.TEXT_PRIMARY,
                hover_color=theme.BORDER,
                command=lambda c=chave: self.mostrar(c),
            )
            botao.pack(fill="x", padx=theme.PAD_S, pady=2)
            self.botoes_nav[chave] = botao

        rodape = ctk.CTkFrame(barra, fg_color="transparent")
        rodape.pack(side="bottom", fill="x", padx=theme.PAD_S, pady=theme.PAD_M)
        ctk.CTkButton(
            rodape, text="Abrir pasta de saída", height=30, font=self.f_pequena,
            fg_color="transparent", text_color=theme.TEXT_MUTED,
            hover_color=theme.BORDER, command=self.abrir_pasta_saida,
        ).pack(fill="x", pady=(0, theme.PAD_XS))
        ctk.CTkButton(
            rodape, text="Definições", height=30, font=self.f_pequena,
            fg_color="transparent", text_color=theme.TEXT_MUTED,
            hover_color=theme.BORDER, command=self.abrir_definicoes,
        ).pack(fill="x")

    def _rodape(self) -> None:
        barra = ctk.CTkFrame(self, height=32, corner_radius=0, fg_color=theme.SIDEBAR)
        barra.grid(row=1, column=0, columnspan=2, sticky="ew")
        barra.grid_columnconfigure(0, weight=1)

        self.lbl_estado = ctk.CTkLabel(
            barra, text="Pronto.", font=self.f_pequena,
            text_color=theme.TEXT_MUTED, anchor="w",
        )
        self.lbl_estado.grid(row=0, column=0, sticky="w", padx=theme.PAD_M, pady=theme.PAD_XS)

        self.progresso = ctk.CTkProgressBar(barra, width=150, height=6, mode="indeterminate")
        self.progresso.grid(row=0, column=1, padx=theme.PAD_M)
        self.progresso.grid_remove()

        ctk.CTkLabel(
            barra, text=__credit__, font=self.f_pequena, text_color=theme.TEXT_MUTED
        ).grid(row=0, column=2, sticky="e", padx=theme.PAD_M)

    # ------------------------------------------------------------------
    # PT-PT: Pecas reutilizaveis / EN-UK: Reusable pieces
    # ------------------------------------------------------------------

    def _titulo(self, pagina, texto: str, subtitulo: str) -> None:
        caixa = ctk.CTkFrame(pagina, fg_color="transparent")
        caixa.grid(row=0, column=0, sticky="ew", pady=(0, theme.PAD_S))
        ctk.CTkLabel(
            caixa, text=texto, font=self.f_titulo, text_color=theme.TEXT_PRIMARY
        ).pack(anchor="w")
        ctk.CTkLabel(
            caixa, text=subtitulo, font=self.f_pequena, text_color=theme.TEXT_MUTED,
            justify="left", anchor="w", wraplength=760,
        ).pack(anchor="w")

    def _botao(self, pai, texto: str, comando: Callable[[], None], principal: bool = False):
        botao = ctk.CTkButton(
            pai, text=texto, height=32, font=self.f_corpo, corner_radius=theme.RADIUS,
            fg_color=theme.ACCENT if principal else "transparent",
            text_color=theme.TEXT_ON_ACCENT if principal else theme.TEXT_PRIMARY,
            hover_color=theme.ACCENT_HOVER if principal else theme.BORDER,
            border_width=0 if principal else 1, border_color=theme.BORDER,
            command=comando,
        )
        botao.pack(side="left", padx=(0, theme.PAD_S))
        return botao

    def _saida(self, pagina, chave: str) -> ctk.CTkTextbox:
        caixa = ctk.CTkTextbox(
            pagina, font=self.f_mono, corner_radius=theme.RADIUS,
            fg_color=theme.SURFACE_RAISED, text_color=theme.TEXT_PRIMARY,
            border_width=1, border_color=theme.BORDER, wrap="word",
        )
        caixa.grid(row=3, column=0, sticky="nsew", pady=(0, theme.PAD_M))
        caixa.configure(state="disabled")
        self.saidas[chave] = caixa
        return caixa

    # ------------------------------------------------------------------
    # PT-PT: Separador dos formularios / EN-UK: Forms tab
    # ------------------------------------------------------------------

    def _pagina_formularios(self, pagina) -> None:
        self._titulo(
            pagina,
            "PDF preenchível",
            "Detecta onde ficam os campos de um formulário em papel e grava uma "
            "cópia preenchível. A detecção é uma proposta — reveja no editor antes de gravar.",
        )

        botoes = ctk.CTkFrame(pagina, fg_color="transparent")
        botoes.grid(row=1, column=0, sticky="ew", pady=(0, theme.PAD_S))
        self._botao(botoes, "Escolher PDF…", self.escolher_pdf, principal=True)
        self.btn_editor = self._botao(botoes, "Abrir editor visual", self.abrir_editor)
        self.btn_gravar_form = self._botao(botoes, "Gravar PDF preenchível", self.gravar_formulario)
        self.btn_editor.configure(state="disabled")
        self.btn_gravar_form.configure(state="disabled")

        opcoes = ctk.CTkFrame(pagina, fg_color="transparent")
        opcoes.grid(row=2, column=0, sticky="ew", pady=(0, theme.PAD_S))

        self.var_dois_pontos = ctk.BooleanVar(value=self.config_app.detectar_dois_pontos)
        ctk.CTkCheckBox(
            opcoes, text="Incluir campos deduzidos de «etiqueta:» seguida de espaço",
            variable=self.var_dois_pontos, font=self.f_pequena,
            command=self._redetectar,
        ).pack(side="left", padx=(0, theme.PAD_L))

        self.var_substituir = ctk.BooleanVar(value=self.config_app.substituir_campos_existentes)
        ctk.CTkCheckBox(
            opcoes, text="Substituir campos que já existam no PDF",
            variable=self.var_substituir, font=self.f_pequena,
        ).pack(side="left")

        self._saida(pagina, "formularios")
        self.escrever(
            "formularios",
            "Escolha um PDF para começar.\n\n"
            "A aplicação procura sublinhados, linhas desenhadas, caixas e "
            "etiquetas seguidas de espaço em branco, e propõe um campo em cada "
            "sítio onde alguém escreveria.\n\n"
            "Nenhum ficheiro é alterado: é sempre gravada uma cópia nova.",
        )

    def escolher_pdf(self) -> None:
        caminho = filedialog.askopenfilename(
            title="Escolher o PDF a converter",
            filetypes=[("Ficheiros PDF", "*.pdf"), ("Todos os ficheiros", "*.*")],
        )
        if not caminho:
            return

        self.pdf_formulario = Path(caminho)
        self.campos = []
        self._redetectar()

    def _redetectar(self) -> None:
        if not self.pdf_formulario:
            return

        caminho = self.pdf_formulario
        dois_pontos = bool(self.var_dois_pontos.get())

        def trabalho():
            from ..detect import detectar
            from ..forms import tem_formulario

            existentes = tem_formulario(caminho)
            campos, avisos = detectar(caminho, usar_dois_pontos=dois_pontos)
            return campos, avisos, existentes

        self._trabalhar(trabalho, "formularios", f"A analisar {caminho.name}…")

    def _receber_formularios(self, resultado) -> None:
        campos, avisos, existentes = resultado
        self.campos = campos
        self.avisos_deteccao = list(avisos)

        self.btn_editor.configure(state="normal" if self.pdf_formulario else "disabled")
        self.btn_gravar_form.configure(state="normal" if campos else "disabled")

        linhas = [f"Ficheiro: {self.pdf_formulario.name}", ""]

        if existentes:
            linhas.append(
                f"⚠  Este PDF já tem {existentes} campo(s) de formulário. "
                "Se já é preenchível, não precisa de ser convertido — e sobrepor "
                "campos novos aos antigos produz um formulário onde metade não grava. "
                "Use a opção «Substituir campos que já existam» se quiser recomeçar."
            )
            linhas.append("")

        for aviso in avisos:
            linhas.append(f"⚠  {aviso}")
        if avisos:
            linhas.append("")

        if not campos:
            linhas.append(
                "Não foi detectado nenhum campo.\n\n"
                "Acontece com PDF digitalizados, que não têm linhas nem texto para "
                "a detecção seguir. Abra o editor visual e marque os campos à mão — "
                "arrastar um rectângulo sobre a página cria um campo."
            )
            self.escrever("formularios", "\n".join(linhas))
            return

        baixa = [c for c in campos if c.confianca < self.config_app.confianca_minima]
        linhas.append(f"{len(campos)} campo(s) detectado(s).")
        if baixa:
            linhas.append(
                f"{len(baixa)} com confiança baixa — vale a pena confirmar no editor."
            )
        linhas.append("")
        linhas.append(f"{'Nome':<26}{'Tipo':<14}{'Origem':<14}{'Pág.':>5}  Confiança  Etiqueta")
        linhas.append("─" * 104)

        for campo in campos:
            marca = "  " if campo.confianca >= self.config_app.confianca_minima else "! "
            linhas.append(
                f"{marca}{campo.nome[:24]:<24}{campo.tipo.value:<14}"
                f"{campo.origem.value:<14}{campo.pagina + 1:>5}"
                f"{campo.confianca:>10.0%}  {campo.etiqueta[:34]}"
            )

        linhas.append("")
        linhas.append(
            "Abra o editor visual para corrigir posições, nomes e tipos, ou grave já."
        )
        self.escrever("formularios", "\n".join(linhas))

    def abrir_editor(self) -> None:
        if not self.pdf_formulario:
            return
        EditorCampos(self, self.pdf_formulario, self.campos, ao_gravar=self._editor_fechou)

    def _editor_fechou(self, campos: list[Campo]) -> None:
        """PT-PT: Chamado quando o editor fecha. / EN-UK: Called when the editor closes."""
        self.campos = campos
        self.btn_gravar_form.configure(state="normal" if campos else "disabled")
        self._receber_formularios((campos, self.avisos_deteccao, 0))
        self.estado(f"{len(campos)} campo(s) depois da revisão.")

    def gravar_formulario(self) -> None:
        if not self.pdf_formulario or not self.campos:
            return

        sugestao = f"{self.pdf_formulario.stem}_preenchivel.pdf"
        destino = filedialog.asksaveasfilename(
            title="Gravar o PDF preenchível",
            initialdir=str(self.config_app.output_dir),
            initialfile=sugestao,
            defaultextension=".pdf",
            filetypes=[("Ficheiros PDF", "*.pdf")],
        )
        if not destino:
            return

        origem = self.pdf_formulario
        campos = list(self.campos)
        substituir = bool(self.var_substituir.get())
        pasta = self.config_app.output_dir

        def trabalho():
            from ..forms import criar_formulario
            from ..reports import gravar_html, relatorio_formulario

            escritos, avisos = criar_formulario(
                origem, Path(destino), campos, substituir_existentes=substituir
            )
            html = relatorio_formulario(origem, Path(destino), campos, avisos)
            relatorio = gravar_html(html, pasta, "formulario")
            return Path(destino), escritos, avisos, relatorio

        self._trabalhar(trabalho, "gravou_formulario", "A gravar o formulário…")

    def _receber_gravou_formulario(self, resultado) -> None:
        destino, escritos, avisos, relatorio = resultado

        linhas = [f"Gravado: {destino}", f"{escritos} campo(s) escritos.", ""]
        for aviso in avisos:
            linhas.append(f"⚠  {aviso}")
        if avisos:
            linhas.append("")
        linhas.append(f"Relatório: {relatorio}")
        linhas.append("")
        linhas.append(
            "Confirme abrindo o PDF no leitor que a equipa usa. Alguns "
            "visualizadores muito simples mostram os campos vazios até se clicar "
            "neles — é do visualizador, não do ficheiro."
        )
        self.escrever("formularios", "\n".join(linhas))
        self.estado(f"Formulário gravado: {destino.name}")

        if self.config_app.abrir_apos_gerar:
            webbrowser.open(destino.as_uri())

    # ------------------------------------------------------------------
    # PT-PT: Separador da comparacao / EN-UK: Comparison tab
    # ------------------------------------------------------------------

    def _pagina_comparar(self, pagina) -> None:
        self._titulo(
            pagina,
            "Comparar propostas",
            "Lê vários documentos, extrai os valores e condições, normaliza o IVA "
            "e pontua numa matriz ponderada. Os valores extraídos são uma leitura "
            "automática — confirme os que a aplicação assinalar.",
        )

        botoes = ctk.CTkFrame(pagina, fg_color="transparent")
        botoes.grid(row=1, column=0, sticky="ew", pady=(0, theme.PAD_S))
        self._botao(botoes, "Escolher ficheiros…", self.escolher_propostas, principal=True)
        self._botao(botoes, "Escolher pasta…", self.escolher_pasta_propostas)
        self._botao(botoes, "Pesos dos critérios", self.abrir_pesos)
        self.btn_comparar = self._botao(botoes, "Comparar", self.executar_comparacao)
        self.btn_comparar.configure(state="disabled")

        botoes2 = ctk.CTkFrame(pagina, fg_color="transparent")
        botoes2.grid(row=2, column=0, sticky="ew", pady=(0, theme.PAD_S))
        self.btn_rel_html = self._botao(botoes2, "Relatório HTML", self.relatorio_comparacao_html)
        self.btn_rel_xlsx = self._botao(botoes2, "Exportar para Excel", self.relatorio_comparacao_excel)
        self.btn_ia_comp = self._botao(botoes2, "Análise assistida", self.analise_assistida)
        for botao in (self.btn_rel_html, self.btn_rel_xlsx, self.btn_ia_comp):
            botao.configure(state="disabled")

        self._saida(pagina, "comparar")
        self.escrever(
            "comparar",
            "Escolha as propostas a comparar.\n\n"
            f"Formatos aceites: {formatos_suportados()}.\n\n"
            "O IVA é normalizado antes de comparar. É a armadilha clássica destas "
            "comparações: uma proposta a 10.000 € com IVA incluído é mais barata "
            "do que uma a 9.000 € mais IVA, e quem compara os números da capa "
            "escolhe a errada.",
        )

    def escolher_propostas(self) -> None:
        caminhos = filedialog.askopenfilenames(
            title="Escolher as propostas",
            filetypes=[
                ("Documentos", " ".join(f"*{e}" for e in EXTENSOES)),
                ("PDF", "*.pdf"),
                ("Todos os ficheiros", "*.*"),
            ],
        )
        if caminhos:
            self.ficheiros_comparar = [Path(c) for c in caminhos]
            self._listar_escolhidos("comparar", self.ficheiros_comparar)
            self.btn_comparar.configure(state="normal")

    def escolher_pasta_propostas(self) -> None:
        pasta = filedialog.askdirectory(title="Pasta com as propostas")
        if not pasta:
            return

        encontrados = sorted(
            p for p in Path(pasta).iterdir()
            if p.is_file() and p.suffix.lower() in EXTENSOES
        )
        if not encontrados:
            messagebox.showinfo(
                __app_name__,
                f"Não há documentos legíveis nessa pasta.\n\nAceites: {formatos_suportados()}",
            )
            return

        self.ficheiros_comparar = encontrados
        self._listar_escolhidos("comparar", encontrados)
        self.btn_comparar.configure(state="normal")

    def _listar_escolhidos(self, destino: str, ficheiros: list[Path]) -> None:
        linhas = [f"{len(ficheiros)} ficheiro(s) escolhido(s):", ""]
        linhas.extend(f"  {f.name}" for f in ficheiros)
        linhas.append("")
        linhas.append("Carregue no botão para começar.")
        self.escrever(destino, "\n".join(linhas))

    def executar_comparacao(self) -> None:
        if not self.ficheiros_comparar:
            return

        ficheiros = list(self.ficheiros_comparar)
        config = self.config_app

        def trabalho():
            from ..analyse import analisar_varios, verificar_coerencia
            from ..extract import ler_varios
            from ..scoring import comparar

            documentos = ler_varios(ficheiros)
            propostas = analisar_varios(documentos)
            return comparar(
                propostas,
                criterios=config.criterios(),
                taxa_iva=config.taxa_iva,
                avisos=verificar_coerencia(propostas),
                penalizar_em_falta=config.penalizar_em_falta,
            )

        self._trabalhar(trabalho, "comparar", f"A ler e analisar {len(ficheiros)} documento(s)…")

    def _receber_comparar(self, comparacao: Comparacao) -> None:
        self.comparacao = comparacao

        estado = "normal" if comparacao.pontuacoes else "disabled"
        for botao in (self.btn_rel_html, self.btn_rel_xlsx, self.btn_ia_comp):
            botao.configure(state=estado)

        self.escrever("comparar", self._texto_comparacao(comparacao))

    def _texto_comparacao(self, comparacao: Comparacao) -> str:
        from ..money import formatar_moeda
        from ..scoring import poupanca

        if not comparacao.pontuacoes:
            linhas = ["Nenhuma proposta pôde ser comparada.", ""]
            linhas.extend(f"⚠  {a}" for a in comparacao.avisos)
            return "\n".join(linhas)

        linhas: list[str] = []
        vencedora = comparacao.vencedora

        if comparacao.decisao_segura and vencedora:
            linhas.append(
                f"Melhor pontuada: {vencedora.proposta.rotulo} "
                f"({vencedora.total:.1f} pontos, {vencedora.completude:.0f}% dos critérios)"
            )
        elif vencedora:
            linhas.append(
                f"Sem vencedor claro. À frente por pouco: {vencedora.proposta.rotulo} "
                f"({vencedora.total:.1f} pontos)"
            )

        diferenca = poupanca(comparacao)
        if diferenca:
            valor, barata, cara = diferenca
            linhas.append(
                f"Entre a mais barata ({barata}) e a mais cara ({cara}) vão "
                f"{formatar_moeda(valor)} com IVA."
            )
        linhas.append("")

        cabecalho = f"{'#':<3}{'Proposta':<28}{'Pontos':>7}{'Compl.':>8}{'Total c/IVA':>15}  "
        cabecalho += "".join(f"{c.etiqueta[:9]:>10}" for c in comparacao.criterios[1:])
        linhas.append(cabecalho)
        linhas.append("─" * len(cabecalho))

        for posicao, pontuacao in enumerate(comparacao.ordenadas, 1):
            preco = pontuacao.valores.get("preco")
            linha = (
                f"{posicao:<3}{pontuacao.proposta.rotulo[:27]:<28}"
                f"{pontuacao.total:>7.1f}{pontuacao.completude:>7.0f}%"
                f"{formatar_moeda(preco, pontuacao.proposta.moeda or 'EUR'):>15}  "
            )
            for criterio in comparacao.criterios[1:]:
                valor = pontuacao.valores.get(criterio.chave)
                linha += f"{'—' if valor is None else f'{valor:.0f}':>10}"
            linhas.append(linha)

        linhas.append("")
        linhas.append("Valores extraídos, por proposta:")
        linhas.append("")

        for pontuacao in comparacao.ordenadas:
            proposta = pontuacao.proposta
            iva = {True: "IVA incluído", False: "acresce IVA", None: "IVA não declarado"}[
                proposta.iva_incluido
            ]
            linhas.append(
                f"  {proposta.rotulo}  ·  {proposta.documento.nome}"
                + (f"  ·  ref. {proposta.referencia.valor}" if proposta.referencia.conhecido else "")
            )
            linhas.append(
                f"    Total no documento: {formatar_moeda(proposta.total.valor)} ({iva})"
                f"  →  {formatar_moeda(proposta.total_com_iva(comparacao.taxa_iva_omissao))} com IVA"
            )
            if proposta.total.contexto:
                linhas.append(f"    Lido de: «{proposta.total.contexto[:110]}»")
            for nota in proposta.notas:
                linhas.append(f"    ⚠  {nota}")
            linhas.append("")

        if comparacao.avisos:
            linhas.append("─" * 70)
            linhas.append("Avisos da comparação:")
            for aviso in comparacao.avisos:
                linhas.append(f"  ⚠  {aviso}")

        return "\n".join(linhas)

    def relatorio_comparacao_html(self) -> None:
        if not self.comparacao:
            return
        comparacao = self.comparacao
        pasta = self.config_app.output_dir

        def trabalho():
            from ..reports import gravar_html, relatorio_comparacao

            return gravar_html(relatorio_comparacao(comparacao), pasta, "comparacao")

        self._trabalhar(trabalho, "gravou_ficheiro", "A gerar o relatório…")

    def relatorio_comparacao_excel(self) -> None:
        if not self.comparacao:
            return

        destino = filedialog.asksaveasfilename(
            title="Exportar para Excel",
            initialdir=str(self.config_app.output_dir),
            initialfile="comparacao_propostas.xlsx",
            defaultextension=".xlsx",
            filetypes=[("Livro do Excel", "*.xlsx")],
        )
        if not destino:
            return

        comparacao = self.comparacao

        def trabalho():
            from ..reports import excel_comparacao

            return excel_comparacao(comparacao, Path(destino))

        self._trabalhar(trabalho, "gravou_ficheiro", "A exportar…")

    def _receber_gravou_ficheiro(self, destino: Path) -> None:
        self.estado(f"Gravado: {destino.name}")
        self.escrever(
            self._separador_actual, f"\n\nGravado em:\n{destino}\n", limpar=False
        )
        if self.config_app.abrir_apos_gerar:
            webbrowser.open(Path(destino).as_uri())

    def analise_assistida(self) -> None:
        """
        PT-PT: Envia os documentos para o modelo, depois de confirmar.
        EN-UK: Sends the documents to the model, after confirming.
        """
        if not self.comparacao:
            return

        from ..ai import disponivel, resumo_do_envio

        pode, motivo = disponivel(self.chave_ia)
        if not pode:
            messagebox.showwarning(__app_name__, motivo)
            return

        textos = [
            (p.proposta.rotulo, p.proposta.documento.texto)
            for p in self.comparacao.ordenadas
        ]

        # PT-PT: A confirmacao diz quantos documentos e quantos caracteres saem
        #        da maquina. Um «Continuar?» generico nao dava a quem decide o
        #        que precisa para decidir.
        # EN-UK: The confirmation says how many documents and characters leave
        #        the machine.
        if not messagebox.askyesno(
            f"{__app_name__} — enviar para análise",
            resumo_do_envio(textos),
            icon="warning",
        ):
            return

        chave = self.chave_ia
        modelo = self.config_app.modelo_ia

        def trabalho():
            from ..ai import comparar_com_ia

            return comparar_com_ia(textos, chave=chave, modelo=modelo)

        self._trabalhar(trabalho, "recebeu_ia", "A analisar com o modelo…")

    def _receber_recebeu_ia(self, texto: str) -> None:
        self.escrever(
            self._separador_actual,
            "\n\n" + "═" * 70 + "\nANÁLISE ASSISTIDA POR MODELO\n"
            "Interpretação gerada, não texto dos documentos. Confirme no original "
            "antes de usar numa decisão.\n" + "═" * 70 + "\n\n" + texto + "\n",
            limpar=False,
        )
        self.estado("Análise assistida concluída.")

    # ------------------------------------------------------------------
    # PT-PT: Separador do resumo / EN-UK: Summary tab
    # ------------------------------------------------------------------

    def _pagina_resumir(self, pagina) -> None:
        self._titulo(
            pagina,
            "Resumir documentos",
            "Resumo extractivo: escolhe as frases mais representativas e "
            "apresenta-as por ordem de leitura. Não gera texto novo — cada frase "
            "está no documento tal e qual.",
        )

        botoes = ctk.CTkFrame(pagina, fg_color="transparent")
        botoes.grid(row=1, column=0, sticky="ew", pady=(0, theme.PAD_S))
        self._botao(botoes, "Escolher ficheiros…", self.escolher_resumir, principal=True)
        self.btn_resumir = self._botao(botoes, "Resumir", self.executar_resumo)
        self.btn_rel_resumo = self._botao(botoes, "Relatório HTML", self.relatorio_resumo_html)
        self.btn_ia_resumo = self._botao(botoes, "Análise assistida", self.resumo_assistido)
        for botao in (self.btn_resumir, self.btn_rel_resumo, self.btn_ia_resumo):
            botao.configure(state="disabled")

        opcoes = ctk.CTkFrame(pagina, fg_color="transparent")
        opcoes.grid(row=2, column=0, sticky="ew", pady=(0, theme.PAD_S))
        ctk.CTkLabel(opcoes, text="Frases por documento:", font=self.f_pequena).pack(
            side="left", padx=(0, theme.PAD_S)
        )
        self.cb_frases = ctk.CTkComboBox(
            opcoes, values=["4", "6", "8", "12", "20"], width=80,
            state="readonly", font=self.f_corpo,
        )
        self.cb_frases.set(str(self.config_app.frases_resumo))
        self.cb_frases.pack(side="left")

        self._saida(pagina, "resumir")
        self.escrever(
            "resumir",
            "Escolha um ou vários documentos.\n\n"
            f"Formatos aceites: {formatos_suportados()}.\n\n"
            "Com dois ou mais documentos, a aplicação mostra também os termos "
            "comuns a todos e os exclusivos de cada um — que é o caminho mais "
            "curto para saber o que um relatório diz que os outros não dizem.",
        )

    def escolher_resumir(self) -> None:
        caminhos = filedialog.askopenfilenames(
            title="Escolher os documentos",
            filetypes=[
                ("Documentos", " ".join(f"*{e}" for e in EXTENSOES)),
                ("Todos os ficheiros", "*.*"),
            ],
        )
        if caminhos:
            self.ficheiros_resumir = [Path(c) for c in caminhos]
            self._listar_escolhidos("resumir", self.ficheiros_resumir)
            self.btn_resumir.configure(state="normal")

    def executar_resumo(self) -> None:
        if not self.ficheiros_resumir:
            return

        ficheiros = list(self.ficheiros_resumir)
        try:
            quantas = int(self.cb_frases.get())
        except ValueError:
            quantas = self.config_app.frases_resumo

        def trabalho():
            from ..extract import ler_varios
            from ..summarise import comparar_textos, resumir

            documentos = ler_varios(ficheiros)
            resumos = [resumir(d, quantas) for d in documentos]
            termos = comparar_textos(documentos) if len(documentos) > 1 else None
            return resumos, termos

        self._trabalhar(trabalho, "resumir", f"A resumir {len(ficheiros)} documento(s)…")

    def _receber_resumir(self, resultado) -> None:
        resumos, termos = resultado
        self.resumos = resumos
        self.termos = termos

        estado = "normal" if resumos else "disabled"
        self.btn_rel_resumo.configure(state=estado)
        self.btn_ia_resumo.configure(state=estado)

        linhas: list[str] = []
        for resumo in resumos:
            documento = resumo.documento
            linhas.append("═" * 70)
            linhas.append(f"{documento.nome}  ·  {documento.formato}"
                          + (f"  ·  {documento.paginas} pág." if documento.paginas else "")
                          + f"  ·  {documento.palavras} palavras")
            linhas.append("═" * 70)

            if documento.erro:
                linhas.append(f"⚠  {documento.erro}")
                linhas.append("")
                continue
            if documento.digitalizado:
                linhas.append(
                    "⚠  Pouco texto para o número de páginas: o documento parece "
                    "estar digitalizado e o resumo pode estar incompleto."
                )

            linhas.append("")
            for frase in resumo.frases:
                linhas.append(f"  • {frase}")
            linhas.append("")

            if resumo.numeros:
                linhas.append(f"  Valores e prazos: {', '.join(resumo.numeros[:12])}")
            if resumo.datas:
                linhas.append(f"  Datas: {', '.join(resumo.datas[:8])}")
            if resumo.palavras_chave:
                chave = ", ".join(f"{p} ({n})" for p, n in resumo.palavras_chave[:10])
                linhas.append(f"  Termos frequentes: {chave}")
            linhas.append("")

        if termos:
            linhas.append("═" * 70)
            linhas.append("TERMOS")
            linhas.append("═" * 70)
            linhas.append(f"  Comuns a todos: {', '.join(termos.get('__comuns__', [])[:20])}")
            linhas.append("")
            for rotulo, exclusivos in termos.items():
                if rotulo == "__comuns__" or not exclusivos:
                    continue
                linhas.append(f"  Só em {rotulo}: {', '.join(exclusivos[:14])}")

        self.escrever("resumir", "\n".join(linhas))

    def relatorio_resumo_html(self) -> None:
        if not self.resumos:
            return
        resumos = self.resumos
        termos = self.termos
        pasta = self.config_app.output_dir

        def trabalho():
            from ..reports import gravar_html, relatorio_resumo

            return gravar_html(relatorio_resumo(resumos, termos), pasta, "resumo")

        self._trabalhar(trabalho, "gravou_ficheiro", "A gerar o relatório…")

    def resumo_assistido(self) -> None:
        if not self.resumos:
            return

        from ..ai import disponivel, resumo_do_envio

        pode, motivo = disponivel(self.chave_ia)
        if not pode:
            messagebox.showwarning(__app_name__, motivo)
            return

        validos = [r for r in self.resumos if r.documento.ok]
        if not validos:
            messagebox.showinfo(__app_name__, "Nenhum documento tem texto para analisar.")
            return

        textos = [(r.documento.nome, r.documento.texto) for r in validos]
        if not messagebox.askyesno(
            f"{__app_name__} — enviar para análise", resumo_do_envio(textos), icon="warning"
        ):
            return

        chave = self.chave_ia
        modelo = self.config_app.modelo_ia

        def trabalho():
            from ..ai import resumir_com_ia

            partes = []
            for nome, texto in textos:
                partes.append(f"### {nome}\n\n{resumir_com_ia(nome, texto, chave, modelo)}")
            return "\n\n".join(partes)

        self._trabalhar(trabalho, "recebeu_ia", "A resumir com o modelo…")

    # ------------------------------------------------------------------
    # PT-PT: Navegacao, concorrencia e janelas / EN-UK: Navigation, threads
    # ------------------------------------------------------------------

    def mostrar(self, chave: str) -> None:
        self._separador_actual = chave
        self.paginas[chave].tkraise()
        for nome, botao in self.botoes_nav.items():
            activo = nome == chave
            botao.configure(
                fg_color=theme.ACCENT if activo else "transparent",
                text_color=theme.TEXT_ON_ACCENT if activo else theme.TEXT_PRIMARY,
            )

    def escrever(self, chave: str, texto: str, limpar: bool = True) -> None:
        """PT-PT: Escreve numa caixa. So do fio principal. / EN-UK: Main thread only."""
        caixa = self.saidas.get(chave)
        if caixa is None:
            return
        caixa.configure(state="normal")
        if limpar:
            caixa.delete("1.0", "end")
        caixa.insert("end", texto)
        caixa.see("end" if not limpar else "1.0")
        caixa.configure(state="disabled")

    def estado(self, texto: str) -> None:
        self.lbl_estado.configure(text=texto)

    def _trabalhar(self, funcao: Callable[[], Any], destino: str, estado: str) -> None:
        """
        PT-PT: Corre `funcao` num fio e entrega o resultado a interface.

               Recusa arrancar se ja houver trabalho em curso: carregar duas
               vezes em «Comparar» lancava dois fios a escrever na mesma caixa
               de texto ao mesmo tempo.

        EN-UK: Runs `funcao` on a thread and hands the result to the interface.
               Refuses to start when work is in progress.
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
                self._fila.put(("resultado", (destino, funcao())))
            except Exception as exc:  # noqa: BLE001 — a mensagem tem de chegar ao operador
                log.exception("Falha em %s", destino)
                self._fila.put(("erro", (destino, str(exc))))

        threading.Thread(target=alvo, daemon=True).start()

    def _pump(self) -> None:
        """PT-PT: Le a fila no fio principal. / EN-UK: Reads the queue, main thread."""
        try:
            while True:
                tipo, carga = self._fila.get_nowait()
                destino, valor = carga
                self._terminar()

                if tipo == "erro":
                    alvo = destino if destino in self.saidas else self._separador_actual
                    self.escrever(alvo, f"\n\nFalhou: {valor}\n", limpar=False)
                    self.estado("A operação falhou — veja o registo com --verbose.")
                    continue

                tratador = getattr(self, f"_receber_{destino}", None)
                if tratador:
                    tratador(valor)
                elif destino in self.saidas:
                    self.escrever(destino, str(valor))
        except queue.Empty:
            pass
        self.after(120, self._pump)

    def _terminar(self) -> None:
        self._ocupado = False
        self.progresso.stop()
        self.progresso.grid_remove()
        self.estado("Pronto.")

    def abrir_definicoes(self) -> None:
        JanelaDefinicoes(self, self.config_app, ao_gravar=self._aplicar_definicoes)

    def _aplicar_definicoes(self) -> None:
        ctk.set_appearance_mode(self.config_app.tema)
        self.config_app.ensure_directories()
        self.config_app.save()
        self.var_dois_pontos.set(self.config_app.detectar_dois_pontos)
        self.var_substituir.set(self.config_app.substituir_campos_existentes)
        self.cb_frases.set(str(self.config_app.frases_resumo))
        self.estado("Definições gravadas.")

    def abrir_pesos(self) -> None:
        JanelaPesos(self, self.config_app, ao_gravar=self._aplicar_pesos)

    def _aplicar_pesos(self) -> None:
        self.config_app.save()
        self.estado("Pesos actualizados.")
        if self.comparacao:
            # PT-PT: Voltar a pontuar com os pesos novos, sem reler os
            #        ficheiros. Mudar um peso e reler seis PDF do disco seria
            #        esperar segundos por uma conta que demora milissegundos.
            # EN-UK: Rescore with the new weights without rereading the files.
            propostas = [p.proposta for p in self.comparacao.pontuacoes]
            config = self.config_app

            def trabalho():
                from ..scoring import comparar

                return comparar(
                    propostas,
                    criterios=config.criterios(),
                    taxa_iva=config.taxa_iva,
                    penalizar_em_falta=config.penalizar_em_falta,
                )

            self._trabalhar(trabalho, "comparar", "A voltar a pontuar…")

    def abrir_pasta_saida(self) -> None:
        self.config_app.ensure_directories()
        try:
            webbrowser.open(self.config_app.output_dir.as_uri())
        except (OSError, ValueError) as exc:
            messagebox.showerror(__app_name__, f"Não foi possível abrir a pasta:\n{exc}")


def correr(config: AppConfig) -> None:
    """
    PT-PT: Abre a janela e entra no ciclo de eventos.
    EN-UK: Opens the window and enters the event loop.
    """
    app = PDFSuiteApp(config)
    app.mainloop()
