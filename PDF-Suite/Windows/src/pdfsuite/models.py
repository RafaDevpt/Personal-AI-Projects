"""
PT-PT: Estruturas de dados partilhadas pelos dois modulos.
       Sem dependencias de GUI, de PDF ou de rede — e o que torna a logica
       testavel sem abrir um ficheiro sequer.

EN-UK: Data structures shared by both modules. No GUI, PDF or network
       dependencies — which is what makes the logic testable without opening a
       single file.

Created by Redfox using Claude
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class TipoCampo(Enum):
    """
    PT-PT: Tipos de campo que sabemos escrever num AcroForm.

           Deliberadamente poucos. Cada tipo extra e mais uma forma de o
           formulario abrir mal num leitor de PDF menos comum, e a maioria dos
           formularios em papel de uma empresa e feita de caixas de texto,
           caixas de seleccao e uma assinatura no fim.

    EN-UK: Field types we know how to write into an AcroForm. Deliberately few:
           each extra type is another way for the form to open badly in a less
           common PDF reader, and most paper forms in a company are made of
           text boxes, tick boxes and a signature at the end.
    """

    TEXTO = "texto"
    MULTILINHA = "multilinha"
    CAIXA = "caixa"
    DATA = "data"
    ESCOLHA = "escolha"
    ASSINATURA = "assinatura"

    @property
    def etiqueta(self) -> str:
        """PT-PT: Nome para a interface. / EN-UK: Name for the interface."""
        return {
            TipoCampo.TEXTO: "Texto",
            TipoCampo.MULTILINHA: "Texto (várias linhas)",
            TipoCampo.CAIXA: "Caixa de selecção",
            TipoCampo.DATA: "Data",
            TipoCampo.ESCOLHA: "Lista de opções",
            TipoCampo.ASSINATURA: "Assinatura",
        }[self]


class Origem(Enum):
    """
    PT-PT: Como o campo foi encontrado. Guardado porque a confianca a dar a
           cada deteccao nao e a mesma: uma linha desenhada e um sinal muito
           mais fiavel do que um espaco em branco depois de dois pontos.
    EN-UK: How the field was found. Kept because the confidence each detection
           deserves differs: a drawn line is a far more reliable signal than
           blank space after a colon.
    """

    SUBLINHADO = "sublinhado"
    LINHA = "linha"
    RECTANGULO = "rectângulo"
    QUADRADO = "quadrado"
    DOIS_PONTOS = "dois pontos"
    MANUAL = "manual"
    EXISTENTE = "existente"


@dataclass(slots=True)
class Campo:
    """
    PT-PT: Um campo de formulario, em coordenadas PDF.

           As coordenadas seguem a convencao do PDF: origem no canto inferior
           esquerdo, unidade em pontos (1/72 de polegada). E diferente da
           convencao do pdfplumber, que conta de cima para baixo — a conversao
           faz-se uma unica vez, no detector, e nao anda espalhada pelo codigo.
           Misturar as duas convencoes e o erro classico neste tipo de
           ferramenta e produz campos correctos na horizontal e invertidos na
           vertical.

    EN-UK: A form field, in PDF coordinates: origin at the bottom-left, units
           in points. That differs from pdfplumber's convention, which counts
           from the top — the conversion happens once, in the detector, and is
           not scattered through the code. Mixing the two is the classic bug in
           a tool like this: fields right horizontally and upside down
           vertically.
    """

    nome: str
    pagina: int
    x0: float
    y0: float
    x1: float
    y1: float
    tipo: TipoCampo = TipoCampo.TEXTO
    origem: Origem = Origem.MANUAL
    etiqueta: str = ""
    obrigatorio: bool = False
    opcoes: tuple[str, ...] = ()
    #: PT-PT: 0 a 1. Abaixo de 0,5 a interface assinala para revisao.
    #: EN-UK: 0 to 1. Below 0.5 the interface flags it for review.
    confianca: float = 1.0

    @property
    def largura(self) -> float:
        return self.x1 - self.x0

    @property
    def altura(self) -> float:
        return self.y1 - self.y0

    def valido(self) -> bool:
        """
        PT-PT: Um campo com area nula ou negativa nao e escrevivel. Acontece
               quando a deteccao encontra uma linha de comprimento zero ou
               quando o utilizador arrasta um rectangulo ao contrario no editor.
        EN-UK: A field with zero or negative area cannot be written. It happens
               when detection finds a zero-length line, or when the user drags a
               rectangle backwards in the editor.
        """
        return self.largura >= 4 and self.altura >= 4

    def normalizar(self) -> None:
        """
        PT-PT: Garante x0<x1 e y0<y1, trocando se preciso.
        EN-UK: Ensures x0<x1 and y0<y1, swapping when needed.
        """
        if self.x0 > self.x1:
            self.x0, self.x1 = self.x1, self.x0
        if self.y0 > self.y1:
            self.y0, self.y1 = self.y1, self.y0


def nome_seguro_campo(bruto: str, usados: set[str]) -> str:
    """
    PT-PT: Converte uma etiqueta num nome de campo utilizavel e unico.

           Os nomes de campo de um AcroForm sao o que aparece na exportacao
           para FDF e o que qualquer automatismo posterior vai usar como chave.
           Espacos e acentos funcionam na maioria dos leitores, mas partem
           assim que alguem tente ler o formulario com um script — e a razao de
           serem normalizados aqui.

           O ponto e reservado: no PDF separa campo de campo-pai numa
           hierarquia, portanto «Data.Nascimento» criaria uma arvore em vez de
           um campo chamado assim.

    EN-UK: Turns a label into a usable, unique field name. AcroForm field names
           are what appears in an FDF export and what any later automation uses
           as a key. Spaces and accents work in most readers but break the
           moment anyone reads the form with a script.

           The full stop is reserved: in a PDF it separates a field from its
           parent in a hierarchy, so "Date.Birth" would build a tree rather
           than a field of that name.
    """
    texto = (bruto or "campo").strip().lower()

    acentos = str.maketrans(
        "áàâãäéèêëíìîïóòôõöúùûüçñ", "aaaaaeeeeiiiiooooouuuucn"
    )
    texto = texto.translate(acentos)
    texto = re.sub(r"[^a-z0-9]+", "_", texto).strip("_")
    texto = texto[:40] or "campo"

    if texto not in usados:
        usados.add(texto)
        return texto

    # PT-PT: Dois campos com o mesmo nome num AcroForm nao sao dois campos: sao
    #        o mesmo campo em dois sitios, e escrever num escreve no outro. Num
    #        formulario com «Nome» em tres paginas, isso e um bug que so aparece
    #        depois de alguem o preencher.
    # EN-UK: Two fields with the same name in an AcroForm are not two fields:
    #        they are one field in two places, and typing in one types in the
    #        other. On a form with "Name" on three pages, that is a bug that
    #        only shows up after somebody fills it in.
    contador = 2
    while f"{texto}_{contador}" in usados:
        contador += 1
    nome = f"{texto}_{contador}"
    usados.add(nome)
    return nome


@dataclass(slots=True)
class Documento:
    """
    PT-PT: Um documento lido, com o texto ja extraido.
    EN-UK: A document that has been read, with the text already extracted.
    """

    caminho: Path
    texto: str = ""
    paginas: int = 0
    formato: str = ""
    #: PT-PT: PDF digitalizado sem camada de texto. Distinguir isto de um PDF
    #:        vazio importa: um diz «preciso de OCR», o outro diz «o ficheiro
    #:        nao tem nada». A v anterior devolvia string vazia nos dois casos.
    #: EN-UK: A scanned PDF with no text layer. Telling this apart from an empty
    #:        PDF matters: one says "needs OCR", the other says "the file has
    #:        nothing in it".
    digitalizado: bool = False
    erro: str = ""

    @property
    def nome(self) -> str:
        return self.caminho.name

    @property
    def rotulo(self) -> str:
        """PT-PT: Nome sem extensao, para tabelas. / EN-UK: Stem, for tables."""
        return self.caminho.stem

    @property
    def ok(self) -> bool:
        return not self.erro and bool(self.texto.strip())

    @property
    def palavras(self) -> int:
        return len(self.texto.split())


@dataclass(slots=True)
class Valor:
    """
    PT-PT: Um valor extraido de um documento, com o contexto onde foi
           encontrado.

           O contexto nao e decorativo. A extracao automatica erra, e quando
           erra o utilizador precisa de ver a frase original para perceber
           porque — sem isso, o unico caminho e abrir o PDF e procurar a olho,
           que e exactamente o trabalho que esta ferramenta devia poupar.

    EN-UK: A value extracted from a document, with the context it was found in.
           The context is not decorative: automatic extraction gets things
           wrong, and when it does the user needs the original sentence to see
           why.
    """

    valor: float | str | None = None
    bruto: str = ""
    contexto: str = ""
    confianca: float = 0.0
    #: PT-PT: True quando foi o utilizador a escrever o valor na tabela.
    #: EN-UK: True when the user typed the value into the table.
    confirmado: bool = False

    @property
    def conhecido(self) -> bool:
        return self.valor is not None


@dataclass(slots=True)
class Proposta:
    """
    PT-PT: Uma proposta de fornecedor, com os sinais extraidos do documento.

           Todos os campos sao `Valor`, e todos podem ser desconhecidos. Uma
           proposta sem prazo de garantia declarado nao vale zero em garantia:
           vale «nao diz», que e informacao diferente e tem de aparecer como
           tal no relatorio.

    EN-UK: A vendor proposal, with the signals extracted from the document.
           Every field is a `Valor` and every one may be unknown. A proposal
           with no stated warranty is not worth zero on warranty: it is worth
           "not stated", which is different information and has to appear as
           such in the report.
    """

    documento: Documento
    fornecedor: Valor = field(default_factory=Valor)
    total: Valor = field(default_factory=Valor)
    moeda: str = ""
    #: PT-PT: True se o total ja inclui IVA, False se acresce, None se nao diz.
    #: EN-UK: True if the total already includes VAT, False if it is added,
    #:        None if the document does not say.
    iva_incluido: bool | None = None
    taxa_iva: Valor = field(default_factory=Valor)
    prazo_pagamento: Valor = field(default_factory=Valor)
    prazo_entrega: Valor = field(default_factory=Valor)
    garantia_meses: Valor = field(default_factory=Valor)
    validade: Valor = field(default_factory=Valor)
    referencia: Valor = field(default_factory=Valor)
    #: PT-PT: Notas geradas pela analise — avisos, ambiguidades, coisas a
    #:        confirmar antes de decidir.
    #: EN-UK: Notes produced by the analysis — warnings and ambiguities.
    notas: list[str] = field(default_factory=list)

    @property
    def rotulo(self) -> str:
        """
        PT-PT: Nome a mostrar: o fornecedor se foi identificado, senao o nome
               do ficheiro. Numa comparacao de seis propostas, «Proposta_2.pdf»
               nao ajuda ninguem a decidir.
        EN-UK: Name to display: the vendor if identified, otherwise the file
               name. In a six-way comparison, "Quote_2.pdf" helps nobody decide.
        """
        if isinstance(self.fornecedor.valor, str) and self.fornecedor.valor.strip():
            return self.fornecedor.valor.strip()
        return self.documento.rotulo

    def total_com_iva(self, taxa_omissao: float = 23.0) -> float | None:
        """
        PT-PT: Total com IVA, para os totais serem comparaveis entre si.

               E o calculo mais importante do modulo e a armadilha classica
               destas comparacoes: uma proposta a 10.000 EUR com IVA incluido e
               mais barata do que uma a 9.000 EUR mais IVA, e quem compara os
               numeros da capa escolhe a errada. Quando o documento nao diz, a
               proposta e marcada e o relatorio avisa em vez de adivinhar.

        EN-UK: Total including VAT, so totals become comparable. This is the
               most important calculation here and the classic trap: a quote at
               EUR 10,000 including VAT is cheaper than one at EUR 9,000 plus
               VAT, and whoever compares the cover figures picks the wrong one.
               When the document does not say, the proposal is flagged and the
               report warns rather than guessing.
        """
        if not isinstance(self.total.valor, (int, float)):
            return None
        base = float(self.total.valor)
        if self.iva_incluido is True:
            return base
        taxa = (
            float(self.taxa_iva.valor)
            if isinstance(self.taxa_iva.valor, (int, float))
            else taxa_omissao
        )
        return base * (1 + taxa / 100)


@dataclass(slots=True)
class Criterio:
    """
    PT-PT: Um criterio da matriz de decisao.

    EN-UK: One criterion of the decision matrix.

    :param maior_melhor:
        PT-PT: True quando mais e melhor (garantia); False quando menos e
               melhor (preco, prazo de entrega).
        EN-UK: True when more is better (warranty); False when less is better
               (price, delivery time).
    """

    chave: str
    etiqueta: str
    peso: float
    maior_melhor: bool
    unidade: str = ""

    def __post_init__(self) -> None:
        self.peso = max(0.0, float(self.peso))


@dataclass(slots=True)
class Pontuacao:
    """PT-PT: Pontuacao de uma proposta. / EN-UK: One proposal's score."""

    proposta: Proposta
    total: float = 0.0
    por_criterio: dict[str, float] = field(default_factory=dict)
    valores: dict[str, float | None] = field(default_factory=dict)
    #: PT-PT: Criterios em que o documento nao diz nada.
    #: EN-UK: Criteria on which the document says nothing.
    em_falta: list[str] = field(default_factory=list)

    @property
    def completude(self) -> float:
        """
        PT-PT: Percentagem de criterios com valor conhecido. Uma proposta que
               ganha por ter dados em dois criterios e falhar quatro nao ganhou
               nada, e isto e o numero que torna isso visivel.
        EN-UK: Percentage of criteria with a known value. A proposal that wins
               on two criteria while missing four has not won anything, and this
               is the number that makes that visible.
        """
        total = len(self.valores)
        if not total:
            return 0.0
        conhecidos = sum(1 for v in self.valores.values() if v is not None)
        return conhecidos / total * 100


