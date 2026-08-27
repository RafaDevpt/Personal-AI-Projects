# -*- coding: utf-8 -*-
"""
PT-PT: Analise assistida por modelo — opcional.

       Tudo o que a aplicacao faz funciona sem este modulo. Ele existe para a
       parte que as expressoes regulares nao alcancam: perceber que uma
       clausula de penalizacao numa proposta e uma condicao de rescisao noutra
       dizem a mesma coisa por palavras diferentes, ou explicar em prosa o que
       distingue duas propostas.

       Tres decisoes de desenho, todas pela mesma razao — os documentos que
       passam por aqui sao propostas comerciais e relatorios internos.

       Primeiro, e desligado por omissao. Ligar tem de ser um acto consciente,
       porque ligar significa enviar o texto do documento para fora da
       empresa.

       Segundo, avisa sempre antes de enviar, dizendo quantos documentos e
       quantos caracteres vao sair da maquina.

       Terceiro, o que volta e sempre identificado como vindo do modelo. Num
       relatorio que vai servir para justificar uma adjudicacao, a diferenca
       entre «o documento diz» e «o modelo interpretou» tem de estar visivel.

       O `anthropic` nao esta nas dependencias obrigatorias. Quem nao o
       instalar tem a aplicacao inteira menos esta funcao.

EN-UK: Model-assisted analysis — optional.

       Everything the application does works without this module. It exists for
       the part regular expressions cannot reach: noticing that a penalty
       clause in one quote and a termination condition in another say the same
       thing in different words.

       Three design decisions, all for the same reason — the documents passing
       through here are commercial quotes and internal reports. It is off by
       default; it always warns before sending, saying how many documents and
       characters will leave the machine; and whatever comes back is always
       labelled as coming from the model.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
import os

log = logging.getLogger(__name__)

# PT-PT: Tecto de caracteres por documento. Serve para dois fins: nao enviar um
#        relatorio de 200 paginas inteiro sem o utilizador contar com isso, e
#        nao gastar contexto com anexos que nao mudam a analise.
# EN-UK: Character ceiling per document. Two purposes: not sending a 200-page
#        report in full without the user expecting it, and not spending context
#        on appendices that do not change the analysis.
MAX_CARACTERES_POR_DOCUMENTO = 12_000

MODELOS: tuple[str, ...] = (
    "claude-sonnet-4-6",
    "claude-opus-4-5",
    "claude-haiku-4-5",
)


class IANaoDisponivel(RuntimeError):
    """PT-PT: A analise assistida nao pode correr. / EN-UK: Assisted analysis cannot run."""


def biblioteca_instalada() -> bool:
    """PT-PT: O pacote `anthropic` esta instalado? / EN-UK: Is `anthropic` installed?"""
    try:
        import anthropic  # noqa: F401

        return True
    except ImportError:
        return False


def chave_do_ambiente() -> str:
    """
    PT-PT: Chave da variavel de ambiente, se existir.
    EN-UK: Key from the environment variable, if present.
    """
    return os.environ.get("ANTHROPIC_API_KEY", "").strip()


def disponivel(chave: str = "") -> tuple[bool, str]:
    """
    PT-PT: A analise assistida pode correr?

    EN-UK: Can assisted analysis run?

    :return:
        PT-PT: (pode, motivo). O motivo diz o que fazer, nao so o que falta.
        EN-UK: (can, reason). The reason says what to do, not merely what is
               missing.
    """
    if not biblioteca_instalada():
        return False, (
            "A biblioteca 'anthropic' não está instalada. "
            "Instale com: pip install anthropic"
        )
    if not (chave or chave_do_ambiente()):
        return False, (
            "Falta a chave da API. Defina a variável de ambiente "
            "ANTHROPIC_API_KEY ou escreva-a nas Definições — nesse caso fica "
            "só em memória durante esta sessão."
        )
    return True, ""


def resumo_do_envio(textos: list[tuple[str, str]]) -> str:
    """
    PT-PT: Descreve o que vai ser enviado, para a confirmacao do utilizador.

           E o texto da caixa de dialogo. Diz o numero de documentos, o total
           de caracteres e os nomes, para a decisao ser tomada com os factos e
           nao com um «Continuar?» generico.

    EN-UK: Describes what is about to be sent, for the user's confirmation. It
           is the dialogue text: number of documents, total characters and the
           names, so the decision is taken on the facts rather than on a
           generic "Continue?".
    """
    total = sum(min(len(t), MAX_CARACTERES_POR_DOCUMENTO) for _, t in textos)
    nomes = ", ".join(nome for nome, _ in textos[:6])
    if len(textos) > 6:
        nomes += f" e mais {len(textos) - 6}"

    return (
        f"Vão ser enviados {len(textos)} documento(s) — cerca de {total:,} "
        f"caracteres — para a API da Anthropic.\n\n{nomes}\n\n"
        "O conteúdo sai desta máquina. Se as propostas tiverem preços, "
        "contactos ou condições comerciais que não devam sair da empresa, "
        "cancele e use apenas a análise local, que faz tudo o resto."
    ).replace(",", ".")


def _cortar(texto: str) -> str:
    """PT-PT: Limita o texto ao tecto. / EN-UK: Caps the text at the ceiling."""
    if len(texto) <= MAX_CARACTERES_POR_DOCUMENTO:
        return texto
    return (
        texto[:MAX_CARACTERES_POR_DOCUMENTO]
        + "\n\n[…texto truncado para envio…]"
    )


def _pedir(prompt: str, sistema: str, chave: str, modelo: str, max_tokens: int = 2000) -> str:
    """
    PT-PT: Faz o pedido e devolve o texto.
    EN-UK: Makes the request and returns the text.
    """
    pode, motivo = disponivel(chave)
    if not pode:
        raise IANaoDisponivel(motivo)

    import anthropic

    cliente = anthropic.Anthropic(api_key=chave or chave_do_ambiente())

    try:
        resposta = cliente.messages.create(
            model=modelo,
            max_tokens=max_tokens,
            system=sistema,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as exc:  # noqa: BLE001 — a biblioteca tem a sua própria árvore
        log.error("Pedido à API falhou: %s", exc)
        raise IANaoDisponivel(f"O pedido falhou: {exc}") from exc

    partes = [
        bloco.text for bloco in resposta.content if getattr(bloco, "type", "") == "text"
    ]
    return "\n".join(partes).strip()


SISTEMA_COMPARACAO = (
    "És um analista de compras a apoiar um departamento de IT em Portugal. "
    "Escreves em português europeu, de forma directa e sem floreados. "
    "Analisas propostas comerciais e apontas o que distingue umas das outras — "
    "âmbito, condições, riscos e omissões — em vez de repetir os números que já "
    "estão na tabela. "
    "Quando um documento não diz alguma coisa, dizes que não diz; nunca preenches "
    "lacunas com suposições. "
    "Terminas sempre com o que deve ser perguntado a cada fornecedor antes de decidir."
)

SISTEMA_RESUMO = (
    "És um assistente que resume documentos para um gestor de IT em Portugal. "
    "Escreves em português europeu, de forma directa. "
    "Resumes o que o documento diz, sem acrescentar contexto que ele não tenha. "
    "Destacas compromissos, prazos, valores e responsabilidades. "
    "Se algo estiver ambíguo no original, dizes que está ambíguo."
)


def comparar_com_ia(
    textos: list[tuple[str, str]], chave: str = "", modelo: str = "claude-sonnet-4-6"
) -> str:
    """
    PT-PT: Analise qualitativa de varias propostas.

    EN-UK: Qualitative analysis of several proposals.

    :param textos: PT-PT: Lista de (nome, texto). / EN-UK: List of (name, text).
    """
    if not textos:
        return ""

    blocos = "\n\n".join(
        f"<documento nome=\"{nome}\">\n{_cortar(texto)}\n</documento>"
        for nome, texto in textos
    )

    prompt = (
        f"Seguem {len(textos)} propostas comerciais para o mesmo fornecimento.\n\n"
        f"{blocos}\n\n"
        "Analisa e responde com estas secções:\n\n"
        "**Diferenças de âmbito** — o que uma inclui e as outras não. É aqui que "
        "está a maior parte das comparações injustas.\n"
        "**Condições e riscos** — pagamento, garantia, penalizações, exclusões, "
        "letra pequena que mude o valor real.\n"
        "**Omissões** — o que falta em cada uma.\n"
        "**Perguntas a fazer** — uma lista por fornecedor, do que perguntar antes "
        "de adjudicar.\n\n"
        "Não repitas a tabela de preços: isso já está calculado. "
        "Não declares um vencedor — a decisão é de quem compra."
    )

    return _pedir(prompt, SISTEMA_COMPARACAO, chave, modelo, max_tokens=3000)


def resumir_com_ia(
    nome: str, texto: str, chave: str = "", modelo: str = "claude-sonnet-4-6"
) -> str:
    """
    PT-PT: Resumo em prosa de um documento.
    EN-UK: A prose summary of one document.
    """
    prompt = (
        f"Resume este documento chamado «{nome}».\n\n"
        f"<documento>\n{_cortar(texto)}\n</documento>\n\n"
        "Responde com:\n\n"
        "**Do que trata** — dois ou três parágrafos.\n"
        "**Pontos principais** — lista curta.\n"
        "**Números e prazos** — o que estiver comprometido no documento.\n"
        "**A confirmar** — o que ficou ambíguo ou por dizer."
    )

    return _pedir(prompt, SISTEMA_RESUMO, chave, modelo, max_tokens=2000)
