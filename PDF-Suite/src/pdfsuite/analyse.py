"""
PT-PT: Analise de propostas — extraccao dos sinais que permitem compara-las.

       O que este modulo faz e ler texto corrido e tentar responder a seis
       perguntas: quanto custa, o IVA esta incluido, a quantos dias se paga, em
       quantos dias entregam, quantos meses de garantia dao, e ate quando vale
       a proposta.

       O que este modulo NAO faz e decidir. Tudo o que sai daqui e uma
       proposta de leitura com uma confianca associada, para o utilizador
       confirmar na tabela antes de pontuar. Essa escolha e deliberada: uma
       extraccao por expressoes regulares sobre documentos que cada fornecedor
       escreve a sua maneira acerta na maioria e falha em algumas, e as
       falhas nunca sao obvias a olhar para o resultado final. Numa decisao de
       compra, uma ferramenta que apresenta um numero errado com ar de certo e
       pior do que nao ter ferramenta nenhuma.

EN-UK: Proposal analysis — extracting the signals that make them comparable.

       What this module does is read running text and try to answer six
       questions: how much, is VAT included, payment days, delivery days,
       warranty months, and how long the quote stands.

       What it does NOT do is decide. Everything leaving here is a reading
       suggestion with a confidence attached, for the user to confirm in the
       table before scoring. In a purchasing decision, a tool that presents a
       wrong number with a confident air is worse than no tool at all.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
import re

from .models import Documento, Proposta, Valor
from .money import detectar_iva, detectar_taxa_iva, encontrar_montantes, limpar_numero

log = logging.getLogger(__name__)

# PT-PT: Palavras que marcam o total. Ordenadas por especificidade: «total
#        geral» e melhor sinal do que «total», que aparece tambem no fim de
#        cada seccao. A ordem e usada para desempatar quando ha varias.
# EN-UK: Words marking the total, ordered by specificity: "grand total" is a
#        better signal than "total", which also ends each section.
MARCAS_TOTAL: tuple[tuple[str, float], ...] = (
    ("total geral", 1.0),
    ("valor total", 0.95),
    ("total da proposta", 0.95),
    ("montante total", 0.95),
    ("preco total", 0.9),
    ("preço total", 0.9),
    ("grand total", 1.0),
    ("total amount", 0.95),
    ("total a pagar", 0.95),
    ("total geral a pagar", 1.0),
    ("investimento total", 0.9),
    ("total", 0.75),
    ("total:", 0.8),
)

# PT-PT: Rotulos de subtotal. Sao excluidos activamente: numa proposta com tres
#        seccoes ha tres subtotais maiores do que zero e um deles seria
#        escolhido como total se nada os distinguisse.
# EN-UK: Subtotal labels, actively excluded: a three-section quote has three
#        subtotals and one of them would be picked as the total.
MARCAS_SUBTOTAL: tuple[str, ...] = (
    "subtotal", "sub-total", "sub total", "parcial", "por linha",
    "unitario", "unitário", "unit price", "preco unit", "preço unit",
    "iva", "vat", "desconto", "discount",
)

RE_DIAS = re.compile(
    r"(\d{1,3})\s*(?:\(\w+\)\s*)?dias?(?:\s+(?:uteis|úteis|corridos|seguidos))?",
    re.IGNORECASE,
)
RE_MESES = re.compile(r"(\d{1,3})\s*(?:\(\w+\)\s*)?(?:meses|mês|mes)\b", re.IGNORECASE)
RE_ANOS = re.compile(r"(\d{1,2})\s*(?:\(\w+\)\s*)?anos?\b", re.IGNORECASE)
RE_DAYS = re.compile(r"(\d{1,3})\s*(?:working\s+|business\s+)?days?\b", re.IGNORECASE)
RE_MONTHS = re.compile(r"(\d{1,3})\s*months?\b", re.IGNORECASE)
RE_YEARS = re.compile(r"(\d{1,2})\s*years?\b", re.IGNORECASE)

RE_REFERENCIA = re.compile(
    r"(?:refer[eê]ncia|ref\.?|proposta\s+n\.?[ºo]?|quote\s+no\.?|n\.?[ºo]\s*proposta)"
    r"[:\s]+([A-Z0-9][A-Z0-9/\-\.]{2,24})",
    re.IGNORECASE,
)

# PT-PT: Sufixos societarios. Servem para reconhecer o nome do fornecedor: uma
#        linha com «Lda.» ou «S.A.» e quase sempre a razao social.
# EN-UK: Company suffixes, used to recognise the vendor name: a line containing
#        "Ltd" or "S.A." is almost always the registered name.
SUFIXOS_EMPRESA: tuple[str, ...] = (
    "lda", "lda.", "s.a.", "sa", "unipessoal", "ltd", "ltd.", "limited",
    "gmbh", "srl", "b.v.", "bv", "inc", "inc.", "llc", "plc", "s.l.",
)


def _janela(texto: str, posicao: int, antes: int = 90, depois: int = 90) -> str:
    """PT-PT: Contexto a volta de uma posicao. / EN-UK: Context around a position."""
    return " ".join(texto[max(0, posicao - antes) : posicao + depois].split())


def extrair_fornecedor(documento: Documento) -> Valor:
    """
    PT-PT: Nome do fornecedor.

           Procura nas primeiras linhas, que e onde esta o cabecalho, e da
           preferencia a linhas com sufixo societario. Sem o encontrar, devolve
           desconhecido em vez de adivinhar a primeira linha — o titulo de uma
           proposta e muitas vezes «Proposta Comercial», e ter seis propostas
           todas chamadas assim na tabela e pior do que ter o nome do ficheiro.

    EN-UK: The vendor's name. Searches the first lines, where the letterhead
           is, preferring lines with a company suffix. Failing that, returns
           unknown rather than guessing the first line.
    """
    linhas = [ln.strip() for ln in documento.texto.split("\n")[:14] if ln.strip()]

    for linha in linhas:
        if len(linha) > 70:
            continue
        palavras = linha.replace(",", " ").lower().split()
        if any(p.strip(".") in SUFIXOS_EMPRESA for p in palavras):
            return Valor(
                valor=linha.strip(" -–—:"),
                bruto=linha,
                contexto=linha,
                confianca=0.9,
            )

    # PT-PT: Sem sufixo, a primeira linha curta que nao seja um titulo generico.
    # EN-UK: With no suffix, the first short line that is not a generic title.
    genericos = ("proposta", "orcamento", "orçamento", "quotation", "quote", "cotacao", "cotação")
    for linha in linhas[:5]:
        if 3 < len(linha) <= 60 and not any(g in linha.lower() for g in genericos):
            return Valor(valor=linha, bruto=linha, contexto=linha, confianca=0.5)

    return Valor(confianca=0.0)


def extrair_total(documento: Documento) -> tuple[Valor, str]:
    """
    PT-PT: O total da proposta.

           A estrategia e procurar montantes proximos de uma palavra que marque
           um total, e escolher entre os candidatos pela pontuacao da marca. Se
           nenhum candidato aparecer, cai no maior montante do documento — que
           e uma heuristica fraca, e por isso sai com confianca baixa e uma
           nota a dizer que foi assim que se chegou la.

    EN-UK: The proposal total. Looks for amounts near a word marking a total and
           picks among candidates by the marker's score. With no candidate it
           falls back to the largest amount in the document — a weak heuristic,
           so it comes out with low confidence and a note saying how it got
           there.

    :return: PT-PT: (total, moeda). / EN-UK: (total, currency).
    """
    texto = documento.texto
    minusculas = texto.lower()

    montantes = encontrar_montantes(texto)
    if not montantes:
        return Valor(confianca=0.0), ""

    moedas = [m for _, m, _, _ in montantes if m]
    moeda = max(set(moedas), key=moedas.count) if moedas else ""

    melhor: tuple[float, float, str, str] | None = None  # (pontuacao, valor, bruto, contexto)

    for marca, peso in MARCAS_TOTAL:
        inicio = 0
        while True:
            posicao = minusculas.find(marca, inicio)
            if posicao == -1:
                break
            inicio = posicao + 1

            janela = minusculas[posicao : posicao + 160]
            if any(s in janela[: len(marca) + 14] for s in MARCAS_SUBTOTAL):
                continue
            # PT-PT: Excluir tambem quando a marca de subtotal esta logo antes:
            #        «Subtotal» contem «total» e seria apanhado pela marca
            #        generica se so olhassemos para a frente.
            # EN-UK: Exclude when the subtotal marker sits just before, too:
            #        "Subtotal" contains "total".
            antes = minusculas[max(0, posicao - 12) : posicao]
            if any(s in antes for s in ("sub", "-", "iva ", "vat ")):
                continue

            # PT-PT: E excluir o cabecalho da coluna. Numa tabela de precos a
            #        ultima coluna chama-se «Total», e o primeiro montante a
            #        seguir a esse cabecalho e a primeira linha de artigos — nao
            #        o total da proposta. Reconhece-se pelo que vem a seguir:
            #        um cabecalho e seguido de uma mudanca de linha, enquanto um
            #        total a serio e seguido do proprio valor na mesma linha.
            # EN-UK: And exclude the column header. In a price table the last
            #        column is called "Total", and the first amount after that
            #        header is the first line item, not the proposal total. It
            #        is recognised by what follows: a header is followed by a
            #        line break, a real total by its own value on the same line.
            resto_da_linha = janela[len(marca) :].split("\n", 1)[0]
            if not re.search(r"\d", resto_da_linha):
                continue

            for valor, _moeda_local, bruto, confianca_numero in montantes:
                # PT-PT: A procura e estritamente para a frente. Permitir uns
                #        caracteres para tras parecia inofensivo e nao era: numa
                #        tabela, a linha imediatamente acima do total acaba com
                #        um montante, e esse ficava mais perto da palavra
                #        «TOTAL» do que o proprio total. O resultado era a
                #        ultima linha de artigos a ser apresentada como total da
                #        proposta — plausivel, errada, e dificil de notar sem
                #        abrir o PDF ao lado.
                # EN-UK: The search runs strictly forward. Allowing a few
                #        characters backwards looked harmless and was not: in a
                #        table, the row immediately above the total ends with an
                #        amount, and that one sat closer to the word "TOTAL"
                #        than the total itself.
                posicao_montante = texto.find(bruto, posicao)
                if posicao_montante == -1 or posicao_montante - posicao > 140:
                    continue
                if valor <= 0:
                    continue

                pontuacao = peso * confianca_numero
                # PT-PT: Entre candidatos igualmente marcados, o maior e quase
                #        sempre o total e os outros sao linhas de detalhe.
                # EN-UK: Among equally marked candidates the largest is almost
                #        always the total.
                pontuacao += min(valor / 1_000_000, 0.05)

                if melhor is None or pontuacao > melhor[0]:
                    melhor = (
                        pontuacao,
                        valor,
                        bruto,
                        _janela(texto, posicao_montante),
                    )
                break

    if melhor is not None:
        return (
            Valor(
                valor=melhor[1],
                bruto=melhor[2],
                contexto=melhor[3],
                confianca=min(melhor[0], 1.0),
            ),
            moeda,
        )

    maior = max(montantes, key=lambda m: m[0])
    posicao = texto.find(maior[2])
    return (
        Valor(
            valor=maior[0],
            bruto=maior[2],
            contexto=_janela(texto, max(posicao, 0)),
            confianca=0.3,
        ),
        moeda,
    )


def _procurar_dias(texto: str, marcas: tuple[str, ...]) -> Valor:
    """
    PT-PT: Um numero de dias associado a uma das marcas indicadas.
    EN-UK: A number of days associated with one of the given markers.
    """
    minusculas = texto.lower()

    for marca in marcas:
        posicao = minusculas.find(marca)
        if posicao == -1:
            continue
        janela = texto[posicao : posicao + 130]
        for padrao in (RE_DIAS, RE_DAYS):
            correspondencia = padrao.search(janela)
            if correspondencia:
                valor, _ = limpar_numero(correspondencia.group(1))
                if valor is not None and 0 < valor <= 365:
                    return Valor(
                        valor=valor,
                        bruto=correspondencia.group(0),
                        contexto=_janela(texto, posicao, antes=10, depois=140),
                        confianca=0.85,
                    )
    return Valor(confianca=0.0)


def extrair_pagamento(documento: Documento) -> Valor:
    """
    PT-PT: Prazo de pagamento, em dias.

           Pronto pagamento conta como zero dias, e essa leitura tem de ser
           explicita: quem escreve «pronto pagamento» nunca escreve «0 dias», e
           sem esta regra a proposta ficava sem prazo em vez de ficar com o
           prazo mais curto possivel.

    EN-UK: Payment terms in days. Cash on delivery counts as zero days and that
           reading has to be explicit: nobody who writes "cash payment" also
           writes "0 days".
    """
    minusculas = documento.texto.lower()

    for marca in ("pronto pagamento", "pagamento a pronto", "cash payment", "payment in advance"):
        posicao = minusculas.find(marca)
        if posicao != -1:
            # PT-PT: Muitas propostas oferecem as duas coisas: «pronto
            #        pagamento com desconto, ou 30 dias». Nesse caso o prazo
            #        real disponivel e o maior, e e esse que interessa a
            #        tesouraria — o desconto entra na coluna do preco, nao na
            #        do prazo.
            # EN-UK: Many quotes offer both: "cash with discount, or 30 days".
            #        The real available term is the longer one, and that is what
            #        matters to finance.
            alternativa = _procurar_dias(
                documento.texto[posicao : posicao + 160], ("pagamento", "ou", "dias")
            )
            if alternativa.conhecido:
                return alternativa
            return Valor(
                valor=0.0,
                bruto=marca,
                contexto=_janela(documento.texto, posicao),
                confianca=0.85,
            )

    return _procurar_dias(
        documento.texto,
        (
            "condicoes de pagamento", "condições de pagamento", "prazo de pagamento",
            "pagamento a", "pagamento:", "payment terms", "pagamento",
        ),
    )


def extrair_entrega(documento: Documento) -> Valor:
    """
    PT-PT: Prazo de entrega, em dias.
    EN-UK: Delivery lead time, in days.
    """
    minusculas = documento.texto.lower()

    for marca in ("entrega imediata", "disponibilidade imediata", "immediate delivery", "em stock"):
        posicao = minusculas.find(marca)
        if posicao != -1:
            return Valor(
                valor=0.0,
                bruto=marca,
                contexto=_janela(documento.texto, posicao),
                confianca=0.8,
            )

    return _procurar_dias(
        documento.texto,
        (
            "prazo de entrega", "prazo de execucao", "prazo de execução",
            "entrega em", "entrega:", "delivery time", "lead time", "entrega",
        ),
    )


def extrair_garantia(documento: Documento) -> Valor:
    """
    PT-PT: Garantia, convertida sempre para meses.

           A conversao dos anos e o ponto todo: uma proposta diz «3 anos» e
           outra diz «24 meses», e compara-las como estao daria 3 contra 24, com
           a pior a ganhar por oito vezes. Guardar sempre em meses e o que torna
           a coluna comparavel.

    EN-UK: Warranty, always converted to months. The year conversion is the
           whole point: one quote says "3 years" and another "24 months", and
           comparing them as written gives 3 against 24, with the worse one
           winning eight times over.
    """
    minusculas = documento.texto.lower()

    for marca in ("garantia", "warranty", "guarantee"):
        inicio = 0
        while True:
            posicao = minusculas.find(marca, inicio)
            if posicao == -1:
                break
            inicio = posicao + 1
            janela = documento.texto[posicao : posicao + 130]

            for padrao, multiplicador in (
                (RE_ANOS, 12), (RE_YEARS, 12), (RE_MESES, 1), (RE_MONTHS, 1)
            ):
                correspondencia = padrao.search(janela)
                if not correspondencia:
                    continue
                valor, _ = limpar_numero(correspondencia.group(1))
                if valor is None:
                    continue
                meses = valor * multiplicador
                if not 0 < meses <= 240:
                    continue
                return Valor(
                    valor=meses,
                    bruto=correspondencia.group(0),
                    contexto=_janela(documento.texto, posicao, antes=10, depois=140),
                    confianca=0.85,
                )

    return Valor(confianca=0.0)


def extrair_validade(documento: Documento) -> Valor:
    """
    PT-PT: Validade da proposta, em dias.
    EN-UK: Quote validity, in days.
    """
    return _procurar_dias(
        documento.texto,
        (
            "validade da proposta", "proposta valida", "proposta válida",
            "valida por", "válida por", "validade", "valid for", "validity",
        ),
    )


def extrair_referencia(documento: Documento) -> Valor:
    """
    PT-PT: Referencia da proposta, para citar no pedido de esclarecimentos e na
           adjudicacao. Sem ela, responder ao fornecedor obriga a reabrir o PDF.
    EN-UK: The quote reference, for use in follow-up questions and in the award.
    """
    correspondencia = RE_REFERENCIA.search(documento.texto)
    if not correspondencia:
        return Valor(confianca=0.0)
    return Valor(
        valor=correspondencia.group(1).strip(" .,;"),
        bruto=correspondencia.group(0),
        contexto=_janela(documento.texto, correspondencia.start()),
        confianca=0.8,
    )


def analisar(documento: Documento) -> Proposta:
    """
    PT-PT: Le uma proposta e devolve os sinais encontrados, com as notas do que
           deve ser confirmado a mao.
    EN-UK: Reads a proposal and returns the signals found, with notes on what
           should be confirmed by hand.
    """
    proposta = Proposta(documento=documento)

    if not documento.ok:
        proposta.notas.append(documento.erro or "Documento sem texto legível.")
        return proposta

    proposta.fornecedor = extrair_fornecedor(documento)
    proposta.total, proposta.moeda = extrair_total(documento)
    proposta.prazo_pagamento = extrair_pagamento(documento)
    proposta.prazo_entrega = extrair_entrega(documento)
    proposta.garantia_meses = extrair_garantia(documento)
    proposta.validade = extrair_validade(documento)
    proposta.referencia = extrair_referencia(documento)

    incluido, marca = detectar_iva(documento.texto)
    proposta.iva_incluido = incluido

    taxa = detectar_taxa_iva(documento.texto)
    if taxa is not None:
        proposta.taxa_iva = Valor(valor=taxa, bruto=f"{taxa:g}%", confianca=0.85)

    # --- PT-PT: Notas para o utilizador / EN-UK: Notes for the user ---------

    if documento.digitalizado:
        proposta.notas.append(
            "O PDF parece estar digitalizado: foi lido pouco texto e os valores "
            "extraídos podem estar incompletos."
        )

    if not proposta.total.conhecido:
        proposta.notas.append(
            "Não foi encontrado nenhum valor total. Escreva-o à mão na tabela."
        )
    elif proposta.total.confianca < 0.6:
        proposta.notas.append(
            f"O total foi deduzido com pouca confiança a partir de «{proposta.total.bruto}». "
            "Confirme antes de decidir."
        )

    if incluido is None and proposta.total.conhecido:
        proposta.notas.append(
            "O documento não diz se o total inclui IVA. Está a ser assumido que "
            "acresce — confirme, porque é o erro que mais inverte comparações."
        )
    elif marca:
        proposta.notas.append(f"IVA determinado pela expressão «{marca}».")

    if not proposta.garantia_meses.conhecido:
        proposta.notas.append("Garantia não declarada no documento.")
    if not proposta.prazo_entrega.conhecido:
        proposta.notas.append("Prazo de entrega não declarado no documento.")
    if not proposta.prazo_pagamento.conhecido:
        proposta.notas.append("Condições de pagamento não declaradas no documento.")

    return proposta


def analisar_varios(documentos: list[Documento]) -> list[Proposta]:
    """PT-PT: Analisa varios documentos. / EN-UK: Analyses several documents."""
    return [analisar(d) for d in documentos]


def verificar_coerencia(propostas: list[Proposta]) -> list[str]:
    """
    PT-PT: Avisos que so se percebem olhando para o conjunto.

           Uma proposta em dolares no meio de cinco em euros nao e um problema
           de nenhuma delas em particular — e da comparacao. O mesmo para uma
           proposta cujo valor esta uma ordem de grandeza fora das outras, que
           normalmente significa que se leu mal o numero ou que o ambito nao e
           o mesmo. Sao as duas coisas que estragam uma comparacao e nenhuma se
           ve a olhar para uma proposta de cada vez.

    EN-UK: Warnings that only make sense across the set. A quote in dollars
           among five in euros is not any one quote's problem — it is the
           comparison's. Same for one whose value is an order of magnitude away
           from the rest, which usually means the number was misread or the
           scope is different.
    """
    avisos: list[str] = []
    validas = [p for p in propostas if p.total.conhecido]

    if not validas:
        return ["Nenhuma das propostas tem um total identificável."]

    moedas = {p.moeda for p in validas if p.moeda}
    if len(moedas) > 1:
        avisos.append(
            f"As propostas estão em moedas diferentes ({', '.join(sorted(moedas))}). "
            "Os totais não são comparáveis sem converter — a aplicação não converte."
        )

    sem_iva = [p.rotulo for p in validas if p.iva_incluido is None]
    if sem_iva:
        avisos.append(
            f"Não foi possível determinar o IVA em: {', '.join(sem_iva)}. "
            "Assumido que acresce à taxa por omissão."
        )

    totais = sorted(float(p.total.valor) for p in validas)  # type: ignore[arg-type]
    if len(totais) >= 3:
        mediana = totais[len(totais) // 2]
        for proposta in validas:
            valor = float(proposta.total.valor)  # type: ignore[arg-type]
            if mediana > 0 and (valor > mediana * 5 or valor < mediana / 5):
                avisos.append(
                    f"«{proposta.rotulo}» tem um total muito afastado das restantes "
                    f"({proposta.total.bruto}). Verifique se o valor foi bem lido e se "
                    "o âmbito da proposta é o mesmo."
                )

    return avisos
