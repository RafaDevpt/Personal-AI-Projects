# -*- coding: utf-8 -*-
"""
PT-PT: Interpretacao de numeros, moeda e IVA.

       Este modulo existe por causa de uma unica ambiguidade que estraga
       comparacoes de propostas: `1.234` sao mil duzentos e trinta e quatro em
       Portugal e um virgula dois tres quatro em Inglaterra. Numa proposta em
       euros vinda de um fornecedor britanico, adivinhar mal por mil vezes
       inverte a decisao de compra.

       A regra usada e a do ultimo separador: o separador decimal e o que
       aparece mais a direita, desde que tenha um a tres digitos a seguir. E a
       regra que funciona nos dois formatos sem precisar de saber a origem do
       documento. Os casos que continuam ambiguos — `1.234` sozinho — sao
       resolvidos pela convencao dos milhares, porque um valor com exactamente
       tres digitos a seguir ao ponto e quase sempre milhares, e assinalados
       com confianca mais baixa para o utilizador confirmar.

EN-UK: Number, currency and VAT parsing.

       This module exists because of one ambiguity that wrecks quote
       comparisons: `1.234` is one thousand two hundred and thirty-four in
       Portugal and one point two three four in Britain. On a euro quote from a
       British vendor, guessing wrong by a factor of a thousand inverts the
       purchasing decision.

       The rule used is the last-separator rule: the decimal separator is the
       rightmost one, provided it has one to three digits after it.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
import re

log = logging.getLogger(__name__)

# PT-PT: Simbolos e codigos reconhecidos. A ordem importa na alternancia da
#        expressao regular: os codigos de tres letras vem primeiro para «EUR»
#        nao ser lido como «E» seguido de «UR».
# EN-UK: Recognised symbols and codes. Order matters in the regex alternation:
#        three-letter codes come first so "EUR" is not read as "E" then "UR".
MOEDAS: dict[str, str] = {
    "EUR": "EUR",
    "USD": "USD",
    "GBP": "GBP",
    "CHF": "CHF",
    "BRL": "BRL",
    "€": "EUR",
    "$": "USD",
    "£": "GBP",
    "R$": "BRL",
}

_SIMBOLOS = "|".join(re.escape(s) for s in sorted(MOEDAS, key=len, reverse=True))

# PT-PT: Um numero com separadores, em duas alternativas.
#
#        A primeira aceita o espaco como separador de milhares — `1 234,56` —
#        mas so quando cada grupo tem exactamente tres digitos. Sem essa
#        exigencia, o espaco engolia a coluna do lado numa tabela de precos:
#        numa linha `Switch 4 1.180,00 €`, a quantidade e o preco colavam-se e
#        saía o montante 41.180,00 €. Numa proposta comercial isso nao e um
#        erro de leitura, e uma decisao de compra errada.
#
#        A segunda cobre tudo o resto sem espaco nenhum: `1.180,00`,
#        `1,234.56`, `1234`, `1234.5`.
#
# EN-UK: A number with separators, in two alternatives.
#
#        The first accepts the space as a thousands separator — `1 234.56` —
#        but only when each group has exactly three digits. Without that
#        requirement, the space swallowed the neighbouring column in a price
#        table: on a row reading `Switch 4 1,180.00 €`, quantity and price were
#        glued together and out came 41,180.00 €.
_NUMERO = (
    r"\d{1,3}(?:[\u00a0\u202f ]\d{3})+(?:[.,]\d{1,2})?"
    r"|\d+(?:[.,]\d+)*"
)

# PT-PT: Moeda antes ou depois do numero. Sao dois padroes porque `€ 1.000` e
#        `1.000 €` sao ambos correntes e um so padrao com moeda opcional dos
#        dois lados apanharia texto que nao e dinheiro nenhum.
# EN-UK: Currency before or after the number.
RE_MOEDA_ANTES = re.compile(rf"(?P<moeda>{_SIMBOLOS})\s*(?P<numero>{_NUMERO})", re.IGNORECASE)
RE_MOEDA_DEPOIS = re.compile(rf"(?P<numero>{_NUMERO})\s*(?P<moeda>{_SIMBOLOS})", re.IGNORECASE)

RE_PERCENTAGEM = re.compile(rf"(?P<numero>{_NUMERO})\s*%")

# PT-PT: Marcadores de IVA. Separados em duas listas porque significam o
#        oposto um do outro e confundi-los inverte o total.
# EN-UK: VAT markers, in two lists because they mean the opposite of each other.
MARCAS_IVA_INCLUIDO: tuple[str, ...] = (
    "iva incluido",
    "iva incluído",
    "c/ iva",
    "com iva",
    "inclui iva",
    "iva included",
    "vat included",
    "incl. vat",
    "including vat",
    "preco final",
    "preço final",
    "valor final",
    "gross total",
    "total ilíquido",
    "total iliquido",
)

MARCAS_IVA_ACRESCE: tuple[str, ...] = (
    "acresce iva",
    "acresce o iva",
    "s/ iva",
    "sem iva",
    "mais iva",
    "+ iva",
    "iva nao incluido",
    "iva não incluído",
    "excluding vat",
    "vat excluded",
    "excl. vat",
    "plus vat",
    "net of vat",
    "valor liquido",
    "valor líquido",
    "total liquido",
    "total líquido",
    "net total",
)

# PT-PT: Isencao de IVA. Nao e o mesmo que «incluido» nem que «acresce»: o
#        total ja e o total e nao ha nada a somar. Tratar isto como «acresce»
#        inflacionava a proposta em 23% e podia eliminar a melhor.
# EN-UK: VAT exemption. Not the same as included or added: the total is already
#        the total. Treating it as "added" inflated the quote by 23% and could
#        eliminate the best one.
MARCAS_IVA_ISENTO: tuple[str, ...] = (
    "isento de iva",
    "isenta de iva",
    "iva - regime de isencao",
    "iva – regime de isenção",
    "regime de isencao",
    "regime de isenção",
    "vat exempt",
    "zero rated",
    "artigo 53",
    "art. 53",
)


def limpar_numero(bruto: str) -> tuple[float | None, float]:
    """
    PT-PT: Converte um numero escrito em texto para float.

    EN-UK: Converts a number written as text into a float.

    :return:
        PT-PT: (valor, confianca). A confianca desce quando o formato e
               ambiguo, para o relatorio poder assinalar o que vale a pena
               confirmar a mao.
        EN-UK: (value, confidence). Confidence drops on ambiguous formats.
    """
    if not bruto:
        return None, 0.0

    # PT-PT: Espacos de todos os tipos fora — sao sempre separadores de
    #        milhares, nunca decimais.
    # EN-UK: Spaces of every kind out — always thousands separators.
    texto = re.sub(r"[\s\u00a0\u202f]", "", str(bruto).strip())
    if not texto:
        return None, 0.0

    negativo = texto.startswith("-") or (texto.startswith("(") and texto.endswith(")"))
    texto = texto.strip("-()")

    if not re.fullmatch(r"[\d.,]+", texto):
        return None, 0.0

    pontos = texto.count(".")
    virgulas = texto.count(",")
    confianca = 1.0

    if pontos and virgulas:
        # PT-PT: Os dois separadores presentes: o que aparece mais a direita e
        #        o decimal. Sem ambiguidade nenhuma.
        # EN-UK: Both separators present: the rightmost one is the decimal.
        if texto.rfind(".") > texto.rfind(","):
            texto = texto.replace(",", "").replace(".", ".")
            decimal = "."
        else:
            texto = texto.replace(".", "").replace(",", ".")
            decimal = "."
        _ = decimal
    elif virgulas:
        partes = texto.split(",")
        if virgulas == 1 and 1 <= len(partes[1]) <= 2:
            # PT-PT: `1234,56` — decimal em formato portugues.
            texto = texto.replace(",", ".")
        elif all(len(p) == 3 for p in partes[1:]):
            # PT-PT: `1,234,567` — milhares em formato ingles.
            texto = texto.replace(",", "")
        else:
            texto = texto.replace(",", ".")
            confianca = 0.6
    elif pontos:
        partes = texto.split(".")
        if pontos == 1 and 1 <= len(partes[1]) <= 2:
            # PT-PT: `1234.56` — decimal em formato ingles.
            pass
        elif all(len(p) == 3 for p in partes[1:]):
            # PT-PT: `1.234` ou `1.234.567` — milhares em formato portugues.
            #        Fica com confianca mais baixa porque `1.234` tambem pode
            #        ser um decimal ingles de tres casas, e nao ha no proprio
            #        numero forma de distinguir. Cabe ao utilizador confirmar.
            # EN-UK: Thousands in Portuguese format. Lower confidence, because
            #        `1.234` could also be a three-decimal English number and
            #        nothing in the number itself tells them apart.
            texto = texto.replace(".", "")
            confianca = 0.75 if pontos > 1 else 0.6
        else:
            texto = texto.replace(".", "")
            confianca = 0.5

    try:
        valor = float(texto)
    except ValueError:
        return None, 0.0

    return (-valor if negativo else valor), confianca


def encontrar_montantes(texto: str) -> list[tuple[float, str, str, float]]:
    """
    PT-PT: Todos os montantes com moeda encontrados no texto.

           Os dois padroes sao recolhidos primeiro e so depois se decide quais
           ficam, porque competem pelo mesmo simbolo. Em `1.180,00 € 4.720,00 €`
           — duas celulas de uma tabela — o padrao «moeda depois» le os dois
           montantes correctamente, e o padrao «moeda antes» agarra o euro da
           primeira celula e junta-o ao numero da segunda. Como o simbolo so
           pode pertencer a um montante, aceitam-se os candidatos por ordem de
           posicao e rejeita-se quem se sobreponha a um ja aceite.

    EN-UK: Every currency amount found in the text. Both patterns are collected
           first and only then filtered, because they compete for the same
           symbol: in `1,180.00 € 4,720.00 €` the "currency after" pattern reads
           both amounts correctly while "currency before" grabs the first cell's
           euro sign and pairs it with the second cell's number.

    :return:
        PT-PT: Lista de (valor, moeda, texto original, confianca).
        EN-UK: List of (value, currency, original text, confidence).
    """
    candidatos: list[tuple[int, int, float, str, str, float]] = []

    for padrao in (RE_MOEDA_DEPOIS, RE_MOEDA_ANTES):
        for correspondencia in padrao.finditer(texto):
            valor, confianca = limpar_numero(correspondencia.group("numero"))
            if valor is None:
                continue
            moeda = MOEDAS.get(correspondencia.group("moeda").upper(), "")
            candidatos.append(
                (
                    correspondencia.start(),
                    correspondencia.end(),
                    valor,
                    moeda,
                    correspondencia.group(0).strip(),
                    confianca,
                )
            )

    # PT-PT: Por posicao, e a maior primeiro em caso de empate no inicio.
    # EN-UK: By position, longest first when two start at the same place.
    candidatos.sort(key=lambda c: (c[0], -(c[1] - c[0])))

    aceites: list[tuple[int, int]] = []
    encontrados: list[tuple[float, str, str, float]] = []

    for inicio, fim, valor, moeda, bruto, confianca in candidatos:
        if any(inicio < f and i < fim for i, f in aceites):
            continue
        aceites.append((inicio, fim))
        encontrados.append((valor, moeda, bruto, confianca))

    return encontrados


def detectar_iva(texto: str) -> tuple[bool | None, str]:
    """
    PT-PT: Determina se um total inclui IVA.

    EN-UK: Determines whether a total includes VAT.

    :return:
        PT-PT: (incluido, marca encontrada). `incluido` e None quando o
               documento nao diz — que e diferente de dizer que nao inclui.
        EN-UK: (included, marker found). `incluido` is None when the document
               does not say, which differs from saying it does not include it.
    """
    minusculas = texto.lower()

    # PT-PT: A isencao e verificada primeiro. «Isento de IVA» contem «iva» e
    #        seria apanhado por qualquer das outras listas se elas viessem
    #        antes, dando a resposta oposta a correcta.
    # EN-UK: Exemption is checked first: "exempt from VAT" contains "VAT" and
    #        would be caught by either other list, giving the opposite answer.
    for marca in MARCAS_IVA_ISENTO:
        if marca in minusculas:
            return True, marca

    posicao_inc = min(
        (minusculas.find(m) for m in MARCAS_IVA_INCLUIDO if m in minusculas), default=-1
    )
    posicao_acr = min(
        (minusculas.find(m) for m in MARCAS_IVA_ACRESCE if m in minusculas), default=-1
    )

    if posicao_inc == -1 and posicao_acr == -1:
        return None, ""
    if posicao_acr == -1:
        return True, _marca_em(minusculas, MARCAS_IVA_INCLUIDO)
    if posicao_inc == -1:
        return False, _marca_em(minusculas, MARCAS_IVA_ACRESCE)

    # PT-PT: As duas marcas presentes acontece em propostas que decompoem o
    #        valor liquido e o ilíquido. A que aparece mais tarde no documento
    #        e normalmente a do total final, que e a que interessa.
    # EN-UK: Both markers appear in quotes that break out net and gross. The one
    #        appearing later is usually the final total, which is the one that
    #        matters.
    if posicao_inc > posicao_acr:
        return True, _marca_em(minusculas, MARCAS_IVA_INCLUIDO)
    return False, _marca_em(minusculas, MARCAS_IVA_ACRESCE)


def _marca_em(texto: str, marcas: tuple[str, ...]) -> str:
    """PT-PT: Primeira marca presente. / EN-UK: First marker present."""
    for marca in marcas:
        if marca in texto:
            return marca
    return ""


def detectar_taxa_iva(texto: str) -> float | None:
    """
    PT-PT: Taxa de IVA declarada no documento.

           So aceita as taxas que existem em Portugal continental e nas regioes
           autonomas. Sem essa restricao, qualquer «desconto de 10%» na proposta
           era lido como taxa de IVA — e um desconto aparece com muito mais
           frequencia do que a taxa numa proposta comercial.

    EN-UK: The VAT rate stated in the document. Only accepts rates that exist in
           mainland Portugal and the autonomous regions: without that
           restriction, any "10% discount" was read as a VAT rate, and discounts
           appear far more often than the rate does.
    """
    taxas_validas = {4.0, 5.0, 6.0, 9.0, 12.0, 13.0, 16.0, 18.0, 22.0, 23.0}
    minusculas = texto.lower()

    for correspondencia in RE_PERCENTAGEM.finditer(minusculas):
        janela = minusculas[max(0, correspondencia.start() - 40) : correspondencia.end() + 20]
        if "iva" not in janela and "vat" not in janela:
            continue
        valor, _ = limpar_numero(correspondencia.group("numero"))
        if valor is not None and valor in taxas_validas:
            return valor
    return None


def formatar_moeda(valor: float | None, moeda: str = "EUR") -> str:
    """
    PT-PT: Formata um montante em convencao portuguesa: milhares com ponto,
           decimais com virgula, simbolo depois do numero.
    EN-UK: Formats an amount in Portuguese convention: full stop for thousands,
           comma for decimals, symbol after the number.
    """
    if valor is None:
        return "—"
    simbolo = {"EUR": "€", "USD": "$", "GBP": "£", "BRL": "R$"}.get(moeda, moeda)
    inteiro, decimal = f"{abs(valor):,.2f}".split(".")
    inteiro = inteiro.replace(",", ".")
    sinal = "-" if valor < 0 else ""
    return f"{sinal}{inteiro},{decimal} {simbolo}".strip()