@dataclass(slots=True)
class Comparacao:
    """PT-PT: Resultado completo de uma comparacao. / EN-UK: A full comparison."""

    pontuacoes: list[Pontuacao]
    criterios: list[Criterio]
    gerado: dt.datetime = field(default_factory=dt.datetime.now)
    avisos: list[str] = field(default_factory=list)
    taxa_iva_omissao: float = 23.0

    @property
    def vencedora(self) -> Pontuacao | None:
        if not self.pontuacoes:
            return None
        return max(self.pontuacoes, key=lambda p: p.total)

    @property
    def ordenadas(self) -> list[Pontuacao]:
        return sorted(self.pontuacoes, key=lambda p: -p.total)

    @property
    def decisao_segura(self) -> bool:
        """
        PT-PT: A diferenca entre o primeiro e o segundo justifica a escolha?

               Cinco pontos numa escala de cem estao dentro da margem de erro
               de uma extracao automatica. Dizer «A vence» quando A e B estao
               empatados e pior do que nao dizer nada, porque da a uma
               estimativa a aparencia de um facto.

        EN-UK: Does the gap between first and second justify the choice? Five
               points on a hundred-point scale sit inside the error margin of
               automatic extraction. Saying "A wins" when A and B are level is
               worse than saying nothing, because it lends a guess the look of
               a fact.
        """
        ordem = self.ordenadas
        if len(ordem) < 2:
            return bool(ordem)
        return (ordem[0].total - ordem[1].total) >= 5.0


@dataclass(slots=True)
class Resumo:
    """PT-PT: Resumo de um documento. / EN-UK: A document summary."""

    documento: Documento
    frases: list[str] = field(default_factory=list)
    palavras_chave: list[tuple[str, int]] = field(default_factory=list)
    numeros: list[str] = field(default_factory=list)
    datas: list[str] = field(default_factory=list)
    #: PT-PT: Texto devolvido pelo modelo, quando a analise assistida e usada.
    #: EN-UK: Text returned by the model, when assisted analysis is used.
    texto_ia: str = ""

    @property
    def texto(self) -> str:
        return " ".join(self.frases)
