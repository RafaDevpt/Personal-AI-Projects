"""
PT-PT: Matriz de decisao ponderada.

       Cada criterio e normalizado para uma escala de 0 a 100 dentro do
       conjunto de propostas, e o resultado e a media pesada. Normalizar dentro
       do conjunto — e nao contra uma escala absoluta — e o que faz sentido
       aqui: nao existe um preco «bom» em abstracto, existe o mais barato das
       propostas que estao em cima da mesa.

       Duas coisas que este modulo faz questao de nao fazer.

       Nao inventa valores em falta. Uma proposta sem garantia declarada nao
       recebe zero nem recebe a media: fica de fora daquele criterio e o peso
       e redistribuido pelos restantes. Dar zero castigava quem simplesmente
       nao escreveu; dar a media premiava. Nenhuma das duas e verdade, e a
       unica resposta honesta e dizer que falta e mostrar a completude ao lado
       da pontuacao.

       Nao declara vencedor por margens pequenas. Cinco pontos numa escala de
       cem estao dentro do erro de uma extraccao automatica.

EN-UK: Weighted decision matrix.

       Each criterion is normalised to 0-100 within the set of proposals, and
       the result is the weighted mean. Normalising within the set rather than
       against an absolute scale is what makes sense: there is no "good" price
       in the abstract, there is the cheapest of the quotes on the table.

       Two things this module takes care not to do.

       It does not invent missing values. A proposal with no stated warranty
       gets neither zero nor the average: it drops out of that criterion and
       the weight is redistributed. Zero punished whoever simply did not write
       it down; the average rewarded them.

       It does not declare a winner on small margins.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging

from .models import Comparacao, Criterio, Pontuacao, Proposta

log = logging.getLogger(__name__)

# PT-PT: Criterios por omissao, com os pesos que fazem sentido numa compra de
#        equipamento com instalacao. O preco pesa mais do que tudo o resto
#        junto mas nao decide sozinho — se decidisse, esta ferramenta seria uma
#        folha de calculo com uma coluna.
#
#        Os pesos sao editaveis na interface, e devem ser editados: numa compra
#        urgente o prazo de entrega vale mais do que a garantia, e numa compra
#        de infraestrutura que vai ficar cinco anos no sitio e ao contrario.
#
# EN-UK: Default criteria, with weights that make sense for an equipment
#        purchase with installation. Price outweighs everything else together
#        but does not decide alone. The weights are editable in the interface
#        and should be edited: on an urgent purchase, delivery time is worth
#        more than warranty; on infrastructure meant to last five years, the
#        reverse.
CRITERIOS_OMISSAO: tuple[Criterio, ...] = (
    Criterio("preco", "Preço com IVA", 45.0, maior_melhor=False, unidade="€"),
    Criterio("garantia", "Garantia", 20.0, maior_melhor=True, unidade="meses"),
    Criterio("entrega", "Prazo de entrega", 15.0, maior_melhor=False, unidade="dias"),
    Criterio("pagamento", "Prazo de pagamento", 12.0, maior_melhor=True, unidade="dias"),
    Criterio("validade", "Validade da proposta", 8.0, maior_melhor=True, unidade="dias"),
)


def valor_do_criterio(
    proposta: Proposta, chave: str, taxa_iva: float = 23.0
) -> float | None:
    """
    PT-PT: O valor de uma proposta num criterio, ou None se nao for conhecido.
    EN-UK: A proposal's value on a criterion, or None when unknown.
    """
    if chave == "preco":
        return proposta.total_com_iva(taxa_iva)

    origem = {
        "garantia": proposta.garantia_meses,
        "entrega": proposta.prazo_entrega,
        "pagamento": proposta.prazo_pagamento,
        "validade": proposta.validade,
    }.get(chave)

    if origem is None or not isinstance(origem.valor, (int, float)):
        return None
    return float(origem.valor)


def normalizar(valores: list[float], maior_melhor: bool) -> list[float]:
    """
    PT-PT: Converte uma lista de valores em pontuacoes de 0 a 100.

           Quando todos os valores sao iguais, todos recebem 100. E a resposta
           certa: se as seis propostas dao 24 meses de garantia, a garantia nao
           distingue nenhuma e nao deve penalizar ninguem. Dar zero a todos —
           que e o que uma divisao pela amplitude nula produziria — anulava o
           criterio de forma silenciosa e deslocava o peso para os outros sem
           ninguem perceber.

    EN-UK: Converts a list of values into 0-100 scores. When every value is
           equal, all get 100. That is the right answer: if all six quotes give
           24 months, warranty distinguishes none of them and should penalise
           nobody.
    """
    if not valores:
        return []

    menor = min(valores)
    maior = max(valores)
    amplitude = maior - menor

    if amplitude == 0:
        return [100.0] * len(valores)

    if maior_melhor:
        return [(v - menor) / amplitude * 100 for v in valores]
    return [(maior - v) / amplitude * 100 for v in valores]


def comparar(
    propostas: list[Proposta],
    criterios: list[Criterio] | None = None,
    taxa_iva: float = 23.0,
    avisos: list[str] | None = None,
    penalizar_em_falta: float = 0.0,
) -> Comparacao:
    """
    PT-PT: Pontua e ordena as propostas.

    EN-UK: Scores and ranks the proposals.

    :param criterios:
        PT-PT: Criterios e pesos. Omitido usa os valores por omissao.
        EN-UK: Criteria and weights. Omitted uses the defaults.
    :param taxa_iva:
        PT-PT: Taxa a aplicar as propostas que nao declaram IVA.
        EN-UK: Rate applied to proposals that do not state VAT.
    :param penalizar_em_falta:
        PT-PT: De 0 a 1, quanto penalizar quem tem criterios em falta.

               Existe porque a redistribuicao de peso tem um efeito perverso
               conhecido: uma proposta que so declara os criterios onde e forte
               e comparada apenas nesses e pode ganhar a outra que declarou
               tudo e perdeu num deles. Nao ha resposta universalmente certa —
               por vezes o fornecedor simplesmente nao escreveu, por vezes
               omitiu de proposito. Em 0, a pontuacao ignora a omissao e o
               relatorio limita-se a assinala-la; em 1, a pontuacao e reduzida
               na proporcao dos criterios em falta.

        EN-UK: From 0 to 1, how much to penalise missing criteria. It exists
               because weight redistribution has a known perverse effect: a
               proposal declaring only the criteria it is strong on is compared
               only on those and can beat one that declared everything and lost
               on one of them. There is no universally right answer.
    """
    criterios = list(criterios or CRITERIOS_OMISSAO)
    avisos = list(avisos or [])
    penalizar_em_falta = max(0.0, min(float(penalizar_em_falta), 1.0))

    criterios = [c for c in criterios if c.peso > 0]
    if not criterios:
        return Comparacao(
            pontuacoes=[],
            criterios=[],
            avisos=["Nenhum critério com peso maior do que zero."],
            taxa_iva_omissao=taxa_iva,
        )

    utilizaveis = [p for p in propostas if p.documento.ok]
    descartadas = [p for p in propostas if not p.documento.ok]

    for proposta in descartadas:
        avisos.append(
            f"«{proposta.documento.nome}» ficou de fora: "
            f"{proposta.documento.erro or 'sem texto legível'}."
        )

    # PT-PT: Documentos que nao tem valor nenhum em criterio nenhum nao sao
    #        propostas — sao o formulario, a especificacao tecnica ou o email
    #        que estavam na mesma pasta. Pontua-los a zero enchia a tabela de
    #        linhas vazias e, pior, arrastava a normalizacao: um documento sem
    #        preco nao afecta a escala, mas um com um numero mal lido afecta, e
    #        a distincao nao e obvia a olhar para a tabela. Ficam de fora com
    #        uma linha a dizer porque.
    # EN-UK: Documents with no value on any criterion are not proposals — they
    #        are the form, the technical spec or the email that happened to be
    #        in the same folder. Scoring them zero filled the table with empty
    #        rows and, worse, dragged the normalisation.
    sem_dados = [
        p
        for p in utilizaveis
        if all(valor_do_criterio(p, c.chave, taxa_iva) is None for c in criterios)
    ]
    if sem_dados:
        utilizaveis = [p for p in utilizaveis if p not in sem_dados]
        avisos.append(
            "Ficaram de fora por não terem nenhum valor nem condição comercial "
            "identificável — provavelmente não são propostas: "
            + ", ".join(p.documento.nome for p in sem_dados)
            + "."
        )

    if not utilizaveis:
        return Comparacao(
            pontuacoes=[], criterios=criterios, avisos=avisos, taxa_iva_omissao=taxa_iva
        )

    pontuacoes = [Pontuacao(proposta=p) for p in utilizaveis]

    # PT-PT: Uma passagem por criterio: recolhe os valores conhecidos,
    #        normaliza-os entre si e distribui as pontuacoes.
    # EN-UK: One pass per criterion: gather the known values, normalise them
    #        against each other and hand out the scores.
    for criterio in criterios:
        valores = [
            valor_do_criterio(p.proposta, criterio.chave, taxa_iva) for p in pontuacoes
        ]
        conhecidos = [v for v in valores if v is not None]

        for pontuacao, valor in zip(pontuacoes, valores, strict=True):
            pontuacao.valores[criterio.chave] = valor
            if valor is None:
                pontuacao.em_falta.append(criterio.etiqueta)

        if not conhecidos:
            avisos.append(
                f"Nenhuma proposta declara «{criterio.etiqueta}»; "
                "o critério não foi usado."
            )
            continue

        escala = normalizar(conhecidos, criterio.maior_melhor)
        mapa = dict(zip(conhecidos, escala, strict=True))

        for pontuacao, valor in zip(pontuacoes, valores, strict=True):
            if valor is not None:
                pontuacao.por_criterio[criterio.chave] = mapa[valor]

    # PT-PT: O total e a media pesada apenas sobre os criterios em que a
    #        proposta tem valor. E aqui que o peso dos criterios em falta e
    #        redistribuido, sem precisar de codigo especial: o divisor e a soma
    #        dos pesos usados, nao a soma de todos.
    # EN-UK: The total is the weighted mean over only the criteria the proposal
    #        has a value for. This is where the missing criteria's weight is
    #        redistributed, with no special-case code: the divisor is the sum of
    #        the weights used, not of all weights.
    for pontuacao in pontuacoes:
        soma = 0.0
        peso_usado = 0.0
        peso_total = 0.0
        for criterio in criterios:
            peso_total += criterio.peso
            if criterio.chave in pontuacao.por_criterio:
                soma += pontuacao.por_criterio[criterio.chave] * criterio.peso
                peso_usado += criterio.peso
        pontuacao.total = soma / peso_usado if peso_usado else 0.0

        if penalizar_em_falta and peso_total:
            cobertura = peso_usado / peso_total
            pontuacao.total *= (1 - penalizar_em_falta) + penalizar_em_falta * cobertura

    if penalizar_em_falta:
        avisos.append(
            f"As propostas com critérios em falta foram penalizadas a "
            f"{penalizar_em_falta * 100:.0f}% da proporção em falta."
        )

    ordem = sorted(pontuacoes, key=lambda p: -p.total)

    if len(ordem) >= 2 and (ordem[0].total - ordem[1].total) < 5.0:
        avisos.append(
            f"«{ordem[0].proposta.rotulo}» e «{ordem[1].proposta.rotulo}» estão "
            f"separadas por {ordem[0].total - ordem[1].total:.1f} pontos. "
            "É menos do que a margem de erro da extracção automática — não há "
            "vencedor claro e a decisão deve ser tomada com os critérios que "
            "esta análise não mede."
        )

    incompletas = [p for p in ordem if p.completude < 60]
    if incompletas:
        avisos.append(
            "Com muitos dados em falta: "
            + ", ".join(f"{p.proposta.rotulo} ({p.completude:.0f}%)" for p in incompletas)
            + ". A pontuação destas propostas assenta em poucos critérios."
        )

    if ordem and ordem[0].em_falta:
        avisos.append(
            f"A proposta mais bem pontuada não declara: "
            f"{', '.join(ordem[0].em_falta)}. Vale a pena pedir esses dados antes "
            "de adjudicar."
        )

    return Comparacao(
        pontuacoes=pontuacoes,
        criterios=criterios,
        avisos=avisos,
        taxa_iva_omissao=taxa_iva,
    )


def poupanca(comparacao: Comparacao) -> tuple[float, str, str] | None:
    """
    PT-PT: Diferenca de preco entre a mais barata e a mais cara.

           E o numero que se leva a reuniao. A pontuacao explica a escolha; a
           poupanca explica-a a quem so vai olhar para uma linha.

    EN-UK: The price gap between cheapest and dearest. It is the figure taken
           to the meeting: the score explains the choice, the saving explains it
           to whoever will only read one line.
    """
    precos = [
        (p.valores.get("preco"), p.proposta.rotulo)
        for p in comparacao.pontuacoes
        if p.valores.get("preco") is not None
    ]
    if len(precos) < 2:
        return None

    precos.sort(key=lambda item: item[0])  # type: ignore[arg-type,return-value]
    barata, cara = precos[0], precos[-1]
    return float(cara[0]) - float(barata[0]), barata[1], cara[1]  # type: ignore[arg-type]
