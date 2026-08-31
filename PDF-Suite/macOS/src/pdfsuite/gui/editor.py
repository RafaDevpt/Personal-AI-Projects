"""
PT-PT: Editor visual dos campos.

       Mostra a pagina do PDF como imagem e desenha os campos por cima. O
       utilizador arrasta para criar, clica para seleccionar, arrasta as pegas
       para redimensionar e apaga com o teclado.

       Porque e que isto existe em vez de uma tabela de coordenadas: a deteccao
       automatica acerta na maioria dos campos e falha em alguns, e corrigir um
       campo mal colocado numa tabela de numeros e impossivel na pratica —
       ninguem sabe o que significa mudar y0 de 472 para 468 sem ver a pagina.
       Com a pagina a vista, e obvio.

       A rasterizacao usa o `pdftoppm` do poppler, que ja e uma dependencia
       indirecta do pdfplumber, ou o `pypdfium2` se estiver instalado. Se
       nenhum estiver disponivel, o editor abre na mesma sem a imagem de fundo
       e diz porque — os campos continuam a poder ser corrigidos pelas
       coordenadas, o que e pior mas nao e nada.

EN-UK: Visual field editor.

       Shows the PDF page as an image and draws the fields on top. The user
       drags to create, clicks to select, drags handles to resize and deletes
       with the keyboard.

       Why this exists rather than a table of coordinates: automatic detection
       gets most fields right and some wrong, and fixing a misplaced field in a
       table of numbers is impossible in practice — nobody knows what changing
       y0 from 472 to 468 means without seeing the page.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

import customtkinter as ctk

from ..models import Campo, Origem, TipoCampo, nome_seguro_campo
from . import theme

log = logging.getLogger(__name__)

# PT-PT: Tamanho das pegas de redimensionamento, em pixeis do ecra.
# EN-UK: Size of the resize handles, in screen pixels.
PEGA = 7

# PT-PT: Abaixo disto, um arrasto e considerado um clique e nao cria campo.
#        Sem esta margem, cada clique para seleccionar criava um campo de dois
#        pixeis por cima do que se queria seleccionar.
# EN-UK: Below this, a drag counts as a click and creates no field. Without the
#        margin, every click to select created a two-pixel field on top of what
#        was being selected.
ARRASTO_MINIMO = 8


def rasterizar(caminho: Path, pagina: int, dpi: int = theme.EDITOR_DPI):
    """
    PT-PT: Converte uma pagina do PDF numa imagem.

    EN-UK: Renders one PDF page as an image.

    :return:
        PT-PT: (imagem PIL, escala) ou (None, motivo) se nao for possivel.
        EN-UK: (PIL image, scale) or (None, reason) when not possible.
    """
    try:
        from PIL import Image
    except ImportError:
        return None, (
            "A biblioteca Pillow não está instalada — sem ela não é possível "
            "mostrar a página. Instale com: pip install pillow"
        )

    # PT-PT: Primeiro o pypdfium2, se existir: nao depende de nada instalado
    #        fora do Python, o que numa maquina de dominio e uma vantagem
    #        decisiva.
    # EN-UK: pypdfium2 first, if present: it depends on nothing installed
    #        outside Python, which on a domain machine is decisive.
    try:
        import pypdfium2

        documento = pypdfium2.PdfDocument(str(caminho))
        try:
            imagem = documento[pagina].render(scale=dpi / 72).to_pil()
            return imagem, dpi / 72
        finally:
            documento.close()
    except ImportError:
        pass
    except Exception as exc:  # noqa: BLE001
        log.warning("pypdfium2 falhou: %s", exc)

    if not shutil.which("pdftoppm"):
        return None, (
            "Não foi encontrada nenhuma forma de desenhar a página.\n\n"
            "Instale uma destas:\n"
            "  pip install pypdfium2      (recomendado, não precisa de mais nada)\n"
            "  ou o poppler-utils, que traz o pdftoppm\n\n"
            "Sem isto pode continuar a rever os campos na lista, mas sem ver a página."
        )

    try:
        with tempfile.TemporaryDirectory() as pasta:
            prefixo = Path(pasta) / "pagina"
            subprocess.run(  # noqa: S603 — argumentos construídos aqui, não pelo utilizador
                [
                    "pdftoppm", "-r", str(dpi), "-png",
                    "-f", str(pagina + 1), "-l", str(pagina + 1),
                    str(caminho), str(prefixo),
                ],
                check=True,
                capture_output=True,
                timeout=60,
            )
            geradas = sorted(Path(pasta).glob("pagina*.png"))
            if not geradas:
                return None, "O pdftoppm não produziu nenhuma imagem."
            # PT-PT: A imagem e copiada para memoria antes de a pasta temporaria
            #        desaparecer — o Pillow le em modo preguicoso e devolveria um
            #        ficheiro ja apagado.
            # EN-UK: The image is copied into memory before the temp folder goes
            #        away — Pillow reads lazily and would return a deleted file.
            with Image.open(geradas[0]) as aberta:
                return aberta.copy(), dpi / 72
    except subprocess.TimeoutExpired:
        return None, "A página demorou demasiado a ser desenhada."
    except Exception as exc:  # noqa: BLE001
        return None, f"Não foi possível desenhar a página: {exc}"


class EditorCampos(ctk.CTkToplevel):
    """
    PT-PT: Janela do editor visual.

           As coordenadas do PDF contam de baixo para cima; as da tela contam
           de cima para baixo. A conversao esta em `_para_tela` e `_para_pdf` e
           nao aparece em mais lado nenhum — misturar as duas convencoes e o
           erro classico deste tipo de editor e produz campos correctos na
           horizontal e invertidos na vertical.

    EN-UK: The visual editor window. PDF coordinates count from the bottom,
           canvas coordinates from the top. The conversion lives in
           `_para_tela` and `_para_pdf` and nowhere else.
    """

    def __init__(self, pai, caminho: Path, campos: list[Campo], ao_gravar) -> None:
        super().__init__(pai)
        self.caminho = Path(caminho)
        self.campos = campos
        self.ao_gravar = ao_gravar

        self.pagina_actual = 0
        self.total_paginas = self._contar_paginas()
        self.escala = 1.0
        self.altura_pdf = 842.0
        self.imagem_tk = None
        self.seleccionado: Campo | None = None

        self._arrasto_inicio: tuple[float, float] | None = None
        self._rectangulo_temporario = None
        self._modo = "criar"
        self._pega_activa = ""
        self._offset = (0.0, 0.0)

        self.title(f"Editor de campos — {self.caminho.name}")
        self.geometry("1180x820")
        self.configure(fg_color=theme.SURFACE)
        self.transient(pai)

        self._construir()
        self.after(200, self._focar)
        self.after(260, self.carregar_pagina)

    def _focar(self) -> None:
        """
        PT-PT: O `grab_set` esta num `after` de proposito: chamado logo a seguir
               ao construtor, em Windows o CustomTkinter ainda nao terminou de
               desenhar e o pedido de foco falha em silencio — a janela abre
               atras da principal e o utilizador conclui que o botao nao fez
               nada.
        EN-UK: The `grab_set` sits in an `after` deliberately: called right after
               the constructor on Windows, the focus request fails silently and
               the window opens behind the main one.
        """
        try:
            self.grab_set()
            self.lift()
            self.focus_force()
        except Exception as exc:  # noqa: BLE001
            log.debug("Não foi possível fixar o foco: %s", exc)

    def _contar_paginas(self) -> int:
        try:
            from pypdf import PdfReader

            return len(PdfReader(str(self.caminho)).pages)
        except Exception as exc:  # noqa: BLE001
            log.warning("Não foi possível contar as páginas: %s", exc)
            return 1

    # ------------------------------------------------------------------
    # PT-PT: Construcao / EN-UK: Construction
    # ------------------------------------------------------------------

    def _construir(self) -> None:
        import tkinter as tk

        barra = ctk.CTkFrame(self, fg_color=theme.SIDEBAR, corner_radius=0)
        barra.pack(fill="x")

        self.btn_anterior = ctk.CTkButton(
            barra, text="◀", width=36, command=lambda: self.mudar_pagina(-1),
            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
        )
        self.btn_anterior.pack(side="left", padx=(theme.PAD_M, theme.PAD_XS), pady=theme.PAD_S)

        self.lbl_pagina = ctk.CTkLabel(barra, text="Página 1", width=110)
        self.lbl_pagina.pack(side="left")

        self.btn_seguinte = ctk.CTkButton(
            barra, text="▶", width=36, command=lambda: self.mudar_pagina(1),
            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
        )
        self.btn_seguinte.pack(side="left", padx=(theme.PAD_XS, theme.PAD_L))

        ctk.CTkLabel(barra, text="Tipo do novo campo:", font=ctk.CTkFont(size=theme.SIZE_SMALL)).pack(
            side="left", padx=(0, theme.PAD_XS)
        )
        self.cb_tipo = ctk.CTkComboBox(
            barra,
            values=[t.etiqueta for t in TipoCampo],
            width=170,
            state="readonly",
        )
        self.cb_tipo.set(TipoCampo.TEXTO.etiqueta)
        self.cb_tipo.pack(side="left", padx=(0, theme.PAD_L))

        ctk.CTkButton(
            barra, text="Apagar seleccionado", command=self.apagar_seleccionado,
            fg_color="transparent", text_color=theme.TEXT_PRIMARY,
            border_width=1, border_color=theme.BORDER, hover_color=theme.BORDER,
        ).pack(side="left", padx=(0, theme.PAD_S))

        ctk.CTkButton(
            barra, text="Concluir", command=self.concluir,
            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
        ).pack(side="right", padx=theme.PAD_M)

        # --- PT-PT: Tela com barras de deslocamento -----------------------
        moldura = ctk.CTkFrame(self, fg_color=theme.SURFACE)
        moldura.pack(fill="both", expand=True, padx=theme.PAD_M, pady=(theme.PAD_S, 0))

        self.tela = tk.Canvas(
            moldura, bg=theme.EDITOR_FUNDO, highlightthickness=0, cursor="crosshair"
        )
        vertical = tk.Scrollbar(moldura, orient="vertical", command=self.tela.yview)
        horizontal = tk.Scrollbar(moldura, orient="horizontal", command=self.tela.xview)
        self.tela.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)

        vertical.pack(side="right", fill="y")
        horizontal.pack(side="bottom", fill="x")
        self.tela.pack(side="left", fill="both", expand=True)

        self.tela.bind("<ButtonPress-1>", self._premir)
        self.tela.bind("<B1-Motion>", self._arrastar)
        self.tela.bind("<ButtonRelease-1>", self._largar)
        self.tela.bind("<Motion>", self._mover_rato)

        # PT-PT: O foco no clique e o que faz o teclado funcionar. Uma tela Tk
        #        sem foco ignora as teclas em silencio, e o utilizador conclui
        #        que a tecla Delete nao esta implementada.
        # EN-UK: Taking focus on click is what makes the keyboard work. A Tk
        #        canvas without focus ignores keys silently.
        self.tela.bind("<Button-1>", lambda _: self.tela.focus_set(), add="+")
        self.bind("<Delete>", lambda _: self.apagar_seleccionado())
        self.bind("<BackSpace>", lambda _: self.apagar_seleccionado())
        self.bind("<Escape>", lambda _: self._limpar_seleccao())
        self.bind("<Prior>", lambda _: self.mudar_pagina(-1))
        self.bind("<Next>", lambda _: self.mudar_pagina(1))

        # --- PT-PT: Painel do campo seleccionado --------------------------
        painel = ctk.CTkFrame(self, fg_color=theme.SIDEBAR, corner_radius=0, height=76)
        painel.pack(fill="x", side="bottom")

        ctk.CTkLabel(painel, text="Nome:", font=ctk.CTkFont(size=theme.SIZE_SMALL)).pack(
            side="left", padx=(theme.PAD_M, theme.PAD_XS), pady=theme.PAD_S
        )
        self.entrada_nome = ctk.CTkEntry(painel, width=190)
        self.entrada_nome.pack(side="left", pady=theme.PAD_S)
        self.entrada_nome.bind("<KeyRelease>", self._actualizar_nome)

        ctk.CTkLabel(painel, text="Etiqueta:", font=ctk.CTkFont(size=theme.SIZE_SMALL)).pack(
            side="left", padx=(theme.PAD_M, theme.PAD_XS)
        )
        self.entrada_etiqueta = ctk.CTkEntry(painel, width=210)
        self.entrada_etiqueta.pack(side="left")
        self.entrada_etiqueta.bind("<KeyRelease>", self._actualizar_etiqueta)

        ctk.CTkLabel(painel, text="Tipo:", font=ctk.CTkFont(size=theme.SIZE_SMALL)).pack(
            side="left", padx=(theme.PAD_M, theme.PAD_XS)
        )
        self.cb_tipo_seleccionado = ctk.CTkComboBox(
            painel, values=[t.etiqueta for t in TipoCampo], width=170,
            state="readonly", command=self._actualizar_tipo,
        )
        self.cb_tipo_seleccionado.pack(side="left")

        self.var_obrigatorio = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            painel, text="Obrigatório", variable=self.var_obrigatorio,
            command=self._actualizar_obrigatorio,
        ).pack(side="left", padx=theme.PAD_M)

        self.lbl_ajuda = ctk.CTkLabel(
            painel,
            text="Arraste para criar · clique para seleccionar · Delete apaga",
            font=ctk.CTkFont(size=theme.SIZE_SMALL),
            text_color=theme.TEXT_MUTED,
        )
        self.lbl_ajuda.pack(side="right", padx=theme.PAD_M)

    # ------------------------------------------------------------------
    # PT-PT: Coordenadas / EN-UK: Coordinates
    # ------------------------------------------------------------------

    def _para_tela(self, campo: Campo) -> tuple[float, float, float, float]:
        """PT-PT: Coordenadas PDF → tela. / EN-UK: PDF → canvas coordinates."""
        x0 = campo.x0 * self.escala
        x1 = campo.x1 * self.escala
        y0 = (self.altura_pdf - campo.y1) * self.escala
        y1 = (self.altura_pdf - campo.y0) * self.escala
        return x0, y0, x1, y1

    def _para_pdf(self, x0: float, y0: float, x1: float, y1: float) -> tuple[float, float, float, float]:
        """PT-PT: Coordenadas tela → PDF. / EN-UK: Canvas → PDF coordinates."""
        return (
            x0 / self.escala,
            self.altura_pdf - y1 / self.escala,
            x1 / self.escala,
            self.altura_pdf - y0 / self.escala,
        )

    # ------------------------------------------------------------------
    # PT-PT: Desenho / EN-UK: Drawing
    # ------------------------------------------------------------------

    def carregar_pagina(self) -> None:
        """PT-PT: Desenha a pagina actual. / EN-UK: Renders the current page."""
        self.tela.delete("all")
        self.lbl_pagina.configure(text=f"Página {self.pagina_actual + 1} de {self.total_paginas}")
        self.btn_anterior.configure(state="normal" if self.pagina_actual > 0 else "disabled")
        self.btn_seguinte.configure(
            state="normal" if self.pagina_actual < self.total_paginas - 1 else "disabled"
        )

        imagem, resultado = rasterizar(self.caminho, self.pagina_actual)

        if imagem is None:
            self.escala = 1.0
            self.tela.create_text(
                40, 40, anchor="nw", fill="#FFFFFF", width=700,
                text=str(resultado),
                font=("TkDefaultFont", 11),
            )
            self.tela.configure(scrollregion=(0, 0, 800, 600))
            self._desenhar_campos()
            return

        self.escala = resultado
        self.altura_pdf = imagem.height / self.escala

        try:
            from PIL import ImageTk

            # PT-PT: A referencia tem de ficar guardada no objecto. O Tk nao
            #        mantem referencia as imagens que desenha, e sem esta linha
            #        o recolector de lixo do Python leva a imagem uns
            #        milissegundos depois — o efeito visivel e uma tela em
            #        branco, sem erro nenhum.
            # EN-UK: The reference must be held on the object. Tk keeps no
            #        reference to the images it draws, and without this line
            #        Python's garbage collector takes it milliseconds later —
            #        the visible effect is a blank canvas with no error at all.
            self.imagem_tk = ImageTk.PhotoImage(imagem)
            self.tela.create_image(0, 0, anchor="nw", image=self.imagem_tk)
            self.tela.configure(scrollregion=(0, 0, imagem.width, imagem.height))
        except Exception as exc:  # noqa: BLE001
            log.error("Não foi possível mostrar a imagem: %s", exc)
            self.tela.create_text(40, 40, anchor="nw", fill="#FFFFFF", text=str(exc))

        self._desenhar_campos()

    def _desenhar_campos(self) -> None:
        """PT-PT: Desenha os campos da pagina. / EN-UK: Draws the page's fields."""
        self.tela.delete("campo")

        for campo in self.campos:
            if campo.pagina != self.pagina_actual:
                continue

            x0, y0, x1, y1 = self._para_tela(campo)
            escolhido = campo is self.seleccionado

            if escolhido:
                cor = theme.EDITOR_SELECCIONADO
            elif campo.tipo is TipoCampo.CAIXA:
                cor = theme.EDITOR_CAIXA
            else:
                cor = theme.EDITOR_CAMPO

            self.tela.create_rectangle(
                x0, y0, x1, y1,
                outline=cor, width=2 if escolhido else 1,
                fill=cor, stipple="gray12",
                tags=("campo", f"c{id(campo)}"),
            )

            if campo.altura * self.escala >= 11:
                self.tela.create_text(
                    x0 + 3, y0 + 2, anchor="nw", text=campo.nome, fill=cor,
                    font=("TkDefaultFont", 7), tags=("campo",),
                )

            if escolhido:
                for cx, cy in self._pegas(x0, y0, x1, y1).values():
                    self.tela.create_rectangle(
                        cx - PEGA / 2, cy - PEGA / 2, cx + PEGA / 2, cy + PEGA / 2,
                        outline=cor, fill="#FFFFFF", tags=("campo",),
                    )

    @staticmethod
    def _pegas(x0: float, y0: float, x1: float, y1: float) -> dict[str, tuple[float, float]]:
        """PT-PT: Posicao das oito pegas. / EN-UK: The eight handles' positions."""
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        return {
            "nw": (x0, y0), "n": (mx, y0), "ne": (x1, y0),
            "w": (x0, my), "e": (x1, my),
            "sw": (x0, y1), "s": (mx, y1), "se": (x1, y1),
        }

    # ------------------------------------------------------------------
    # PT-PT: Interaccao / EN-UK: Interaction
    # ------------------------------------------------------------------

    def _coordenadas(self, evento) -> tuple[float, float]:
        """
        PT-PT: Coordenadas do evento na tela, ja com o deslocamento aplicado.

               O `canvasx` e obrigatorio: sem ele, os cliques ficam certos no
               topo da pagina e cada vez mais desalinhados a medida que se
               desce, porque o evento traz a posicao na janela e nao na tela.

        EN-UK: The event's canvas coordinates, with scrolling applied. `canvasx`
               is mandatory: without it clicks are right at the top of the page
               and drift further off the further down you scroll.
        """
        return self.tela.canvasx(evento.x), self.tela.canvasy(evento.y)

    def _campo_em(self, x: float, y: float) -> Campo | None:
        """PT-PT: Campo debaixo do ponto. / EN-UK: The field under the point."""
        # PT-PT: Ao contrario, para o campo desenhado por cima ganhar o clique.
        # EN-UK: Reversed, so the field drawn on top wins the click.
        for campo in reversed(self.campos):
            if campo.pagina != self.pagina_actual:
                continue
            x0, y0, x1, y1 = self._para_tela(campo)
            if x0 <= x <= x1 and y0 <= y <= y1:
                return campo
        return None

    def _pega_em(self, x: float, y: float) -> str:
        """PT-PT: Pega debaixo do ponto. / EN-UK: The handle under the point."""
        if self.seleccionado is None:
            return ""
        x0, y0, x1, y1 = self._para_tela(self.seleccionado)
        for nome, (cx, cy) in self._pegas(x0, y0, x1, y1).items():
            if abs(x - cx) <= PEGA and abs(y - cy) <= PEGA:
                return nome
        return ""

    def _mover_rato(self, evento) -> None:
        """PT-PT: Muda o cursor conforme o que esta por baixo.
        EN-UK: Changes the cursor according to what is underneath."""
        x, y = self._coordenadas(evento)
        pega = self._pega_em(x, y)
        if pega:
            cursores = {
                "nw": "top_left_corner", "ne": "top_right_corner",
                "sw": "bottom_left_corner", "se": "bottom_right_corner",
                "n": "sb_v_double_arrow", "s": "sb_v_double_arrow",
                "w": "sb_h_double_arrow", "e": "sb_h_double_arrow",
            }
            self.tela.configure(cursor=cursores.get(pega, "fleur"))
        elif self._campo_em(x, y):
            self.tela.configure(cursor="fleur")
        else:
            self.tela.configure(cursor="crosshair")

    def _premir(self, evento) -> None:
        x, y = self._coordenadas(evento)
        self._arrasto_inicio = (x, y)

        pega = self._pega_em(x, y)
        if pega:
            self._modo = "redimensionar"
            self._pega_activa = pega
            return

        campo = self._campo_em(x, y)
        if campo is not None:
            self.seleccionar(campo)
            self._modo = "mover"
            x0, y0, _, _ = self._para_tela(campo)
            self._offset = (x - x0, y - y0)
            return

        self._limpar_seleccao()
        self._modo = "criar"

    def _arrastar(self, evento) -> None:
        if self._arrasto_inicio is None:
            return
        x, y = self._coordenadas(evento)
        inicio_x, inicio_y = self._arrasto_inicio

        if self._modo == "criar":
            if self._rectangulo_temporario:
                self.tela.delete(self._rectangulo_temporario)
            self._rectangulo_temporario = self.tela.create_rectangle(
                inicio_x, inicio_y, x, y,
                outline=theme.EDITOR_CAMPO, width=1, dash=(3, 2),
            )
            return

        if self.seleccionado is None:
            return

        x0, y0, x1, y1 = self._para_tela(self.seleccionado)

        if self._modo == "mover":
            largura, altura = x1 - x0, y1 - y0
            novo_x0 = x - self._offset[0]
            novo_y0 = y - self._offset[1]
            novas = (novo_x0, novo_y0, novo_x0 + largura, novo_y0 + altura)
        else:
            pega = self._pega_activa
            novas = [x0, y0, x1, y1]
            if "n" in pega:
                novas[1] = y
            if "s" in pega:
                novas[3] = y
            if "w" in pega:
                novas[0] = x
            if "e" in pega:
                novas[2] = x

        pdf = self._para_pdf(*novas)
        self.seleccionado.x0, self.seleccionado.y0 = pdf[0], pdf[1]
        self.seleccionado.x1, self.seleccionado.y1 = pdf[2], pdf[3]
        self.seleccionado.normalizar()
        self._desenhar_campos()

    def _largar(self, evento) -> None:
        if self._arrasto_inicio is None:
            return

        x, y = self._coordenadas(evento)
        inicio_x, inicio_y = self._arrasto_inicio
        self._arrasto_inicio = None

        if self._rectangulo_temporario:
            self.tela.delete(self._rectangulo_temporario)
            self._rectangulo_temporario = None

        if self._modo != "criar":
            self._modo = "criar"
            self._pega_activa = ""
            return

        if abs(x - inicio_x) < ARRASTO_MINIMO or abs(y - inicio_y) < ARRASTO_MINIMO:
            return

        pdf = self._para_pdf(min(inicio_x, x), min(inicio_y, y), max(inicio_x, x), max(inicio_y, y))
        etiqueta = self.cb_tipo.get()
        tipo = next((t for t in TipoCampo if t.etiqueta == etiqueta), TipoCampo.TEXTO)

        usados = {c.nome for c in self.campos}
        campo = Campo(
            nome=nome_seguro_campo(f"campo_p{self.pagina_actual + 1}", usados),
            pagina=self.pagina_actual,
            x0=pdf[0], y0=pdf[1], x1=pdf[2], y1=pdf[3],
            tipo=tipo,
            origem=Origem.MANUAL,
            confianca=1.0,
        )
        campo.normalizar()
        self.campos.append(campo)
        self.seleccionar(campo)

    # ------------------------------------------------------------------
    # PT-PT: Seleccao e edicao / EN-UK: Selection and editing
    # ------------------------------------------------------------------

    def seleccionar(self, campo: Campo) -> None:
        self.seleccionado = campo
        self.entrada_nome.delete(0, "end")
        self.entrada_nome.insert(0, campo.nome)
        self.entrada_etiqueta.delete(0, "end")
        self.entrada_etiqueta.insert(0, campo.etiqueta)
        self.cb_tipo_seleccionado.set(campo.tipo.etiqueta)
        self.var_obrigatorio.set(campo.obrigatorio)
        self._desenhar_campos()

    def _limpar_seleccao(self) -> None:
        self.seleccionado = None
        self.entrada_nome.delete(0, "end")
        self.entrada_etiqueta.delete(0, "end")
        self._desenhar_campos()

    def _actualizar_nome(self, _evento=None) -> None:
        if self.seleccionado is None:
            return
        bruto = self.entrada_nome.get().strip()
        if not bruto:
            return
        # PT-PT: O nome e normalizado a medida que se escreve, mas sem o
        #        contador de duplicados: acrescentar «_2» enquanto a pessoa
        #        ainda esta a escrever seria enlouquecedor. A verificacao de
        #        duplicados fica para o momento de gravar.
        # EN-UK: The name is normalised as it is typed, but without the
        #        duplicate counter: appending "_2" mid-typing would be maddening.
        self.seleccionado.nome = nome_seguro_campo(bruto, set())
        self._desenhar_campos()

    def _actualizar_etiqueta(self, _evento=None) -> None:
        if self.seleccionado is not None:
            self.seleccionado.etiqueta = self.entrada_etiqueta.get()

    def _actualizar_tipo(self, escolha: str) -> None:
        if self.seleccionado is None:
            return
        self.seleccionado.tipo = next(
            (t for t in TipoCampo if t.etiqueta == escolha), TipoCampo.TEXTO
        )
        self._desenhar_campos()

    def _actualizar_obrigatorio(self) -> None:
        if self.seleccionado is not None:
            self.seleccionado.obrigatorio = bool(self.var_obrigatorio.get())

    def apagar_seleccionado(self) -> None:
        if self.seleccionado is None:
            return
        self.campos.remove(self.seleccionado)
        self._limpar_seleccao()

    def mudar_pagina(self, direccao: int) -> None:
        nova = self.pagina_actual + direccao
        if not 0 <= nova < self.total_paginas:
            return
        self.pagina_actual = nova
        self.seleccionado = None
        self.carregar_pagina()

    def concluir(self) -> None:
        """
        PT-PT: Resolve nomes duplicados e devolve os campos.

               A resolucao acontece aqui e nao a medida que se escreve porque
               dois campos com o mesmo nome num AcroForm nao sao dois campos:
               sao o mesmo campo em dois sitios, e escrever num escreve no
               outro. Num formulario com «Nome» em tres paginas, e um bug que
               so aparece depois de alguem o preencher.

        EN-UK: Resolves duplicate names and hands the fields back. Two fields
               with the same name in an AcroForm are not two fields: they are
               one field in two places.
        """
        usados: set[str] = set()
        for campo in self.campos:
            campo.nome = nome_seguro_campo(campo.nome or campo.etiqueta or "campo", usados)
        self.ao_gravar(self.campos)
        self.destroy()
