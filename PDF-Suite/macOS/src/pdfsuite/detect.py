"""
PT-PT: Detecção de campos num PDF estático.

       O problema: um formulário em papel digitalizado ou exportado do Word não
       tem campos nenhuns — tem traços, quadrados e espaço em branco desenhados
       na página. Este módulo olha para esses desenhos e adivinha onde as
       pessoas escreveriam.

       Adivinhar e a palavra certa e o desenho da ferramenta assume-o: cada
       campo detectado traz uma confiança, e a interface põe o utilizador a
       rever antes de gravar. Uma detecção automática que grave sem revisão
       produz formulários com campos a mais, a menos e no sítio errado, e o
       utilizador acaba a fazer o trabalho todo a mão — com o agravante de ter
       primeiro de apagar o que a ferramenta inventou.

EN-UK: Field detection in a static PDF.

       The problem: a scanned or Word-exported paper form has no fields at all
       — it has rules, boxes and white space drawn on the page. This module
       looks at those drawings and guesses where people would write.

       Guess is the right word and the design admits it: every detected field
       carries a confidence, and the interface puts the user in front of them
       before saving.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
import re

from .models import Campo, Origem, TipoCampo, nome_seguro_campo

log = logging.getLogger(__name__)

# PT-PT: Limites em pontos PDF (1 ponto = 1/72 de polegada).
# EN-UK: Limits in PDF points (1 point = 1/72 inch).
LARGURA_MINIMA_LINHA = 35.0
LARGURA_MAXIMA_LINHA = 520.0
ESPESSURA_MAXIMA_LINHA = 3.0
ALTURA_CAMPO = 16.0
FOLGA_ACIMA_DA_LINHA = 2.0

LADO_MINIMO_QUADRADO = 6.0
LADO_MAXIMO_QUADRADO = 22.0
TOLERANCIA_QUADRADO = 0.35

# PT-PT: Um rectângulo maior do que isto é uma caixa de texto de várias linhas
#        («Observacoes»), não um campo de uma linha.
# EN-UK: A rectangle taller than this is a multi-line text box, not a one-line
#        field.
ALTURA_MULTILINHA = 40.0

# PT-PT: Distância máxima entre uma linha e a etiqueta a sua esquerda. Acima
#        disto, a etiqueta pertence a outra coisa qualquer da mesma linha.
# EN-UK: Maximum distance between a rule and the label to its left. Beyond
#        this, the label belongs to something else on the same row.
DISTANCIA_MAXIMA_ETIQUETA = 260.0

# PT-PT: Palavras que aparecem antes de um espaço em branco mas nunca são um
#        campo. Sem esta lista, os cabeçalhos e os rodapes de qualquer
#        formulário transformavam-se em caixas de texto.
# EN-UK: Words appearing before white space that are never a field. Without
#        this list, headers and footers turned into text boxes.
NAO_SAO_CAMPOS: frozenset[str] = frozenset(
    {
        "pagina", "página", "page", "de", "of", "total", "subtotal",
        "nota", "notas", "note", "notes", "obs", "anexo", "anexos",
        "www", "http", "https", "tel", "fax", "email", "e-mail",
        "capitulo", "capítulo", "artigo", "secao", "secção", "ponto",
    }
)

# PT-PT: Etiquetas que indicam o tipo do campo. A detecção do tipo vale a pena
#        porque muda o comportamento no leitor: um campo de data com formato
#        definido evita que cada pessoa escreva a data a sua maneira, e uma
#        caixa de selecção e infinitamente mais rápida de preencher do que
#        escrever «sim».
# EN-UK: Labels indicating the field type. Type detection is worth doing
#        because it changes behaviour in the reader.
PISTAS_DATA: tuple[str, ...] = (
    "data", "date", "dia", "nascimento", "validade", "inicio", "início",
    "fim", "prazo", "desde", "ate", "até", "emissao", "emissão",
)
PISTAS_ASSINATURA: tuple[str, ...] = (
    "assinatura", "signature", "assinado", "rubrica", "visto", "aprovado por",
)
PISTAS_MULTILINHA: tuple[str, ...] = (
    "observacoes", "observações", "comentarios", "comentários", "descricao",
    "descrição", "notas", "remarks", "comments", "justificacao", "justificação",
    "motivo", "detalhe", "detalhes", "morada", "address",
)


def _tipo_pela_etiqueta(etiqueta: str, altura: float) -> TipoCampo:
    """
    PT-PT: Deduz o tipo de campo a partir da etiqueta e da altura da caixa.
    EN-UK: Infers the field type from the label and the box height.
    """
    minusculas = etiqueta.lower()

    if any(p in minusculas for p in PISTAS_ASSINATURA):
        return TipoCampo.ASSINATURA
    if any(p in minusculas for p in PISTAS_DATA):
        return TipoCampo.DATA
    if altura >= ALTURA_MULTILINHA:
        return TipoCampo.MULTILINHA
    if any(p in minusculas for p in PISTAS_MULTILINHA):
        return TipoCampo.MULTILINHA
    return TipoCampo.TEXTO


def _etiqueta_util(texto: str) -> bool:
    """
    PT-PT: A etiqueta serve para nomear um campo?
    EN-UK: Is the label usable as a field name?
    """
    limpo = texto.strip().strip(":.-–—").strip()
    if len(limpo) < 2 or len(limpo) > 60:
        return False
    if limpo.lower() in NAO_SAO_CAMPOS:
        return False
    # PT-PT: Uma etiqueta sem letras e um número de página ou um traço.
    # EN-UK: A label with no letters is a page number or a rule.
    return bool(re.search(r"[A-Za-zÀ-ÿ]", limpo))


def _limpar_etiqueta(bruto: str) -> str:
    """
    PT-PT: Tira de uma etiqueta o que não é etiqueta.

           O caso que motivou isto: numa linha com dois campos —
           `Email: ______  Extensão: ____` — a etiqueta do segundo campo vinha
           com a corrida de sublinhados do primeiro colada à frente. O nome do
           campo saía com trinta caracteres de lixo antes da palavra útil.

    EN-UK: Strips from a label what is not the label. The case behind this: on a
           row with two fields, the second field's label arrived with the first
           field's run of underscores stuck to the front.
    """
    texto = re.sub(r"[_\u2014\u2013.]{3,}", " ", bruto or "")
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip().strip(":.-–—").strip()


def _etiqueta_a_esquerda(palavras: list[dict], x0: float, topo: float, base: float) -> str:
    """
    PT-PT: Procura o texto imediatamente a esquerda de uma caixa.

           Junta as palavras que estejam a mesma altura, dentro da distância
           máxima, e devolve as últimas — «Nome do requerente:» dá «Nome do
           requerente», não só «requerente».

    EN-UK: Looks for the text immediately to the left of a box. Joins words at
           the same height within the maximum distance and returns the last of
           them.
    """
    centro = (topo + base) / 2
    candidatas = [
        p
        for p in palavras
        if p["x1"] <= x0 + 2
        and x0 - p["x1"] <= DISTANCIA_MAXIMA_ETIQUETA
        and p["top"] - 4 <= centro <= p["bottom"] + 4
    ]
    if not candidatas:
        return ""

    candidatas.sort(key=lambda p: p["x0"])
    # PT-PT: Cortar nos dois pontos: em «Departamento: Nome:» o que interessa
    #        para o segundo campo e «Nome», não a linha inteira.
    # EN-UK: Cut at the colon: in "Department: Name:" the second field wants
    #        "Name", not the whole row.
    texto = " ".join(p["text"] for p in candidatas[-8:])
    if ":" in texto[:-1]:
        texto = texto.rsplit(":", 1)[-1] if texto.rstrip().endswith(":") else texto.split(":")[-1]
    return _limpar_etiqueta(texto)


def _etiqueta_abaixo(palavras: list[dict], x0: float, x1: float, base: float) -> str:
    """
    PT-PT: Etiqueta por baixo da caixa.

           E a convenção das assinaturas: desenha-se a linha e escreve-se por
           baixo, em letra pequena, «Assinatura do colaborador». Sem esta
           procura, todas as linhas de assinatura de todos os formulários
           ficavam sem nome — e a assinatura e precisamente o campo que mais
           importa identificar bem, porque num formulário com duas há sempre
           duas pessoas diferentes a assinar.

    EN-UK: Label underneath the box. This is the signature convention: draw the
           rule and write "Employee signature" below it in small type. Without
           this search, every signature line on every form came out unnamed.
    """
    candidatas = [
        p
        for p in palavras
        if 0 < p["top"] - base <= 16 and p["x1"] > x0 - 10 and p["x0"] < x1 + 10
    ]
    if not candidatas:
        return ""
    candidatas.sort(key=lambda p: p["x0"])
    return _limpar_etiqueta(" ".join(p["text"] for p in candidatas[:8]))


def _etiqueta_acima(palavras: list[dict], x0: float, x1: float, topo: float) -> str:
    """
    PT-PT: Etiqueta por cima da caixa, para os formulários que rotulam assim.
    EN-UK: Label above the box, for forms that label that way.
    """
    candidatas = [
        p
        for p in palavras
        if 0 < topo - p["bottom"] <= 16 and p["x1"] > x0 - 10 and p["x0"] < x1 + 10
    ]
    if not candidatas:
        return ""
    candidatas.sort(key=lambda p: p["x0"])
    return _limpar_etiqueta(" ".join(p["text"] for p in candidatas[:8]))


def _sobrepoe(a: Campo, b: Campo, tolerancia: float = 6.0) -> bool:
    """
    PT-PT: Duas caixas ocupam o mesmo sítio?

           Necessario porque as estratégias de detecção encontram a mesma coisa
           por caminhos diferentes: um campo desenhado como rectângulo tem
           quatro linhas, e o detector de linhas vê nele um campo por cada
           lado. Sem esta verificação, um formulário com molduras ficava com
           quatro campos sobrepostos em cada caixa.

    EN-UK: Do two boxes occupy the same place? Needed because the strategies
           find the same thing by different routes: a field drawn as a
           rectangle has four sides, and the line detector sees a field on each.
    """
    return not (
        a.x1 < b.x0 + tolerancia
        or b.x1 < a.x0 + tolerancia
        or a.y1 < b.y0 + tolerancia
        or b.y1 < a.y0 + tolerancia
    )


def _de_sublinhados(pagina, palavras: list[dict], altura_pagina: float) -> list[Campo]:
    """
    PT-PT: Campos escritos como corridas de sublinhados: `Nome: ______`.

           E o sinal mais fiável de todos, porque quem escreveu o documento
           pôs ali os sublinhados exactamente com a intenção de que alguém
           escrevesse por cima.

    EN-UK: Fields written as runs of underscores. The most reliable signal of
           all, because whoever wrote the document put them there precisely so
           that somebody would write on top.
    """
    campos: list[Campo] = []

    for palavra in palavras:
        texto = palavra["text"]
        if len(texto) < 3 or not re.fullmatch(r"[_\u2014\u2013.]{3,}", texto):
            continue
        # PT-PT: Corridas de pontos são também indices («Capitulo 1 ....... 12»).
        #        Exigir que não haja número logo a seguir tira a maioria deles.
        # EN-UK: Dot runs are also tables of contents; requiring no number
        #        immediately after removes most of them.
        if set(texto) == {"."}:
            seguintes = [
                p for p in palavras
                if 0 < p["x0"] - palavra["x1"] < 40 and abs(p["top"] - palavra["top"]) < 4
            ]
            if any(s["text"].strip().isdigit() for s in seguintes):
                continue

        etiqueta = _etiqueta_a_esquerda(palavras, palavra["x0"], palavra["top"], palavra["bottom"])
        if not etiqueta:
            etiqueta = _etiqueta_acima(palavras, palavra["x0"], palavra["x1"], palavra["top"])

        # PT-PT: A conversão de coordenadas acontece aqui e só aqui. O
        #        pdfplumber conta de cima para baixo; o PDF conta de baixo para
        #        cima.
        # EN-UK: The coordinate conversion happens here and only here.
        y1 = altura_pagina - palavra["top"] + 2
        y0 = altura_pagina - palavra["bottom"] - 2

        campos.append(
            Campo(
                nome="",
                pagina=0,
                x0=palavra["x0"],
                y0=y0,
                x1=palavra["x1"],
                y1=max(y1, y0 + ALTURA_CAMPO),
                etiqueta=etiqueta,
                origem=Origem.SUBLINHADO,
                tipo=_tipo_pela_etiqueta(etiqueta, ALTURA_CAMPO),
                confianca=0.9 if etiqueta else 0.7,
            )
        )

    return campos


def _de_linhas(pagina, palavras: list[dict], altura_pagina: float) -> list[Campo]:
    """
    PT-PT: Campos escritos como linhas horizontais desenhadas.
    EN-UK: Fields drawn as horizontal rules.
    """
    campos: list[Campo] = []

    for linha in getattr(pagina, "lines", []) or []:
        largura = abs(linha.get("x1", 0) - linha.get("x0", 0))
        espessura = abs(linha.get("bottom", 0) - linha.get("top", 0))

        if not (LARGURA_MINIMA_LINHA <= largura <= LARGURA_MAXIMA_LINHA):
            continue
        if espessura > ESPESSURA_MAXIMA_LINHA:
            continue

        x0 = min(linha["x0"], linha["x1"])
        x1 = max(linha["x0"], linha["x1"])
        topo = min(linha["top"], linha["bottom"])

        etiqueta = _etiqueta_a_esquerda(palavras, x0, topo - 6, topo + 6)
        if not etiqueta:
            etiqueta = _etiqueta_acima(palavras, x0, x1, topo)
        if not etiqueta:
            etiqueta = _etiqueta_abaixo(palavras, x0, x1, topo)
        if etiqueta and not _etiqueta_util(etiqueta):
            etiqueta = ""

        # PT-PT: O campo fica por cima da linha, que é onde se escreve.
        # EN-UK: The field sits above the rule, which is where one writes.
        base = altura_pagina - topo + FOLGA_ACIMA_DA_LINHA

        campos.append(
            Campo(
                nome="",
                pagina=0,
                x0=x0,
                y0=base,
                x1=x1,
                y1=base + ALTURA_CAMPO,
                etiqueta=etiqueta,
                origem=Origem.LINHA,
                tipo=_tipo_pela_etiqueta(etiqueta, ALTURA_CAMPO),
                confianca=0.8 if etiqueta else 0.45,
            )
        )

    return campos


def _de_rectangulos(pagina, palavras: list[dict], altura_pagina: float) -> list[Campo]:
    """
    PT-PT: Caixas e quadrados desenhados.

           Um quadrado pequeno e uma caixa de selecção; um rectângulo largo e
           uma caixa de texto. A distinção pelo tamanho e grosseira mas
           funciona: não há formulários com caixas de selecção de cinco
           centímetros nem com campos de nome de meio centímetro.

    EN-UK: Drawn boxes and squares. A small square is a tick box; a wide
           rectangle is a text box. Distinguishing by size is crude but works.
    """
    campos: list[Campo] = []

    for rect in getattr(pagina, "rects", []) or []:
        largura = abs(rect.get("x1", 0) - rect.get("x0", 0))
        altura = abs(rect.get("bottom", 0) - rect.get("top", 0))

        if largura < 4 or altura < 4:
            continue

        x0 = min(rect["x0"], rect["x1"])
        x1 = max(rect["x0"], rect["x1"])
        topo = min(rect["top"], rect["bottom"])
        base = max(rect["top"], rect["bottom"])

        quadrado = (
            LADO_MINIMO_QUADRADO <= largura <= LADO_MAXIMO_QUADRADO
            and LADO_MINIMO_QUADRADO <= altura <= LADO_MAXIMO_QUADRADO
            and abs(largura - altura) <= max(largura, altura) * TOLERANCIA_QUADRADO
        )

        if quadrado:
            # PT-PT: Numa caixa de selecção a etiqueta esta a direita («☐ Sim»),
            #        ao contrário de todos os outros campos. E a excepção que
            #        justifica esta procura separada.
            # EN-UK: On a tick box the label is to the right, unlike every other
            #        field. That exception justifies this separate search.
            centro = (topo + base) / 2
            direita = [
                p for p in palavras
                if 0 <= p["x0"] - x1 <= 90 and p["top"] - 4 <= centro <= p["bottom"] + 4
            ]
            direita.sort(key=lambda p: p["x0"])
            etiqueta = " ".join(p["text"] for p in direita[:4]).strip()
            if not etiqueta:
                etiqueta = _etiqueta_a_esquerda(palavras, x0, topo, base)

            campos.append(
                Campo(
                    nome="",
                    pagina=0,
                    x0=x0,
                    y0=altura_pagina - base,
                    x1=x1,
                    y1=altura_pagina - topo,
                    etiqueta=etiqueta,
                    origem=Origem.QUADRADO,
                    tipo=TipoCampo.CAIXA,
                    confianca=0.85 if etiqueta else 0.6,
                )
            )
            continue

        if largura < LARGURA_MINIMA_LINHA or altura > 160:
            continue

        etiqueta = _etiqueta_a_esquerda(palavras, x0, topo, base)
        if not etiqueta:
            etiqueta = _etiqueta_acima(palavras, x0, x1, topo)
        if etiqueta and not _etiqueta_util(etiqueta):
            etiqueta = ""

        campos.append(
            Campo(
                nome="",
                pagina=0,
                x0=x0 + 1,
                y0=altura_pagina - base + 1,
                x1=x1 - 1,
                y1=altura_pagina - topo - 1,
                etiqueta=etiqueta,
                origem=Origem.RECTANGULO,
                tipo=_tipo_pela_etiqueta(etiqueta, altura),
                confianca=0.7 if etiqueta else 0.4,
            )
        )

    return campos


def _de_dois_pontos(palavras: list[dict], altura_pagina: float, largura_pagina: float) -> list[Campo]:
    """
    PT-PT: Etiquetas terminadas em dois pontos seguidas de espaço em branco.

           E a estratégia menos fiável das quatro e a confiança reflecte-o. Um
           documento em prosa esta cheio de dois pontos que não são campo
           nenhum. Só se aplica quando há espaço livre suficiente a direita e
           nada escrito la — e mesmo assim o utilizador vai ver alguns a mais.

    EN-UK: Labels ending in a colon followed by white space. The least reliable
           of the four strategies and the confidence says so.
    """
    campos: list[Campo] = []

    for indice, palavra in enumerate(palavras):
        if not palavra["text"].rstrip().endswith(":"):
            continue

        etiqueta = palavra["text"].rstrip(":").strip()
        if not etiqueta:
            # PT-PT: Dois pontos isolados: a etiqueta e a palavra anterior.
            # EN-UK: A lone colon: the label is the previous word.
            if indice == 0:
                continue
            etiqueta = palavras[indice - 1]["text"]
        if not _etiqueta_util(etiqueta):
            continue

        centro = (palavra["top"] + palavra["bottom"]) / 2
        seguinte = [
            p for p in palavras
            if p["x0"] > palavra["x1"] and p["top"] - 4 <= centro <= p["bottom"] + 4
        ]
        limite = min((p["x0"] for p in seguinte), default=largura_pagina - 50)

        largura = limite - palavra["x1"] - 6
        if largura < 60:
            continue

        campos.append(
            Campo(
                nome="",
                pagina=0,
                x0=palavra["x1"] + 6,
                y0=altura_pagina - palavra["bottom"] - 2,
                x1=palavra["x1"] + 6 + min(largura, 300),
                y1=altura_pagina - palavra["top"] + 3,
                etiqueta=etiqueta,
                origem=Origem.DOIS_PONTOS,
                tipo=_tipo_pela_etiqueta(etiqueta, ALTURA_CAMPO),
                confianca=0.4,
            )
        )

    return campos


def detectar_pagina(
    pagina, numero: int, usar_dois_pontos: bool = True
) -> list[Campo]:
    """
    PT-PT: Todos os campos de uma pagina, sem sobreposicoes.

    EN-UK: Every field on one page, with overlaps removed.

    :param pagina: PT-PT: Pagina do pdfplumber. / EN-UK: A pdfplumber page.
    :param numero: PT-PT: Indice da pagina, a contar de zero.
    :param usar_dois_pontos:
        PT-PT: Incluir a estrategia menos fiavel. Ligada por omissao porque
               apanha os formularios de Word que nao desenham linha nenhuma,
               mas desligavel porque num documento de prosa so gera ruido.
        EN-UK: Include the least reliable strategy.
    """
    try:
        palavras = pagina.extract_words(use_text_flow=False, keep_blank_chars=False)
    except Exception as exc:  # noqa: BLE001
        log.warning("Não foi possível ler as palavras da página %d: %s", numero + 1, exc)
        palavras = []

    altura = float(pagina.height)
    largura = float(pagina.width)

    encontrados: list[Campo] = []
    encontrados.extend(_de_sublinhados(pagina, palavras, altura))
    encontrados.extend(_de_rectangulos(pagina, palavras, altura))
    encontrados.extend(_de_linhas(pagina, palavras, altura))
    if usar_dois_pontos:
        encontrados.extend(_de_dois_pontos(palavras, altura, largura))

    # PT-PT: A ordem de eliminação segue a fiabilidade: o primeiro a ficar com
    #        o sítio e o de maior confiança. Como as estratégias foram
    #        acrescentadas por ordem decrescente de fiabilidade, ordenar por
    #        confiança garante que um sublinhado ganha sempre a um par de dois
    #        pontos que ocupe o mesmo espaço.
    # EN-UK: Elimination follows reliability: the higher-confidence field keeps
    #        the spot.
    encontrados.sort(key=lambda c: -c.confianca)

    aceites: list[Campo] = []
    for campo in encontrados:
        campo.normalizar()
        if not campo.valido():
            continue
        if any(_sobrepoe(campo, existente) for existente in aceites):
            continue
        aceites.append(campo)

    # PT-PT: Segunda eliminação, por etiqueta. São campos que não se sobrepoem
    #        mas descrevem a mesma coisa: «Observações:» seguido de uma caixa
    #        desenhada por baixo dá dois campos, um pela estratégia dos dois
    #        pontos e outro pela do rectângulo. O rectângulo e o campo a sério;
    #        o outro e a etiqueta. Fica o de maior confiança, e só quando estão
    #        próximos na vertical — duas páginas com um campo «Nome» cada são
    #        dois campos legítimos e não podem ser fundidos.
    # EN-UK: A second pass, by label. These are fields that do not overlap but
    #        describe the same thing: a label with a colon and a box drawn
    #        underneath produces two. The higher-confidence one stays, and only
    #        when they sit close vertically — a "Name" field on each of two
    #        pages is two legitimate fields.
    finais: list[Campo] = []
    for campo in aceites:
        chave = campo.etiqueta.strip().lower()
        duplicado = next(
            (
                c
                for c in finais
                if chave
                and c.etiqueta.strip().lower() == chave
                and abs(c.y1 - campo.y1) < 90
            ),
            None,
        )
        if duplicado is not None:
            continue
        finais.append(campo)

    for campo in finais:
        campo.pagina = numero

    # PT-PT: A ordem final e a de leitura — de cima para baixo, da esquerda
    #        para a direita. E a ordem em que o utilizador vai percorrer o
    #        formulário com o Tab, e portanto a ordem em que os campos devem
    #        aparecer na lista de revisão.
    # EN-UK: The final order is reading order, which is also the order the user
    #        will tab through the form.
    finais.sort(key=lambda c: (-c.y1, c.x0))
    return finais


def detectar(caminho, usar_dois_pontos: bool = True) -> tuple[list[Campo], list[str]]:
    """
    PT-PT: Detecta campos num PDF inteiro.

    EN-UK: Detects fields across a whole PDF.

    :return:
        PT-PT: (campos, avisos). Os avisos dizem o que correu mal sem impedir
               o resto — uma página ilegível, um PDF digitalizado.
        EN-UK: (fields, warnings).
    """
    import pdfplumber

    campos: list[Campo] = []
    avisos: list[str] = []

    with pdfplumber.open(str(caminho)) as pdf:
        for numero, pagina in enumerate(pdf.pages):
            try:
                encontrados = detectar_pagina(pagina, numero, usar_dois_pontos)
            except Exception as exc:  # noqa: BLE001
                avisos.append(f"Página {numero + 1} não pôde ser analisada: {exc}")
                log.warning("Página %d falhou: %s", numero + 1, exc)
                continue

            if not encontrados:
                texto = pagina.extract_text() or ""
                if not texto.strip():
                    avisos.append(
                        f"Página {numero + 1} não tem texto — se o PDF está digitalizado, "
                        "a detecção automática não tem por onde se guiar. "
                        "Pode marcar os campos à mão no editor."
                    )

            campos.extend(encontrados)

    # PT-PT: Os nomes são atribuidos no fim, sobre a lista toda, para a
    #        numeracao de duplicados ser coerente entre páginas. «nome» na
    #        página 1 e «nome» na página 3 tem de dar «nome» e «nome_2», e isso
    #        só se sabe olhando para o documento inteiro.
    # EN-UK: Names are assigned at the end, over the whole list, so duplicate
    #        numbering is consistent across pages.
    usados: set[str] = set()
    for campo in campos:
        campo.nome = nome_seguro_campo(campo.etiqueta or f"campo_p{campo.pagina + 1}", usados)

    return campos, avisos
