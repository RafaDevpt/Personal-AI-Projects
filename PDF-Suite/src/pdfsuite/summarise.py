"""
PT-PT: Resumo de documentos.

       O resumo aqui e extractivo: escolhe as frases mais representativas do
       documento e apresenta-as por ordem de leitura. Nao gera texto novo.

       A escolha e deliberada e vale a pena ser explicita sobre ela. Um resumo
       gerado inventa a formulacao, e num relatorio tecnico ou num contrato uma
       formulacao inventada e um risco: quem le assume que aquilo esta escrito
       no documento. Um resumo extractivo pode ser incompleto, mas cada frase
       que apresenta esta la, tal e qual. Para quem quiser o outro tipo, ha o
       modulo `ai`, que e opcional, e o texto que ele devolve aparece sempre
       identificado como tal.

       O metodo e frequencia de termos com penalizacao das palavras vulgares —
       o principio do TF-IDF sobre um documento so. Nao e o estado da arte; e
       previsivel, nao precisa de rede, corre em milissegundos e nao envia o
       documento para lado nenhum, o que num relatorio interno importa mais.

EN-UK: Document summarisation.

       The summary here is extractive: it picks the document's most
       representative sentences and shows them in reading order. It generates no
       new text.

       That is deliberate. A generated summary invents the wording, and in a
       technical report or a contract invented wording is a risk: the reader
       assumes it is written in the document. An extractive summary may be
       incomplete, but every sentence it shows is there, exactly as written.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
import re
from collections import Counter

from .models import Documento, Resumo

log = logging.getLogger(__name__)

# PT-PT: Palavras sem valor informativo, em portugues e ingles. Sem esta lista,
#        as palavras-chave de qualquer documento sao «de», «a» e «para».
# EN-UK: Words with no informational value, in Portuguese and English.
VAZIAS: frozenset[str] = frozenset(
    ["a", "o", "as", "os", "um", "uma", "uns", "umas", "de", "do", "da", "dos", "das", "em", "no", "na", "nos", "nas", "por", "para", "com", "sem", "sob", "sobre", "ao", "aos", "à", "às", "e", "ou", "mas", "que", "se", "como", "quando", "onde", "qual", "quais", "quem", "cujo", "cuja", "este", "esta", "estes", "estas", "esse", "essa", "esses", "essas", "aquele", "aquela", "isto", "isso", "aquilo", "seu", "sua", "seus", "suas", "meu", "minha", "nosso", "nossa", "dele", "dela", "deles", "delas", "lhe", "lhes", "me", "te", "nos", "vos", "já", "não", "sim", "também", "mais", "menos", "muito", "pouco", "todo", "toda", "todos", "todas", "outro", "outra", "outros", "outras", "mesmo", "mesma", "cada", "qualquer", "ser", "estar", "ter", "haver", "fazer", "poder", "dever", "ir", "vir", "dar", "ver", "saber", "é", "são", "foi", "foram", "era", "eram", "será", "serão", "tem", "têm", "tinha", "havia", "há", "está", "estão", "pode", "podem", "deve", "devem", "entre", "até", "desde", "após", "antes", "durante", "através", "bem", "mal", "assim", "então", "porque", "pois", "logo", "ainda", "apenas", "só", "mesmo", "enquanto", "embora", "caso", "conforme", "the", "of", "and", "to", "in", "for", "on", "with", "at", "by", "from", "as", "is", "are", "was", "were", "be", "been", "being", "this", "that", "these", "those", "it", "its", "he", "she", "they", "we", "you", "i", "not", "no", "yes", "but", "or", "if", "which", "who", "whom", "whose", "what", "when", "where", "how", "than", "then", "there", "here", "have", "has", "had", "do", "does", "did", "can", "could", "shall", "should", "will", "would", "may", "might", "must"]
)

# PT-PT: Fim de frase. O olhar para tras evita cortar em abreviaturas comuns e
#        em iniciais — «Exmo. Sr.» e «S. A.» nao sao fim de frase, e sem esta
#        precaucao um documento comercial ficava partido em fragmentos de tres
#        palavras.
# EN-UK: Sentence end. The look-behind avoids splitting on common abbreviations
#        and initials.
RE_FRASE = re.compile(
    r"(?<![A-ZÁÉÍÓÚÂÊÔÃÕÇ])(?<!\bSr)(?<!\bDr)(?<!\bEng)(?<!\bExmo)(?<!\bn\.º)"
    r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ0-9])"
)

RE_PALAVRA = re.compile(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'-]{2,}")
RE_NUMERO_RELEVANTE = re.compile(
    r"\b\d{1,3}(?:[.,\u00a0 ]\d{3})*(?:[.,]\d{1,2})?\s*(?:€|EUR|%|dias?|meses|anos?)\b",
    re.IGNORECASE,
)
RE_DATA = re.compile(
    r"\b(?:\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}"
    r"|\d{1,2}\s+de\s+\w+\s+de\s+\d{4}"
    r"|\d{4}-\d{2}-\d{2})\b",
    re.IGNORECASE,
)

COMPRIMENTO_MINIMO_FRASE = 40
COMPRIMENTO_MAXIMO_FRASE = 420


def dividir_frases(texto: str) -> list[str]:
    """
    PT-PT: Divide o texto em frases utilizaveis.
    EN-UK: Splits the text into usable sentences.
    """
    # PT-PT: As mudancas de linha simples viram espaco: num PDF, uma frase
    #        atravessa varias linhas e mante-las partia todas as frases pela
    #        largura da coluna. As linhas em branco, essas, sao fim de
    #        paragrafo a serio e ficam.
    # EN-UK: Single line breaks become spaces: in a PDF a sentence spans several
    #        lines, and keeping them split every sentence at column width.
    normalizado = re.sub(r"(?<![.!?:])\n(?!\n)", " ", texto)
    normalizado = re.sub(r"\n+", ". ", normalizado)

    frases = []
    for bruta in RE_FRASE.split(normalizado):
        frase = " ".join(bruta.split()).strip()
        if COMPRIMENTO_MINIMO_FRASE <= len(frase) <= COMPRIMENTO_MAXIMO_FRASE:
            frases.append(frase)
    return frases


def palavras_chave(texto: str, quantas: int = 15) -> list[tuple[str, int]]:
    """
    PT-PT: Palavras mais frequentes, sem as vulgares.
    EN-UK: Most frequent words, minus the common ones.
    """
    contagem: Counter[str] = Counter()
    for palavra in RE_PALAVRA.findall(texto.lower()):
        if palavra in VAZIAS or len(palavra) < 4:
            continue
        contagem[palavra] += 1
    return contagem.most_common(quantas)


def _pontuar_frases(frases: list[str], frequencias: Counter[str]) -> list[float]:
    """
    PT-PT: Pontua cada frase pela densidade de termos importantes.

           A divisao pelo numero de palavras e o que impede as frases longas de
           ganharem so por serem longas. Sem ela, o resumo de qualquer contrato
           era feito das tres clausulas mais compridas do documento, que sao
           quase sempre as menos informativas.

    EN-UK: Scores each sentence by the density of important terms. Dividing by
           word count is what stops long sentences winning merely for being
           long: without it, any contract's summary consisted of its three
           longest clauses.
    """
    if not frequencias:
        return [0.0] * len(frases)

    maxima = max(frequencias.values())
    pontuacoes = []

    for indice, frase in enumerate(frases):
        palavras = RE_PALAVRA.findall(frase.lower())
        uteis = [p for p in palavras if p not in VAZIAS and len(p) >= 4]
        if not palavras:
            pontuacoes.append(0.0)
            continue

        soma = sum(frequencias.get(p, 0) / maxima for p in uteis)
        pontuacao = soma / len(palavras) ** 0.5

        # PT-PT: Uma frase com numeros e datas costuma ser onde estao os
        #        compromissos: valores, prazos, percentagens. Num relatorio, e
        #        o que interessa reter.
        # EN-UK: A sentence with figures and dates is usually where the
        #        commitments are: amounts, deadlines, percentages.
        if RE_NUMERO_RELEVANTE.search(frase):
            pontuacao *= 1.35
        if RE_DATA.search(frase):
            pontuacao *= 1.15

        # PT-PT: As primeiras frases de um documento tem quase sempre o
        #        assunto. As ultimas tem a conclusao. O meio e o
        #        desenvolvimento, e e onde e mais seguro cortar.
        # EN-UK: A document's first sentences almost always carry the subject
        #        and the last ones the conclusion; the middle is where it is
        #        safest to cut.
        if indice < 3:
            pontuacao *= 1.25
        elif indice >= len(frases) - 2:
            pontuacao *= 1.1

        pontuacoes.append(pontuacao)

    return pontuacoes


def resumir(documento: Documento, frases_desejadas: int = 6) -> Resumo:
    """
    PT-PT: Resume um documento.

    EN-UK: Summarises a document.

    :param frases_desejadas:
        PT-PT: Quantas frases o resumo deve ter.
        EN-UK: How many sentences the summary should hold.
    """
    resumo = Resumo(documento=documento)

    if not documento.ok:
        return resumo

    frases = dividir_frases(documento.texto)
    resumo.palavras_chave = palavras_chave(documento.texto)

    resumo.numeros = list(dict.fromkeys(RE_NUMERO_RELEVANTE.findall(documento.texto)))[:18]
    resumo.datas = list(dict.fromkeys(RE_DATA.findall(documento.texto)))[:12]

    if not frases:
        # PT-PT: Documento sem frases reconheciveis — uma tabela, uma lista de
        #        artigos. Devolver as linhas mais densas e melhor do que
        #        devolver nada, e a interface diz de onde vieram.
        # EN-UK: A document with no recognisable sentences — a table, a parts
        #        list. Returning the densest lines beats returning nothing.
        linhas = [
            " ".join(ln.split())
            for ln in documento.texto.split("\n")
            if len(ln.strip()) > 25
        ]
        resumo.frases = linhas[:frases_desejadas]
        return resumo

    frequencias = Counter(dict(palavras_chave(documento.texto, quantas=200)))
    pontuacoes = _pontuar_frases(frases, frequencias)

    melhores = sorted(range(len(frases)), key=lambda i: -pontuacoes[i])[:frases_desejadas]
    # PT-PT: A ordem final e a do documento, nao a da pontuacao. Um resumo cujas
    #        frases aparecem por ordem de relevancia le-se como uma lista solta;
    #        por ordem de leitura, le-se como um texto.
    # EN-UK: The final order is the document's, not the score's. A summary whose
    #        sentences come in relevance order reads as a loose list; in reading
    #        order, it reads as a text.
    melhores.sort()
    resumo.frases = [frases[i] for i in melhores]

    return resumo


def comparar_textos(documentos: list[Documento]) -> dict[str, list[str]]:
    """
    PT-PT: Termos comuns e termos exclusivos de cada documento.

           Serve para o caso em que a comparacao nao e de precos: seis
           relatorios sobre o mesmo assunto, e a pergunta e o que um diz que os
           outros nao dizem. Os termos exclusivos sao o caminho mais curto para
           essa resposta.

    EN-UK: Terms shared by all documents and terms exclusive to each. For the
           case where the comparison is not about prices: six reports on the
           same subject, and the question is what one says that the others do
           not.
    """
    validos = [d for d in documentos if d.ok]
    if len(validos) < 2:
        return {}

    conjuntos: dict[str, set[str]] = {}
    for documento in validos:
        termos = {
            p for p, _ in palavras_chave(documento.texto, quantas=120)
        }
        conjuntos[documento.rotulo] = termos

    comuns = set.intersection(*conjuntos.values())

    resultado: dict[str, list[str]] = {"__comuns__": sorted(comuns)[:25]}
    for rotulo, termos in conjuntos.items():
        outros = set().union(*(t for r, t in conjuntos.items() if r != rotulo))
        resultado[rotulo] = sorted(termos - outros)[:20]

    return resultado
